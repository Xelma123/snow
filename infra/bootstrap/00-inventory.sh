#!/usr/bin/env bash
# =============================================================================
# Snow Homelab — Adım 0: Sunucu Envanteri
# =============================================================================
# SALT-OKUNUR. Bu script sunucuda HİÇBİR ŞEYİ değiştirmez:
#   - dosya yazmaz, paket kurmaz, servis başlatmaz/durdurmaz
#   - yalnızca okur ve rapor basar
#
# Kullanım (Acer'da):
#   sudo bash 00-inventory.sh
#   sudo bash 00-inventory.sh > /tmp/envanter.txt   # dosyaya almak istersen
#
# sudo olmadan da çalışır, ama bazı bölümler (SMART, sshd -T) eksik kalır.
#
# GİZLİLİK: Bu çıktı sohbete yapıştırılacak. Script sır DEĞERİ basmaz —
# .env dosyalarından yalnızca anahtar ADLARINI ve dosya izinlerini gösterir.
# =============================================================================

set -uo pipefail   # -e YOK: eksik komut tüm raporu düşürmesin

HOMELAB_DIR="${HOMELAB_DIR:-/srv/homelab}"

# --- yardımcılar -------------------------------------------------------------
section() { printf '\n\n=============== %s ===============\n' "$1"; }
sub()     { printf '\n--- %s ---\n' "$1"; }
have()    { command -v "$1" >/dev/null 2>&1; }

# Komutu çalıştır; yoksa/başarısızsa raporu düşürmeden not düş
try() {
  if have "$1"; then
    "$@" 2>&1 || echo "  (komut hata verdi: $*)"
  else
    echo "  (yok: $1 kurulu değil)"
  fi
}

# Dosyayı göster, yorum ve boş satırları at
showconf() {
  if [ -r "$1" ]; then
    grep -vE '^\s*(#|$)' "$1" 2>/dev/null || echo "  (okunamadı)"
  else
    echo "  (yok veya okuma izni yok: $1)"
  fi
}

IS_ROOT=0
[ "$(id -u)" -eq 0 ] && IS_ROOT=1

printf '################################################################\n'
printf '#  SNOW HOMELAB ENVANTER RAPORU\n'
printf '#  Tarih : %s\n' "$(date -Is)"
printf '#  Host  : %s\n' "$(hostname)"
printf '#  Kullanıcı: %s (root=%s)\n' "$(id -un)" "$IS_ROOT"
printf '#  Bu script salt-okunurdur; hiçbir değişiklik yapılmadı.\n'
printf '################################################################\n'

[ "$IS_ROOT" -eq 0 ] && printf '\n!! UYARI: sudo olmadan çalışıyor — SMART, sshd -T ve bazı\n!! bölümler eksik kalacak. Tam rapor için: sudo bash %s\n' "$0"

# =============================================================================
section "1. İŞLETİM SİSTEMİ"
# =============================================================================
sub "Dağıtım"
showconf /etc/os-release | grep -E '^(NAME|VERSION|VERSION_ID|VERSION_CODENAME)='

sub "Çekirdek / mimari"
uname -a

sub "Uptime / yük"
uptime

sub "Zaman senkronizasyonu (loglar ve zamanlanmış işler için kritik)"
try timedatectl

sub "Yeniden başlatma gerekiyor mu?"
if [ -f /var/run/reboot-required ]; then
  echo "  EVET — bekleyen çekirdek/güvenlik güncellemesi var:"
  cat /var/run/reboot-required* 2>/dev/null
else
  echo "  hayır"
fi

# =============================================================================
section "2. DONANIM VE KAYNAKLAR"
# =============================================================================
sub "CPU"
if have lscpu; then
  lscpu | grep -E 'Model name|^CPU\(s\)|Thread|Core|MHz|Architecture' || true
else
  grep -E 'model name|cpu cores' /proc/cpuinfo | sort -u
fi

sub "RAM ve swap"
free -h

sub "Swap detayı (8 GB için >=2 GB bekleniyor)"
swapon --show 2>/dev/null || echo "  (swap yok!)"
echo "vm.swappiness = $(cat /proc/sys/vm/swappiness 2>/dev/null || echo '?')"

sub "Disk kullanımı"
df -hT -x tmpfs -x devtmpfs -x squashfs 2>/dev/null

sub "Blok cihazlar"
try lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,ROTA

sub "En çok yer kaplayan 10 dizin (/)"
du -xh --max-depth=2 / 2>/dev/null | sort -rh | head -10

sub "Disk sağlığı (SMART) — eski laptop diski için kritik"
if have smartctl; then
  for d in /dev/sd? /dev/nvme?n?; do
    [ -b "$d" ] || continue
    echo "### $d"
    smartctl -H "$d" 2>&1 | grep -Ei 'result|SMART overall|Unavailable' || echo "  (okunamadı)"
    smartctl -A "$d" 2>&1 | grep -Ei 'Power_On_Hours|Reallocated_Sector|Wear_Leveling|Percentage Used|Media_Wearout|Temperature_Celsius' || true
  done
else
  echo "  (yok: smartmontools kurulu değil — 'apt install smartmontools' ile bakılabilir)"
fi

sub "Sıcaklıklar"
if have sensors; then
  sensors 2>&1 | grep -Ei 'Core|Package|temp|fan' || true
else
  echo "  (yok: lm-sensors kurulu değil)"
  for z in /sys/class/thermal/thermal_zone*/temp; do
    [ -r "$z" ] || continue
    echo "  $(dirname "$z"): $(awk '{printf "%.1f C", $1/1000}' "$z")"
  done
fi

# =============================================================================
section "3. LAPTOP-SUNUCU AYARLARI  (gizemli kesintilerin 1 numaralı sebebi)"
# =============================================================================
sub "Kapak kapanınca ne oluyor? (logind)"
# NOT: logind.conf.d/*.conf glob'u eşleşmezse grep hata döndürür ve yedek mesaj
# yanlışlıkla tetiklenir. Bu yüzden önce var olan dosyaları topluyoruz.
_lid_files=(/etc/systemd/logind.conf)
for _f in /etc/systemd/logind.conf.d/*.conf; do [ -f "$_f" ] && _lid_files+=("$_f"); done
if grep -HE '^\s*Handle(LidSwitch|LidSwitchExternalPower|LidSwitchDocked|SuspendKey)' \
     "${_lid_files[@]}" 2>/dev/null; then
  :
else
  echo "  (açıkça ayarlanmamış → VARSAYILAN 'suspend' geçerli, yani kapak kapanınca sunucu UYUR)"
fi

sub "Uyku/hazırda bekletme hedefleri maskeli mi?"
for t in sleep.target suspend.target hibernate.target hybrid-sleep.target; do
  echo "  $t: $(systemctl is-enabled "$t" 2>&1)"
done

sub "Wi-Fi güç tasarrufu (açıksa gece bağlantı düşer)"
if have iw; then
  for i in $(ls /sys/class/net 2>/dev/null); do
    [ -d "/sys/class/net/$i/wireless" ] || continue
    echo "### $i"
    iw dev "$i" get power_save 2>&1 || echo "  (okunamadı)"
  done
else
  echo "  (yok: iw kurulu değil)"
fi
echo "NetworkManager wifi.powersave:"
grep -rHE 'wifi\.powersave' /etc/NetworkManager/ 2>/dev/null || echo "  (ayarlanmamış)"

sub "Ağ arayüzleri ve IP'ler"
ip -brief addr 2>/dev/null || ip addr

sub "Varsayılan rota"
ip route show default 2>/dev/null

# =============================================================================
section "4. DOCKER"
# =============================================================================
sub "Sürümler"
try docker --version
docker compose version 2>&1 || echo "  (docker compose plugin yok)"

sub "Docker servisi"
try systemctl is-active docker
try systemctl is-enabled docker

sub "Çalışan + duran container'lar"
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}' 2>&1 \
  || echo "  (docker'a erişilemedi — sudo ile mi çalıştırdın?)"

sub "Anlık kaynak kullanımı"
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}' 2>&1 || true

sub "Restart politikaları (reboot sonrası kendiliğinden kalkıyor mu?)"
docker inspect --format '{{.Name}}: {{.HostConfig.RestartPolicy.Name}}' $(docker ps -aq 2>/dev/null) 2>/dev/null \
  || echo "  (okunamadı)"

sub "Ağlar"
docker network ls 2>&1 || true

sub "Volume'lar"
docker volume ls 2>&1 || true

sub "Docker disk kullanımı"
docker system df 2>&1 || true

# =============================================================================
section "5. /srv/homelab — PROJE DİZİNİ"
# =============================================================================
sub "Sahiplik ve izinler"
ls -la "$HOMELAB_DIR" 2>&1 || echo "  ($HOMELAB_DIR yok veya erişilemiyor)"

sub "Dizin boyutları"
du -sh "$HOMELAB_DIR"/* 2>/dev/null || true

sub "Ağaç (3 seviye, build/venv/cache hariç)"
if have tree; then
  tree -L 3 -a -I '.git|__pycache__|.venv|node_modules|build|.gradle' "$HOMELAB_DIR" 2>&1
else
  find "$HOMELAB_DIR" -maxdepth 3 \
    \( -name .git -o -name __pycache__ -o -name .venv -o -name node_modules -o -name build \) -prune -o \
    -print 2>/dev/null | head -80
  echo "  (tree kurulu değil — düz liste, ilk 80 satır)"
fi

sub "Compose dosyaları nerede?"
find "$HOMELAB_DIR" -maxdepth 3 -type f \
  \( -name 'docker-compose*.y*ml' -o -name 'compose*.y*ml' \) 2>/dev/null \
  || echo "  (bulunamadı)"

sub "Git deposu var mı?"
if [ -d "$HOMELAB_DIR/.git" ]; then
  git -C "$HOMELAB_DIR" log --oneline -5 2>&1
  git -C "$HOMELAB_DIR" remote -v 2>&1
else
  echo "  hayır — $HOMELAB_DIR bir git deposu değil (beklenen: Sprint 5'te klon olacak)"
fi

sub ".env dosyaları — İZİNLER ve ANAHTAR ADLARI (değerler MASKELİ)"
while IFS= read -r f; do
  [ -n "$f" ] || continue
  echo "### $f"
  stat -c '  izin=%a sahip=%U:%G boyut=%s' "$f" 2>/dev/null
  # yalnızca KEY= kısmı; değer asla basılmaz
  sed -nE 's/^\s*([A-Za-z_][A-Za-z0-9_]*)=.*/  \1=<gizli>/p' "$f" 2>/dev/null \
    || echo "  (okunamadı)"
done < <(find "$HOMELAB_DIR" -maxdepth 3 -name '.env' -type f 2>/dev/null)

sub "Snow veritabanı"
for db in "$HOMELAB_DIR"/snow/data/*.db; do
  [ -f "$db" ] || continue
  stat -c '%n  boyut=%s  değişim=%y' "$db"
done
ls -la "$HOMELAB_DIR"/snow/data/ 2>/dev/null || echo "  (snow/data yok)"

# =============================================================================
section "6. HOME ASSISTANT — KURULUM YÖNTEMİ"
# =============================================================================
# Sprint 2'nin yedek stratejisi buna bağlı: Docker mı, Supervised mı, HAOS mu?
sub "HA container'ı"
docker ps -a --filter 'name=home' --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' 2>&1 || true
docker ps -a --format '{{.Image}}' 2>/dev/null | grep -i -E 'home-?assistant|hass' || echo "  (homeassistant imajı bulunamadı)"

sub "Supervised kurulum izleri"
for s in hassio-supervisor hassio_supervisor haos-agent os-agent; do
  systemctl is-active "$s" >/dev/null 2>&1 && echo "  AKTİF: $s"
done
[ -d /usr/share/hassio ] && echo "  /usr/share/hassio VAR → Supervised kurulum"
have ha && echo "  'ha' CLI mevcut → Supervised/HAOS"

sub "HA config dizini (yedeklenecek asıl veri)"
for d in "$HOMELAB_DIR/homeassistant" "$HOMELAB_DIR/homeassistant/config" /usr/share/hassio/homeassistant; do
  [ -d "$d" ] || continue
  echo "### $d"
  du -sh "$d" 2>/dev/null
  ls -la "$d" 2>/dev/null | head -25
done

sub "HA veritabanı boyutu (recorder — genelde en büyük dosya)"
find "$HOMELAB_DIR" /usr/share/hassio -maxdepth 4 -name 'home-assistant_v2.db*' -type f 2>/dev/null \
  -exec ls -lh {} \; || echo "  (bulunamadı)"

# =============================================================================
section "7. GÜVENLİK DURUMU"
# =============================================================================
sub "Dinlenen portlar (0.0.0.0 = LAN'a açık!)"
if have ss; then
  ss -tulpn 2>/dev/null | grep -E 'LISTEN|UNCONN' || ss -tuln
else
  try netstat -tulpn
fi

sub "UFW firewall"
if have ufw; then
  ufw status verbose 2>&1
else
  echo "  (yok: ufw kurulu değil)"
fi

sub "iptables / nftables zincirleri (Docker UFW'yi baypas ediyor mu?)"
try nft list chains
iptables -L DOCKER-USER -n 2>&1 | head -5 || echo "  (DOCKER-USER zinciri okunamadı)"

sub "SSH etkin yapılandırması"
if [ "$IS_ROOT" -eq 1 ] && have sshd; then
  sshd -T 2>/dev/null | grep -iE '^(port|permitrootlogin|passwordauthentication|pubkeyauthentication|maxauthtries|permitemptypasswords|x11forwarding|allowusers|allowgroups)' \
    || echo "  (sshd -T başarısız)"
else
  echo "  (sudo gerekli — dosyadan okunuyor:)"
  grep -HiE '^\s*(Port|PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|MaxAuthTries)' \
    /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null \
    || echo "  (açıkça ayarlanmamış → varsayılanlar geçerli)"
fi

sub "authorized_keys (key-only auth'a geçmeden önce ZORUNLU kontrol)"
for h in /home/*/ /root/; do
  ak="${h}.ssh/authorized_keys"
  [ -r "$ak" ] || continue
  echo "### $ak"
  stat -c '  izin=%a sahip=%U' "$ak" 2>/dev/null
  # anahtar tipi + yorum; anahtar gövdesi basılmaz
  awk '{print "  " $1 " ... " ($NF ~ /@/ ? $NF : "(yorumsuz)")}' "$ak" 2>/dev/null
  echo "  → toplam $(grep -cvE '^\s*(#|$)' "$ak" 2>/dev/null || echo 0) anahtar"
done

sub "fail2ban"
if have fail2ban-client; then
  fail2ban-client status 2>&1
else
  echo "  (yok: fail2ban kurulu değil)"
fi

sub "Otomatik güvenlik güncellemeleri"
if [ -f /etc/apt/apt.conf.d/20auto-upgrades ]; then
  showconf /etc/apt/apt.conf.d/20auto-upgrades
else
  echo "  (20auto-upgrades yok → unattended-upgrades yapılandırılmamış)"
fi
try systemctl is-enabled unattended-upgrades

sub "Bekleyen güvenlik güncellemeleri"
apt list --upgradable 2>/dev/null | grep -ci security | xargs -I{} echo "  {} adet güvenlik güncellemesi bekliyor" \
  || echo "  (sayılamadı)"

sub "sudo yetkisi olan kullanıcılar"
getent group sudo admin 2>/dev/null

# =============================================================================
section "8. ZAMANLANMIŞ İŞLER"
# =============================================================================
sub "systemd timer'ları"
systemctl list-timers --all --no-pager 2>&1 | head -20

sub "Cron"
crontab -l 2>/dev/null || echo "  (bu kullanıcı için cron yok)"
ls -la /etc/cron.d/ 2>/dev/null

sub "Yedekleme izi var mı? (restic/borg/rsync)"
for c in restic borg rclone rsnapshot; do
  have "$c" && echo "  KURULU: $c ($($c version 2>/dev/null | head -1))"
done
systemctl list-units --all --no-pager 2>/dev/null | grep -iE 'backup|restic|borg' || echo "  (yedekleme servisi/timer'ı bulunamadı)"

# =============================================================================
section "9. SNOW SERVİS SAĞLIĞI"
# =============================================================================
sub "Snow /health (localhost)"
curl -sS -m 5 http://127.0.0.1:8787/api/v1/health 2>&1 | head -c 900; echo

sub "Home Assistant erişilebilir mi?"
curl -sS -m 5 -o /dev/null -w '  HTTP %{http_code}  (%{time_total}s)\n' http://127.0.0.1:8123/ 2>&1

sub "Snow container logu (son 25 satır)"
docker logs --tail 25 snow 2>&1 || echo "  ('snow' adlı container bulunamadı)"

sub "Sistem günlüğünde hata/uyarı (son 20)"
journalctl -p err -n 20 --no-pager 2>/dev/null || echo "  (journalctl okunamadı — sudo gerekli)"

# =============================================================================
printf '\n\n################################################################\n'
printf '#  ENVANTER TAMAMLANDI — hiçbir değişiklik yapılmadı.\n'
printf '#  Bu çıktının TAMAMINI sohbete yapıştır.\n'
printf '#  Sırlar maskelendi; yine de göz gezdirip emin ol.\n'
printf '################################################################\n'
