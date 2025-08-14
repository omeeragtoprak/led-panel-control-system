"""
LED Panel Control System - Final Multi-Location Version
Ana sayfa: lokasyon seçimi
Her lokasyon: /belediye, /havuzbasi, /yenisehir, /gurcukapi - tam özellikli sayfalar
"""

import os, time, json, logging, threading, subprocess
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, abort, redirect, url_for, session
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import cv2, psutil

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
class Config:
    BASE_UPLOAD = os.path.join(os.getcwd(), 'uploads')
    PAGE_TITLE = "EBB LED Kontrol Sistemi"
    HOST = '0.0.0.0'
    PORT = 5000
    SUPPORTED_FORMATS = {
        'image': {'png','jpg','jpeg','gif','bmp'},
        'video': {'mp4','avi','mov','mkv','wmv'}
    }
    
    # Lokasyon bazlı çalışma için
    CURRENT_LOCATION = os.environ.get('LED_LOCATION', 'belediye')  # Varsayılan: belediye
    STANDALONE_MODE = os.environ.get('STANDALONE_MODE', 'false').lower() == 'true'
    # SSO için shared secret (tüm cihazlarda aynı olmalı)
    SSO_SECRET = os.environ.get('SSO_SECRET', 'ebb-ledpanel-sso-shared-secret')
    SSO_TOKEN_MAX_AGE = int(os.environ.get('SSO_TOKEN_MAX_AGE', '300'))  # saniye
    
    # Her lokasyon için Raspberry Pi IP'leri
    LOCATION_IPS = {
        'belediye': '192.168.251.174',
        'havuzbasi': '192.168.251.175', 
        'yenisehir': '192.168.251.176',
        'gurcukapi': '192.168.251.177'
    }

LOCATIONS = ['belediye', 'havuzbasi', 'yenisehir', 'gurcukapi']

# Lokasyon isimleri mapping'i
LOCATION_NAMES = {
    'belediye': 'Belediye Binası LED Ekran',
    'havuzbasi': 'Havuzbaşı Kent Meydanı LED Ekran',
    'yenisehir': 'Yenişehir LED Ekran',
    'gurcukapi': 'Gürcükapı LED Ekran'
}

# ---------------------------------------------------------------------------
# FLASK & SOCKETIO SETUP
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'led_panel_secret_key_2025'
app.config['UPLOAD_FOLDER'] = Config.BASE_UPLOAD
# Upload boyutu limiti kaldırıldı (sınırsız)
app.config['MAX_CONTENT_LENGTH'] = None
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_PERMANENT'] = True

# SocketIO with threading mode (safer for Windows)
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   async_mode='threading',
                   logger=True,
                   engineio_logger=True,
                   ping_timeout=60,
                   ping_interval=25)

# Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# In-memory user store (single admin user)
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Hardcoded admin credentials (username: admin, password: EbbLed-2025!)
USERS = {
    'admin': generate_password_hash('Ebbled-2025!')
}

@login_manager.user_loader
def load_user(user_id):
    if user_id in USERS:
        return User(user_id)
    return None

# ---------------------------------------------------------------------------
# LOGGING SETUP
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GLOBAL STATE MANAGEMENT (per location)
# ---------------------------------------------------------------------------
state = {}

def init_location_state():
    """Her lokasyon için state başlatma"""
    for location in LOCATIONS:
        upload_dir = os.path.join(Config.BASE_UPLOAD, location)
        os.makedirs(upload_dir, exist_ok=True)
        
        state[location] = {
            'content': [],
            'current_index': 0,
            'is_running': False,
            'display_thread': None,
            'lock': threading.Lock(),
            'upload_dir': upload_dir,
            'content_file': os.path.join(upload_dir, 'content_list.json')
        }
        load_content_list(location)

def load_content_list(location):
    """Lokasyona özel içerik listesini yükle"""
    st = state[location]
    try:
        if os.path.exists(st['content_file']):
            with open(st['content_file'], 'r', encoding='utf-8') as f:
                st['content'] = json.load(f)
        logger.info(f"{LOCATION_NAMES[location]} içerik listesi yüklendi: {len(st['content'])} öğe")
    except Exception as e:
        logger.error(f"{location} içerik listesi yükleme hatası: {e}")
        st['content'] = []

def save_content_list(location):
    """Lokasyona özel içerik listesini kaydet"""
    st = state[location]
    try:
        with open(st['content_file'], 'w', encoding='utf-8') as f:
            json.dump(st['content'], f, ensure_ascii=False, indent=2)
        logger.debug(f"{location.title()} içerik listesi kaydedildi")
    except Exception as e:
        logger.error(f"{location} içerik listesi kaydetme hatası: {e}")

def get_video_duration(path):
    """Video süresini al - ffprobe, OpenCV ve moviepy ile"""
    try:
        # Önce ffprobe ile dene
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        logger.info(f"ffprobe ile video süresi alındı: {duration}s")
        return duration
    except FileNotFoundError:
        logger.warning("ffprobe bulunamadı, MoviePy ile deneniyor...")
    except Exception as e:
        logger.warning(f"ffprobe hatası: {e}, MoviePy ile deneniyor...")
    
    try:
        # MoviePy ile dene (ffmpeg tabanlı, genelde daha doğru)
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(path)
        duration = float(clip.duration)
        clip.close()
        logger.info(f"MoviePy ile video süresi alındı: {duration}s")
        return duration
    except Exception as e:
        logger.error(f"MoviePy ile video süresi alınırken hata: {e}")
    
    try:
        # OpenCV ile dene
        import cv2
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            logger.error(f"OpenCV ile video açılamadı: {path}")
            return 15
        
        # FPS ve frame sayısını al
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        
        if fps > 0 and frame_count > 0:
            duration = frame_count / fps
            logger.info(f"OpenCV ile video süresi alındı: {duration}s (FPS: {fps}, Frames: {frame_count})")
            return duration
        else:
            logger.error(f"OpenCV ile geçerli FPS veya frame sayısı alınamadı")
            return 15
    except Exception as e:
        logger.error(f"OpenCV ile video süresi alınırken hata: {e}")
    
    return 15

def allowed_file(filename):
    """Dosya uzantısı kontrolü"""
    if '.' not in filename:
        return False, None
    ext = filename.rsplit('.', 1)[1].lower()
    for file_type, extensions in Config.SUPPORTED_FORMATS.items():
        if ext in extensions:
            return True, file_type
    return False, None

# ---------------------------------------------------------------------------
# SSO HELPERS
# ---------------------------------------------------------------------------
def _get_sso_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(Config.SSO_SECRET, salt='led-panel-sso')

def generate_sso_token(username: str) -> str:
    serializer = _get_sso_serializer()
    return serializer.dumps({'u': username})

def verify_sso_token(token: str):
    try:
        serializer = _get_sso_serializer()
        data = serializer.loads(token, max_age=Config.SSO_TOKEN_MAX_AGE)
        return data.get('u')
    except (BadSignature, SignatureExpired):
        return None

def _remove_query_param(url: str, param: str) -> str:
    parts = urlparse(url)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    filtered = [(k, v) for (k, v) in query_items if k != param]
    new_query = urlencode(filtered, doseq=True)
    return urlunparse(parts._replace(query=new_query))

# ---------------------------------------------------------------------------
# BEFORE REQUEST: AUTH HELPERS (STANDALONE AUTO-LOGIN, SSO TOKEN)
# ---------------------------------------------------------------------------
@app.before_request
def ensure_standalone_auto_login():
    """Standalone modda tüm isteklerde otomatik admin girişi yap.

    Böylece Raspberry Pi üzerindeki lokasyon IP'lerinde hiçbir sayfa/API için
    manuel giriş gerekmez. Merkezi sunucuda (standalone değilken) çalışmaz.
    """
    try:
        if not Config.STANDALONE_MODE:
            return None
        # Login ve statik dosyalar için atla
        if request.endpoint in {'login', 'static'}:
            return None
        # Zaten girişliyse geç
        if current_user.is_authenticated:
            return None
        # Otomatik giriş
        user = User('admin')
        session.permanent = True
        login_user(user, remember=True, duration=None)
    except Exception:
        # Her durumda akışı bozma
        return None

@app.before_request
def handle_sso_auto_login():
    token = request.args.get('sso')
    if not token:
        return None
    username = verify_sso_token(token)
    if not username:
        return None
    # Zaten girişliyse ve aynı kullanıcıysa tekrar işlem yapma
    if current_user.is_authenticated and getattr(current_user, 'id', None) == username:
        # URL'den token'ı temizle
        clean_url = _remove_query_param(request.url, 'sso')
        if clean_url != request.url:
            return redirect(clean_url)
        return None
    # Otomatik giriş
    user = User(username)
    session.permanent = True
    login_user(user, remember=True, duration=None)
    clean_url = _remove_query_param(request.url, 'sso')
    return redirect(clean_url)

# ---------------------------------------------------------------------------
# DISPLAY LOOP (per location)
# ---------------------------------------------------------------------------
def display_loop(location):
    """Lokasyona özel gösterim döngüsü"""
    st = state[location]
    logger.info(f"{LOCATION_NAMES[location]} yayın döngüsü başlatıldı")
    
    while st['is_running']:
        with st['lock']:
            # Sadece aktif içerikleri sıraya al
            active_content = [item for item in st['content'] if item.get('is_active', True)]
            if not active_content:
                socketio.sleep(1)
                continue
            
            # Mevcut öğeyi al
            current_item = active_content[st['current_index'] % len(active_content)]
            filepath = os.path.join(st['upload_dir'], current_item['filename'])
            
            if not os.path.exists(filepath):
                logger.warning(f"Dosya bulunamadı: {filepath}")
                st['current_index'] = (st['current_index'] + 1) % len(active_content)
                continue
            
            logger.info(f"{LOCATION_NAMES[location]} yayında: {current_item['filename']} ({current_item['type']})")
            
            # Süre hesapla - görüntü için kullanıcı/varsayılan, video için her oynatışta dosyadan ölç
            if current_item['type'] == 'video':
                measured = None
                try:
                    measured = int(get_video_duration(filepath))
                except Exception:
                    measured = None
                duration = measured if measured and measured > 0 else int(current_item.get('duration', 15))
                # küçük bir tampon ekle (ağ/gecikme payı)
                duration = max(1, duration)
            else:
                duration = int(current_item.get('duration', 7))
            
            # Socket event gönder (current_item ile birlikte)
            socketio.emit('display_status', {
                'status': 'playing',
                'location': location,
                'current_item': current_item
            })
            
            # Sonraki öğeye geç
            st['current_index'] = (st['current_index'] + 1) % len(active_content)
        
        # Bekleme
        socketio.sleep(duration)

def start_display_thread(location):
    """Lokasyona özel gösterim thread'i başlat"""
    st = state[location]
    with st['lock']:
        # Video sürelerini başlatmadan önce doğrula/güncelle
        try:
            updated_any_duration = False
            for item in st['content']:
                if item.get('type') == 'video':
                    filepath = os.path.join(st['upload_dir'], item['filename'])
                    if os.path.exists(filepath):
                        try:
                            actual_duration = int(get_video_duration(filepath))
                            if actual_duration > 0 and abs(actual_duration - int(item.get('duration', 0))) > 1:
                                item['duration'] = actual_duration
                                updated_any_duration = True
                        except Exception as _e:
                            pass
            if updated_any_duration:
                save_content_list(location)
                # Güncellenen süreleri istemcilere duyur
                socketio.emit('content_updated', {
                    'action': 'duration_fix',
                    'location': location,
                    'content_list': st['content']
                })
        except Exception:
            pass

        if st['display_thread'] is not None:
            logger.warning(f"{location} gösterim zaten çalışıyor")
            return False
        
        if not st['content']:
            logger.warning(f"{location} içerik listesi boş")
            return False
        
        st['is_running'] = True
        st['current_index'] = 0
        st['display_thread'] = socketio.start_background_task(display_loop, location)
        logger.info(f"{LOCATION_NAMES[location]} yayın thread'i başlatıldı")
        return True

def stop_display_thread(location):
    """Lokasyona özel gösterim thread'i durdur"""
    st = state[location]
    with st['lock']:
        if st['display_thread'] is None:
            return False
        
        st['is_running'] = False
        st['display_thread'] = None
        logger.info(f"{LOCATION_NAMES[location]} yayın thread'i durduruldu")
        
        # Durdurma eventi gönder
        socketio.emit('display_status', {
            'status': 'stopped',
            'location': location,
            'current_item': None
        })
        return True

# ---------------------------------------------------------------------------
# AUTHENTICATION ROUTES
# ---------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in USERS and check_password_hash(USERS[username], password):
            user = User(username)
            session.permanent = True
            login_user(user, remember=True, duration=None)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Geçersiz kullanıcı adı veya şifre')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ---------------------------------------------------------------------------
# ROUTES - ANA SAYFA (Lokasyon Seçimi)
# ---------------------------------------------------------------------------
@app.route('/')
@login_required
def index():
    """Ana sayfa - standalone modda sadece mevcut lokasyon, normal modda tüm lokasyonlar"""
    if Config.STANDALONE_MODE:
        # Standalone modda sadece mevcut lokasyona yönlendir
        return redirect(url_for('location_page', location=Config.CURRENT_LOCATION))
    else:
        # Normal modda lokasyon seçimi
        return render_template('index_selector.html', 
                             title=Config.PAGE_TITLE,
                             locations=LOCATIONS,
                             location_names=LOCATION_NAMES,
                             location_ips=Config.LOCATION_IPS)

# ---------------------------------------------------------------------------
# ROUTES - LOKASYON SAYFALARI
# ---------------------------------------------------------------------------
@app.route('/<location>')
def location_page(location):
    """Lokasyona özel tam özellikli sayfa - Raspberry Pi'ya yönlendirme"""
    if location not in LOCATIONS:
        abort(404)
    
    # Eğer standalone modda değilse, Raspberry Pi'ya yönlendir
    if not Config.STANDALONE_MODE:
        # Merkezi sunucudan lokasyon cihazına yönlendirirken SSO belirteci ekle (oturumdan bağımsız)
        sso_token = generate_sso_token('admin')
        raspberry_pi_url = f"http://{Config.LOCATION_IPS[location]}:5000/{location}?sso={sso_token}"
        return redirect(raspberry_pi_url)
    
    # Standalone modda local sayfa göster
    return render_template('index_location.html',
                         title=f"{Config.PAGE_TITLE} - {LOCATION_NAMES[location]}",
                         location=location,
                         location_title=LOCATION_NAMES[location])

@app.route('/screen<location>')
def screen_location(location):
    """Lokasyona özel tam ekran sayfa"""
    if location not in LOCATIONS:
        abort(404)
    
    return render_template('screen_location.html', location=location)

# ---------------------------------------------------------------------------
# API ROUTES (per location)
# ---------------------------------------------------------------------------
@app.route('/api/<location>/content')
@login_required
def api_get_content(location):
    """Lokasyon içerik listesi"""
    if location not in LOCATIONS:
        abort(404)
    
    return jsonify({
        'success': True,
        'content': state[location]['content']
    })

@app.route('/api/<location>/content/upload', methods=['POST'])
@login_required
def api_upload_content(location):
    """Lokasyona dosya yükleme (çoklu dosya desteği)"""
    if location not in LOCATIONS:
        abort(404)
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Dosya seçilmedi'}), 400
    
    # Çoklu dosya desteği - request.files.getlist('file') kullan
    files = request.files.getlist('file')
    if not files or all(file.filename == '' for file in files):
        return jsonify({'success': False, 'error': 'Dosya seçilmedi'}), 400
    
    st = state[location]
    uploaded_items = []
    
    with st['lock']:
        for file in files:
            if file.filename == '':
                continue
                
            is_valid, file_type = allowed_file(file.filename)
            if not is_valid:
                logger.warning(f"Desteklenmeyen dosya formatı: {file.filename}")
                continue
            
            # Dosyayı kaydet
            filepath = os.path.join(st['upload_dir'], file.filename)
            file.save(filepath)
            
            # Süre bilgisini al (form verisi veya varsayılan)
            duration = request.form.get('duration', type=int)
            if not duration or duration <= 0:
                # Varsayılan süreler
                if file_type == 'image':
                    duration = 7
                elif file_type == 'video':
                    # Video süresini dosyadan al
                    try:
                        video_duration = get_video_duration(filepath)
                        logger.info(f"Video dosyası {file.filename} için süre hesaplandı: {video_duration}s")
                        duration = int(video_duration) if video_duration > 0 else 15
                        logger.info(f"Video süresi {duration}s olarak ayarlandı")
                    except Exception as e:
                        logger.error(f"Video süresi alınırken hata: {e}")
                        duration = 15
                else:
                    duration = 7
            
            # İçerik listesine ekle
            new_item = {
                'id': int(time.time() * 1000) + len(uploaded_items),  # Benzersiz ID için offset ekle
                'filename': file.filename,
                'type': file_type,
                'order': len(st['content']),
                'duration': duration,
                'is_active': True
            }
            
            st['content'].append(new_item)
            uploaded_items.append(new_item)
            
            logger.info(f"{LOCATION_NAMES[location]} yeni içerik: {file.filename} (süre: {duration}s)")
        
        if uploaded_items:
            save_content_list(location)
            
            # Socket event
            socketio.emit('content_updated', {
                'action': 'upload',
                'location': location,
                'content_list': st['content']
            })
    
    if uploaded_items:
        return jsonify({
            'success': True, 
            'content': uploaded_items, 
            'message': f'{len(uploaded_items)} dosya başarıyla yüklendi'
        })
    else:
        return jsonify({'success': False, 'error': 'Hiçbir geçerli dosya yüklenemedi'}), 400

@app.route('/api/<location>/content/<int:content_id>', methods=['DELETE'])
@login_required
def api_delete_content(location, content_id):
    """İçerik silme"""
    if location not in LOCATIONS:
        abort(404)
    
    st = state[location]
    
    with st['lock']:
        item = next((x for x in st['content'] if x['id'] == content_id), None)
        if not item:
            return jsonify({'success': False, 'error': 'İçerik bulunamadı'}), 404
        
        # Dosyayı sil
        filepath = os.path.join(st['upload_dir'], item['filename'])
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Listeden çıkar
        st['content'].remove(item)
        
        # Sıraları yeniden düzenle
        for i, x in enumerate(st['content']):
            x['order'] = i
        
        save_content_list(location)
        logger.info(f"{LOCATION_NAMES[location]} içerik silindi: {item['filename']}")
        
        # Socket event
        socketio.emit('content_updated', {
            'action': 'delete',
            'location': location,
            'content_list': st['content']
        })
    
    return jsonify({'success': True, 'message': 'İçerik silindi'})

@app.route('/api/<location>/content/clear', methods=['DELETE'])
@login_required
def api_clear_content(location):
    """Tüm içerikleri temizle"""
    if location not in LOCATIONS:
        abort(404)
    
    st = state[location]
    
    with st['lock']:
        # Tüm dosyaları sil
        for item in st['content']:
            filepath = os.path.join(st['upload_dir'], item['filename'])
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.info(f"Dosya silindi: {item['filename']}")
                except Exception as e:
                    logger.error(f"Dosya silinirken hata: {item['filename']} - {e}")
        
        # İçerik listesini temizle
        st['content'].clear()
        save_content_list(location)
        
        # Gösterimi durdur
        if st['is_running']:
            stop_display_thread(location)
        
        logger.info(f"{LOCATION_NAMES[location]} tüm içerikler temizlendi")
        
        # Socket event
        socketio.emit('content_updated', {
            'action': 'clear',
            'location': location,
            'content_list': []
        })
    
    return jsonify({'success': True, 'message': 'Tüm içerikler temizlendi'})

@app.route('/api/<location>/content/<int:content_id>/duration', methods=['PUT'])
@login_required
def api_update_duration(location, content_id):
    """İçerik süresini güncelle"""
    if location not in LOCATIONS:
        abort(404)
    
    data = request.get_json()
    if not data or 'duration' not in data:
        return jsonify({'success': False, 'error': 'Süre bilgisi gerekli'}), 400
    
    duration = data['duration']
    if not isinstance(duration, int) or duration <= 0:
        return jsonify({'success': False, 'error': 'Geçerli bir süre girin (1+ saniye)'}), 400
    
    st = state[location]
    
    with st['lock']:
        item = next((x for x in st['content'] if x['id'] == content_id), None)
        if not item:
            return jsonify({'success': False, 'error': 'İçerik bulunamadı'}), 404
        
        item['duration'] = duration
        save_content_list(location)
        logger.info(f"{LOCATION_NAMES[location]} içerik süresi güncellendi: {item['filename']} -> {duration}s")
        
        # Socket event
        socketio.emit('content_updated', {
            'action': 'duration_update',
            'location': location,
            'content_list': st['content']
        })
    
    return jsonify({'success': True, 'message': 'Süre güncellendi'})

@app.route('/api/<location>/content/fix-video-durations', methods=['POST'])
@login_required
def api_fix_video_durations(location):
    """Video dosyalarının sürelerini düzelt"""
    if location not in LOCATIONS:
        abort(404)
    
    st = state[location]
    fixed_count = 0
    
    with st['lock']:
        for item in st['content']:
            if item['type'] == 'video':
                filepath = os.path.join(st['upload_dir'], item['filename'])
                if os.path.exists(filepath):
                    try:
                        video_duration = get_video_duration(filepath)
                        new_duration = int(video_duration) if video_duration > 0 else 15
                        old_duration = item['duration']
                        item['duration'] = new_duration
                        fixed_count += 1
                        logger.info(f"Video süresi düzeltildi: {item['filename']} {old_duration}s -> {new_duration}s")
                    except Exception as e:
                        logger.error(f"Video süresi düzeltilirken hata: {item['filename']} - {e}")
        
        if fixed_count > 0:
            save_content_list(location)
            logger.info(f"{LOCATION_NAMES[location]} {fixed_count} video süresi düzeltildi")
            
            # Socket event
            socketio.emit('content_updated', {
                'action': 'duration_fix',
                'location': location,
                'content_list': st['content']
            })
    
    return jsonify({
        'success': True, 
        'message': f'{fixed_count} video süresi düzeltildi',
        'fixed_count': fixed_count
    })

@app.route('/api/<location>/debug/state')
@login_required
def api_debug_state(location):
    """Debug: State bilgilerini göster"""
    if location not in LOCATIONS:
        abort(404)
    
    st = state[location]
    return jsonify({
        'success': True,
        'location': location,
        'is_running': st['is_running'],
        'current_index': st['current_index'],
        'content_count': len(st['content']),
        'current_item': st['content'][st['current_index']] if st['content'] and st['is_running'] else None,
        'all_content': st['content']
    })

@app.route('/api/<location>/content/order', methods=['POST'])
@login_required
def api_update_order(location):
    """İçerik sırası güncelleme"""
    if location not in LOCATIONS:
        abort(404)
    
    data = request.get_json()
    if not data or 'order' not in data:
        return jsonify({'success': False, 'error': 'Geçersiz veri'}), 400
    
    st = state[location]
    
    with st['lock']:
        # Yeni sıralamayı uygula
        for item_data in data['order']:
            content_id = int(item_data['id'])
            new_order = int(item_data['order'])
            
            item = next((x for x in st['content'] if x['id'] == content_id), None)
            if item:
                item['order'] = new_order
        
        # Sıraya göre düzenle
        st['content'].sort(key=lambda x: x['order'])
        
        # Sıra numaralarını yeniden düzenle
        for i, item in enumerate(st['content']):
            item['order'] = i
        
        save_content_list(location)
        logger.info(f"{LOCATION_NAMES[location]} içerik sırası güncellendi")
        
        # Socket event
        socketio.emit('content_updated', {
            'action': 'reorder',
            'location': location,
            'content_list': st['content']
        })
    
    return jsonify({'success': True, 'message': 'Sıra güncellendi'})

@app.route('/api/<location>/content/<int:content_id>/active', methods=['PUT'])
@login_required
def api_update_active(location, content_id):
    """İçeriği aktif/pasif yap"""
    if location not in LOCATIONS:
        abort(404)
    data = request.get_json()
    if not data or 'is_active' not in data:
        return jsonify({'success': False, 'error': 'Durum bilgisi gerekli'}), 400
    is_active = bool(data['is_active'])
    st = state[location]
    with st['lock']:
        item = next((x for x in st['content'] if x['id'] == content_id), None)
        if not item:
            return jsonify({'success': False, 'error': 'İçerik bulunamadı'}), 404
        item['is_active'] = is_active
        save_content_list(location)
        logger.info(f"{LOCATION_NAMES[location]} içerik aktiflik güncellendi: {item['filename']} -> {is_active}")
        # Socket event
        socketio.emit('content_updated', {
            'action': 'active_update',
            'location': location,
            'content_list': st['content']
        })
    return jsonify({'success': True, 'message': 'Durum güncellendi'})

@app.route('/api/<location>/display/start', methods=['POST'])
@login_required
def api_start_display(location):
    """Gösterim başlat"""
    if location not in LOCATIONS:
        abort(404)
    
    if start_display_thread(location):
        logger.info(f"{LOCATION_NAMES[location]} gösterim başlatıldı")
        return jsonify({'success': True, 'message': 'Gösterim başlatıldı'})
    else:
        return jsonify({'success': False, 'error': 'Gösterim başlatılamadı'}), 400

@app.route('/api/<location>/display/stop', methods=['POST'])
@login_required
def api_stop_display(location):
    """Gösterim durdur"""
    if location not in LOCATIONS:
        abort(404)
    
    if stop_display_thread(location):
        logger.info(f"{LOCATION_NAMES[location]} gösterim durduruldu")
        return jsonify({'success': True, 'message': 'Gösterim durduruldu'})
    else:
        return jsonify({'success': False, 'error': 'Gösterim durdurulamadı'}), 400

@app.route('/api/<location>/display/status')
@login_required
def api_display_status(location):
    """Gösterim durumu"""
    if location not in LOCATIONS:
        abort(404)
    
    st = state[location]
    current_item = None
    
    if st['is_running'] and st['content']:
        # current_index zaten sonraki öğeyi gösteriyor, bu yüzden bir önceki öğeyi al
        # Eğer current_index 0 ise, son öğeyi al
        if st['current_index'] == 0:
            current_item = st['content'][-1]
        else:
            current_item = st['content'][st['current_index'] - 1]
    
    return jsonify({
        'success': True,
        'status': 'playing' if st['is_running'] else 'stopped',
        'location': location,
        'current_item': current_item
    })

@app.route('/api/system/info')
@login_required
def api_system_info():
    """Sistem bilgileri - SD kart ve hafıza durumu"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Hafıza hesaplamaları (GB cinsinden)
        total_gb = round(disk.total / (1024**3), 2)
        used_gb = round(disk.used / (1024**3), 2)
        free_gb = round(disk.free / (1024**3), 2)
        used_percent = round(disk.percent, 1)
        
        # RAM bilgileri (GB cinsinden)
        ram_total_gb = round(memory.total / (1024**3), 2)
        ram_used_gb = round((memory.total - memory.available) / (1024**3), 2)
        ram_free_gb = round(memory.available / (1024**3), 2)
        
        return jsonify({
            'success': True,
            'cpu': round(cpu_percent, 1),
            'memory': {
                'percent': round(memory.percent, 1),
                'total_gb': ram_total_gb,
                'used_gb': ram_used_gb,
                'free_gb': ram_free_gb
            },
            'disk': {
                'percent': used_percent,
                'total_gb': total_gb,
                'used_gb': used_gb,
                'free_gb': free_gb,
                'sd_card_size': f"{total_gb} GB SD Kart"
            },
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
    except Exception as e:
        logger.error(f"Sistem bilgisi hatası: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ---------------------------------------------------------------------------
# STATIC FILE ROUTES
# ---------------------------------------------------------------------------
@app.route('/uploads/<location>/<filename>')
def uploaded_file(location, filename):
    """Lokasyona özel dosya servisi"""
    if location not in LOCATIONS:
        abort(404)
    
    return send_from_directory(state[location]['upload_dir'], filename)

# ---------------------------------------------------------------------------
# SOCKETIO EVENTS
# ---------------------------------------------------------------------------
@socketio.on('connect')
def handle_connect():
    """Client bağlantısı"""
    try:
        logger.info(f"Client bağlandı: {request.sid}")
    except Exception as e:
        logger.error(f"Connect error: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    """Client bağlantısı koptu"""
    try:
        logger.info(f"Client ayrıldı: {request.sid}")
    except Exception as e:
        logger.error(f"Disconnect error: {e}")

@socketio.on('join_location')
def handle_join_location(data):
    """Lokasyona özel odaya katıl"""
    try:
        location = data.get('location')
        if location in LOCATIONS:
            # İlk bağlantıda mevcut durumu gönder
            st = state[location]
            emit('content_updated', {
                'action': 'sync',
                'location': location,
                'content_list': st['content']
            })
            
            # Gösterim durumunu gönder
            current_item = None
            if st['is_running'] and st['content']:
                # current_index zaten sonraki öğeyi gösteriyor, bu yüzden bir önceki öğeyi al
                if st['current_index'] == 0:
                    current_item = st['content'][-1]
                else:
                    current_item = st['content'][st['current_index'] - 1]
            
            emit('display_status', {
                'status': 'playing' if st['is_running'] else 'stopped',
                'location': location,
                'current_item': current_item
            })
    except Exception as e:
        logger.error(f"Join location error: {e}")
        emit('error', {'message': 'Bağlantı hatası'})

# ---------------------------------------------------------------------------
# APPLICATION STARTUP
# ---------------------------------------------------------------------------
def create_directories():
    """Gerekli klasörleri oluştur"""
    os.makedirs('logs', exist_ok=True)
    os.makedirs(Config.BASE_UPLOAD, exist_ok=True)

if __name__ == '__main__':
    try:
        create_directories()
        init_location_state()
        
        if Config.STANDALONE_MODE:
            print(f"\n=== STANDALONE MOD - {Config.CURRENT_LOCATION.upper()} ===")
            print(f"Lokasyon: {LOCATION_NAMES[Config.CURRENT_LOCATION]}")
            print(f"Static IP: {Config.LOCATION_IPS[Config.CURRENT_LOCATION]}")
            print(f"Web arayüzü: http://{Config.LOCATION_IPS[Config.CURRENT_LOCATION]}:{Config.PORT}/")
            print(f"Tam ekran: http://{Config.LOCATION_IPS[Config.CURRENT_LOCATION]}:{Config.PORT}/screen{Config.CURRENT_LOCATION}")
        else:
            print(f"\nMulti-Location LED Panel Control System başlatılıyor...")
            print(f"Ana sayfa: http://{Config.HOST}:{Config.PORT}/")
            print(f"Lokasyonlar: {', '.join([f'http://{Config.HOST}:{Config.PORT}/{loc} ({LOCATION_NAMES[loc]})' for loc in LOCATIONS])}")
        
        print(f"Upload klasörleri: {Config.BASE_UPLOAD}")
        print()
        
        socketio.run(app, 
                    host=Config.HOST, 
                    port=Config.PORT,
                    allow_unsafe_werkzeug=True,
                    debug=False,
                    use_reloader=False)
                    
    except KeyboardInterrupt:
        logger.info("Uygulama kapatılıyor...")
        # Tüm lokasyonların thread'lerini durdur
        for location in LOCATIONS:
            stop_display_thread(location)
    except Exception as e:
        logger.error(f"Uygulama hatası: {e}")
        raise
