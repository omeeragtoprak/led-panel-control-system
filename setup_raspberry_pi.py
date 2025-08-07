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
            print("✅ Başarılı")
            if result.stdout:
                print(result.stdout)
        else:
            print("❌ Hata")
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Hata: {e}")
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
        print(f"❌ Geçersiz lokasyon: {location}")
        return False
    
    # dhcpcd.conf dosyasını düzenle
    dhcpcd_conf = """
interface eth0
static ip_address={}/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4
""".format(ip)
    
    try:
        with open('/etc/dhcpcd.conf', 'a') as f:
            f.write(dhcpcd_conf)
        print(f"✅ Static IP ayarlandı: {ip}")
        return True
    except Exception as e:
        print(f"❌ Static IP ayarlama hatası: {e}")
        return False

def create_startup_script(location):
    """Otomatik başlatma scripti oluştur"""
    script_content = f"""#!/bin/bash
cd /home/pi/ledkontrol
source led_env/bin/activate
export LED_LOCATION={location}
export STANDALONE_MODE=true
python3 app_final.py
"""
    
    script_path = f"/home/pi/ledkontrol/start_{location}.sh"
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        print(f"✅ Başlatma scripti oluşturuldu: {script_path}")
        return True
    except Exception as e:
        print(f"❌ Script oluşturma hatası: {e}")
        return False

def setup_autostart(location):
    """Otomatik başlatma ayarla"""
    autostart_dir = "/home/pi/.config/autostart"
    os.makedirs(autostart_dir, exist_ok=True)
    
    desktop_file = f"""[Desktop Entry]
Type=Application
Name=LED Panel {location}
Exec=/home/pi/ledkontrol/start_{location}.sh
Terminal=false
X-GNOME-Autostart-enabled=true
"""
    
    desktop_path = f"{autostart_dir}/led-panel-{location}.desktop"
    try:
        with open(desktop_path, 'w') as f:
            f.write(desktop_file)
        print(f"✅ Otomatik başlatma ayarlandı: {desktop_path}")
        return True
    except Exception as e:
        print(f"❌ Otomatik başlatma hatası: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Kullanım: python3 setup_raspberry_pi.py <lokasyon>")
        print("Lokasyonlar: belediye, havuzbasi, yenisehir, gurcukapi")
        sys.exit(1)
    
    location = sys.argv[1]
    if location not in ['belediye', 'havuzbasi', 'yenisehir', 'gurcukapi']:
        print("❌ Geçersiz lokasyon!")
        sys.exit(1)
    
    print(f"=== Raspberry Pi LED Panel Kurulumu - {location.upper()} ===")
    print("Not: Sanal ortam ve paketler zaten kurulmuş varsayılıyor.")
    
    # Static IP
    if not setup_static_ip(location):
        sys.exit(1)
    
    # Başlatma scripti
    if not create_startup_script(location):
        sys.exit(1)
    
    # Otomatik başlatma
    if not setup_autostart(location):
        sys.exit(1)
    
    print(f"\n🎉 Kurulum tamamlandı!")
    print(f"Lokasyon: {location}")
    print(f"Static IP: 192.168.1.{10 + ['belediye', 'havuzbasi', 'yenisehir', 'gurcukapi'].index(location)}")
    print(f"Web arayüzü: http://192.168.1.{10 + ['belediye', 'havuzbasi', 'yenisehir', 'gurcukapi'].index(location)}:5000")
    print(f"Tam ekran: http://192.168.1.{10 + ['belediye', 'havuzbasi', 'yenisehir', 'gurcukapi'].index(location)}:5000/screen{location}")
    print(f"\nSistemi yeniden başlatmak için: sudo reboot")

if __name__ == "__main__":
    main()
