# Snow mobil istemci

## Rol

Telefon = **ince köprü**. Beyin Acer’da.

| Yüzey | URL | Amaç |
|--------|-----|------|
| **Ses (birincil telefon)** | `/voice` | Çift yönlü konuşma: dinle → chat API → sesli cevap → tekrar |
| **İstasyon** | `/` | Işık/TV paneli, işler, rutinler, yazılı komut |

## Ses köprüsü (`/voice`)

1. **STT** — Web Speech API, cihazda (Chrome Android)  
2. **Snow** — `POST /api/v1/chat` (aynı agent pipeline)  
3. **TTS** — `speechSynthesis`, cihazda Türkçe ses tercihi  
4. Döngü sürekli; orb / Durdur ile kesilir  
5. Konuşurken orb = barge-in (TTS kes, yeniden dinle)

Ses dosyası sunucuya **yüklenmez**.

### Tarayıcı

| İstemci | Beklenti |
|---------|----------|
| Chrome Android | Önerilen |
| Snow APK (WebView) | `/voice` + RECORD_AUDIO |
| Firefox / iOS Safari | STT zayıf veya yok |

LAN `http://` mikrofon izni isteyebilir; mümkünse sabit DHCP IP kullan.

## Native Android APK

`android/` — WebView kabuk, varsayılan `{base}/voice`.

Detay: `android/README.md`.

## iOS

Ayrı native yok; Safari “Ana Ekrana Ekle” → `/voice` (STT sınırlı olabilir).
