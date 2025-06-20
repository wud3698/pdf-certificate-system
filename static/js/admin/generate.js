let selectedWinners = new Set();

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    // 确保初始状态正确
    document.getElementById('currentTemplate').classList.add('d-none');
    document.getElementById('uploadTemplate').classList.remove('d-none');
    
    console.log('页面初始化完成，上传模板区域已显示');
});

// 显示/隐藏加载状态
function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

// 显示通知
function showNotification(message, type = 'info') {
    // 简单的alert，后续可以替换为toast通知
    alert(message);
}

// 文件拖拽处理
const fileUploadArea = document.querySelector('.file-upload-area');
const fileInput = document.getElementById('template');

if (fileUploadArea && fileInput) {
    fileUploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('dragover');
    });

    fileUploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
    });

    fileUploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            updateFileDisplay(files[0]);
        }
    });

    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            updateFileDisplay(this.files[0]);
        }
    });
}

function updateFileDisplay(file) {
    const uploadText = fileUploadArea.querySelector('.upload-text');
    const uploadIcon = fileUploadArea.querySelector('.upload-icon i');
    
    uploadText.textContent = `已选择文件：${file.name}`;
    uploadIcon.className = 'fas fa-file-word';
}

// 渲染获奖者列表
function renderWinners(winners) {
    const container = document.getElementById('winnersContainer');
    
    if (!winners || winners.length === 0) {
        container.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--gray-500);">暂无参赛者数据</div>';
        return;
    }

    container.innerHTML = winners.map(winner => `
        <div class="winner-item" data-id="${winner.id}" onclick="toggleWinner(${winner.id})">
            <input type="checkbox" class="winner-checkbox" ${selectedWinners.has(winner.id) ? 'checked' : ''} 
                   onchange="toggleWinner(${winner.id})">
            <div class="winner-info">
                <div class="winner-name">${winner.name}</div>
                <div class="winner-details">${winner.award_type || '未设置奖项'}</div>
            </div>
            <div class="winner-badge ${winner.has_certificate ? 'badge-generated' : 'badge-pending'}">
                ${winner.has_certificate ? '已生成' : '待生成'}
            </div>
        </div>
    `).join('');
}

// 切换获奖者选择
function toggleWinner(winnerId) {
    if (selectedWinners.has(winnerId)) {
        selectedWinners.delete(winnerId);
    } else {
        selectedWinners.add(winnerId);
    }
    
    // 更新UI
    const item = document.querySelector(`[data-id="${winnerId}"]`);
    const checkbox = item.querySelector('.winner-checkbox');
    
    if (selectedWinners.has(winnerId)) {
        item.classList.add('selected');
        checkbox.checked = true;
    } else {
        item.classList.remove('selected');
        checkbox.checked = false;
    }
}

// 处理模板上传
document.getElementById('templateForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const activityId = document.getElementById('activitySelect').value;
    if (!activityId) {
        showNotification('请先选择活动', 'warning');
        return;
    }

    const formData = new FormData();
    const templateFile = document.getElementById('template').files[0];
    
    if (!templateFile) {
        showNotification('请选择模板文件', 'warning');
        return;
    }

    formData.append('template', templateFile);
    formData.append('activity_id', activityId);
    formData.append('template_type', 'docx');

    showLoading();

    try {
        const response = await fetch('/upload_template', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        if (result.success) {
            showNotification('模板上传成功', 'success');
            // 刷新活动信息
            document.getElementById('activitySelect').dispatchEvent(new Event('change'));
        } else {
            throw new Error(result.message);
        }
    } catch (error) {
        showNotification('模板上传失败：' + error.message, 'danger');
    } finally {
        hideLoading();
    }
});

// 处理模板删除
document.getElementById('removeTemplate').addEventListener('click', async function() {
    const activityId = document.getElementById('activitySelect').value;
    if (!activityId) {
        return;
    }

    if (!confirm('确定要删除当前模板吗？')) {
        return;
    }

    showLoading();

    try {
        const response = await fetch(`/api/delete_template/${activityId}`, {
            method: 'DELETE'
        });

        const result = await response.json();
        if (result.success) {
            showNotification('模板删除成功', 'success');
            document.getElementById('currentTemplate').classList.add('d-none');
            document.getElementById('uploadTemplate').classList.remove('d-none');
        } else {
            throw new Error(result.message);
        }
    } catch (error) {
        showNotification('模板删除失败：' + error.message, 'danger');
    } finally {
        hideLoading();
    }
});

// 当选择活动时
document.getElementById('activitySelect').addEventListener('change', async function() {
    const activityId = this.value;
    selectedWinners.clear();
    
    if (!activityId) {
        document.getElementById('currentTemplate').classList.add('d-none');
        document.getElementById('uploadTemplate').classList.remove('d-none');
        renderWinners([]);
        return;
    }

    showLoading();

    try {
        // 加载获奖者列表
        const winnersResponse = await fetch(`/api/winners/${activityId}`);
        
        if (winnersResponse.ok) {
            const winners = await winnersResponse.json();
            if (Array.isArray(winners)) {
                renderWinners(winners);
            }
        } else {
            console.warn('加载获奖者列表失败:', winnersResponse.status);
            renderWinners([]);
        }

        // 加载活动的证书模板
        const templateResponse = await fetch(`/api/activity_template/${activityId}`);
        
        if (templateResponse.ok) {
            const result = await templateResponse.json();
            
            if (result.template_url) {
                // 有模板，显示当前模板信息
                console.log('找到模板:', result.template_name);
                document.getElementById('currentTemplate').classList.remove('d-none');
                document.getElementById('templateName').textContent = result.template_name || '未命名模板';
                document.getElementById('uploadTemplate').classList.add('d-none');
            } else {
                // 没有模板，显示上传界面
                console.log('没有模板，显示上传界面');
                document.getElementById('currentTemplate').classList.add('d-none');
                document.getElementById('uploadTemplate').classList.remove('d-none');
            }
        } else {
            // 模板接口调用失败，通常表示没有模板，显示上传界面
            console.log('模板接口返回错误，显示上传界面');
            document.getElementById('currentTemplate').classList.add('d-none');
            document.getElementById('uploadTemplate').classList.remove('d-none');
            
            // 只有在400错误且包含"模板"关键字时，才给出友好提示
            if (templateResponse.status === 400) {
                const errorResult = await templateResponse.json().catch(() => ({}));
                if (errorResult.error && errorResult.error.includes('模板')) {
                    showNotification('该活动尚未上传证书模板，请先上传模板文件', 'info');
                }
            }
        }
    } catch (error) {
        console.error('加载活动信息失败:', error);
        // 发生异常时，确保显示上传界面让用户可以继续操作
        document.getElementById('currentTemplate').classList.add('d-none');
        document.getElementById('uploadTemplate').classList.remove('d-none');
        renderWinners([]);
        
        // 只有真正的网络错误才显示错误信息
        showNotification('网络连接异常，请刷新页面重试', 'warning');
    } finally {
        hideLoading();
    }
});

// 处理全选复选框
document.getElementById('generate_all').addEventListener('change', function() {
    const winnerSelection = document.getElementById('winner_selection');
    if (this.checked) {
        winnerSelection.style.display = 'none';
        selectedWinners.clear();
    } else {
        winnerSelection.style.display = 'block';
    }
});

// 生成证书
document.getElementById('generateBtn').addEventListener('click', async function() {
    const btn = this;
    const spinner = btn.querySelector('.spinner');
    const btnText = btn.querySelector('.btn-text');
    
    const activityId = document.getElementById('activitySelect').value;
    if (!activityId) {
        showNotification('请选择活动', 'warning');
        return;
    }

    const generateAll = document.getElementById('generate_all').checked;
    const selectedWinnerIds = Array.from(selectedWinners);
    const imageSize = document.getElementById('imageSizeSelect').value; // 获取主图片尺寸
    const backupImageSize = document.getElementById('backupImageSizeSelect').value; // 获取备用图片尺寸

    if (!generateAll && selectedWinnerIds.length === 0) {
        showNotification('请选择至少一个参赛者', 'warning');
        return;
    }

    try {
        // 禁用按钮并显示加载状态
        btn.disabled = true;
        spinner.classList.remove('d-none');
        btnText.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 生成中...';

        const response = await fetch('/admin/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                activity_id: activityId,
                generate_all: generateAll,
                winner_ids: generateAll ? null : selectedWinnerIds,
                image_size: imageSize,  // 添加主图片尺寸参数
                backup_image_size: backupImageSize  // 添加备用图片尺寸参数
            })
        });

        const result = await response.json();
        if (result.success) {
            showNotification(result.message, 'success');
            // 刷新获奖者列表
            document.getElementById('activitySelect').dispatchEvent(new Event('change'));
        } else {
            throw new Error(result.message);
        }
    } catch (error) {
        showNotification('生成证书失败：' + error.message, 'danger');
    } finally {
        // 恢复按钮状态
        btn.disabled = false;
        spinner.classList.add('d-none');
        btnText.innerHTML = '<i class="fas fa-play"></i> 开始生成证书';
    }
}); 