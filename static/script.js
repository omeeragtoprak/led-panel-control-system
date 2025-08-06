document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing SocketIO...');
    
    // SocketIO bağlantısı
    const socket = io({
        transports: ['websocket', 'polling'],
        timeout: 20000
    });

    // Element referansları
    const startBtn = document.getElementById('start-display');
    const stopBtn = document.getElementById('stop-display');
    const clearBtn = document.getElementById('clear-panel');
    const displayStatus = document.getElementById('display-status-indicator');
    const contentListEl = document.getElementById('content-list');
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const cpuUsageEl = document.getElementById('cpu-usage');
    const ramUsageEl = document.getElementById('ram-usage');
    const diskUsageEl = document.getElementById('disk-usage');
    const toastContainer = document.getElementById('toast-container');
    const connectionStatusEl = document.getElementById('connection-status');
    const currentDisplayInfo = document.getElementById('current-display-info');
    
    // Global değişkenler
    let currentLocation = 'belediye';
    const locationButtons = document.querySelectorAll('.location-btn');
    locationButtons.forEach(btn=>{
        if(btn.dataset.loc===currentLocation) btn.classList.add('active');
        btn.addEventListener('click',()=>{
            locationButtons.forEach(b=>b.classList.remove('active'));
            btn.classList.add('active');
            currentLocation = btn.dataset.loc;
            reloadLocationData();
        });
    });

    function reloadLocationData(){
        fetchContentList();
        fetchDisplayStatus();
    }
    let currentDisplayItem = null;
    let isDisplayRunning = false;
    let contentList = [];
    
    // Sortable.js başlat
    let sortable = new Sortable(contentListEl, {
        animation: 150,
        ghostClass: 'blue-background-class',
        onEnd: function (evt) {
            const order = Array.from(contentListEl.children).map(item => item.dataset.id);
            updateContentOrder(order);
        }
    });

    // Event Listeners
    startBtn.addEventListener('click', startDisplay);
    stopBtn.addEventListener('click', stopDisplay);
    clearBtn.addEventListener('click', () => showToast('Bu özellik yakında eklenecektir.', 'warning'));
    
    // Tam ekran butonu
    const fullscreenBtn = document.getElementById('fullscreen-toggle');
    fullscreenBtn.addEventListener('click', toggleFullscreen);
    document.addEventListener('keydown',(e)=>{if(e.key==='F11'){e.preventDefault();toggleFullscreen();}});
    function toggleFullscreen(){
        if(!document.fullscreenElement){
            document.documentElement.requestFullscreen().then(()=>{
                document.body.classList.add('fullscreen');
                fullscreenBtn.innerHTML='<i class="fas fa-compress"></i> Çık';
                fullscreenBtn.onclick = ()=>window.open(`/screen/${currentLocation}`, '_blank');
            }).catch(err=>showToast('Tam ekran başarısız','error'));
        }else{
            document.exitFullscreen().then(()=>{
                document.body.classList.remove('fullscreen');
                fullscreenBtn.innerHTML='<i class="fas fa-expand"></i> Tam Ekran';
                fullscreenBtn.onclick = toggleFullscreen;
            });
        }
    }
    
    uploadArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

    const uploadBtn = document.getElementById('upload-btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', function() {
            if (selectedFile) {
                uploadFile(selectedFile);
                selectedFile = null;
                uploadBtn.disabled = true;
            }
        });
    }
    
    // Duration controls event listeners
    const durationSlider = document.getElementById('duration-slider');
    const durationInput = document.getElementById('duration-input');
    const presetBtns = document.querySelectorAll('.preset-btn');
    
    if (durationSlider && durationInput) {
        durationSlider.addEventListener('input', function() {
            durationInput.value = this.value;
            updatePresetButtons(parseInt(this.value));
        });
        
        durationInput.addEventListener('input', function() {
            durationSlider.value = this.value;
            updatePresetButtons(parseInt(this.value));
        });
    }
    
    presetBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const duration = parseInt(this.dataset.duration);
            durationSlider.value = duration;
            durationInput.value = duration;
            updatePresetButtons(duration);
        });
    });
    
    setupDragDrop();

    // SocketIO Event Handlers
    socket.on('connect', () => {
        console.log('SocketIO connected successfully');
        updateConnectionStatus(true);
        showToast('Yönetim paneline başarıyla bağlanıldı.', 'success');
    });

    socket.on('disconnect', () => {
        console.log('SocketIO disconnected');
        updateConnectionStatus(false);
        showToast('Sunucu ile bağlantı kesildi.', 'error');
    });

    socket.on('connect_error', (error) => {
        console.error('SocketIO connection error:', error);
        updateConnectionStatus(false);
        showToast('Bağlantı hatası oluştu.', 'error');
    });

    socket.on('display_status', (data) => {
        console.log('Received display_status:', data);
        handleDisplayStatus(data);
    });

    socket.on('content_updated', (data) => {
        console.log('Received content_updated:', data);
        handleContentUpdate(data);
    });

    socket.on('system_info', (data) => {
        updateSystemInfo(data);
    });

    // Functions
    function startDisplay() {
        console.log('Start button clicked');
        startBtn.disabled = true;
        
        fetch(`/api/${currentLocation}/display/start`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                console.log('Start response:', data);
                if (data.success) {
                    showToast('Gösterim başlatıldı!', 'success');
                    isDisplayRunning = true;
                    updateControlButtons();
                } else {
                    showToast(data.message || 'Gösterim başlatılamadı.', 'error');
                    startBtn.disabled = false;
                }
            })
            .catch(error => {
                console.error('Start error:', error);
                showToast('Gösterim başlatılırken hata oluştu.', 'error');
                startBtn.disabled = false;
            });
    }

    function stopDisplay() {
        console.log('Stop button clicked');
        stopBtn.disabled = true;
        
        fetch(`/api/${currentLocation}/display/stop`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                console.log('Stop response:', data);
                if (data.success) {
                    showToast('Gösterim durduruldu!', 'success');
                    isDisplayRunning = false;
                    currentDisplayItem = null;
                    updatePlaybackUI('stopped', null);
                    updateControlButtons();
                } else {
                    showToast(data.message || 'Gösterim durdurulamadı.', 'error');
                    stopBtn.disabled = false;
                }
            })
            .catch(error => {
                console.error('Stop error:', error);
                showToast('Gösterim durdurulurken hata oluştu.', 'error');
                stopBtn.disabled = false;
            });
    }

    function handleDisplayStatus(data) {
        if (data && data.status && data.location === currentLocation) {
            console.log('Processing display status:', data.status, data.current_item);
            
            if (data.status === 'playing' && data.current_item) {
                currentDisplayItem = data.current_item;
                isDisplayRunning = true;
                updatePlaybackUI('playing', data.current_item);
                highlightCurrentItem(data.current_item);
                
                // Animasyon efekti
                const currentDisplayCard = document.querySelector('.current-display-card');
                if (currentDisplayCard) {
                    currentDisplayCard.style.animation = 'none';
                    setTimeout(() => {
                        currentDisplayCard.style.animation = 'shimmer 0.5s ease-in-out';
                    }, 10);
                }
            } else if (data.status === 'stopped') {
                currentDisplayItem = null;
                isDisplayRunning = false;
                updatePlaybackUI('stopped', null);
                removeHighlight();
            }
            
            updateControlButtons();
        }
    }

    function handleContentUpdate(data) {
        if ((data.action === 'sync' || data.action === 'upload' || data.action === 'delete' || data.action === 'reorder') && data.location === currentLocation) {
            if (data.content_list) {
                contentList = data.content_list;
                renderContentList(contentList);
                updateControlButtons();
            }
            
            if (data.action === 'reorder') {
                showToast('Yayın akışı sıralaması güncellendi.', 'success');
            } else if (data.action === 'upload') {
                showToast(`'${data.content.filename}' başarıyla yüklendi.`, 'success');
            } else if (data.action === 'delete') {
                showToast('İçerik silindi.', 'success');
            }
        }
    }

    function updateContentOrder(order) {
        fetch(`/api/${currentLocation}/content/order`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order: order })
        })
        .then(res => res.json())
        .then(data => {
            if (data.message) {
                showToast(data.message, 'success');
            }
        })
        .catch(error => {
            console.error('Order update error:', error);
            showToast('Sıralama güncellenirken hata oluştu.', 'error');
        });
    }

    function updatePlaybackUI(status, currentItem) {
        console.log(`Updating UI: Status - ${status}`, currentItem);

        // Durum çubuğunu güncelle
        if (status === 'playing' && currentItem && currentItem.filename) {
            displayStatus.innerHTML = `<i class="fas fa-play-circle"></i> Gösteriliyor: <strong>${currentItem.filename}</strong>`;
            displayStatus.className = 'status-indicator running';
        } else {
            displayStatus.innerHTML = '<i class="fas fa-stop-circle"></i> Gösterim Durumu: DURDURULDU';
            displayStatus.className = 'status-indicator stopped';
        }

        // "Şu An Gösterilen" kutusunu güncelle
        if (status === 'playing' && currentItem && currentItem.filename) {
            const iconClass = currentItem.type === 'image' ? 'fa-file-image' : 'fa-file-video';
            const typeText = currentItem.type === 'image' ? 'Resim (7 saniye)' : 'Video (süre kadar)';
            
            // Resim önizlemesi için HTML
            const imagePreview = currentItem.type === 'image' 
                ? `<div class="current-display-preview">
                     <img src="/uploads/${currentLocation}/${currentItem.filename}" alt="${currentItem.filename}" 
                          onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                     <div class="preview-fallback" style="display: none;">
                       <i class="fas ${iconClass}"></i>
                       <span>Önizleme yüklenemedi</span>
                     </div>
                   </div>`
                : `<div class="current-display-preview">
                     <video src="/uploads/${currentItem.filename}#t=0.1" autoplay muted controls style="width:100%;height:100%;object-fit:cover;border-radius:12px;"></video>
                   </div>`;
            
            currentDisplayInfo.innerHTML = `
                <div class="current-display-content">
                    ${imagePreview}
                    <div class="current-display-details">
                        <h3>${currentItem.filename}</h3>
                        <p><strong>Sıra:</strong> ${currentItem.order + 1}</p>
                        <p><strong>Tür:</strong> <span class="current-display-type ${currentItem.type}">${typeText}</span></p>
                    </div>
                </div>`;
        } else {
            currentDisplayInfo.innerHTML = `
                <div class="current-display-placeholder">
                    <i class="fas fa-tv"></i>
                    <p>Henüz gösterim başlatılmadı</p>
                </div>`;
        }
    }

    function highlightCurrentItem(currentItem) {
        // Önceki vurgulamayı kaldır
        removeHighlight();
        
        // Yeni aktif öğeyi vurgula
        if (currentItem && currentItem.id) {
            const activeItem = document.querySelector(`[data-id="${currentItem.id}"]`);
            if (activeItem) {
                activeItem.classList.add('current-playing');
            }
        }
    }

    function removeHighlight() {
        document.querySelectorAll('.content-item').forEach(item => {
            item.classList.remove('current-playing');
        });
    }

    function updateControlButtons() {
        const hasContent = contentList.length > 0;
        startBtn.disabled = isDisplayRunning || !hasContent;
        stopBtn.disabled = !isDisplayRunning;
        
        // Buton durumlarını görsel olarak güncelle
        if (isDisplayRunning) {
            startBtn.classList.add('disabled');
            stopBtn.classList.remove('disabled');
        } else {
            startBtn.classList.remove('disabled');
            stopBtn.classList.add('disabled');
        }
    }

    function renderContentList(items) {
        contentListEl.innerHTML = '';
        if (!items || items.length === 0) {
            const placeholder = document.createElement('li');
            placeholder.className = 'content-item-placeholder';
            placeholder.textContent = 'Yayın akışında gösterilecek içerik bulunmuyor.';
            contentListEl.appendChild(placeholder);
        } else {
            items.sort((a, b) => a.order - b.order).forEach(item => {
                const li = document.createElement('li');
                li.className = 'content-item';
                li.dataset.id = item.id;
                
                const iconClass = item.type === 'image' ? 'fa-file-image' : 'fa-file-video';
                
                li.innerHTML = `
                    <div class="content-info">
                        <i class="fas ${iconClass} file-icon"></i>
                        <span>${item.filename}</span>
                    </div>
                    <button class="delete-btn" onclick="deleteContent(${item.id})"><i class="fas fa-trash-alt"></i></button>
                `;
                contentListEl.appendChild(li);
            });
        }
    }

    window.deleteContent = function(id) {
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
            .then(res => res.json())
            .then(data => {
                showToast(data.message || 'İçerik silindi.', 'success');
                closeDeleteDialog();
                // İçerik listesini güncelle
                fetchContentList();
            })
            .catch(error => {
                console.error('Delete error:', error);
                showToast('İçerik silinirken hata oluştu.', 'error');
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
        const modal = document.getElementById('delete-dialog');
        if (event.target === modal) {
            closeDeleteDialog();
        }
    });

    // ESC tuşu ile modal kapatma
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeDeleteDialog();
        }
    });

    // Global fonksiyonları window objesine ekle
    window.closeDeleteDialog = closeDeleteDialog;
    window.confirmDelete = confirmDelete;

    function updateConnectionStatus(isConnected) {
        if (isConnected) {
            connectionStatusEl.classList.remove('offline');
            connectionStatusEl.classList.add('online');
            connectionStatusEl.innerHTML = '<i class="fas fa-circle"></i> Bağlı';
        } else {
            connectionStatusEl.classList.remove('online');
            connectionStatusEl.classList.add('offline');
            connectionStatusEl.innerHTML = '<i class="fas fa-circle"></i> Bağlantı Yok';
        }
    }

    function updateSystemInfo(data) {
        if (!data || data.error) return;
        cpuUsageEl.textContent = `${data.cpu_percent.toFixed(1)}%`;
        ramUsageEl.textContent = `${data.memory_percent.toFixed(1)}%`;
        diskUsageEl.textContent = `${data.disk_usage.toFixed(1)}%`;
    }

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 500);
        }, 3000);
    }

    function setupDragDrop() {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.add('dragover'), false);
        });
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.remove('dragover'), false);
        });
        uploadArea.addEventListener('drop', handleDrop, false);
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function handleDrop(e) {
        let dt = e.dataTransfer;
        let files = dt.files;
        handleFiles(files);
    }

    function handleFiles(files) {
        if (!files || files.length === 0) return;
        const file = files[0];
        selectedFile = file;
        if (file.type.startsWith('video/')) {
            const video = document.createElement('video');
            video.preload = 'metadata';
            video.onloadedmetadata = function() {
                const duration = Math.round(video.duration);
                console.log('Video süresi:', duration);
                updateDurationUI(duration);
            };
            video.onerror = function() {
                updateDurationUI(10);
            };
            video.src = URL.createObjectURL(file);
        } else {
            updateDurationUI(7);
        }
        uploadBtn.disabled = false;
    }

    function updateDurationUI(duration) {
        const durationSettings = document.getElementById('duration-settings');
        if (durationSettings) durationSettings.style.display = 'block';
        const durationSlider = document.getElementById('duration-slider');
        const durationInput = document.getElementById('duration-input');
        if (durationSlider && durationInput) {
            durationSlider.value = duration;
            durationInput.value = duration;
            updatePresetButtons(duration);
        }
    }

    function updatePresetButtons(duration) {
        const presetBtns = document.querySelectorAll('.preset-btn');
        presetBtns.forEach(btn => {
            btn.classList.remove('active');
            if (parseInt(btn.dataset.duration) === duration) {
                btn.classList.add('active');
            }
        });
    }

    function performUpload(formData, fileName) {
        // Yükleme progress bar'ını göster
        const progressBar = document.getElementById('upload-progress');
        const progressFill = progressBar.querySelector('.progress-fill');
        const progressText = progressBar.querySelector('.progress-text');
        
        progressBar.style.display = 'block';
        progressText.textContent = `${fileName} yükleniyor...`;
        
        // Simüle edilmiş progress (gerçek progress için XMLHttpRequest kullanılabilir)
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) progress = 90;
            progressFill.style.width = progress + '%';
        }, 200);

        fetch(`/api/${currentLocation}/content/upload`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            clearInterval(progressInterval);
            progressFill.style.width = '100%';
            progressText.textContent = 'Yükleme tamamlandı!';
            
            setTimeout(() => {
                progressBar.style.display = 'none';
                progressFill.style.width = '0%';
            }, 1000);
            
            if(data.error) {
                showToast(`Hata: ${data.error}`, 'error');
            } else {
                showToast(`'${data.content.filename}' başarıyla yüklendi.`, 'success');
                // Content listesini güncelle
                contentList.push(data.content);
                renderContentList(contentList);
            }
        })
        .catch(error => {
            clearInterval(progressInterval);
            progressBar.style.display = 'none';
            progressFill.style.width = '0%';
            console.error('Yükleme hatası:', error);
            showToast('Yükleme sırasında bir hata oluştu.', 'error');
        });
    }

    // Periyodik sistem bilgisi güncelleme
    setInterval(() => {
        socket.emit('get_system_info');
    }, 5000);

    // Başlangıçta içerik listesini yükle
    console.log('Initializing application...');
    fetch(`/api/${currentLocation}/content`)
        .then(response => response.json())
        .then(data => {
            contentList = data.content || [];
            isDisplayRunning = data.display_running || false;
            renderContentList(contentList);
            updateControlButtons();
            
            // Mevcut durumu al
            return fetch(`/api/${currentLocation}/display/status`);
        })
        .then(response => response.json())
        .then(data => {
            console.log('Initial display status:', data);
            if (data.current_item) {
                currentDisplayItem = data.current_item;
                updatePlaybackUI(data.status, data.current_item);
                highlightCurrentItem(data.current_item);
            }
        })
        .catch(error => {
            console.error('Initialization error:', error);
        });

    updateConnectionStatus(socket.connected);
    socket.emit('get_system_info');
});