/** On-device STT only — audio never uploaded to Snow. */
export function createVoice({ onText, onError, lang = "tr-TR" }) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    return {
      supported: false,
      start() {
        onError?.("Bu tarayıcı ses tanımayı desteklemiyor.");
      },
      stop() {},
    };
  }

  const rec = new SR();
  rec.lang = lang;
  rec.interimResults = false;
  rec.maxAlternatives = 1;
  let listening = false;

  rec.onresult = (ev) => {
    const t = ev.results[0][0].transcript;
    onText?.(t);
  };
  rec.onerror = () => {
    listening = false;
    onError?.("Ses tanıma hatası");
  };
  rec.onend = () => {
    listening = false;
  };

  return {
    supported: true,
    get listening() {
      return listening;
    },
    start() {
      listening = true;
      rec.start();
    },
    stop() {
      try {
        rec.stop();
      } catch {
        /* ignore */
      }
      listening = false;
    },
  };
}
