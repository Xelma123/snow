# Snow — Sıfırdan Acer kurulumu (yanlış anlaşılmaz rehber)

Bu belge **senin kişisel lab’ın** içindir.  
Hedef: Acer sunucuda Snow’u **`/srv/homelab/snow`** altına kurmak; Home Assistant zaten (veya yakında) aynı çatı altında.

---

## 0) Kavramlar (önce bunu oku)

| Terim | Anlamı |
|--------|--------|
| **MSI** | Senin günlük Windows laptop’un — buradan dosya kopyalar, SSH açarsın |
| **Acer** | 7/24 açık sunucu — Ubuntu Server, Docker, HA, Snow burada çalışır |
| **`/srv/homelab/snow`** | Snow’un **kalıcı** kurulum klasörü (ev dizini `~/snow` değil, kök `/` de değil) |
| **Home Assistant (HA)** | Akıllı ev paneli — genelde `http://ACER_IP:8123` |
| **Snow** | AI asistan API + web arayüzü — genelde `http://ACER_IP:8787` |
| **`.env`** | Şifreler ve ayarlar dosyası — **asla sohbete/GitHub’a yapıştırma** |
| **entity_id** | HA içindeki cihaz kimliği, örn. `light.salon_ampul` |

### Wi‑Fi

Acer **Wi‑Fi ile çalışır**. Zorunlu Ethernet yok.  
Ama:

1. Router’da Acer’a **sabit IP** ver (DHCP rezervasyonu).  
2. Mümkünse Wi‑Fi güç tasarrufu / sleep kapat.  
3. İleride Ethernet daha stabil olur.

Telefon ve MSI’nin Wi‑Fi’de olması normal.

---

## 1) Acer’da sabit IP (router)

1. Telefonda veya MSI’da tarayıcı aç.  
2. Adres: `http://192.168.1.1` (Huawei).  
3. Giriş yap.  
4. **DHCP / bağlı cihazlar / LAN** menüsünü bul.  
5. Acer bilgisayarını listede bul (hostname veya MAC).  
6. **IP rezervasyonu / static DHCP** ver.  
   - Örnek: `192.168.1.10`  
7. Bu IP’yi bir yere yaz. Bundan sonra her yerde **ACER_IP** = bu numara.

Acer’ı bir kez yeniden başlat; IP’nin değişmediğini kontrol et.

---

## 2) MSI’dan Acer’a SSH çalışıyor mu?

MSI’da **PowerShell** aç:

```powershell
ssh KULLANICI@192.168.1.10
```

- `KULLANICI` = Ubuntu kurarken verdiğin kullanıcı adı  
- `192.168.1.10` = senin sabit IP’n  

İlk seferde `yes` de, şifreyi gir.  
Girdiysen Acer terminalindesin. Çıkmak için:

```bash
exit
```

SSH yoksa: Acer’da OpenSSH kurulu mu, aynı Wi‑Fi’de misiniz, IP doğru mu kontrol et.

---

## 3) Acer’da klasör iskeleti

MSI’dan tekrar SSH ile Acer’a gir:

```powershell
ssh KULLANICI@192.168.1.10
```

Acer’da **sırayla**:

```bash
# 1) /srv/homelab klasörünü oluştur (yoksa)
sudo mkdir -p /srv/homelab

# 2) Bu klasörün sahibi sen ol (Docker ve dosya kopyası kolay olsun)
sudo chown -R "$USER:$USER" /srv/homelab

# 3) Kontrol
ls -la /srv
ls -la /srv/homelab
```

Görmen gereken: `/srv/homelab` var ve sahibi senin kullanıcın.

HA zaten `/srv/homelab/homeassistant` altındaysa bozma; yanına `snow` eklenecek.

Çık:

```bash
exit
```

---

## 4) MSI’da Snow projesini hazırla (kopyalamadan önce)

### 4.1 Klasöre gir

PowerShell:

```powershell
cd C:\Users\Xelma123\Desktop\Homelab\snow
dir
```

Şunlar görünmeli: `server`, `web`, `personal`, `docker-compose.yml`, …

### 4.2 `.env` oluştur

```powershell
copy personal\env.example .env
notepad .env
```

**Notepad’de şunları doldur** (örnek değerleri kendininkiyle değiştir):

```env
SNOW_APP_TOKEN=BURAYA_COK_UZUN_RASTGELE_YAZ
OPENROUTER_API_KEY=sk-or-v1-SENIN_KEY
HA_URL=http://192.168.1.10:8123
HA_TOKEN=SENIN_HA_LONG_LIVED_TOKEN
HA_DEFAULT_LIGHT=light.SENIN_TAPO_ENTITY
HA_DEFAULT_TV=media_player.arcelik_android_tv
HOME_LAT=41.0082
HOME_LON=28.9784
ENABLE_RULE_FALLBACK=true
RATE_LIMIT_PER_MINUTE=60
```

#### `SNOW_APP_TOKEN` nasıl üretilir?

PowerShell:

```powershell
-join ((48..57) + (97..102) | Get-Random -Count 48 | ForEach-Object {[char]$_})
```

Çıkanı kopyala → `.env` içine yapıştır.  
Bu token **telefonda da** gireceğin parola gibi bir şey; güçlü olsun.

#### `OPENROUTER_API_KEY`

1. https://openrouter.ai adresine gir, hesap aç.  
2. Keys / API Keys → Create.  
3. Key’i kopyala → `.env`.

#### `HA_TOKEN` (Long-Lived Access Token)

1. Tarayıcı: `http://192.168.1.10:8123`  
2. Sol altta **kullanıcı adına** tıkla (profil).  
3. En alta in → **Long-Lived Access Tokens**.  
4. **Create Token** → isim: `snow` → Create.  
5. Token **bir kez** gösterilir → kopyala → `.env` `HA_TOKEN=...`  
6. Kaybetme; sonra göremezsin (yeniden üretirsin).

#### `HA_DEFAULT_LIGHT` (entity_id)

1. HA → **Geliştirici araçları** (Developer tools).  
2. **Durumlar / States**.  
3. Listede `light.` ile başlayan Tapo satırını bul.  
4. Tam adı kopyala, örn. `light.l530_xxxx`.  
5. `.env` → `HA_DEFAULT_LIGHT=light.l530_xxxx`

#### `HA_DEFAULT_TV` (entity_id)

1. HA → States → `media_player.` ile başlayan Android TV satırı.  
2. Bu lab için: `media_player.arcelik_android_tv`  
3. `.env` → `HA_DEFAULT_TV=media_player.arcelik_android_tv`  
4. Station TV kartı ve “tv aç/kapat” komutları bunu kullanır.

#### `HA_URL`

- Acer LAN IP + `:8123` — örnek: `http://192.168.1.13:8123`  
- Docker alternatif: `http://host.docker.internal:8123` (compose `extra_hosts` ile)  
- **Yanlış:** container içinden `http://127.0.0.1:8123` (Snow kendini görür, HA’yı değil)

Kaydet, Notepad’i kapat.

### 4.3 Cihaz aliasları

```powershell
notepad personal\devices.yaml
```

Şöyle düzenle (entity’yi **seninkiyle** değiştir):

```yaml
devices:
  salon: light.l530_xxxx
  ampul: light.l530_xxxx
  lamba: light.l530_xxxx
  isik: light.l530_xxxx
```

Kaydet.

### 4.4 `.env` dosyasının yerini doğrula

```powershell
cd C:\Users\Xelma123\Desktop\Homelab\snow
dir .env
```

`.env` **snow klasörünün kökünde** olmalı (`server` içinde değil).

---

## 5) Projeyi Acer’a kopyala (`/srv/homelab/snow`)

MSI PowerShell (Acer’a SSH **kapalı** olsun; scp ayrı çalışır):

```powershell
cd C:\Users\Xelma123\Desktop\Homelab

# Tüm snow klasörünü Acer'daki /srv/homelab/ altına kopyala
scp -r snow KULLANICI@192.168.1.10:/srv/homelab/
```

- `KULLANICI` ve IP’yi kendine göre yaz.  
- Bitene kadar bekle (birkaç dakika sürebilir).  
- Şifre sorarsa Acer kullanıcı şifreni gir.

### Kontrol

```powershell
ssh KULLANICI@192.168.1.10
ls -la /srv/homelab
ls -la /srv/homelab/snow
ls -la /srv/homelab/snow/.env
ls -la /srv/homelab/snow/docker-compose.yml
exit
```

Görmen gereken:

```text
/srv/homelab/snow/
  .env
  docker-compose.yml
  server/
  web/
  personal/
  ...
```

`.env` yoksa MSI’dan ayrıca:

```powershell
scp C:\Users\Xelma123\Desktop\Homelab\snow\.env KULLANICI@192.168.1.10:/srv/homelab/snow/.env
```

---

## 6) Acer’da Docker ile Snow’u ayağa kaldır

SSH:

```powershell
ssh KULLANICI@192.168.1.10
```

Acer’da:

```bash
cd /srv/homelab/snow

# Docker kurulu mu?
docker --version
docker compose version

# İlk build + çalıştır
docker compose up -d --build

# Durum
docker ps

# Log (Ctrl+C ile çık, container durmaz)
docker logs --tail 50 snow
```

`docker ps` çıktısında **snow** satırı ve **Up** görmelisin.  
Port: `0.0.0.0:8787->8787/tcp` benzeri.

### Sağlık kontrolü (Acer üzerinde)

```bash
curl -s http://127.0.0.1:8787/api/v1/health
echo
curl -s "http://127.0.0.1:8787/api/v1/health?deep=1"
echo
```

**İyi sonuçta kabaca:**

- `"ok": true`  
- `"openrouter_configured": true`  
- `"ha_token_configured": true`  
- `deep.home_assistant.ok`: **true**

**HA ok false ise:**

1. `.env` içindeki `HA_URL` Acer LAN IP mi?  
2. `HA_TOKEN` doğru mu?  
3. HA gerçekten ayakta mı? `curl -s http://192.168.1.10:8123` (IP’ni yaz)  
4. Düzelttikten sonra:

```bash
cd /srv/homelab/snow
nano .env
# kaydet: Ctrl+O Enter, çık: Ctrl+X
docker compose up -d --force-recreate
curl -s "http://127.0.0.1:8787/api/v1/health?deep=1"
```

Çık:

```bash
exit
```

---

## 7) MSI / telefondan erişim testi

Aynı ev Wi‑Fi’sinde:

1. Tarayıcı: `http://192.168.1.10:8787` (IP’ni yaz)  
2. İlk ekran **onboarding**:  
   - Sunucu adresi: `http://192.168.1.10:8787` (genelde otomatik dolu)  
   - Token: `.env` içindeki **`SNOW_APP_TOKEN` ile birebir aynı**  
3. **Bağlan**  
4. Komut dene:
   - `Işığı kapat`  
   - `Işığı aç`  
   - `Azıcık kıs`  
   - `Işık ne durumda?`  
   - `Hava nasıl?`  
   - `Ev nasıl?`

### Telefonu ana ekrana eklemek (isteğe bağlı)

Chrome/Android: menü → **Ana ekrana ekle** / Add to Home screen.  
Bu bir “uygulama kabuğu” gibi açılır; hâlâ köprüdür, AI telefonda değildir.

---

## 8) Her gün / bakım (kısa)

Acer SSH:

```bash
cd /srv/homelab/snow

# Durum
docker ps

# Yeniden başlat
docker compose restart

# Güncel kodu MSI'dan attıktan sonra
docker compose up -d --build

# Log
docker logs -f snow
```

Acer reboot sonrası Snow genelde **kendisi ayağa kalkar** (`restart: unless-stopped`).

---

## 9) Klasör haritası (nihai)

```text
/srv/homelab/
├── homeassistant/     ← mevcut HA (varsa)
└── snow/              ← Snow (burası)
    ├── .env           ← secret (chmod 600 önerilir)
    ├── data/          ← sqlite (otomatik oluşur)
    ├── personal/
    │   ├── devices.yaml
    │   └── RUNBOOK.md
    ├── server/
    ├── web/
    └── docker-compose.yml
```

`.env` izinleri (Acer):

```bash
chmod 600 /srv/homelab/snow/.env
```

---

## 10) Sık hatalar

| Ne görüyorsun | Ne yap |
|---------------|--------|
| SSH bağlanmıyor | IP, Wi‑Fi, kullanıcı, OpenSSH |
| `Permission denied` `/srv` | `sudo chown -R $USER:$USER /srv/homelab` |
| scp bitti ama `.env` yok | `.env`’yi ayrıca scp et; gizli dosya bazen unutulur |
| 401 / 403 Snow UI | Token `.env` ile aynı değil |
| deep HA fail | HA_URL LAN IP, token, HA ayakta |
| Işık yok | `HA_DEFAULT_LIGHT` + HA’da manuel aç/kapa testi |
| OpenRouter hata | Key/kota; yine de “Işığı kapat” kural fallback deneyebilir |
| Sayfa açılmıyor | `docker ps`, port 8787, firewall, doğru IP |

---

## 11) Güvenlik (kısa)

- Token / key’i sohbete yapıştırma  
- `8787` portunu modemden **internete açma** (şimdilik sadece ev ağı)  
- Dışarıdan lazımsa sonra VPN  

---

## 12) Başarı checklist

- [ ] Acer sabit IP  
- [ ] `/srv/homelab/snow` var, içinde `.env` var  
- [ ] `.env` içinde `HA_DEFAULT_LIGHT` + `HA_DEFAULT_TV` doğru  
- [ ] `docker ps` → snow Up  
- [ ] `health?deep=1` → HA ok  
- [ ] Telefondan UI + token  
- [ ] Işık komutu gerçekten çalışıyor  
- [ ] TV aç/kapat veya Station TV kartı  
- [ ] “adım ne” isim **yazmıyor**; “benim adım X” yazıyor  
- [ ] “film gecesi” / rutin butonu loş ışık + TV  
- [ ] “5 dk sonra…” Station **Zamanlanmış** kartında görünür  

Hepsi tikliyse: **Snow kişisel sunucunda canlı.**

---

## 12b) Sesli çift yönlü (telefon)

| URL | Ne |
|-----|-----|
| `http://ACER_IP:8787/voice` | **Ses köprüsü** — dinle / cevapla / tekrar |
| `http://ACER_IP:8787/` | Tam istasyon (panel, işler) |

1. Telefonda **Chrome** ile `/voice` aç.  
2. Token (Station ile aynı `SNOW_APP_TOKEN`).  
3. **Başlat** / büyük orb → konuş → Snow cevap seslendirir → tekrar dinler.  
4. **Durdur** veya dinlerken orb = kes.  
5. Konuşurken orb = cevabı kes, yeniden dinle.

**APK:** `android/` → `snow_default_url` = Acer, uygulama `/voice` açar; mikrofon izni ver.

Not: STT/TTS cihaz tarafı (Chrome). Firefox/iOS zayıf kalabilir.

---

## 13) Kod güncelleme (MSI → Acer hızlı)

MSI PowerShell (repo kökünden):

```powershell
scp -r C:\Users\Xelma123\Desktop\Homelab\snow\server `
  C:\Users\Xelma123\Desktop\Homelab\snow\web `
  C:\Users\Xelma123\Desktop\Homelab\snow\personal\routines.yaml `
  KULLANICI@ACER_IP:/srv/homelab/snow/
```

Acer SSH:

```bash
cd /srv/homelab/snow
# .env içinde HA_DEFAULT_TV kontrol
docker compose up -d --build
curl -s "http://127.0.0.1:8787/api/v1/health?deep=1"
```

Yerel smoke (MSI, Python path):

```powershell
cd C:\Users\Xelma123\Desktop\Homelab\snow
python -m compileall server/app
python scripts/smoke_identity.py
python scripts/smoke_rules.py
python scripts/smoke_manifest.py
python scripts/smoke_routines.py
python scripts/smoke_profile.py
```

---

## PC / MSI kontrol (WOL + agent)

**Politika:** Komutlar **o anlık** veya tek seferlik gecikme (5 dk sonra kapat).  
**Yok:** her akşam / her gün 16:00 gibi yinelenen program.

### Acer (Snow)
1. `personal/pcs.yaml` — host + MAC + agent_url
2. `.env`: `SNOW_PC_AGENT_TOKEN=uzun-gizli` (MSI agent ile aynı)
3. `docker compose up -d --build`
4. Ses: “bilgisayarı uyandır”, “MSI açık mı”

### MSI (pc-agent) — otomatik (elle açma yok)
Bir kez (Yönetici PowerShell önerilir):

```powershell
cd ...\snow\pc-agent
.\install-autostart.ps1 -Token "aynı-token"
```

- Oturum açılınca gizli başlar (Görev Zamanlayıcı: **SnowPcAgent**)
- Log: `pc-agent\logs\`
- Kaldır: `.\uninstall-autostart.ps1`
- Firewall 8790 → sadece Acer IP

### WOL sorun giderme
- Wi‑Fi WOL zayıf olabilir; Ethernet MAC + kablo daha güvenilir
- BIOS WOL açık; Fast Startup kapalı
- Magic packet Acer’dan LAN broadcast’e gider; uyanma 30–60 sn sürebilir
