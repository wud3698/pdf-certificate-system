from flask import send_file, jsonify, request
import os
import zipfile
from io import BytesIO
from app.models import db, Activity, Certificate
from app.auth import admin_login_required
from . import admin_bp

# 全局变量
app = None
certificate_generator = None
certificate_service = None

def init_module(flask_app, cert_gen, cert_service):
    """初始化模块"""
    global app, certificate_generator, certificate_service
    app = flask_app
    certificate_generator = cert_gen
    certificate_service = cert_service

def _generate_certificate_filename(cert):
    """生成证书文件名：单位+组别+项目+姓名.pdf"""
    parts = []
    
    # 单位名称
    if cert.unit_name:
        parts.append(cert.unit_name.strip())
    
    # 组别
    if cert.param_group:
        parts.append(cert.param_group.strip())
    
    # 项目
    if cert.project:
        parts.append(cert.project.strip())
    
    # 姓名
    if cert.name:
        parts.append(cert.name.strip())
    
    # 如果没有任何有效部分，使用证书编号或默认名称
    if not parts:
        if cert.cert_number:
            parts.append(cert.cert_number.strip())
        else:
            parts.append('证书')
    
    # 连接各部分，移除非法字符
    filename = '_'.join(parts)
    # 移除文件名中的非法字符
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '（', '）', '(', ')'))
    filename = filename.replace(' ', '_')
    
    return f'{filename}.pdf'

@admin_bp.route('/download/selected', methods=['POST'])
@admin_login_required
def admin_download_selected_certificates():
    """下载选中的证书"""
    try:
        data = request.get_json()
        cert_ids = data.get('cert_ids', [])
        
        if not cert_ids:
            return jsonify({'error': '未选择任何证书'}), 400
        
        # 获取选中的证书
        certificates = Certificate.query.filter(Certificate.id.in_(cert_ids)).all()
        
        if not certificates:
            return jsonify({'error': '未找到证书'}), 404
        
        # 检查是否所有证书都有文件
        valid_certs = []
        for cert in certificates:
            if cert.certificate_file and os.path.exists(cert.certificate_file):
                valid_certs.append(cert)
        
        if not valid_certs:
            return jsonify({'error': '所选证书均未生成文件'}), 404
        
        # 如果只有一个证书，直接下载
        if len(valid_certs) == 1:
            cert = valid_certs[0]
            # 生成新文件名：单位+组别+项目+获奖名次
            filename = _generate_certificate_filename(cert)
            return send_file(
                cert.certificate_file,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        
        # 多个证书打包下载 - 使用流式压缩提高性能
        def generate_zip():
            memory_file = BytesIO()
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
                for cert in valid_certs:
                    try:
                        # 生成新文件名：单位+组别+项目+获奖名次
                        filename = _generate_certificate_filename(cert)
                        # 检查文件是否重名，如果重名则添加序号
                        counter = 1
                        original_filename = filename
                        while filename in [info.filename for info in zf.filelist]:
                            name, ext = os.path.splitext(original_filename)
                            filename = f"{name}_{counter}{ext}"
                            counter += 1
                        
                        zf.write(cert.certificate_file, filename)
                    except Exception as e:
                        app.logger.warning(f'添加证书文件失败 {cert.id}: {str(e)}')
                        continue
            
            memory_file.seek(0)
            return memory_file
        
        zip_file = generate_zip()
        
        # 获取活动名称作为压缩包名称
        activity = certificates[0].activity if certificates else None
        zip_name = f'{activity.title}_选中证书.zip' if activity else '选中证书.zip'
        
        return send_file(
            zip_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_name
        )
        
    except Exception as e:
        app.logger.error(f'下载选中证书失败: {str(e)}')
        return jsonify({'error': f'下载失败: {str(e)}'}), 500

@admin_bp.route('/download/all/<int:activity_id>')
@admin_login_required
def admin_download_all_certificates(activity_id):
    """下载活动的全部证书 - 优化版本"""
    try:
        # 获取活动信息
        activity = Activity.query.get_or_404(activity_id)
        
        # 获取所有已生成的证书
        certificates = Certificate.query.filter_by(activity_id=activity_id).all()
        
        if not certificates:
            return jsonify({'error': '该活动暂无证书'}), 404
        
        # 筛选有文件的证书
        valid_certs = []
        for cert in certificates:
            if cert.certificate_file and os.path.exists(cert.certificate_file):
                valid_certs.append(cert)
        
        if not valid_certs:
            return jsonify({'error': '该活动暂无已生成的证书文件'}), 404
        
        # 如果证书数量很多，建议分批下载
        if len(valid_certs) > 100:
            return jsonify({
                'error': f'证书数量过多({len(valid_certs)}份)，建议使用选中下载功能分批下载',
                'suggestion': 'batch_download'
            }), 400
        
        # 使用生成器函数创建ZIP文件，提高内存效率
        def generate_zip():
            memory_file = BytesIO()
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
                processed = 0
                for cert in valid_certs:
                    try:
                        # 生成新文件名：单位+组别+项目+获奖名次
                        filename = _generate_certificate_filename(cert)
                        # 检查文件是否重名，如果重名则添加序号
                        counter = 1
                        original_filename = filename
                        while filename in [info.filename for info in zf.filelist]:
                            name, ext = os.path.splitext(original_filename)
                            filename = f"{name}_{counter}{ext}"
                            counter += 1
                        
                        zf.write(cert.certificate_file, filename)
                        processed += 1
                        
                        # 记录进度（可用于后续添加进度条）
                        if processed % 10 == 0:
                            app.logger.info(f'打包进度: {processed}/{len(valid_certs)}')
                            
                    except Exception as e:
                        app.logger.warning(f'添加证书文件失败 {cert.id}: {str(e)}')
                        continue
            
            memory_file.seek(0)
            return memory_file
        
        zip_file = generate_zip()
        zip_name = f'{activity.title}_全部证书.zip'
        
        return send_file(
            zip_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_name
        )
        
    except Exception as e:
        app.logger.error(f'下载全部证书失败: {str(e)}')
        return jsonify({'error': f'下载失败: {str(e)}'}), 500

@admin_bp.route('/download/progress/<int:activity_id>')
@admin_login_required
def get_download_progress(activity_id):
    """获取下载进度（为将来的进度条功能预留）"""
    try:
        # 这里可以实现下载进度查询
        # 目前返回证书数量信息
        total_certs = Certificate.query.filter_by(activity_id=activity_id).count()
        valid_certs = Certificate.query.filter_by(activity_id=activity_id).filter(
            Certificate.certificate_file.isnot(None)
        ).count()
        
        return jsonify({
            'total': total_certs,
            'valid': valid_certs,
            'ready': valid_certs > 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500 