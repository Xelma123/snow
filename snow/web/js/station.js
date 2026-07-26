import { createApi } from "./api.js";
import { createVoice } from "./voice.js";

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
    return localStorage.getItem("snow_session") || "";
  },
  set session(v) {
    if (v) localStorage.setItem("snow_session", v);
    else localStorage.removeItem("snow_session");
  },
};

const api = createApi(
  () => store.server,
  () => store.token
);

let lastSnap = null;
let busy = false;

function setBusy(on, label = "Bekleniyor…") {
  busy = on;
  document.body.classList.toggle("is-busy", on);
  const busyLed = $("ledBusy");
  if (busyLed) {
    busyLed.classList.remove("on", "off", "warn");
    busyLed.classList.add(on ? "warn" : "off");
  }
  const cmd = $("cmd");
  const go = $("btnGo");
  const mic = $("btnMic");
  const power = $("btnPower");
  const slider = $("briSlider");
  if (cmd) {
    cmd.disabled = on;
    cmd.placeholder = on ? label : "Komut yaz… (ışığı aç ve tv kapat)";
  }
  if (go) {
    go.disabled = on;
    go.textContent = on ? "…" : "Çalıştır";
  }
  if (mic) mic.disabled = on;
  if (power) power.disabled = on;
  if (slider) slider.disabled = on;
  document.querySelectorAll("[data-cmd], .quick button, .scene-row button").forEach((b) => {
    b.disabled = on;
  });
  if (on) {
    try {
      voice?.stop?.();
    } catch {
      /* ignore */
    }
    mic?.classList.remove("listening");
  }
}

function setLed(id, mode) {
  const el = $(id);
  if (!el) return;
  el.classList.remove("on", "off", "warn");
  el.classList.add(mode);
}

function logFeed(text, kind = "ok") {
  const ul = $("feed");
  const li = document.createElement("li");
  li.className = kind;
  const t = new Date().toLocaleTimeString("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  li.innerHTML = `<span class="t">${t}</span>${text}`;
  ul.prepend(li);
  while (ul.children.length > 40) ul.lastChild.remove();
}

function stateTr(st) {
  const s = (st || "").toLowerCase();
  return (
    {
      on: "Açık",
      off: "Kapalı",
      playing: "Oynatılıyor",
      paused: "Duraklatıldı",
      idle: "Boşta",
      standby: "Beklemede",
      unavailable: "Ulaşılamıyor",
    }[s] || st || "—"
  );
}

function applySnap(snap) {
  if (!snap) return;
  lastSnap = snap;
  const name = snap.friendly_name || "Salon ışığı";
  $("lightName").textContent = name;
  const on = snap.state === "on";
  $("btnPower").classList.toggle("is-off", !on);
  $("btnPower").classList.toggle("on", on);
  $("powerState").textContent = on ? "Açık" : "Kapalı";
  const pill = $("lightStatusPill");
  if (pill) {
    const pct = snap.brightness_pct;
    pill.textContent = on
      ? pct != null
        ? `Açık · yüzde ${pct}`
        : "Açık"
      : "Kapalı";
    pill.classList.toggle("is-off", !on);
  }
  const pct = snap.brightness_pct;
  if (pct != null) {
    $("briVal").textContent = `%${pct}`;
    $("briSlider").value = String(pct);
  } else {
    $("briVal").textContent = on ? "—" : "0";
  }
}

async function refreshStatus() {
  try {
    const h = await api.health(true);
    setLed("ledAi", h.openrouter_configured ? "on" : "warn");
    const haOk = h.deep?.home_assistant?.ok;
    setLed("ledHa", haOk ? "on" : h.ha_token_configured ? "warn" : "off");
    setLed("ledBusy", "off");
  } catch {
    setLed("ledHa", "off");
    setLed("ledAi", "off");
    setLed("ledBusy", "off");
  }
}

async function refreshHome() {
  try {
    const s = await api.summary();
    if (s.default_light) applySnap(s.default_light);
    $("homeMain").textContent = `${s.counts?.lights ?? 0} ışık`;
    $("homeSub").textContent = `${s.counts?.switches ?? 0} priz · ${s.counts?.media_players ?? 0} TV/medya · ${s.counts?.scenes ?? 0} sahne`;
    if (s.default_tv) {
      $("tvMain").textContent = s.default_tv.friendly_name || "Televizyon";
      const st = stateTr(s.default_tv.state);
      $("tvSub").textContent = s.default_tv.media_title
        ? `${st} · ${s.default_tv.media_title}`
        : st;
    } else if ((s.counts?.media_players || 0) === 0) {
      $("tvMain").textContent = "Yok";
      $("tvSub").textContent = "Home Assistant’ta TV bulunamadı";
    } else {
      $("tvMain").textContent = `${s.counts.media_players} medya`;
      $("tvSub").textContent = "Varsayılan TV ayarını kontrol et";
    }

    const row = $("sceneRow");
    row.innerHTML = "";
    if (s.scenes?.length) {
      s.scenes.slice(0, 10).forEach((sc) => {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = sc.name;
        b.onclick = () => runCmd(`${sc.name} sahnesini aç`);
        row.appendChild(b);
      });
    } else {
      row.innerHTML = '<span class="muted">Sahne yok</span>';
    }
  } catch (e) {
    $("homeMain").textContent = "Hata";
    $("homeSub").textContent = e.message;
    logFeed(e.message, "bad");
  }
}

async function runCmd(text) {
  if (busy) return;
  const msg = (text || $("cmd").value || "").trim();
  if (!msg) return;
  if (!store.token) {
    showGate(true);
    return;
  }
  $("cmd").value = "";
  setBusy(true, "Cevap bekleniyor…");
  logFeed(`→ ${msg}`, "ok");
  logFeed("Snow çalışıyor…", "wait");
  try {
    const res = await api.chat(msg, store.session || null);
    if (res.session_id) store.session = res.session_id;
    // remove trailing "çalışıyor" line if still top wait
    const top = $("feed").firstElementChild;
    if (top && top.classList.contains("wait")) top.remove();
    const kind = res.error && !res.actions?.length ? "bad" : "ok";
    logFeed(res.reply || "OK", kind);
    if (res.path && document.body.classList.contains("debug")) {
      const pb = $("pathBadge");
      if (pb) pb.textContent = `debug: ${res.path}${res.model ? " · " + res.model : ""}`;
    }
    if (res.home_snapshot) applySnap(res.home_snapshot);
    else refreshHome();
    refreshJobs();
  } catch (e) {
    const top = $("feed").firstElementChild;
    if (top && top.classList.contains("wait")) top.remove();
    let m = e.message || String(e);
    if (/401|403|token/i.test(m)) m = "Token hatalı — ayarlardan SNOW_APP_TOKEN kontrol et.";
    if (/timeout|zaman aşımı|abort/i.test(m)) m = "Zaman aşımı — AI veya ağ yavaş; tekrar dene.";
    if (/fetch|network|Failed to fetch/i.test(m)) m = "Sunucuya ulaşılamıyor — Wi‑Fi ve 8787 açık mı?";
    logFeed(m, "bad");
  } finally {
    setBusy(false);
  }
}

async function refreshJobs() {
  if (!store.token) return;
  const ul = $("jobsList");
  if (!ul) return;
  try {
    const data = await api.jobs();
    const jobs = data.jobs || [];
    ul.innerHTML = "";
    if (!jobs.length) {
      ul.innerHTML = '<li class="muted">Bekleyen iş yok</li>';
      return;
    }
    jobs.forEach((j) => {
      const li = document.createElement("li");
      li.className = "ok";
      const mins = Math.ceil((j.in_seconds || 0) / 60);
      li.innerHTML = `<span class="t">#${j.id}</span>${j.label} · ~${mins} dk`;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "jobs-cancel";
      btn.textContent = "iptal";
      btn.onclick = async () => {
        try {
          await api.cancelJob(j.id);
          logFeed(`İş #${j.id} iptal`, "ok");
          refreshJobs();
        } catch (e) {
          logFeed(e.message, "bad");
        }
      };
      li.appendChild(btn);
      ul.appendChild(li);
    });
  } catch (e) {
    ul.innerHTML = `<li class="bad">${e.message}</li>`;
  }
}

async function refreshPc() {
  const main = $("pcMain");
  const sub = $("pcSub");
  const pill = $("pcStatusPill");
  const wake = $("btnPcWake");
  if (!main || !store.token) return;
  try {
    const res = await api.chat("Bilgisayar açık mı", store.session || null);
    if (res.session_id) store.session = res.session_id;
    const reply = (res.reply || "").toLowerCase();
    const open =
      reply.includes("açık") ||
      reply.includes("ajan hazır") ||
      reply.includes("ağda görünüyor");
    const closed =
      reply.includes("kapalı") ||
      reply.includes("uykuda") ||
      reply.includes("yapamadım");
    main.textContent = "MSI";
    if (open && !closed) {
      sub.textContent = res.reply || "Açık";
      if (pill) {
        pill.textContent = "Açık";
        pill.classList.remove("is-off");
      }
      if (wake) {
        wake.classList.add("on");
        wake.classList.remove("is-off");
      }
    } else {
      sub.textContent = res.reply || "Kapalı / bilinmiyor";
      if (pill) {
        pill.textContent = closed ? "Kapalı" : "—";
        pill.classList.add("is-off");
      }
      if (wake) {
        wake.classList.add("is-off");
        wake.classList.remove("on");
      }
    }
  } catch (e) {
    sub.textContent = e.message || "PC durumu alınamadı";
    if (pill) {
      pill.textContent = "Hata";
      pill.classList.add("is-off");
    }
  }
}

async function refreshRoutines() {
  if (!store.token) return;
  const row = $("routineRow");
  if (!row) return;
  try {
    const data = await api.routines();
    const list = data.routines || [];
    row.innerHTML = "";
    if (!list.length) {
      row.innerHTML = '<span class="muted">Rutin yok</span>';
      return;
    }
    list.forEach((r) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = r.title || r.id;
      b.title = r.description || r.id;
      b.onclick = () => runCmd(`${r.title || r.id} rutini`);
      row.appendChild(b);
    });
  } catch (e) {
    row.innerHTML = `<span class="muted">${e.message}</span>`;
  }
}

function showGate(force) {
  const need = force || !store.token;
  $("gate").classList.toggle("hidden", !need);
  $("station").classList.toggle("hidden", need);
  if (need) {
    $("gateToken").value = store.token;
    $("gateServer").value = store.server;
  }
}

async function enter() {
  const token = $("gateToken").value.trim();
  const server = $("gateServer").value.trim() || window.location.origin;
  $("gateErr").textContent = "";
  if (!token) {
    $("gateErr").textContent = "Token gir.";
    return;
  }
  store.token = token;
  store.server = server;
  try {
    await api.health(false);
    showGate(false);
    logFeed("İstasyon bağlandı");
    await refreshStatus();
    await refreshHome();
    await refreshJobs();
    await refreshRoutines();
    await runCmd("Hava nasıl?");
  } catch (e) {
    $("gateErr").textContent = e.message || "Bağlanamadı";
  }
}

// Power toggle
$("btnPower").onclick = () => {
  const on = lastSnap?.state === "on";
  runCmd(on ? "Işığı kapat" : "Işığı aç");
};

const btnPcWake = $("btnPcWake");
if (btnPcWake) {
  btnPcWake.onclick = async () => {
    await runCmd("Bilgisayarı uyandır");
    refreshPc();
  };
}

$("briSlider").addEventListener("change", () => {
  const v = $("briSlider").value;
  runCmd(`Parlaklığı ${v} yap`);
});

// Quick buttons
document.querySelectorAll("[data-cmd]").forEach((b) => {
  b.addEventListener("click", () => runCmd(b.getAttribute("data-cmd")));
});

$("btnGo").onclick = () => runCmd();
$("cmd").addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    if (!busy) runCmd();
  }
});
$("btnRefresh").onclick = () => {
  refreshStatus();
  refreshHome();
  refreshJobs();
  refreshRoutines();
  refreshPc();
};
const btnRj = $("btnRefreshJobs");
if (btnRj) btnRj.onclick = () => refreshJobs();
$("btnClearFeed").onclick = () => {
  $("feed").innerHTML = "";
};
$("gateGo").onclick = enter;
$("btnCfg").onclick = () => {
  $("cfgServer").value = store.server;
  $("cfgToken").value = store.token;
  $("cfg").classList.remove("hidden");
};
$("cfgClose").onclick = () => $("cfg").classList.add("hidden");
$("cfgSave").onclick = () => {
  store.server = $("cfgServer").value.trim() || window.location.origin;
  store.token = $("cfgToken").value.trim();
  $("cfg").classList.add("hidden");
  if (store.token) {
    showGate(false);
    refreshStatus();
    refreshHome();
  } else showGate(true);
};

const voice = createVoice({
  onText: (t) => {
    $("btnMic").classList.remove("listening");
    if (!busy) runCmd(t);
  },
  onError: (m) => {
    $("btnMic").classList.remove("listening");
    logFeed(m, "bad");
  },
});
$("btnMic").onclick = () => {
  if (busy) return;
  if (!voice.supported) {
    logFeed("Ses tanıma yok", "bad");
    return;
  }
  if ($("btnMic").classList.contains("listening")) {
    voice.stop();
    $("btnMic").classList.remove("listening");
    return;
  }
  $("btnMic").classList.add("listening");
  voice.start();
};

// boot
if (new URLSearchParams(location.search).has("debug")) {
  document.body.classList.add("debug");
}
const sh = $("serverHint");
if (sh) {
  try {
    sh.textContent = new URL(store.server).host || "istasyon";
  } catch {
    sh.textContent = "istasyon";
  }
}
showGate();
if (store.token) {
  showGate(false);
  setBusy(false);
  const busyLed = $("ledBusy");
  if (busyLed) {
    busyLed.classList.remove("on", "warn");
    busyLed.classList.add("off");
  }
  refreshStatus();
  refreshHome();
  refreshJobs();
  refreshRoutines();
  refreshPc();
  logFeed("Hazır. Işık, TV, PC, rutin veya yazarak komut ver.");
}
