# Uzaktan erişim (VPN yok)

Snow **beyin sunucuda** kalır. Telefon sadece HTTP(S) ile konuşur.  
LAN dışında erişim için **port açmak veya WireGuard/VPN istemiyorsan** en güvenli pratik yol:

## Cloudflare Tunnel (önerilen)

### Neden?
- Acer’dan **dışarı giden** tünel (modemde port forward yok)
- HTTPS otomatik
- Cloudflare Access ile ek kimlik (e-posta OTP) eklenebilir
- VPN uygulaması telefonda şart değil

### Güvenlik katmanları (zorunlu düşün)

| Katman | Ne |
|--------|-----|
| 1 | Güçlü `SNOW_APP_TOKEN` (uzun rastgele) |
| 2 | HTTPS (tünel) — düz HTTP internete açma |
| 3 | (İsteğe bağlı) Cloudflare Access — tünel URL’sine ikinci kapı |
| 4 | Rate limit (Snow zaten var) |
| 5 | Token’ı sohbete/GitHub’a yapıştırma |

**Yapma:** 8787’yi modemden WAN’a açmak.

### Kurulum (özet)

1. [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) → Networks → Tunnels → Create  
2. Linux (Acer) connector komutunu kopyala; token al  
3. Public hostname: `snow.senindomain.com` → `http://127.0.0.1:8787`  
4. Acer’da tüneli çalıştır (aşağıda compose örneği)  
5. Telefonda Snow Ses / Station **Sunucu** alanına:  
   `https://snow.senindomain.com`  
6. Token: aynı `SNOW_APP_TOKEN`

### Compose eklentisi

`docker-compose.tunnel.yml` (repo kökü) — token’ı `.env` içine `CLOUDFLARE_TUNNEL_TOKEN=...` koy:

```bash
cd /srv/homelab/snow
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d
```

Tunnel sadece Cloudflare’e bağlanır; Snow hâlâ `localhost:8787`.

### Alternatifler (VPN değil)

| Seçenek | Not |
|---------|-----|
| Cloudflare Tunnel | En dengeli, ücretsiz katman genelde yeter |
| Tailscale Funnel / node share | Teknik olarak mesh; sen “VPN istemiyorum” dediğin için öncelik değil |
| ngrok | Hızlı test; uzun vadede CF tercih |

### APK

APK’da varsayılan LAN IP gömülü olabilir. Uzaktan kullanımda uygulama **Ayar → Sunucu** ile tünel HTTPS URL’sini kaydet (localStorage). Yeniden build şart değil.

### Kontrol listesi

- [ ] `.env` token zayıf değil  
- [ ] Tünel sadece 8787’ye  
- [ ] Tarayıcıda `https://…/api/v1/health` (token gerekmez health için — bilinçli; chat token’lı)  
- [ ] Chat 401’siz token ile çalışıyor  
- [ ] Modem port forward **kapalı**
