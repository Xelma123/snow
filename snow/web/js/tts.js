/**
 * On-device TTS.
 * Prefer Android native bridge (SnowNative) inside the APK WebView —
 * browser speechSynthesis is often silent there.
 */

function hasNativeTts() {
  try {
    return (
      typeof window.SnowNative !== "undefined" &&
      typeof window.SnowNative.speak === "function"
    );
  } catch {
    return false;
  }
}

export function createTts({ lang = "tr-TR" } = {}) {
  const synth = window.speechSynthesis;
  const native = hasNativeTts();

  if (!native && !synth) {
    return {
      supported: false,
      speaking: false,
      engine: "none",
      speak() {
        return Promise.resolve();
      },
      cancel() {},
    };
  }

  let speaking = false;
  let preferVoice = null;
  let pendingResolve = null;
  let pendingId = null;

  // Native callback from Kotlin UtteranceProgressListener
  window.__snowTtsDone = (id) => {
    if (pendingId && id && id !== pendingId) return;
    speaking = false;
    const r = pendingResolve;
    pendingResolve = null;
    pendingId = null;
    if (r) r();
  };

  function pickVoice() {
    if (!synth) return null;
    if (preferVoice) return preferVoice;
    const voices = synth.getVoices() || [];
    preferVoice =
      voices.find((v) => v.lang && v.lang.toLowerCase().startsWith("tr")) ||
      voices.find((v) => /turkish|türk/i.test(v.name || "")) ||
      voices.find((v) => v.lang && v.lang.toLowerCase().startsWith("en")) ||
      voices[0] ||
      null;
    return preferVoice;
  }

  if (synth) {
    try {
      synth.addEventListener?.("voiceschanged", () => {
        preferVoice = null;
        pickVoice();
      });
    } catch {
      /* ignore */
    }
  }

  function waitVoices(ms = 400) {
    return new Promise((resolve) => {
      if (!synth) return resolve();
      if ((synth.getVoices() || []).length) return resolve();
      const t = setTimeout(resolve, ms);
      const once = () => {
        clearTimeout(t);
        resolve();
      };
      try {
        synth.addEventListener?.("voiceschanged", once, { once: true });
      } catch {
        /* ignore */
      }
    });
  }

  return {
    supported: true,
    engine: native ? "android-native" : "web-speech",
    get speaking() {
      return speaking;
    },
    cancel() {
      try {
        if (native && typeof window.SnowNative.cancel === "function") {
          window.SnowNative.cancel();
        }
      } catch {
        /* ignore */
      }
      try {
        synth?.cancel();
      } catch {
        /* ignore */
      }
      speaking = false;
      const r = pendingResolve;
      pendingResolve = null;
      pendingId = null;
      if (r) r();
    },
    async speak(text) {
      const t = (text || "").trim();
      if (!t) return;

      this.cancel();
      speaking = true;

      // Prefer native TTS in APK
      if (native) {
        const id = `utt-${Date.now()}`;
        pendingId = id;
        return new Promise((resolve) => {
          pendingResolve = resolve;
          let ok = false;
          try {
            ok = window.SnowNative.speak(t, id);
          } catch {
            ok = false;
          }
          if (!ok) {
            // Fallback to web if bridge not ready
            pendingResolve = null;
            pendingId = null;
            speakWeb(t).then(resolve);
            return;
          }
          // Safety timeout (~3 min max speech)
          setTimeout(() => {
            if (pendingId === id) {
              speaking = false;
              pendingId = null;
              const r = pendingResolve;
              pendingResolve = null;
              if (r) r();
            }
          }, 180000);
        });
      }

      return speakWeb(t);
    },
  };

  function speakWeb(t) {
    return waitVoices().then(
      () =>
        new Promise((resolve) => {
          if (!synth) {
            speaking = false;
            resolve();
            return;
          }
          // Chrome bug: cancel then speak needs a tick
          try {
            synth.cancel();
          } catch {
            /* ignore */
          }
          setTimeout(() => {
            const u = new SpeechSynthesisUtterance(t);
            u.lang = lang;
            const v = pickVoice();
            if (v) u.voice = v;
            u.rate = 1.02;
            u.pitch = 1;
            speaking = true;
            u.onend = () => {
              speaking = false;
              resolve();
            };
            u.onerror = () => {
              speaking = false;
              resolve();
            };
            try {
              synth.speak(u);
              // Some Chromium builds pause unless resumed
              setTimeout(() => {
                try {
                  if (synth.paused) synth.resume();
                } catch {
                  /* ignore */
                }
              }, 50);
            } catch {
              speaking = false;
              resolve();
            }
          }, 40);
        })
    );
  }
}
