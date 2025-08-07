# LED Panel Control System - Multi-Location

Erzurum Büyükşehir Belediyesi LED Panel Kontrol Sistemi - Çoklu Lokasyon Desteği

## 🎯 Proje Açıklaması

Bu sistem, farklı lokasyonlardaki LED panelleri merkezi olarak yönetmek ve internet kesintilerinde bile bağımsız çalışabilmek için tasarlanmıştır.

### Özellikler

- ✅ **Çoklu Lokasyon Desteği**: Belediye, Havuzbaşı, Yenişehir, Gürcükapı
- ✅ **Bağımsız Çalışma**: İnternet kesintisinde bile çalışmaya devam eder
- ✅ **Real-time Güncelleme**: WebSocket ile anlık durum takibi
- ✅ **Dosya Yönetimi**: Resim ve video dosyaları için destek
- ✅ **Otomatik Süre Hesaplama**: Video dosyaları için otomatik süre tespiti
- ✅ **Responsive Tasarım**: Mobil ve masaüstü uyumlu arayüz
- ✅ **Güvenlik**: Kullanıcı girişi ve yetkilendirme

## 🏗️ Sistem Mimarisi

### Normal Mod (İnternet Var)
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Merkezi       │    │   Raspberry Pi  │    │   Raspberry Pi  │
│   Sunucu        │◄──►│   Belediye      │    │   Havuzbaşı     │
│   10.10.0.150   │    │   192.168.1.10  │    │   192.168.1.11  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Standalone Mod (İnternet Yok)
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Raspberry Pi  │    │   Raspberry Pi  │    │   Raspberry Pi  │
│   Belediye      │    │   Havuzbaşı     │    │   Yenişehir     │
│   192.168.1.10  │    │   192.168.1.11  │    │   192.168.1.12  │
│   (Bağımsız)    │    │   (Bağımsız)    │    │   (Bağımsız)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Gereksinimler

### Python Paketleri
```
flask
flask-socketio
flask-login
werkzeug
opencv-python
psutil
python-socketio
```

### Sistem Gereksinimleri
- Python 3.7+
- FFmpeg (video işleme için)
- OpenCV
- Raspberry Pi (lokasyon cihazları için)

## 🚀 Kurulum

### 1. Merkezi Sunucu Kurulumu

```bash
# Projeyi klonla
git clone <repository-url>
cd ledkontrol

# Sanal ortam oluştur
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate     # Windows

# Bağımlılıkları yükle
pip install -r requirements.txt

# Uygulamayı başlat
python app_final.py
```

### 2. Raspberry Pi Kurulumu

Her lokasyon için ayrı Raspberry Pi kurulumu:

```bash
# Raspberry Pi'da
cd /home/pi
git clone <repository-url> ledkontrol
cd ledkontrol

# Kurulum scriptini çalıştır
python3 setup_raspberry_pi.py belediye    # Belediye için
python3 setup_raspberry_pi.py havuzbasi   # Havuzbaşı için
python3 setup_raspberry_pi.py yenisehir   # Yenişehir için
python3 setup_raspberry_pi.py gurcukapi   # Gürcükapı için

# Sistemi yeniden başlat
sudo reboot
```

## 🔧 Konfigürasyon

### Environment Variables

```bash
# Standalone mod için
export LED_LOCATION=belediye
export STANDALONE_MODE=true

# Normal mod için
export STANDALONE_MODE=false
```

### Static IP Ayarları

Her lokasyon için sabit IP adresleri:
- Belediye: 192.168.1.10
- Havuzbaşı: 192.168.1.11
- Yenişehir: 192.168.1.12
- Gürcükapı: 192.168.1.13

## 📱 Kullanım

### Web Arayüzü Erişimi

#### Merkezi Sunucu
```
http://10.10.0.150:5000/
```

#### Lokasyon Cihazları
```
http://192.168.1.10:5000/  # Belediye
http://192.168.1.11:5000/  # Havuzbaşı
http://192.168.1.12:5000/  # Yenişehir
http://192.168.1.13:5000/  # Gürcükapı
```

### Tam Ekran Modu
```
http://192.168.1.10:5000/screenbelediye
http://192.168.1.11:5000/screenhavuzbasi
http://192.168.1.12:5000/screenyenisehir
http://192.168.1.13:5000/screengurcukapi
```

### Giriş Bilgileri
- **Kullanıcı Adı:** admin
- **Şifre:** admin123

## 📁 Proje Yapısı

```
ledkontrol/
├── app_final.py              # Ana uygulama
├── setup_raspberry_pi.py     # Raspberry Pi kurulum scripti
├── requirements.txt          # Python bağımlılıkları
├── README.md                 # Bu dosya
├── .gitignore               # Git ignore kuralları
├── config.py                # Konfigürasyon (eski)
├── static/                  # CSS, JS, resimler
│   ├── style.css
│   ├── script.js
│   └── erzurum-buyuksehir-belediyesi-logo.png
├── templates/               # HTML şablonları
│   ├── index.html
│   ├── index_location.html
│   ├── index_selector.html
│   ├── login.html
│   ├── screen.html
│   └── screen_location.html
├── uploads/                 # Yüklenen dosyalar (git'e dahil değil)
│   ├── belediye/
│   ├── havuzbasi/
│   ├── yenisehir/
│   └── gurcukapi/
└── logs/                    # Log dosyaları (git'e dahil değil)
    └── app.log
```

## 🔄 Çalışma Modları

### Normal Mod
- Merkezi sunucu tüm lokasyonları yönetir
- İnternet bağlantısı gereklidir
- Tüm lokasyonlar tek yerden kontrol edilir

### Standalone Mod
- Her lokasyon bağımsız çalışır
- İnternet bağlantısı gerekmez
- Sadece kendi lokasyonunu yönetir

## 🛠️ API Endpoints

### İçerik Yönetimi
- `GET /api/<location>/content` - İçerik listesi
- `POST /api/<location>/content/upload` - Dosya yükleme
- `DELETE /api/<location>/content/<id>` - İçerik silme
- `PUT /api/<location>/content/<id>/duration` - Süre güncelleme
- `PUT /api/<location>/content/<id>/active` - Aktiflik durumu

### Gösterim Kontrolü
- `POST /api/<location>/display/start` - Gösterim başlat
- `POST /api/<location>/display/stop` - Gösterim durdur
- `GET /api/<location>/display/status` - Gösterim durumu

### Sistem Bilgileri
- `GET /api/system/info` - CPU, RAM, Disk kullanımı

## 🔒 Güvenlik

- Kullanıcı girişi zorunludur
- Şifre hash'lenmiş olarak saklanır
- Session yönetimi Flask-Login ile yapılır

## 📝 Loglama

Sistem logları `logs/app.log` dosyasında tutulur:
- Uygulama başlatma/durdurma
- Dosya yükleme/silme işlemleri
- Gösterim durumu değişiklikleri
- Hata mesajları

## 🚨 Sorun Giderme

### Yaygın Sorunlar

1. **Port 5000 Açık Değil**
   ```bash
   # Windows
   netsh advfirewall firewall add rule name="Flask 5000" dir=in action=allow protocol=TCP localport=5000
   
   # Linux
   sudo ufw allow 5000
   ```

2. **Video Süresi Alınamıyor**
   - FFmpeg kurulu olduğundan emin olun
   - Video dosyası bozuk olabilir

3. **Static IP Çalışmıyor**
   - Router ayarlarını kontrol edin
   - IP çakışması olabilir

### Debug Modu

```bash
# Debug bilgilerini görmek için
curl http://localhost:5000/api/<location>/debug/state
```

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## 📄 Lisans

Bu proje Erzurum Büyükşehir Belediyesi için geliştirilmiştir.

## 📞 İletişim

- **Geliştirici:** [İsim]
- **E-posta:** [E-posta]
- **Proje:** [GitHub Repository URL]

---

**Not:** Bu sistem internet kesintilerinde bile çalışmaya devam edecek şekilde tasarlanmıştır. Her lokasyonda bağımsız çalışan Raspberry Pi cihazları sayesinde kesintisiz hizmet sağlanır.
