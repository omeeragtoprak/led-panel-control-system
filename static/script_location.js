document.addEventListener('DOMContentLoaded', function() {
    console.log('Location page DOM loaded, initializing SocketIO...');
    
    // Lokasyon bilgisini al (HTML'den)
    const currentLocation = window.CURRENT_LOCATION;
    const locationTitle = window.LOCATION_TITLE;
    
    console.log(`Aktif lokasyon: ${currentLocation}`);
    
    // SocketIO bağlantısı
    const socket = io({
        transports: ['websocket', 'polling'],
        timeout: 20000
    });

    // Element referansları
    const startBtn = document.getElementById('start-display');
    const stopBtn = document.getElementById('stop-display');
    const clearBtn = document.getElementById('clear-panel');
    const fullscreenBtn = document.getElementById('fullscreen-toggle');
    const displayStatus = document.getElementById('display-status-indicator');
    const contentListEl = document.getElementById('content-list');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadProgress = document.getElementById('upload-progress');
    const cpuUsageEl = document.getElementById('cpu-usage');
    const memoryUsageEl = document.getElementById('memory-usage');
    const diskUsageEl = document.getElementById('disk-usage');
    const toastContainer = document.getElementById('toast-container');
    const connectionStatusEl = document.getElementById('connection-status');
    const currentDisplayInfo = document.getElementById('current-display-info');
    const contentCount = document.getElementById('content-count');
    const currentTimeEl = document.getElementById('current-time');
    
    // Duration settings elements
    const durationSettings = document.getElementById('duration-settings');
    const durationSlider = document.getElementById('duration-slider');
    const durationInput = document.getElementById('duration-input');
    const presetButtons = document.querySelectorAll('.preset-btn');
    
    // Global değişkenler
    let currentDisplayItem = null;
    let isDisplayRunning = false;
    let contentList = [];
    
    // Sortable.js başlat
    let sortable = new Sortable(contentListEl, {
        animation: 150,
        ghostClass: 'sortable-ghost',
        onEnd: function (evt) {
            updateContentOrder();
        }
    });

    // Event Listeners
    startBtn.addEventListener('click', startDisplay);
    stopBtn.addEventListener('click', stopDisplay);
    clearBtn.addEventListener('click', clearPanel);
    fullscreenBtn.addEventListener('click', openFullscreen);
    fileInput.addEventListener('change', handleFileSelect);
    uploadBtn.addEventListener('click', uploadFiles);
    
    // Duration settings event listeners
    durationSlider.addEventListener('input', function() {
        durationInput.value = this.value;
        updatePresetButtons();
    });
    
    durationInput.addEventListener('input', function() {
        durationSlider.value = this.value;
        updatePresetButtons();
    });
    
    presetButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const duration = parseInt(this.dataset.duration);
            durationSlider.value = duration;
            durationInput.value = duration;
            updatePresetButtons();
        });
    });

    // SocketIO Events
    socket.on('connect', function() {
        console.log(`${currentLocation} bağlandı, ID: ${socket.id}`);
        connectionStatusEl.innerHTML = '<i class=\"fas fa-circle\"></i> Bağlı';
        connectionStatusEl.className = 'status-badge online';
        
        // Lokasyona katıl ve ilk verileri al
        socket.emit('join_location', { location: currentLocation });
    });

    socket.on('disconnect', function() {
        console.log(`${currentLocation} bağlantısı koptu`);
        connectionStatusEl.innerHTML = '<i class=\"fas fa-circle\"></i> Bağlantı Yok';
        connectionStatusEl.className = 'status-badge offline';
    });

    socket.on('display_status', function(data) {
        console.log(`${currentLocation} display_status aldı:`, data);
        if (data && data.location === currentLocation) {
            handleDisplayStatus(data);
            // Yönetim panelindeki gösterimi güncelle
            updatePlaybackUI(data.status, data.current_item);
        }
    });

    socket.on('content_updated', function(data) {
        console.log(`${currentLocation} content_updated aldı:`, data);
        if (data && data.location === currentLocation) {
            handleContentUpdate(data);
        }
    });

    // Ana fonksiyonlar
    function startDisplay() {
        fetch(`/api/${currentLocation}/display/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Gösterim başlatıldı', 'success');
            } else {
                showToast(data.error || 'Gösterim başlatılamadı', 'error');
            }
        })
        .catch(error => {
            console.error('Başlatma hatası:', error);
            showToast('Bağlantı hatası', 'error');
        });
    }

    function stopDisplay() {
        fetch(`/api/${currentLocation}/display/stop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Gösterim durduruldu', 'success');
            } else {
                showToast(data.error || 'Gösterim durdurulamadı', 'error');
            }
        })
        .catch(error => {
            console.error('Durdurma hatası:', error);
            showToast('Bağlantı hatası', 'error');
        });
    }

    function clearPanel() {
        showClearPanelDialog();
    }

    function showClearPanelDialog() {
        const modal = document.getElementById('clear-panel-dialog');
        modal.style.display = 'flex';
    }

    function closeClearPanelDialog() {
        const modal = document.getElementById('clear-panel-dialog');
        modal.style.display = 'none';
    }

    function confirmClearPanel() {
        fetch(`/api/${currentLocation}/content/clear`, { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('Panel temizlendi', 'success');
                    fetchContentList();
                } else {
                    showToast(data.error || 'Temizleme hatası', 'error');
                }
                closeClearPanelDialog();
            })
            .catch(error => {
                console.error('Temizleme hatası:', error);
                showToast('Temizleme başarısız', 'error');
                closeClearPanelDialog();
            });
    }

    function openFullscreen() {
        window.open(`/screen${currentLocation}`, '_blank');
    }

    function handleFileSelect() {
        const files = Array.from(fileInput.files);
        uploadBtn.disabled = files.length === 0;
        
        if (files.length > 0) {
            uploadBtn.textContent = `${files.length} dosya yükle`;
            
            // Dosya türüne göre süre ayarlarını göster/gizle
            const file = files[0];
            console.log('Dosya seçildi:', file.name, 'Tür:', file.type);
            
            if (file.type.startsWith('video/')) {
                // Video dosyaları için süre ayarlarını gizle
                durationSettings.style.display = 'none';
                console.log('Video dosyası seçildi, süre ayarları gizlendi');
            } else {
                // Resim dosyaları için süre ayarlarını göster
                durationSettings.style.display = 'block';
                console.log('Resim dosyası seçildi, süre ayarları gösterildi');
            }
        } else {
            uploadBtn.textContent = 'Yükle';
            durationSettings.style.display = 'none';
        }
    }

    function uploadFiles() {
        const files = Array.from(fileInput.files);
        if (files.length === 0) return;

        const formData = new FormData();
        
        // Dosya türüne göre süre bilgisini ekle
        files.forEach(file => {
            formData.append('file', file);
        });
        
        // Sadece resim dosyaları için süre bilgisini ekle
        const hasImageFile = files.some(file => !file.type.startsWith('video/'));
        if (hasImageFile) {
            const duration = parseInt(durationInput.value) || 7;
            formData.append('duration', duration);
        }

        // Progress bar'ı hazırla
        uploadProgress.style.display = 'block';
        const progressFill = uploadProgress.querySelector('.progress-fill');
        const progressText = uploadProgress.querySelector('.progress-text');
        progressFill.style.width = '0%';
        progressText.textContent = 'Yükleniyor... 0%';
        uploadBtn.disabled = true;

        // XMLHttpRequest ile gerçek zamanlı progress
        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                progressFill.style.width = percentComplete + '%';
                progressText.textContent = `Yükleniyor... ${Math.round(percentComplete)}%`;
            }
        });

        xhr.addEventListener('load', function() {
            if (xhr.status === 200) {
                try {
                    const data = JSON.parse(xhr.responseText);
                    if (data.success) {
                        progressFill.style.width = '100%';
                        progressText.textContent = 'Yükleme tamamlandı!';
                        progressText.classList.add('completed');
                        
                        setTimeout(() => {
                            uploadProgress.style.display = 'none';
                            uploadBtn.disabled = false;
                            progressText.classList.remove('completed');
                            showToast('Dosya(lar) başarıyla yüklendi', 'success');
                            fileInput.value = '';
                            uploadBtn.textContent = 'Yükle';
                            uploadBtn.disabled = true;
                            durationSettings.style.display = 'none';
                        }, 1000);
                    } else {
                        uploadProgress.style.display = 'none';
                        uploadBtn.disabled = false;
                        showToast(data.error || 'Yükleme hatası', 'error');
                    }
                } catch (e) {
                    uploadProgress.style.display = 'none';
                    uploadBtn.disabled = false;
                    showToast('Yanıt işlenirken hata oluştu', 'error');
                }
            } else {
                uploadProgress.style.display = 'none';
                uploadBtn.disabled = false;
                showToast('Yükleme başarısız', 'error');
            }
        });

        xhr.addEventListener('error', function() {
            uploadProgress.style.display = 'none';
            uploadBtn.disabled = false;
            showToast('Bağlantı hatası', 'error');
        });

        xhr.addEventListener('abort', function() {
            uploadProgress.style.display = 'none';
            uploadBtn.disabled = false;
            showToast('Yükleme iptal edildi', 'error');
        });

        xhr.open('POST', `/api/${currentLocation}/content/upload`);
        xhr.send(formData);
    }

    function fetchContentList() {
        fetch(`/api/${currentLocation}/content`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    contentList = data.content;
                    renderContentList();
                }
            })
            .catch(error => console.error('İçerik listesi alınamadı:', error));
    }

    function fetchDisplayStatus() {
        fetch(`/api/${currentLocation}/display/status`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    handleDisplayStatus(data);
                }
            })
            .catch(error => console.error('Gösterim durumu alınamadı:', error));
    }

    function updateContentOrder() {
        const listItems = Array.from(contentListEl.children);
        const orderData = listItems.map((item, index) => ({
            id: parseInt(item.dataset.id),
            order: index
        }));

        fetch(`/api/${currentLocation}/content/order`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order: orderData })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Sıralama güncellendi', 'success');
            }
        })
        .catch(error => {
            console.error('Sıralama hatası:', error);
            showToast('Sıralama güncellenemedi', 'error');
        });
    }

    function deleteContent(id) {
        // İçerik bilgisini bul
        const item = contentList.find(item => item.id == id);
        if (!item) {
            showToast('İçerik bulunamadı.', 'error');
            return;
        }
        
        // Modal'ı göster
        showDeleteDialog(item);
    }

    // Modal dialog fonksiyonları
    let itemToDelete = null;

    function showDeleteDialog(item) {
        itemToDelete = item;
        const modal = document.getElementById('delete-dialog');
        const itemInfo = document.getElementById('modal-item-info');
        
        // İçerik bilgisini göster
        const fileType = item.type === 'video' ? 'Video' : 'Resim';
        const duration = item.duration ? `${item.duration} saniye` : 'Süre belirtilmemiş';
        itemInfo.innerHTML = `
            <strong>${fileType}:</strong> ${item.filename}<br>
            <strong>Süre:</strong> ${duration}<br>
            <strong>Boyut:</strong> ${formatFileSize(item.size || 0)}
        `;
        
        modal.style.display = 'flex';
    }

    function closeDeleteDialog() {
        const modal = document.getElementById('delete-dialog');
        modal.style.display = 'none';
        itemToDelete = null;
    }

    function confirmDelete() {
        if (!itemToDelete) {
            showToast('Silinecek içerik bulunamadı.', 'error');
            return;
        }

        fetch(`/api/${currentLocation}/content/${itemToDelete.id}`, { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('İçerik silindi', 'success');
                } else {
                    showToast(data.error || 'Silme hatası', 'error');
                }
                closeDeleteDialog();
                // İçerik listesini güncelle
                fetchContentList();
            })
            .catch(error => {
                console.error('Silme hatası:', error);
                showToast('Silme başarısız', 'error');
                closeDeleteDialog();
            });
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Modal dışına tıklandığında kapatma
    document.addEventListener('click', function(event) {
        const deleteModal = document.getElementById('delete-dialog');
        const clearModal = document.getElementById('clear-panel-dialog');
        if (event.target === deleteModal) {
            closeDeleteDialog();
        }
        if (event.target === clearModal) {
            closeClearPanelDialog();
        }
    });

    // ESC tuşu ile modal kapatma
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeDeleteDialog();
            closeClearPanelDialog();
        }
    });

    // Global fonksiyonları window objesine ekle
    window.closeDeleteDialog = closeDeleteDialog;
    window.confirmDelete = confirmDelete;
    window.closeClearPanelDialog = closeClearPanelDialog;
    window.confirmClearPanel = confirmClearPanel;
    window.previewContent = previewContent;

    
    function previewContent(filename, type) {
        // Önizleme modal'ını göster
        const modal = document.createElement('div');
        modal.className = 'preview-modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        `;
        
        const content = document.createElement('div');
        content.style.cssText = `
            max-width: 80%;
            max-height: 80%;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            position: relative;
        `;
        
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '×';
        closeBtn.style.cssText = `
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.5);
            color: white;
            border: none;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            font-size: 20px;
            cursor: pointer;
            z-index: 1001;
        `;
        closeBtn.onclick = () => document.body.removeChild(modal);
        
        if (type === 'image') {
            const img = document.createElement('img');
            img.src = `/uploads/${currentLocation}/${filename}`;
            img.style.cssText = 'max-width: 100%; max-height: 100%; display: block;';
            content.appendChild(img);
        } else {
            const video = document.createElement('video');
            video.src = `/uploads/${currentLocation}/${filename}`;
            video.controls = true;
            video.style.cssText = 'max-width: 100%; max-height: 100%; display: block;';
            content.appendChild(video);
        }
        
        content.appendChild(closeBtn);
        modal.appendChild(content);
        document.body.appendChild(modal);
        
        // Modal dışına tıklandığında kapatma
        modal.onclick = (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        };
        
        // ESC tuşu ile kapatma
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                document.body.removeChild(modal);
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }

    function renderContentList() {
        contentListEl.innerHTML = '';
        
        if (contentList.length === 0) {
            contentListEl.innerHTML = '<li class=\"no-content\"><i class=\"fas fa-inbox\"></i> Henüz içerik yüklenmedi</li>';
            contentCount.textContent = '0 içerik';
            return;
        }

        contentCount.textContent = `${contentList.length} içerik`;

        contentList.forEach((item, index) => {
            const li = document.createElement('li');
            li.className = 'content-item';
            li.dataset.id = item.id;
            
            const iconClass = item.type === 'image' ? 'fa-file-image' : 'fa-file-video';
            const duration = item.duration || (item.type === 'image' ? 7 : 15);
            const typeText = item.type === 'image' ? `Resim (${duration}s)` : `Video (${duration}s)`;
            const durationText = item.type === 'image' ? `${duration}s` : `${duration}s`;
            
                        // Tüm dosya türleri için süre düzenleme butonu göster
            const durationButton = `<button class=\"action-btn duration-btn\" onclick=\"editDuration(${item.id}, ${duration}, '${item.filename}')\">
                      <i class=\"fas fa-clock\"></i>
                    </button>`;
            
            li.innerHTML = `
                <div class=\"item-info\">
                    <div class=\"item-icon\">
                        <i class=\"fas ${iconClass}\"></i>
                    </div>
                    <div class=\"item-details\">
                        <span class=\"item-title\">${item.filename}</span>
                        <span class=\"item-type\">${typeText}</span>
                    </div>
                </div>
                <div class=\"item-duration\">${durationText}</div>
                <div class=\"item-order\">${index + 1}</div>
                <div class=\"item-actions\">
                    ${durationButton}
                    <button class=\"action-btn preview-btn\" onclick=\"previewContent('${item.filename}', '${item.type}')\">
                        <i class=\"fas fa-eye\"></i>
                    </button>
                    <button class=\"action-btn delete-btn\" onclick=\"deleteContent(${item.id})\">
                        <i class=\"fas fa-trash\"></i>
                    </button>
                </div>
            `;
            
            contentListEl.appendChild(li);
        });

        highlightCurrentItem();
    }

    function highlightCurrentItem() {
        // Önce tüm öğelerden 'current' class'ını kaldır
        document.querySelectorAll('.content-item').forEach(item => {
            item.classList.remove('current');
        });

        // Şu an gösterilen öğeye 'current' class'ı ekle
        if (currentDisplayItem) {
            const currentElement = document.querySelector(`[data-id=\"${currentDisplayItem.id}\"]`);
            if (currentElement) {
                currentElement.classList.add('current');
            }
        }
    }

    function handleDisplayStatus(data) {
        console.log(`${currentLocation} handleDisplayStatus:`, data);
        
        isDisplayRunning = data.status === 'playing';
        currentDisplayItem = data.current_item;
        
        updatePlaybackUI(data.status, data.current_item);
        highlightCurrentItem();
    }

    function handleContentUpdate(data) {
        console.log(`${currentLocation} handleContentUpdate:`, data);
        
        if (data.action === 'sync' || data.action === 'upload' || data.action === 'delete' || data.action === 'reorder' || data.action === 'duration_update') {
            if (data.content_list) {
                contentList = data.content_list;
                renderContentList();
            } else {
                fetchContentList();
            }
        }
    }

    function updatePlaybackUI(status, currentItem) {
        console.log(`${currentLocation} updatePlaybackUI:`, status, currentItem);

        // Durum çubuğunu güncelle
        if (status === 'playing' && currentItem && currentItem.filename) {
            displayStatus.innerHTML = `<i class=\"fas fa-play-circle\"></i> Gösteriliyor: <strong>${currentItem.filename}</strong>`;
            displayStatus.className = 'status-indicator running';
        } else {
            displayStatus.innerHTML = '<i class=\"fas fa-stop-circle\"></i> Gösterim Durumu: DURDURULDU';
            displayStatus.className = 'status-indicator stopped';
        }

        // \"Şu An Gösterilen\" kutusunu güncelle
        if (status === 'playing' && currentItem && currentItem.filename) {
            const iconClass = currentItem.type === 'image' ? 'fa-file-image' : 'fa-file-video';
            const duration = currentItem.duration || (currentItem.type === 'image' ? 7 : 15);
            const typeText = `${currentItem.type === 'image' ? 'Resim' : 'Video'} (${duration}s)`;
            
            let mediaElement;
            if (currentItem.type === 'image') {
                mediaElement = `<img src=\"/uploads/${currentLocation}/${currentItem.filename}\" alt=\"${currentItem.filename}\" 
                                    onerror=\"this.style.display='none'; this.nextElementSibling.style.display='block';\">`;
            } else if (currentItem.type === 'video') {
                mediaElement = `<video src=\"/uploads/${currentLocation}/${currentItem.filename}\" autoplay loop muted controls></video>`;
            } else {
                mediaElement = `<i class=\"fas ${iconClass}\"></i><span>Önizleme yok</span>`;
            }

            currentDisplayInfo.innerHTML = `
                <div class=\"current-display-content\">
                    <div class=\"current-display-preview\">
                        ${mediaElement}
                        <div class=\"preview-fallback\" style=\"display: none;\">
                            <i class=\"fas ${iconClass}\"></i>
                            <span>Önizleme yüklenemedi</span>
                        </div>
                    </div>
                    <div class=\"current-display-details\">
                        <h3>${currentItem.filename}</h3>
                        <p><strong>Sıra:</strong> ${currentItem.order + 1}</p>
                        <p><strong>Tür:</strong> <span class=\"current-display-type ${currentItem.type}\">${typeText}</span></p>
                        <p><strong>Lokasyon:</strong> <span class=\"location-tag\">${locationTitle}</span></p>
                    </div>
                </div>`;
        } else {
            currentDisplayInfo.innerHTML = `
                <div class=\"current-display-placeholder\">
                    <i class=\"fas fa-tv\"></i>
                    <p>Henüz gösterim başlatılmadı</p>
                    <p class=\"location-info\">${locationTitle}</p>
                </div>`;
        }
    }

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icon = type === 'success' ? 'check-circle' : 
                     type === 'error' ? 'exclamation-triangle' : 
                     'info-circle';
        
        toast.innerHTML = `
            <i class=\"fas fa-${icon}\"></i>
            <span>${message}</span>
        `;
        
        toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toastContainer.removeChild(toast);
            }, 300);
        }, 3000);
    }

    function updateSystemInfo() {
        fetch('/api/system/info')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    cpuUsageEl.textContent = data.cpu + '%';
                    memoryUsageEl.textContent = data.memory + '%';
                    diskUsageEl.textContent = data.disk + '%';
                }
            })
            .catch(error => console.error('Sistem bilgisi alınamadı:', error));
    }

    function updateTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('tr-TR');
        currentTimeEl.textContent = timeString;
    }

    function updatePresetButtons() {
        const currentDuration = parseInt(durationInput.value);
        presetButtons.forEach(btn => {
            const btnDuration = parseInt(btn.dataset.duration);
            btn.classList.toggle('active', btnDuration === currentDuration);
        });
    }

    function editDuration(contentId, currentDuration, filename) {
        // Modal oluştur
        const modal = document.createElement('div');
        modal.className = 'duration-edit-modal';
        modal.innerHTML = `
            <div class="duration-edit-content">
                <h3><i class="fas fa-clock"></i> Süre Düzenle</h3>
                <p><strong>Dosya:</strong> ${filename}</p>
                
                <div class="duration-input-group">
                    <label for="edit-duration-slider">Gösterim Süresi:</label>
                    <div class="duration-controls">
                        <input type="range" id="edit-duration-slider" min="1" max="120" value="${currentDuration}" class="duration-slider">
                        <input type="number" id="edit-duration-input" min="1" max="120" value="${currentDuration}" class="duration-number">
                        <span class="duration-unit">saniye</span>
                    </div>
                    <div class="duration-presets">
                        <button type="button" class="preset-btn" data-duration="5">5s</button>
                        <button type="button" class="preset-btn" data-duration="7">7s</button>
                        <button type="button" class="preset-btn" data-duration="10">10s</button>
                        <button type="button" class="preset-btn" data-duration="15">15s</button>
                        <button type="button" class="preset-btn" data-duration="30">30s</button>
                        <button type="button" class="preset-btn" data-duration="60">60s</button>
                    </div>
                </div>
                
                <div class="duration-edit-actions">
                    <button class="btn-cancel">İptal</button>
                    <button class="btn-save">Kaydet</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const editSlider = modal.querySelector('#edit-duration-slider');
        const editInput = modal.querySelector('#edit-duration-input');
        const editPresets = modal.querySelectorAll('.preset-btn');
        const saveBtn = modal.querySelector('.btn-save');
        const cancelBtn = modal.querySelector('.btn-cancel');
        
        // Event listeners
        editSlider.addEventListener('input', function() {
            editInput.value = this.value;
            updateEditPresets();
        });
        
        editInput.addEventListener('input', function() {
            editSlider.value = this.value;
            updateEditPresets();
        });
        
        editPresets.forEach(btn => {
            btn.addEventListener('click', function() {
                const duration = parseInt(this.dataset.duration);
                editSlider.value = duration;
                editInput.value = duration;
                updateEditPresets();
            });
        });
        
        function updateEditPresets() {
            const currentVal = parseInt(editInput.value);
            editPresets.forEach(btn => {
                const btnDuration = parseInt(btn.dataset.duration);
                btn.classList.toggle('active', btnDuration === currentVal);
            });
        }
        
        saveBtn.addEventListener('click', function() {
            const newDuration = parseInt(editInput.value);
            if (newDuration && newDuration > 0) {
                updateContentDuration(contentId, newDuration);
                document.body.removeChild(modal);
            }
        });
        
        cancelBtn.addEventListener('click', function() {
            document.body.removeChild(modal);
        });
        
        // İlk preset güncellemesi
        updateEditPresets();
    }

    function updateContentDuration(contentId, duration) {
        fetch(`/api/${currentLocation}/content/${contentId}/duration`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ duration: duration })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Süre güncellendi', 'success');
            } else {
                showToast(data.error || 'Süre güncellenemedi', 'error');
            }
        })
        .catch(error => {
            console.error('Süre güncelleme hatası:', error);
            showToast('Güncelleme başarısız', 'error');
        });
    }

    // Global fonksiyonlar (HTML onclick için)
    window.deleteContent = deleteContent;
    window.editDuration = editDuration;
    window.previewContent = function(filename, type) {
        const url = `/uploads/${currentLocation}/${filename}`;
        window.open(url, '_blank');
    };

    // Zamanlayıcılar
    setInterval(updateSystemInfo, 10000);
    setInterval(updateTime, 1000);
    
    // İlk güncellemeler
    updateSystemInfo();
    updateTime();
    updatePresetButtons();
    fetchContentList();
    fetchDisplayStatus();
});