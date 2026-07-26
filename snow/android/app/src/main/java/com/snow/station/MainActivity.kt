package com.snow.station

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.view.View
import android.webkit.JavascriptInterface
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.ProgressBar
import android.widget.TextView
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.view.WindowCompat
import java.util.Locale
import java.util.UUID

/**
 * Snow Ses — voice-first thin bridge.
 *
 * Quality contract (android-dev hybrid + voice PTT plan):
 * - Loads only {base}/voice (push-to-talk UI on server)
 * - No secrets / OpenRouter / HA tokens in native code
 * - Native TTS (WebView speechSynthesis often silent)
 * - Mic only when WebView asks (user press → STT); no wake-word / continuous listen
 * - onPause cancels in-page STT/TTS (battery)
 * - Cleartext limited via network_security_config + strings URL
 */
class MainActivity : AppCompatActivity(), TextToSpeech.OnInitListener {

    private lateinit var webView: WebView
    private lateinit var progress: ProgressBar
    private lateinit var errorView: TextView
    private var pendingPermissionRequest: PermissionRequest? = null
    private lateinit var voiceUrl: String
    private lateinit var serverBase: String

    private var tts: TextToSpeech? = null
    @Volatile private var ttsReady = false
    private val mainHandler = Handler(Looper.getMainLooper())

    private val micPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            val pending = pendingPermissionRequest
            pendingPermissionRequest = null
            if (granted && pending != null) {
                pending.grant(pending.resources)
            } else {
                pending?.deny()
            }
        }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, true)
        setContentView(R.layout.activity_main)

        ensureMicPermission()
        tts = TextToSpeech(this, this)

        webView = findViewById(R.id.webView)
        progress = findViewById(R.id.progress)
        errorView = findViewById(R.id.errorText)

        serverBase = getString(R.string.snow_default_url).trimEnd('/')
        voiceUrl = "$serverBase/voice"

        webView.setBackgroundColor(Color.parseColor("#0A0A0A"))
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView?,
                request: WebResourceRequest?
            ): Boolean {
                // Keep navigation inside our Snow origin when possible
                val url = request?.url?.toString() ?: return false
                if (url.startsWith(serverBase) || url.startsWith("about:")) {
                    return false
                }
                // Block unexpected external navigations in the shell
                return true
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                progress.visibility = View.GONE
                if (errorView.visibility != View.VISIBLE) {
                    webView.visibility = View.VISIBLE
                }
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                if (request?.isForMainFrame != true) return
                showLoadError()
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                if (newProgress in 1..99) {
                    progress.visibility = View.VISIBLE
                    progress.progress = newProgress
                } else {
                    progress.visibility = View.GONE
                }
            }

            override fun onPermissionRequest(request: PermissionRequest?) {
                if (request == null) return
                val needAudio = request.resources.any {
                    it == PermissionRequest.RESOURCE_AUDIO_CAPTURE
                }
                if (needAudio && !hasMicPermission()) {
                    pendingPermissionRequest = request
                    micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                    return
                }
                // Only grant audio capture resources we understand
                val allowed = request.resources.filter {
                    it == PermissionRequest.RESOURCE_AUDIO_CAPTURE
                }.toTypedArray()
                if (allowed.isNotEmpty()) {
                    request.grant(allowed)
                } else {
                    request.deny()
                }
            }
        }

        configureWebSettings(webView.settings)
        webView.addJavascriptInterface(SnowNativeBridge(), "SnowNative")

        errorView.setOnClickListener { reloadVoice() }

        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    if (webView.canGoBack()) webView.goBack()
                    else finish()
                }
            }
        )

        if (savedInstanceState != null) {
            webView.restoreState(savedInstanceState)
        } else {
            progress.visibility = View.VISIBLE
            webView.loadUrl(voiceUrl)
        }
    }

    private fun configureWebSettings(s: WebSettings) {
        s.javaScriptEnabled = true
        s.domStorageEnabled = true
        s.mediaPlaybackRequiresUserGesture = false
        s.cacheMode = WebSettings.LOAD_DEFAULT
        s.mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
        s.allowFileAccess = false
        s.allowContentAccess = false
        @Suppress("DEPRECATION")
        s.allowFileAccessFromFileURLs = false
        @Suppress("DEPRECATION")
        s.allowUniversalAccessFromFileURLs = false
        s.setSupportZoom(false)
        s.builtInZoomControls = false
        s.displayZoomControls = false
        s.loadsImagesAutomatically = true
        // Geolocation not needed for Snow
        s.setGeolocationEnabled(false)
    }

    private fun showLoadError() {
        progress.visibility = View.GONE
        webView.visibility = View.GONE
        errorView.visibility = View.VISIBLE
        errorView.text =
            "Snow’a ulaşılamadı.\n\n" +
                "• Telefon ev Wi‑Fi’sinde mi?\n" +
                "• Acer’da Snow ayakta mı? (docker compose ps)\n" +
                "• Adres: $serverBase\n\n" +
                "Ekrana dokun → yeniden dene."
    }

    private fun reloadVoice() {
        errorView.visibility = View.GONE
        progress.visibility = View.VISIBLE
        webView.visibility = View.VISIBLE
        webView.loadUrl(voiceUrl)
    }

    override fun onInit(status: Int) {
        if (status != TextToSpeech.SUCCESS) {
            ttsReady = false
            return
        }
        val engine = tts ?: return
        val tr = Locale.forLanguageTag("tr-TR")
        val r = engine.setLanguage(tr)
        if (r == TextToSpeech.LANG_MISSING_DATA || r == TextToSpeech.LANG_NOT_SUPPORTED) {
            engine.language = Locale.getDefault()
        }
        engine.setSpeechRate(1.02f)
        engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {}
            override fun onDone(utteranceId: String?) {
                notifyJsSpeakDone(utteranceId)
            }
            @Deprecated("Deprecated in Java")
            override fun onError(utteranceId: String?) {
                notifyJsSpeakDone(utteranceId)
            }
            override fun onError(utteranceId: String?, errorCode: Int) {
                notifyJsSpeakDone(utteranceId)
            }
        })
        ttsReady = true
    }

    private fun notifyJsSpeakDone(utteranceId: String?) {
        val id = utteranceId ?: return
        mainHandler.post {
            if (!::webView.isInitialized) return@post
            val safe = id.replace("\\", "").replace("'", "")
            webView.evaluateJavascript(
                "window.__snowTtsDone && window.__snowTtsDone('$safe');",
                null
            )
        }
    }

    /**
     * JS bridge surface (web/js/tts.js):
     *   SnowNative.isTtsReady()
     *   SnowNative.speak(text, utteranceId)
     *   SnowNative.cancel()
     *   SnowNative.getServerBase()
     */
    private inner class SnowNativeBridge {
        @JavascriptInterface
        fun isTtsReady(): Boolean = ttsReady

        @JavascriptInterface
        fun getServerBase(): String = serverBase

        @JavascriptInterface
        fun speak(text: String?, utteranceId: String?): Boolean {
            val engine = tts ?: return false
            if (!ttsReady) return false
            var body = (text ?: "").trim()
            if (body.isEmpty()) return false
            // Guard: avoid huge payloads freezing TTS
            if (body.length > MAX_TTS_CHARS) {
                body = body.take(MAX_TTS_CHARS - 1) + "…"
            }
            val uid = utteranceId?.ifBlank { null } ?: UUID.randomUUID().toString()
            mainHandler.post {
                try {
                    engine.stop()
                    engine.speak(body, TextToSpeech.QUEUE_FLUSH, null, uid)
                } catch (_: Exception) {
                    notifyJsSpeakDone(uid)
                }
            }
            return true
        }

        @JavascriptInterface
        fun cancel() {
            mainHandler.post {
                try {
                    tts?.stop()
                } catch (_: Exception) {
                    /* ignore */
                }
            }
        }
    }

    private fun hasMicPermission(): Boolean =
        ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED

    private fun ensureMicPermission() {
        if (!hasMicPermission()) {
            micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        if (::webView.isInitialized) {
            webView.saveState(outState)
        }
    }

    override fun onPause() {
        // Battery: stop listening/speaking when app backgrounds (PTT stays off until user returns)
        if (::webView.isInitialized) {
            webView.evaluateJavascript(
                "(function(){try{if(window.__snowCancel)window.__snowCancel();}catch(e){}})();",
                null
            )
            webView.onPause()
        }
        try {
            tts?.stop()
        } catch (_: Exception) {
            /* ignore */
        }
        super.onPause()
    }

    override fun onResume() {
        super.onResume()
        if (::webView.isInitialized) {
            webView.onResume()
        }
        // Do NOT auto-start STT — push-to-talk only (user presses KONUŞ)
    }

    override fun onDestroy() {
        if (::webView.isInitialized) {
            webView.removeJavascriptInterface("SnowNative")
            webView.stopLoading()
            webView.destroy()
        }
        try {
            tts?.stop()
            tts?.shutdown()
        } catch (_: Exception) {
            /* ignore */
        }
        tts = null
        super.onDestroy()
    }

    companion object {
        private const val MAX_TTS_CHARS = 1200
    }
}
