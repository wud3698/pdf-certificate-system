// 证书管理页面 JavaScript
let ACTIVITY_ID;
let isLoading = false;

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    // 从页面获取活动ID
    const activityIdElement = document.querySelector('[data-activity-id]');
    if (activityIdElement) {
        ACTIVITY_ID = parseInt(activityIdElement.dataset.activityId);
    }
    
    // 实时搜索
    const nameInput = document.querySelector('input[name="name"]');
    if (nameInput) {
        let searchTimeout;
        nameInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                if (this.value.length >= 2 || this.value.length === 0) {
                    document.getElementById('searchForm').submit();
                }
            }, 500);
        });
    }
});

// 显示/隐藏加载状态
function showLoading() {
    isLoading = true;
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
    }
}

function hideLoading() {
    isLoading = false;
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
}

// 通知系统
function showNotification(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// 全选/取消全选
function toggleSelectAll(checkbox) {
    const checkboxes = document.querySelectorAll('.cert-checkbox');
    checkboxes.forEach(cb => cb.checked = checkbox.checked);
    updateBulkActions();
}

// 更新批量操作
function updateBulkActions() {
    const checked = document.querySelectorAll('.cert-checkbox:checked');
    const bulkActions = document.getElementById('bulkActions');
    const selectedCount = document.getElementById('selectedCount');
    
    if (checked.length > 0) {
        bulkActions.classList.add('show');
        selectedCount.textContent = checked.length;
    } else {
        bulkActions.classList.remove('show');
    }
}

// 生成单个证件
async function generateCertificate(certId) {
    if (isLoading) return;
    
    // 确保 certId 是数字类型
    certId = parseInt(certId);
    
    // 获取图片尺寸
    const imageSize = document.getElementById('imageSizeSelect').value;
    const backupImageSize = document.getElementById('backupImageSizeSelect').value;
    
    showLoading();
    try {
        const response = await fetch('/admin/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                activity_id: ACTIVITY_ID,
                winner_ids: [certId],
                image_size: imageSize,
                backup_image_size: backupImageSize
            })
        });
        
        const result = await response.json();
        if (result.success) {
            showNotification('证书生成成功');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            throw new Error(result.message || '生成失败');
        }
    } catch (error) {
        showNotification('生成失败：' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

// 生成选中证书
async function generateSelectedCertificates() {
    const checked = document.querySelectorAll('.cert-checkbox:checked');
    if (checked.length === 0) {
        showNotification('请选择要生成的证书', 'warning');
        return;
    }
    
    if (isLoading) return;
    
    const winnerIds = Array.from(checked).map(cb => parseInt(cb.value));
    const imageSize = document.getElementById('imageSizeSelect').value;
    const backupImageSize = document.getElementById('backupImageSizeSelect').value;
    
    showLoading();
    try {
        const response = await fetch('/admin/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                activity_id: ACTIVITY_ID,
                winner_ids: winnerIds,
                image_size: imageSize,
                backup_image_size: backupImageSize
            })
        });
        
        const result = await response.json();
        if (result.success) {
            showNotification(`成功生成 ${winnerIds.length} 份证书`);
            setTimeout(() => window.location.reload(), 1000);
        } else {
            throw new Error(result.message || '生成失败');
        }
    } catch (error) {
        showNotification('生成失败：' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

// 生成全部证书
async function generateAllCertificates() {
    if (!confirm('确定要生成所有未生成的证书吗？')) return;
    if (isLoading) return;
    
    const imageSize = document.getElementById('imageSizeSelect').value;
    const backupImageSize = document.getElementById('backupImageSizeSelect').value;
    
    showLoading();
    try {
        const response = await fetch('/admin/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                activity_id: ACTIVITY_ID,
                generate_all: true,
                image_size: imageSize,
                backup_image_size: backupImageSize
            })
        });
        
        const result = await response.json();
        if (result.success) {
            showNotification('证书生成成功');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            throw new Error(result.message || '生成失败');
        }
    } catch (error) {
        showNotification('生成失败：' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

// 编辑证书
async function editCertificate(id) {
    // 确保 id 是数字类型
    id = parseInt(id);
    
    try {
        const response = await fetch(`/admin/certificate/${id}`);
        const cert = await response.json();
        
        const form = document.getElementById('editCertificateForm');
        Object.keys(cert).forEach(key => {
            const input = form.querySelector(`[name="${key}"]`);
            if (input) input.value = cert[key] || '';
        });
        
        // 显示现有主图片（如果有的话）
        const editPreview = document.getElementById('editPreview');
        const editImg = editPreview.querySelector('img');
        
        if (cert.image_path) {
            editImg.src = `/participant_image/${id}`;
            editPreview.style.display = 'block';
        } else {
            editImg.src = '';
            editPreview.style.display = 'none';
        }
        
        // 显示现有备用图片（如果有的话）
        const editBackupPreview = document.getElementById('editBackupPreview');
        const editBackupImg = editBackupPreview.querySelector('img');
        
        if (cert.image_path_backup) {
            editBackupImg.src = `/participant_backup_image/${id}`;
            editBackupPreview.style.display = 'block';
        } else {
            editBackupImg.src = '';
            editBackupPreview.style.display = 'none';
        }
        
        const modal = new bootstrap.Modal(document.getElementById('editCertificateModal'));
        modal.show();
    } catch (error) {
        showNotification('获取证书信息失败：' + error.message, 'danger');
    }
}

// 提交编辑
async function submitEditCertificate() {
    const form = document.getElementById('editCertificateForm');
    const formData = new FormData(form);
    const certId = parseInt(formData.get('id'));
    
    if (!certId) {
        showNotification('证书ID无效', 'danger');
        return;
    }
    
    try {
        // 处理主图片上传（如果有新图片）
        const imageFile = form.querySelector('input[name="participant_image"]').files[0];
        const backupImageFile = form.querySelector('input[name="participant_image_backup"]').files[0];
        
        if (imageFile || backupImageFile) {
            showNotification('正在上传图片...', 'info');
            
            if (imageFile) {
                await uploadParticipantImage(certId, imageFile, 'main');
            }
            
            if (backupImageFile) {
                await uploadParticipantImage(certId, backupImageFile, 'backup');
            }
        }
        
        // 更新证书信息
        const response = await fetch(`/admin/certificate/${certId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(Object.fromEntries(formData))
        });
        
        const result = await response.json();
        if (response.ok) {
            showNotification(imageFile ? '证书和图片更新成功' : '证书更新成功');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            throw new Error(result.error || '更新失败');
        }
    } catch (error) {
        showNotification('更新失败：' + error.message, 'danger');
    }
}

// 添加证书
async function submitAddCertificate() {
    const form = document.getElementById('addCertificateForm');
    const formData = new FormData(form);
    
    try {
        // 先添加证书
        const response = await fetch(`/admin/activity/${ACTIVITY_ID}/certificate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(Object.fromEntries(formData))
        });
        
        const result = await response.json();
        if (response.ok) {
            const certId = result.id;
            
            // 处理图片上传（如果有图片）
            const imageFile = form.querySelector('input[name="participant_image"]').files[0];
            const backupImageFile = form.querySelector('input[name="participant_image_backup"]').files[0];
            
            if (imageFile || backupImageFile) {
                showNotification('证书添加成功，正在上传图片...', 'info');
                
                if (imageFile) {
                    await uploadParticipantImage(certId, imageFile, 'main');
                }
                
                if (backupImageFile) {
                    await uploadParticipantImage(certId, backupImageFile, 'backup');
                }
                
                showNotification('证书和图片添加成功');
            } else {
                showNotification('证书添加成功');
            }
            
            setTimeout(() => window.location.reload(), 1000);
        } else {
            throw new Error(result.error || '添加失败');
        }
    } catch (error) {
        showNotification('添加失败：' + error.message, 'danger');
    }
}

// 删除证书
async function deleteCertificate(id) {
    // 确保 id 是数字类型
    id = parseInt(id);
    
    if (!confirm('确定要删除这个证书吗？')) return;
    
    try {
        const response = await fetch(`/admin/certificate/${id}`, { method: 'DELETE' });
        const result = await response.json();
        
        if (response.ok) {
            showNotification('证书删除成功');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            throw new Error(result.error || '删除失败');
        }
    } catch (error) {
        showNotification('删除失败：' + error.message, 'danger');
    }
}

// 删除选中证书
async function deleteSelectedCertificates() {
    const checked = document.querySelectorAll('.cert-checkbox:checked');
    if (checked.length === 0) {
        showNotification('请选择要删除的证书', 'warning');
        return;
    }
    
    if (!confirm(`确定要删除选中的 ${checked.length} 个证书吗？`)) return;
    
    const certIds = Array.from(checked).map(cb => parseInt(cb.value));
    let successCount = 0;
    
    for (const certId of certIds) {
        try {
            const response = await fetch(`/admin/certificate/${certId}`, { method: 'DELETE' });
            if (response.ok) successCount++;
        } catch (error) {
            console.error(`删除证书 ${certId} 失败:`, error);
        }
    }
    
    if (successCount > 0) {
        showNotification(`成功删除 ${successCount} 个证书`);
        setTimeout(() => window.location.reload(), 1000);
    }
}

// 删除全部证书
async function deleteAllCertificates() {
    if (!confirm('确定要删除全部证书吗？此操作不可恢复！')) return;
    
    const certificates = Array.from(document.querySelectorAll('.cert-checkbox')).map(cb => parseInt(cb.value));
    let successCount = 0;
    
    for (const certId of certificates) {
        try {
            const response = await fetch(`/admin/certificate/${certId}`, { method: 'DELETE' });
            if (response.ok) successCount++;
        } catch (error) {
            console.error(`删除证书 ${certId} 失败:`, error);
        }
    }
    
    if (successCount > 0) {
        showNotification(`成功删除 ${successCount} 个证书`);
        setTimeout(() => window.location.reload(), 1000);
    }
}

// 下载选中证书
async function downloadSelectedCertificates() {
    const checked = document.querySelectorAll('.cert-checkbox:checked');
    if (checked.length === 0) {
        showNotification('请选择要下载的证书', 'warning');
        return;
    }
    
    const certIds = Array.from(checked).map(cb => parseInt(cb.value));
    
    showLoading();
    try {
        const response = await fetch('/admin/download/selected', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cert_ids: certIds })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '选中证书.zip';
            a.click();
            window.URL.revokeObjectURL(url);
            showNotification(`成功下载 ${certIds.length} 份证书`);
        } else {
            const result = await response.json();
            throw new Error(result.error || '下载失败');
        }
    } catch (error) {
        showNotification('下载失败：' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

// 下载全部证书
async function downloadAllCertificates() {
    if (!confirm('确定要下载全部证书吗？')) return;
    
    showLoading();
    try {
        const response = await fetch(`/admin/download/all/${ACTIVITY_ID}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '全部证书.zip';
            a.click();
            window.URL.revokeObjectURL(url);
            showNotification('证书下载成功');
        } else {
            const result = await response.json();
            throw new Error(result.error || '下载失败');
        }
    } catch (error) {
        showNotification('下载失败：' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

// 导出证书数据
function exportCertificates() {
    // 简单的CSV导出示例
    const rows = [['编号', '姓名', '单位', '项目', '区域']];
    document.querySelectorAll('.cert-row').forEach((row, index) => {
        if (index === 0) return; // 跳过表头
        const cells = row.querySelectorAll('div');
        if (cells.length >= 5) {
            rows.push([
                cells[2].textContent.trim(),
                cells[3].textContent.trim(),
                cells[4].textContent.trim(), 
                cells[5].textContent.trim(),
                cells[4].textContent.trim()
            ]);
        }
    });
    
    const csvContent = rows.map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = '证书数据.csv';
    link.click();
}

// 图片预览功能
function previewImage(input, previewId) {
    const preview = document.getElementById(previewId);
    const img = preview.querySelector('img');
    
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            img.src = e.target.result;
            preview.style.display = 'block';
        };
        
        reader.readAsDataURL(input.files[0]);
    }
}

// 移除图片预览
function removeImage(previewId) {
    const preview = document.getElementById(previewId);
    const img = preview.querySelector('img');
    const input = preview.parentElement.querySelector('input[type="file"]');
    
    img.src = '';
    preview.style.display = 'none';
    input.value = '';
}

// 上传参与者图片
async function uploadParticipantImage(certId, file, imageType = 'main') {
    try {
        const formData = new FormData();
        formData.append('image', file);
        formData.append('image_type', imageType);
        
        const response = await fetch(`/admin/certificate/${certId}/image`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            return result;
        } else {
            throw new Error(result.error || '图片上传失败');
        }
    } catch (error) {
        throw error;
    }
}

// 删除参与者图片
async function deleteParticipantImage(certId) {
    try {
        const response = await fetch(`/admin/certificate/${certId}/image`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            return result;
        } else {
            throw new Error(result.error || '图片删除失败');
        }
    } catch (error) {
        throw error;
    }
} 