/**
 * On-device speech-to-text (Web Speech API).
 * Audio stays on the device — never uploaded to Snow.
 */

export function createStt({ lang = "tr-TR", onPartial } = {}) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    return {
      supported: false,
      listening: false,
      start() {
        return Promise.reject(new Error("Bu tarayıcı ses tanımayı desteklemiyor. Chrome kullan."));
      },
      stop() {},
      abort() {},
    };
  }

  let rec = null;
  let listening = false;
  let resolveFinal = null;
  let rejectFinal = null;

  function kill() {
    if (rec) {
      try {
        rec.onresult = null;
        rec.onerror = null;
        rec.onend = null;
        rec.abort();
      } catch {
        try {
          rec.stop();
        } catch {
          /* ignore */
        }
      }
    }
    rec = null;
    listening = false;
  }

  return {
    supported: true,
    get listening() {
      return listening;
    },
    abort() {
      if (rejectFinal) {
        const r = rejectFinal;
        rejectFinal = null;
        resolveFinal = null;
        r(new Error("iptal"));
      }
      kill();
    },
    stop() {
      try {
        rec?.stop();
      } catch {
        /* ignore */
      }
    },
    /** One utterance → resolves with transcript text. */
    start() {
      kill();
      return new Promise((resolve, reject) => {
        rec = new SR();
        rec.lang = lang;
        rec.interimResults = true;
        rec.continuous = false;
        rec.maxAlternatives = 1;
        listening = true;
        resolveFinal = resolve;
        rejectFinal = reject;
        let last = "";

        rec.onresult = (ev) => {
          let interim = "";
          let final = "";
          for (let i = ev.resultIndex; i < ev.results.length; i++) {
            const r = ev.results[i];
            const t = r[0]?.transcript || "";
            if (r.isFinal) final += t;
            else interim += t;
          }
          if (final) last = final.trim();
          else if (interim) {
            last = interim.trim();
            onPartial?.(last);
          }
        };

        rec.onerror = (ev) => {
          const code = ev?.error || "error";
          listening = false;
          const map = {
            "not-allowed": "Mikrofon izni yok — ayarlardan sese izin ver.",
            "service-not-allowed": "Ses servisi engellendi.",
            "no-speech": "Ses algılanmadı — tekrar dene.",
            aborted: "Dinleme iptal.",
            network: "Ses tanıma ağı hatası (cihaz Google STT kullanıyor olabilir).",
            "audio-capture": "Mikrofon bulunamadı.",
          };
          const msg = map[code] || `Ses tanıma: ${code}`;
          const rej = rejectFinal;
          resolveFinal = null;
          rejectFinal = null;
          if (code === "aborted" || code === "no-speech") {
            // soft: empty is ok for no-speech in loop
            if (code === "no-speech") rej?.(new Error(msg));
            else rej?.(new Error(msg));
          } else {
            rej?.(new Error(msg));
          }
        };

        rec.onend = () => {
          listening = false;
          const res = resolveFinal;
          const rej = rejectFinal;
          resolveFinal = null;
          rejectFinal = null;
          if (res) {
            if (last) res(last);
            else rej?.(new Error("Ses algılanmadı — tekrar dene."));
          }
        };

        try {
          rec.start();
        } catch (e) {
          listening = false;
          reject(e instanceof Error ? e : new Error(String(e)));
        }
      });
    },
  };
}
