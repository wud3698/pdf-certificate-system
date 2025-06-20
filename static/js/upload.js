let currentStep = 1;

// 更新步骤状态
function updateStepStatus(step, status) {
    const stepElement = document.getElementById(`step${step}`);
    stepElement.className = `step-item ${status}`;
    
    if (status === 'active') {
        currentStep = step;
    }
}

// 显示/隐藏加载状态
function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

// 显示通知
function showNotification(message, type = 'info') {
    const statusDiv = document.getElementById('uploadStatus');
    statusDiv.className = `status-alert alert-${type} show`;
    statusDiv.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'danger' ? 'fa-exclamation-circle' : 'fa-info-circle'} me-2"></i>${message}`;
}

// 获取选中的活动ID
function getSelectedActivityId() {
    const activitySelect = document.getElementById('activitySelect');
    const activityId = activitySelect.value;
    if (!activityId) {
        showNotification('请先选择活动', 'danger');
        return null;
    }
    return activityId;
}

// 活动选择事件
function initActivitySelect() {
    document.getElementById('activitySelect').addEventListener('change', function() {
        if (this.value) {
            updateStepStatus(1, 'completed');
            updateStepStatus(2, 'active');
        } else {
            updateStepStatus(1, 'active');
            updateStepStatus(2, '');
            updateStepStatus(3, '');
            updateStepStatus(4, '');
            document.getElementById('uploadBtn').disabled = true;
        }
    });
}

// 文件拖拽处理
function initFileDragDrop() {
    const fileUploadArea = document.querySelector('.file-upload-area');
    const fileInput = document.getElementById('file');

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
            handleFileSelect();
        }
    });

    // 文件选择处理
    fileInput.addEventListener('change', handleFileSelect);
}

// 文件选择处理
async function handleFileSelect() {
    const file = document.getElementById('file').files[0];
    if (!file) return;

    // 更新上传区域显示
    const fileUploadArea = document.querySelector('.file-upload-area');
    const uploadText = fileUploadArea.querySelector('.upload-text');
    const uploadIcon = fileUploadArea.querySelector('.upload-icon i');
    uploadText.textContent = `已选择文件：${file.name}`;
    uploadIcon.className = 'fas fa-file-excel';

    updateStepStatus(2, 'completed');
    updateStepStatus(3, 'active');

    showLoading();
    
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/get_excel_headers', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        
        if (response.ok) {
            showMappingSection(result.headers);
            updateStepStatus(3, 'completed');
            updateStepStatus(4, 'active');
            document.getElementById('uploadBtn').disabled = false;
            showNotification('文件解析成功，请配置字段映射', 'success');
        } else {
            throw new Error(result.error || '获取Excel表头失败');
        }
    } catch (error) {
        showNotification('读取Excel文件失败：' + error.message, 'danger');
        resetFileInput();
    } finally {
        hideLoading();
    }
}

// 显示映射部分
function showMappingSection(headers) {
    const mappingSection = document.getElementById('mappingSection');
    const mappingFields = document.getElementById('mappingFields');
    mappingSection.style.display = 'block';
    mappingFields.innerHTML = '';

    // 系统字段定义
    const systemFields = [
        { value: 'cert_number', label: '证书编号', required: false },
        { value: 'unit_name', label: '单位名称', required: false },
        { value: 'area', label: '所属区域', required: false },
        { value: 'name', label: '姓名', required: true },
        { value: 'id_type', label: '证件类型', required: false },
        { value: 'id_number', label: '证件号', required: false },
        { value: 'gender', label: '性别', required: false },
        { value: 'age', label: '年龄', required: false },
        { value: 'birth_date', label: '出生日期', required: false },
        { value: 'phone', label: '手机号', required: false },
        { value: 'identity', label: '身份', required: false },
        { value: 'grade_major', label: '年级专业', required: false },
        { value: 'image_path', label: '图片', required: false },
        { value: 'image_path_backup', label: '备用图片', required: false },
        { value: 'project', label: '参赛项目', required: false },
        { value: 'param_group', label: '参数组别', required: false }
    ];

    // 创建映射字段
    systemFields.forEach(field => {
        const div = document.createElement('div');
        div.className = 'mapping-item';
        div.innerHTML = `
            <label class="form-label">
                ${field.label}
                ${field.required ? '<span style="color: var(--danger-color);">*</span>' : ''}
            </label>
            <select class="form-select" name="mapping_${field.value}" ${field.required ? 'required' : ''}>
                <option value="">选择对应的Excel列</option>
                ${headers.map(header => 
                    `<option value="${header}">${header}</option>`
                ).join('')}
            </select>
        `;
        mappingFields.appendChild(div);
    });
}

// 重置表单
function resetForm() {
    document.getElementById('uploadForm').reset();
    document.getElementById('mappingSection').style.display = 'none';
    document.getElementById('uploadStatus').className = 'status-alert';
    document.getElementById('uploadBtn').disabled = true;
    
    // 重置文件上传区域
    resetFileInput();
    
    // 重置步骤状态
    updateStepStatus(1, 'active');
    updateStepStatus(2, '');
    updateStepStatus(3, '');
    updateStepStatus(4, '');
}

function resetFileInput() {
    const fileUploadArea = document.querySelector('.file-upload-area');
    const uploadText = fileUploadArea.querySelector('.upload-text');
    const uploadIcon = fileUploadArea.querySelector('.upload-icon i');
    uploadText.textContent = '点击选择文件或拖拽文件到此处';
    uploadIcon.className = 'fas fa-cloud-upload-alt';
}

// 表单提交处理
function initFormSubmit() {
    document.getElementById('uploadForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const activityId = getSelectedActivityId();
        if (!activityId) return;

        // 检查必填映射字段
        const requiredMappings = ['name'];
        const missingFields = [];
        
        requiredMappings.forEach(field => {
            const select = document.querySelector(`[name="mapping_${field}"]`);
            if (!select.value) {
                missingFields.push(field === 'name' ? '姓名' : field);
            }
        });
        
        if (missingFields.length > 0) {
            showNotification(`请配置必填字段的映射：${missingFields.join('、')}`, 'danger');
            return;
        }

        // 收集字段映射
        const mappingFields = document.querySelectorAll('[name^="mapping_"]');
        const fieldMapping = {};
        mappingFields.forEach(field => {
            const systemField = field.name.replace('mapping_', '');
            const excelColumn = field.value;
            if (excelColumn) {
                fieldMapping[systemField] = excelColumn;
            }
        });

        const formData = new FormData(this);
        formData.append('activity_id', activityId);
        formData.append('field_mapping', JSON.stringify(fieldMapping));
        
        const submitBtn = document.getElementById('uploadBtn');
        
        try {
            submitBtn.disabled = true;
            showLoading();
            showNotification('正在导入数据，请稍候...', 'info');
            
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showNotification(result.message, 'success');
            } else {
                throw new Error(result.error || '导入失败');
            }
        } catch (error) {
            showNotification('导入失败：' + error.message, 'danger');
        } finally {
            submitBtn.disabled = false;
            hideLoading();
        }
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initActivitySelect();
    initFileDragDrop();
    initFormSubmit();
}); 