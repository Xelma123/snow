# Snow Ses APK — kalite notu (v1.4)

## Rol

**İnce köprü.** Beyin Acer’da (`/voice` web UI).  
APK: WebView + mikrofon izni + **native TTS** + arka planda iptal.

UI (Persona 5) sunucudaki `web/` dosyalarından gelir — APK sadece shell.

## Kalite checklist (bu sürüm)

| Standart | Uygulama |
|----------|----------|
| Secrets native’de yok | Token sadece web localStorage |
| Push-to-talk | `/voice` PTT; onResume STT başlatmaz |
| Battery | `onPause` → `__snowCancel` + TTS stop + WebView.onPause |
| Mic | Runtime permission (Activity Result API) |
| TTS | `SnowNative.speak` (max 1200 char) |
| Cleartext | `network_security_config` + LAN host `192.168.1.13` |
| Navigation | Sadece Snow origin |
| Crash hygiene | TTS/WebView destroy güvenli |
| Theme | P5 black `#0A0A0A` / red `#FF0000` shell |
| Version | `1.4.0` (versionCode 5) — P5 shell + /voice (PC komutları sunucudan) |

## Build (bu makine)

```powershell
$sdkRoot = "C:\Users\Xelma123\Android\Sdk"
$env:ANDROID_HOME = $sdkRoot
$env:ANDROID_SDK_ROOT = $sdkRoot
$env:JAVA_HOME = "C:\Program Files\Java\jdk-21.0.11"
$env:Path = "$sdkRoot\platform-tools;$env:JAVA_HOME\bin;" +
  [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
  [System.Environment]::GetEnvironmentVariable("Path","User")

cd C:\Users\Xelma123\Desktop\Homelab\snow\android
.\gradlew.bat assembleRelease
copy app\build\outputs\apk\release\app-release.apk ..\Snow-Ses-release.apk
```

## Kur

```powershell
adb install -r C:\Users\Xelma123\Desktop\Homelab\snow\Snow-Ses-release.apk
```

## Önkoşul

Acer’da Snow + **güncel web** (P5 UI):  
`http://192.168.1.13:8787/voice` tarayıcıda açılmalı.
