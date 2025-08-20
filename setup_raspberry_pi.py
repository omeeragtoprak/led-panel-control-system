#!/usr/bin/env python3
"""
Raspberry Pi LED Panel Kurulum Scripti
Her lokasyon için bağımsız çalışacak Raspberry Pi kurulumu
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(command, description=""):
    """Komut çalıştır ve sonucu göster"""
    print(f"\n{description}")
    print(f"Komut: {command}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("[OK] Başarılı")
            if result.stdout:
                print(result.stdout)
        else:
            print("[ERROR] Hata")
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"[ERROR] Hata: {e}")
        return False

def setup_static_ip(location):
    """Static IP ayarla"""
    location_ips = {
        'belediye': '192.168.1.10',
        'havuzbasi': '192.168.1.11',
        'yenisehir': '192.168.1.12',
        'gurcukapi': '192.168.1.13'
    }
    
    ip = location_ips.get(location)
    if not ip:
        print(f"[ERROR] Geçersiz lokasyon: {location}")
        return False
    
    # dhcpcd.conf dosyasını düzenle
    dhcpcd_conf = """
interface eth0
static ip_address={}/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4
""".format(ip)
    
    try:
        # Önce dosyanın var olup olmadığını kontrol et
        if not os.path.exists('/etc/dhcpcd.conf'):
            print("[WARN] /etc/dhcpcd.conf dosyası bulunamadı!")
            return False
            
        with open('/etc/dhcpcd.conf', 'a') as f:
            f.write(dhcpcd_conf)
        print(f"[OK] Static IP ayarlandı: {ip}")
        return True
    except Exception as e:
        print(f"[ERROR] Static IP ayarlama hatası: {e}")
        return False

def create_startup_script(location):
    """Otomatik başlatma scripti oluştur"""
    # Mevcut çalışma dizinini al
    current_dir = os.getcwd()
    print(f"[INFO] Mevcut dizin: {current_dir}")
    
    script_content = f"""#!/bin/bash
cd {current_dir}

# Sanal ortamı aktif et (daha güvenli yöntem)
if [ -f "led_env/bin/activate" ]; then
    source led_env/bin/activate
    echo "[OK] Sanal ortam aktif edildi"
else
    echo "[ERROR] Sanal ortam bulunamadı!"
    exit 1
fi

# Senkronizasyon sistemini başlat (arka planda)
python3 sync_system.py {location} &
SYNC_PID=$!

# Ana uygulamayı başlat
export LED_LOCATION={location}
export STANDALONE_MODE=true
python3 app_final.py

# Uygulama kapandığında senkronizasyonu da durdur
kill $SYNC_PID
"""
    
    script_path = os.path.join(current_dir, f"start_{location}.sh")
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        print(f"[OK] Başlatma scripti oluşturuldu: {script_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Script oluşturma hatası: {e}")
        return False

def setup_autostart(location):
    """Otomatik başlatma ayarla"""
    # Mevcut çalışma dizinini al
    current_dir = os.getcwd()
    
    autostart_dir = str(Path.home() / ".config" / "autostart")
    os.makedirs(autostart_dir, exist_ok=True)
    
    desktop_file = f"""[Desktop Entry]
Type=Application
Name=LED Panel {location}
Exec={current_dir}/start_{location}.sh
Terminal=false
X-GNOME-Autostart-enabled=true
"""
    
    desktop_path = f"{autostart_dir}/led-panel-{location}.desktop"
    try:
        with open(desktop_path, 'w') as f:
            f.write(desktop_file)
        print(f"[OK] Otomatik başlatma ayarlandı: {desktop_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Otomatik başlatma hatası: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Kullanım: python3 setup_raspberry_pi.py <lokasyon>")
        print("Lokasyonlar: belediye, havuzbasi, yenisehir, gurcukapi")
        sys.exit(1)
    
    location = sys.argv[1]
    if location not in ['belediye', 'havuzbasi', 'yenisehir', 'gurcukapi']:
        print("[ERROR] Geçersiz lokasyon!")
        sys.exit(1)
    
    print(f"=== Raspberry Pi LED Panel Kurulumu - {location.upper()} ===")
    print("Not: Sanal ortam ve paketler zaten kurulmuş varsayılıyor.")
    
    # Mevcut dizini kontrol et
    current_dir = os.getcwd()
    print(f"[INFO] Çalışma dizini: {current_dir}")
    
    # Gerekli dosyaların varlığını kontrol et
    if not os.path.exists('app_final.py'):
        print("❌ app_final.py dosyası bulunamadı!")
        print("   Script'i proje klasöründe çalıştırdığınızdan emin olun.")
        sys.exit(1)
    
    if not os.path.exists('led_env'):
        print("❌ led_env klasörü bulunamadı!")
        print("   Sanal ortamın kurulu olduğundan emin olun.")
        sys.exit(1)
    
    # Static IP (sudo gerekli)
    print("\n[WARN] Static IP ayarlanıyor... (sudo gerekli)")
    if not setup_static_ip(location):
        print("[WARN] Static IP ayarlanamadı, manuel olarak ayarlayabilirsiniz.")
    
    # Başlatma scripti
    if not create_startup_script(location):
        sys.exit(1)
    
    # Otomatik başlatma
    if not setup_autostart(location):
        sys.exit(1)
    
    print(f"\n[DONE] Kurulum tamamlandı!")
    print(f"Lokasyon: {location}")
    print(f"Static IP: 192.168.1.{10 + ['belediye', 'havuzbasi', 'yenisehir', 'gurcukapi'].index(location)}")
    print(f"Web arayüzü: http://192.168.1.{10 + ['belediye', 'havuzbasi', 'yenisehir', 'gurcukapi'].index(location)}:5000")
    print(f"Tam ekran: http://192.168.1.{10 + ['belediye', 'havuzbasi', 'yenisehir', 'gurcukapi'].index(location)}:5000/screen{location}")
    print(f"\nManuel başlatmak için: ./start_{location}.sh")
    print(f"Sistemi yeniden başlatmak için: sudo reboot")

if __name__ == "__main__":
    main()
