/**
 * Snow Ses — push-to-talk (tek tur).
 *
 * Kullanıcı ortadaki düğmeye basar → bir kez dinle (1 bip) → sunucuya metin
 * → cevap (TTS) → idle. Otomatik yeniden dinleme YOK.
 */
import { createApi } from "./api.js";
import { createStt } from "./stt.js";
import { createTts } from "./tts.js";

/** Client-side safety net before TTS (server already humanizes). */
function softenForSpeech(text) {
  let t = (text || "").trim();
  if (!t) return "Tamam.";
  t = t.replace(/\b(light|media_player|switch|scene)\.[a-zA-Z0-9_]+\b/g, "");
  t = t.replace(/\boff\b/gi, "kapalı");
  t = t.replace(/\bon\b/gi, "açık");
  t = t.replace(/\bplaying\b/gi, "oynatılıyor");
  t = t.replace(/\bpaused\b/gi, "duraklatıldı");
  t = t.replace(/%\s*(\d+)/g, "yüzde $1");
  t = t.replace(/(\d+)\s*%/g, "yüzde $1");
  t = t.replace(/\s{2,}/g, " ").trim();
  return t || "Tamam.";
}

const $ = (id) => document.getElementById(id);

const store = {
  get server() {
    return (
      localStorage.getItem("snow_server") ||
      window.SNOW_PERSONAL?.serverUrl ||
      window.location.origin
    );
  },
  set server(v) {
    localStorage.setItem("snow_server", v);
  },
  get token() {
    return localStorage.getItem("snow_token") || "";
  },
  set token(v) {
    localStorage.setItem("snow_token", v);
  },
  get session() {
    return localStorage.getItem("snow_voice_session") || "";
  },
  set session(v) {
    if (v) localStorage.setItem("snow_voice_session", v);
    else localStorage.removeItem("snow_voice_session");
  },
  get seenHelp() {
    return localStorage.getItem("snow_voice_help_seen") === "1";
  },
  set seenHelp(v) {
    localStorage.setItem("snow_voice_help_seen", v ? "1" : "0");
  },
};

const api = createApi(
  () => store.server,
  () => store.token
);

const tts = createTts({ lang: "tr-TR" });
const stt = createStt({
  lang: "tr-TR",
  onPartial: (t) => setYou(t, true),
});

/** @type {'idle'|'listening'|'thinking'|'speaking'|'error'} */
let phase = "idle";
/** Cancels in-flight turn when incremented */
let runToken = 0;
let lastOkHealth = false;
let busy = false;

const ORB_LABEL = {
  idle: "KONUŞ",
  listening: "DİNLİYOR",
  thinking: "BEKLE",
  speaking: "KONUŞUYOR",
  error: "TEKRAR",
};

const ORB_ARIA = {
  idle: "Bas ve konuş",
  listening: "Dinleniyor — iptal için bas",
  thinking: "Snow düşünüyor",
  speaking: "Snow konuşuyor — kesmek için bas",
  error: "Tekrar dene",
};

function friendlyError(raw) {
  const s = String(raw || "").trim();
  const low = s.toLowerCase();
  if (!s) return "Bilinmeyen bir hata oluştu.";
  if (/401|403|unauthorized|forbidden|geçersiz token|invalid token/i.test(s)) {
    return "Erişim anahtarı hatalı veya eksik. Ayarlardan token’ı kontrol et.";
  }
  if (/failed to fetch|networkerror|load failed|net::|econnrefused|timeout/i.test(low)) {
    return "Sunucuya ulaşılamıyor. Wi‑Fi aynı mı, Snow açık mı, adres doğru mu bak.";
  }
  if (/cors/i.test(low)) {
    return "Tarayıcı bağlantıyı engelledi. Adresin http:// ile başladığından emin ol.";
  }
  if (/500|internal server/i.test(low)) {
    return "Snow sunucusunda bir hata var. Biraz sonra tekrar dene.";
  }
  if (/rate|429|quota/i.test(low)) {
    return "AI kotası veya hız sınırı. Biraz bekle; ışık/TV için kısa net cümle dene.";
  }
  if (s.length > 160) return s.slice(0, 157) + "…";
  return s;
}

function setBanner(kind, text) {
  const el = $("banner");
  if (!el) return;
  if (!text) {
    el.className = "banner";
    el.textContent = "";
    return;
  }
  el.className = `banner show ${kind || "warn"}`;
  el.textContent = text;
}

function announce(msg) {
  const lr = $("liveRegion");
  if (lr) lr.textContent = msg || "";
}

function shortHost(url) {
  try {
    const u = new URL(url);
    return u.host || url;
  } catch {
    return (url || "").replace(/^https?:\/\//, "").slice(0, 40) || "—";
  }
}

function refreshChrome() {
  const ok = Boolean(store.token);
  $("ledLink")?.classList.toggle("on", ok && lastOkHealth);
  $("ledLink")?.classList.toggle("off", !(ok && lastOkHealth));
  $("ledLink")?.classList.toggle("warn", ok && !lastOkHealth);

  $("ledMic")?.classList.toggle("on", stt.supported);
  $("ledMic")?.classList.toggle("off", !stt.supported);
  $("ledMic")?.classList.toggle("warn", stt.supported === false);

  const label = $("serverLabel");
  if (label) {
    label.textContent = ok
      ? shortHost(store.server)
      : "Bağlı değil — Ayar’dan bağlan";
  }

  $("gate")?.classList.toggle("hidden", ok);

  if (!stt.supported) {
    setBanner(
      "bad",
      "Bu tarayıcı ses tanımayı desteklemiyor. Android’de Chrome veya Snow Ses uygulamasını kullan."
    );
  }
}

function setBusyUi(on) {
  busy = on;
  const start = $("btnStart");
  const stop = $("btnStop");
  if (start) start.disabled = on;
  if (stop) stop.disabled = !on;
}

function setPhase(p, statusText, hintText) {
  phase = p;
  document.body.classList.remove(
    "phase-idle",
    "phase-listening",
    "phase-thinking",
    "phase-speaking",
    "phase-error"
  );
  document.body.classList.add(`phase-${p}`);
  if (statusText != null) $("status").textContent = statusText;
  if (hintText != null) $("hint").textContent = hintText;

  const led = $("ledPhase");
  if (led) {
    led.classList.remove("on", "off", "warn");
    if (p === "listening" || p === "speaking") led.classList.add("on");
    else if (p === "thinking" || p === "error") led.classList.add("warn");
    else led.classList.add("off");
  }

  const orb = $("orb");
  if (orb) {
    const label = ORB_LABEL[p] || "KONUŞ";
    const labelEl = orb.querySelector(".orb-label");
    if (labelEl) labelEl.textContent = label;
    else orb.textContent = label;
    orb.setAttribute("aria-label", ORB_ARIA[p] || "Bas ve konuş");
    // Only block double-start while thinking
    orb.disabled = p === "thinking";
  }

  const ex = $("examples");
  if (ex) ex.hidden = p !== "idle" && p !== "error";

  if (statusText) announce(statusText);
}

function setYou(text, interim = false) {
  const el = $("youText");
  const bubble = $("youBubble");
  if (!el) return;
  const t = (text || "").trim();
  el.textContent = t || (interim ? "Dinleniyor…" : "Henüz bir şey söylemedin");
  bubble?.classList.toggle("empty", !t && !interim);
}

function setSnow(text, meta) {
  const el = $("snowText");
  const bubble = $("snowBubble");
  const m = $("snowMeta");
  if (!el) return;
  const t = (text || "").trim();
  el.textContent = t || "Cevap burada görünecek ve seslenecek";
  bubble?.classList.toggle("empty", !t);
  if (m) {
    if (meta) {
      m.hidden = false;
      m.textContent = meta;
    } else {
      m.hidden = true;
      m.textContent = "";
    }
  }
}

async function wakeAudio() {
  if (tts.engine === "android-native") return;
  try {
    await tts.speak(".");
    tts.cancel();
  } catch {
    /* ignore */
  }
}

function goIdle(status, hint) {
  setBusyUi(false);
  setPhase(
    "idle",
    status || "Hazır",
    hint || "Tekrar konuşmak için büyük düğmeye bas."
  );
}

/** Cancel anything in flight and return to idle. */
function cancelTurn(msg) {
  runToken += 1;
  stt.abort();
  tts.cancel();
  goIdle(msg || "İptal", "İstediğin zaman tekrar bas.");
}

// Android onPause / external cancel hook
window.__snowCancel = () => cancelTurn("Arka plan");

/**
 * One complete turn — no auto re-listen.
 * STT starts only here (user gesture) → one system beep max per press.
 */
async function runOneShot() {
  if (!store.token) {
    openCfg();
    return;
  }
  if (!stt.supported) {
    setPhase(
      "error",
      "Ses tanıma yok",
      "Android Chrome veya Snow Ses uygulamasını kullan."
    );
    setBanner("bad", "Ses tanıma bu ortamda kapalı.");
    return;
  }
  if (phase === "thinking") return;

  // Interrupt speaking / previous
  stt.abort();
  tts.cancel();

  runToken += 1;
  const token = runToken;
  setBusyUi(true);
  setBanner("");

  await wakeAudio();
  if (token !== runToken) return;

  setPhase(
    "listening",
    "Seni dinliyorum…",
    "Konuş, bitince sus. Sunucuya sadece bu tur gider."
  );
  setYou("");

  let heard = "";
  try {
    heard = await stt.start();
  } catch (e) {
    if (token !== runToken) return;
    if (/iptal/i.test(String(e?.message || ""))) {
      goIdle("İptal", "Tekrar basarak konuşabilirsin.");
      return;
    }
    setPhase("error", "Seni duyamadım", friendlyError(e?.message || e));
    setBusyUi(false);
    return;
  }

  if (token !== runToken) return;
  setYou(heard);
  // Immediate UX feedback before network (latency budget)
  setPhase(
    "thinking",
    "Gönderiliyor…",
    "Metin sunucuya iletildi, Snow düşünüyor."
  );

  let reply = "";
  let meta = "";
  try {
    const res = await api.chat(heard, store.session || null);
    if (token !== runToken) return;
    if (res.session_id) store.session = res.session_id;
    reply = (res.reply || "").trim() || "Tamam.";
    if (res.error && !res.reply) reply = friendlyError(res.error);
    const bits = [];
    if (res.path) bits.push(`yol: ${res.path}`);
    if (res.fallback) bits.push("çevrimdışı kural");
    if (res.actions?.length) bits.push(`${res.actions.length} işlem`);
    meta = bits.join(" · ");
    lastOkHealth = true;
    refreshChrome();
  } catch (e) {
    if (token !== runToken) return;
    lastOkHealth = false;
    refreshChrome();
    const msg = friendlyError(e?.message || e);
    setPhase("error", "Bağlantı sorunu", msg);
    setSnow(msg);
    setBusyUi(false);
    return;
  }

  if (token !== runToken) return;
  const spoken = softenForSpeech(reply);
  setSnow(spoken, meta && document.body.classList.contains("debug") ? meta : "");
  setPhase(
    "speaking",
    "Snow konuşuyor…",
    "Bitince durur. Yeni komut için tekrar bas."
  );
  await tts.speak(spoken);

  if (token !== runToken) return;
  goIdle("Tamam", "Yeni bir şey söylemek için büyük düğmeye bas.");
}

function openCfg() {
  $("cfgServer").value = store.server;
  $("cfgToken").value = store.token;
  $("testResult").textContent = "";
  $("testResult").className = "test-result";
  $("cfg").classList.remove("hidden");
  setTimeout(() => $("cfgServer")?.focus(), 50);
}

function closeCfg() {
  $("cfg").classList.add("hidden");
}

function openHelp() {
  $("help").classList.remove("hidden");
}

function closeHelp() {
  $("help").classList.add("hidden");
  store.seenHelp = true;
}

async function testConnection() {
  const result = $("testResult");
  const server = ($("cfgServer").value || "").trim() || window.location.origin;
  const token = ($("cfgToken").value || "").trim();
  result.className = "test-result";
  result.textContent = "Deneniyor…";

  if (!token) {
    result.className = "test-result err";
    result.textContent = "Önce erişim anahtarını yaz.";
    return false;
  }

  try {
    const probe = createApi(
      () => server,
      () => token
    );
    const h = await probe.health(true);
    const base = server.replace(/\/$/, "");
    const r = await fetch(`${base}/api/v1/home/summary`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (r.status === 401 || r.status === 403) {
      throw new Error("Erişim anahtarı hatalı veya eksik.");
    }
    if (r.status === 404) {
      throw new Error("Bu adres Snow gibi görünmüyor (404). Port 8787 mi?");
    }
    if (!r.ok && r.status !== 502) {
      const data = await r.json().catch(() => ({}));
      throw new Error(data.detail || data.error || `HTTP ${r.status}`);
    }
    lastOkHealth = true;
    result.className = "test-result ok";
    const haOk =
      h?.deep?.home_assistant?.ok === true || (r.ok && r.status === 200);
    let extra = "Bağlantı ve anahtar tamam.";
    if (h?.version) extra += ` Snow ${h.version}.`;
    if (h?.model) extra += ` Model: ${h.model}.`;
    if (haOk) extra += " Ev paneli (HA) yanıt veriyor.";
    else extra += " Uyarı: HA şu an zayıf/kapalı (ışık-TV etkilenebilir).";
    if (h?.token_is_default) extra += " Güvenlik: varsayılan token’ı değiştir.";
    result.textContent = extra;
    return true;
  } catch (e) {
    lastOkHealth = false;
    result.className = "test-result err";
    result.textContent = friendlyError(e?.message || e);
    return false;
  }
}

function saveCfg() {
  store.server = ($("cfgServer").value || "").trim() || window.location.origin;
  store.token = ($("cfgToken").value || "").trim();
  closeCfg();
  refreshChrome();
  if (store.token) {
    goIdle("Ayarlar kaydedildi", "Konuşmak için büyük düğmeye bas.");
    setBanner("good", "Bağlantı bilgileri telefonda saklandı.");
    setTimeout(() => setBanner(""), 3500);
    if (!store.seenHelp) openHelp();
  } else {
    setPhase("idle", "Anahtar gerekli", "Ayarlardan erişim anahtarını gir.");
  }
}

// ——— wire ———
$("orb").onclick = () => {
  if (phase === "idle" || phase === "error") {
    runOneShot();
    return;
  }
  if (phase === "listening" || phase === "speaking" || phase === "thinking") {
    cancelTurn("Durduruldu");
  }
};

$("btnStart").onclick = () => {
  if (phase === "idle" || phase === "error") runOneShot();
};
$("btnStop").onclick = () => cancelTurn("Durduruldu");
$("btnCfg").onclick = () => openCfg();
$("btnHelp").onclick = () => openHelp();
$("cfgClose").onclick = () => closeCfg();
$("cfgSave").onclick = () => saveCfg();
$("cfgTest").onclick = () => testConnection();
$("btnGate").onclick = () => openCfg();
$("helpClose").onclick = () => closeHelp();

$("btnToggleToken").onclick = () => {
  const inp = $("cfgToken");
  const btn = $("btnToggleToken");
  if (!inp || !btn) return;
  const show = inp.type === "password";
  inp.type = show ? "text" : "password";
  btn.textContent = show ? "Gizle" : "Göster";
};

$("btnNewSession").onclick = () => {
  store.session = "";
  setSnow("");
  setYou("");
  cancelTurn("Yeni sohbet");
  setBanner("good", "Sohbet bellekten sıfırlandı.");
  setTimeout(() => setBanner(""), 3000);
};

$("cfg")?.addEventListener("click", (e) => {
  if (e.target === $("cfg")) closeCfg();
});
$("help")?.addEventListener("click", (e) => {
  if (e.target === $("help")) closeHelp();
});

// boot — no mic until user presses
refreshChrome();
setBusyUi(false);
if (store.token) {
  goIdle(
    "Merhaba",
    "Büyük düğmeye bas → konuş → cevap. Sonraki tur için yine bas (otomatik dinleme yok)."
  );
  api
    .health(false)
    .then((h) => {
      lastOkHealth = true;
      refreshChrome();
      if (h?.model) {
        /* optional soft note */
      }
    })
    .catch(() => {
      lastOkHealth = false;
      refreshChrome();
      setBanner(
        "warn",
        "Sunucuya şu an ulaşılamıyor. Wi‑Fi ve adresi kontrol et; Ayar → Bağlantıyı dene."
      );
    });
} else {
  setPhase("idle", "Hoş geldin", "Önce bir kez bağlantı ayarla.");
  $("gate")?.classList.remove("hidden");
}
