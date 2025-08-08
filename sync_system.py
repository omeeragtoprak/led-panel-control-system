#!/usr/bin/env python3
"""
LED Panel Senkronizasyon Sistemi
Merkezi sunucudan Raspberry Pi'lara içerik senkronizasyonu
"""

import os
import json
import time
import shutil
import requests
import threading
from datetime import datetime
from pathlib import Path

class ContentSync:
    def __init__(self, location, central_server_url="http://192.168.250.122:5000"):
        self.location = location
        self.central_server_url = central_server_url
        self.local_content_file = f"uploads/{location}/content_list.json"
        self.last_sync_time = 0
        self.sync_interval = 30  # 30 saniyede bir kontrol
        
    def check_internet_connection(self):
        """İnternet bağlantısını kontrol et"""
        try:
            requests.get(self.central_server_url, timeout=5)
            return True
        except:
            return False
    
    def get_central_content(self):
        """Merkezi sunucudan içerik listesini al"""
        try:
            response = requests.get(f"{self.central_server_url}/api/{self.location}/content", timeout=10)
            if response.status_code == 200:
                return response.json()['content']
            return None
        except Exception as e:
            print(f"Merkezi sunucudan içerik alınamadı: {e}")
            return None
    
    def download_file(self, filename):
        """Merkezi sunucudan dosya indir"""
        try:
            url = f"{self.central_server_url}/uploads/{self.location}/{filename}"
            response = requests.get(url, stream=True, timeout=30)
            
            if response.status_code == 200:
                local_path = f"uploads/{self.location}/{filename}"
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"✅ {filename} indirildi")
                return True
            return False
        except Exception as e:
            print(f"❌ {filename} indirilemedi: {e}")
            return False
    
    def sync_content(self):
        """İçerik senkronizasyonu yap"""
        if not self.check_internet_connection():
            print("🌐 İnternet bağlantısı yok, local modda çalışıyor...")
            return False
        
        print("🔄 Merkezi sunucudan senkronizasyon yapılıyor...")
        
        # Merkezi sunucudan içerik listesini al
        central_content = self.get_central_content()
        if not central_content:
            return False
        
        # Local içerik listesini oku
        local_content = []
        if os.path.exists(self.local_content_file):
            try:
                with open(self.local_content_file, 'r', encoding='utf-8') as f:
                    local_content = json.load(f)
            except:
                local_content = []
        
        # İçerikleri karşılaştır
        central_files = {item['filename']: item for item in central_content}
        local_files = {item['filename']: item for item in local_content}
        
        # Yeni dosyaları indir
        for filename, content_info in central_files.items():
            if filename not in local_files:
                print(f"📥 Yeni dosya: {filename}")
                if self.download_file(filename):
                    local_content.append(content_info)
        
        # Silinen dosyaları kaldır
        local_content = [item for item in local_content if item['filename'] in central_files]
        
        # İçerik listesini güncelle
        try:
            with open(self.local_content_file, 'w', encoding='utf-8') as f:
                json.dump(local_content, f, ensure_ascii=False, indent=2)
            print(f"✅ {len(local_content)} içerik senkronize edildi")
            return True
        except Exception as e:
            print(f"❌ İçerik listesi güncellenemedi: {e}")
            return False
    
    def start_sync_loop(self):
        """Sürekli senkronizasyon döngüsü"""
        print(f"🔄 {self.location} için senkronizasyon başlatıldı")
        
        while True:
            try:
                self.sync_content()
                time.sleep(self.sync_interval)
            except KeyboardInterrupt:
                print("🛑 Senkronizasyon durduruldu")
                break
            except Exception as e:
                print(f"❌ Senkronizasyon hatası: {e}")
                time.sleep(self.sync_interval)

def main():
    import sys
    
    if len(sys.argv) != 2:
        print("Kullanım: python3 sync_system.py <lokasyon>")
        print("Lokasyonlar: belediye, havuzbasi, yenisehir, gurcukapi")
        sys.exit(1)
    
    location = sys.argv[1]
    if location not in ['belediye', 'havuzbasi', 'yenisehir', 'gurcukapi']:
        print("❌ Geçersiz lokasyon!")
        sys.exit(1)
    
    # Senkronizasyon sistemini başlat
    sync_system = ContentSync(location)
    
    # İlk senkronizasyonu yap
    print(f"🚀 {location} için ilk senkronizasyon yapılıyor...")
    sync_system.sync_content()
    
    # Sürekli senkronizasyon döngüsünü başlat
    sync_system.start_sync_loop()

if __name__ == "__main__":
    main()
