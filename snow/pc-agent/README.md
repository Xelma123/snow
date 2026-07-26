# Snow PC Agent (MSI) — otomatik servis

Acer’daki Snow `pc_control` ile burayı çağırır.  
**Elle `python main.py` açmana gerek yok** — Windows oturum açılınca gizli başlar.

## Neden Scheduled Task (klasik Windows Service değil)?

| | Scheduled Task @ logon | SYSTEM Service |
|--|------------------------|----------------|
| Elle açma | Yok | Yok |
| Sekme kapat / masaüstü | Çalışır (senin oturumun) | Genelde **çalışmaz** |
| Kimlik | Senin kullanıcın | SYSTEM |

Yani agent bir **arka plan servisi gibi** davranır; ama masaüstü komutları için **kullanıcı oturumunda** kalır.

## Tek seferlik kurulum (MSI)

**Yönetici PowerShell gerekmez** (önceki “Erişim engellendi” hatası `RunLevel Highest` yüzündendi).

Normal PowerShell:

```powershell
cd C:\Users\Xelma123\Desktop\Homelab\snow\pc-agent

# Acer .env içindeki SNOW_PC_AGENT_TOKEN ile aynı değer
.\install-autostart.ps1 -Token "uzun-ortak-gizli"
```

Ne yapar?

1. `.env` yazar  
2. `.venv` + pip install  
3. Görev Zamanlayıcı **SnowPcAgent** (Limited, admin yok) — olmazsa atlanır  
4. **Startup klasörüne** yedek kısayol (her zaman; oturum açılınca gizli başlar)  
5. Hemen başlatır → `http://127.0.0.1:8790/health`

### Sonra

- PC’yi kapatıp aç / oturum aç → agent **kendi gelir**  
- Log: `pc-agent\logs\agent-YYYYMMDD.log`  
- Kaldır: `.\uninstall-autostart.ps1`

Görev Zamanlayıcı’da gör: `taskschd.msc` → **SnowPcAgent**

## Firewall (sadece Acer)

```powershell
# Acer LAN IP'ni yaz (ör. 192.168.1.13)
New-NetFirewallRule -DisplayName "Snow PC Agent" -Direction Inbound `
  -Protocol TCP -LocalPort 8790 -Action Allow -RemoteAddress 192.168.1.13
```

## Acer tarafı

```env
SNOW_PC_AGENT_TOKEN=aynı-token
```

`personal/pcs.yaml` → `host` / `mac` / `agent_url: http://MSI_IP:8790`

## WOL

Uyandırma agent’sız (magic packet). Uyut/kapat/sekme için PC uyanık + agent ayakta (oturum açık).

## Manuel test (gerekirse)

```powershell
.\run_agent.ps1
# veya
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8790
```

## Politika

- Komutlar **anlık** veya Snow’da **tek seferlik gecikme**  
- Agent üzerinde **cron / her akşam** yok  
- Serbest shell yok  
