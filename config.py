"""
LED Pano Kontrol Sistemi - Yapılandırma Dosyası
Bu dosya, sistem ayarlarını ve LED pano parametrelerini içerir.
"""

import os
from pathlib import Path

# Proje kök dizini
BASE_DIR = Path(__file__).parent.absolute()

# Flask Uygulama Ayarları
class Config:
    # Flask temel ayarları
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'led-panel-secret-key-2024'
    DEBUG = False
    TESTING = False
    
    # Sunucu ayarları
    HOST = '0.0.0.0'  # Tüm ağ arayüzlerinden erişim
    PORT = 5000
    
    # Dosya yükleme ayarları
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB maksimum dosya boyutu
    
    # İzin verilen dosya uzantıları
    ALLOWED_EXTENSIONS = {
        'image': {'png', 'jpg', 'jpeg', 'gif', 'bmp'},
        'video': {'mp4', 'avi', 'mov', 'mkv', 'wmv'}
    }
    
    # Log ayarları
    LOG_FOLDER = os.path.join(BASE_DIR, 'logs')
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# LED Pano Donanım Ayarları
class LEDPanelConfig:
    # Panel boyutları (kendi panelinize göre ayarlayın)
    PANEL_ROWS = 32      # Panel satır sayısı
    PANEL_COLS = 64      # Panel sütun sayısı
    
    # Donanım haritası (kullandığınız HAT'a göre değiştirin)
    HARDWARE_MAPPING = 'adafruit-hat'  # 'adafruit-hat', 'rpi-pwm', 'regular'
    
    # Panel zinciri ayarları
    CHAIN_LENGTH = 1     # Zincirdeki panel sayısı
    PARALLEL = 1         # Paralel panel sayısı
    
    # Görüntü kalitesi ayarları
    BRIGHTNESS = 100     # Parlaklık (0-100)
    PWM_BITS = 11        # PWM bit derinliği
    PWM_LSB_NANOS = 130  # PWM LSB nanosaniye
    
    # GPIO ayarları
    GPIO_SLOWDOWN = 4    # GPIO hız yavaşlatma (titreşim azaltma)
    DISABLE_HARDWARE_PULSING = True  # Donanım titreşimini devre dışı bırak
    
    # RGB sıralama (panel tipine göre değişebilir)
    RGB_SEQUENCE = 'RGB'  # 'RGB', 'RBG', 'GRB', 'GBR', 'BRG', 'BGR'
    
    # Görüntü işleme ayarları
    IMAGE_SCALE_MODE = 'fast'  # 'fast', 'quality'
    IMAGE_INTERPOLATION = 'lanczos'  # 'nearest', 'bilinear', 'bicubic', 'lanczos'

# İçerik Gösterim Ayarları
class DisplayConfig:
    # Varsayılan gösterim süreleri (saniye)
    DEFAULT_IMAGE_DURATION = 5
    DEFAULT_VIDEO_DURATION = 30
    
    # Geçiş efektleri
    TRANSITION_DURATION = 0.5  # Geçiş süresi (saniye)
    ENABLE_TRANSITIONS = True
    
    # Döngü ayarları
    LOOP_CONTENT = True
    SHUFFLE_CONTENT = False
    
    # Performans ayarları
    FRAME_RATE = 30  # Video frame rate
    BUFFER_SIZE = 1024  # Video buffer boyutu

# Web Arayüzü Ayarları
class WebConfig:
    # Sayfa başlığı
    PAGE_TITLE = "Erzurum Büyükşehir Belediyesi | LED Pano Yönetim Sistemi"
    
    # Arayüz ayarları
    AUTO_REFRESH_INTERVAL = 1000  # Otomatik yenileme aralığı (ms)
    UPLOAD_PROGRESS_BAR = True
    
    # Dosya boyutu sınırları (MB)
    MAX_IMAGE_SIZE = 50
    MAX_VIDEO_SIZE = 100
    
    # Desteklenen formatlar
    SUPPORTED_FORMATS = {
        'image': ['PNG', 'JPG', 'JPEG', 'GIF', 'BMP'],
        'video': ['MP4', 'AVI', 'MOV', 'MKV', 'WMV']
    }

# Sistem Ayarları
class SystemConfig:
    # Sistem servis ayarları
    SERVICE_NAME = 'led_panel_app'
    SERVICE_DESCRIPTION = 'Flask LED Panel Control Application'
    
    # Otomatik başlatma
    AUTO_START = True
    START_ON_BOOT = True
    
    # Güvenlik ayarları
    ENABLE_SSL = False
    SSL_CERT_PATH = None
    SSL_KEY_PATH = None
    
    # Backup ayarları
    AUTO_BACKUP = True
    BACKUP_INTERVAL = 24  # Saat
    BACKUP_RETENTION = 7  # Gün

# Geliştirme Ayarları
class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    
    # Geliştirme için ek ayarlar
    RELOAD_ON_CHANGE = True
    SHOW_ERROR_DETAILS = True

# Test Ayarları
class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    
    # Test için geçici dosya yolları
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'test_uploads')
    LOG_FOLDER = os.path.join(BASE_DIR, 'test_logs')

# Üretim Ayarları
class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    
    # Üretim güvenlik ayarları
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # SSL ayarları (isteğe bağlı)
    ENABLE_SSL = os.environ.get('ENABLE_SSL', 'False').lower() == 'true'
    SSL_CERT_PATH = os.environ.get('SSL_CERT_PATH')
    SSL_KEY_PATH = os.environ.get('SSL_KEY_PATH')

# Yapılandırma seçimi
def get_config():
    """Ortama göre yapılandırma döndürür"""
    config_name = os.environ.get('FLASK_ENV', 'production').lower()
    
    if config_name == 'development':
        return DevelopmentConfig
    elif config_name == 'testing':
        return TestingConfig
    elif config_name == 'production':
        return ProductionConfig
    else:
        return Config

# Aktif yapılandırma
config = get_config()

# Dizin oluşturma fonksiyonu
def create_directories():
    """Gerekli dizinleri oluşturur"""
    directories = [
        config.UPLOAD_FOLDER,
        config.LOG_FOLDER,
        os.path.join(BASE_DIR, 'static'),
        os.path.join(BASE_DIR, 'templates'),
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Yapılandırma doğrulama
def validate_config():
    """Yapılandırma ayarlarını doğrular"""
    errors = []
    
    # Panel boyutları kontrolü
    if LEDPanelConfig.PANEL_ROWS <= 0 or LEDPanelConfig.PANEL_COLS <= 0:
        errors.append("Panel boyutları pozitif olmalıdır")
    
    # Parlaklık kontrolü
    if not 0 <= LEDPanelConfig.BRIGHTNESS <= 100:
        errors.append("Parlaklık 0-100 arasında olmalıdır")
    
    # Dosya boyutu kontrolü
    if config.MAX_CONTENT_LENGTH <= 0:
        errors.append("Maksimum dosya boyutu pozitif olmalıdır")
    
    return errors

# Yapılandırma bilgilerini yazdırma
def print_config_info():
    """Yapılandırma bilgilerini konsola yazdırır"""
    print("=== LED Pano Kontrol Sistemi Yapılandırması ===")
    print(f"Panel Boyutları: {LEDPanelConfig.PANEL_ROWS}x{LEDPanelConfig.PANEL_COLS}")
    print(f"Donanım Haritası: {LEDPanelConfig.HARDWARE_MAPPING}")
    print(f"Parlaklık: {LEDPanelConfig.BRIGHTNESS}%")
    print(f"Sunucu: {config.HOST}:{config.PORT}")
    print(f"Debug Modu: {config.DEBUG}")
    print(f"Yükleme Klasörü: {config.UPLOAD_FOLDER}")
    print("=" * 50)

if __name__ == "__main__":
    # Test için yapılandırma bilgilerini yazdır
    print_config_info()
    
    # Dizinleri oluştur
    create_directories()
    
    # Yapılandırmayı doğrula
    errors = validate_config()
    if errors:
        print("Yapılandırma hataları:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Yapılandırma doğrulandı ✓") 