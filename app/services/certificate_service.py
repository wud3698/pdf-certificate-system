import os
from io import BytesIO
import zipfile
from flask import send_file, jsonify
from .certificate_generator import CertificateGenerator

class CertificateService:
    def __init__(self, app, db, Activity, Certificate):
        self.app = app
        self.db = db
        self.Activity = Activity
        self.Certificate = Certificate
        self.generator = CertificateGenerator(app, db, Activity, Certificate)

    def preview_certificate(self, cert_id):
        """预览证书"""
        cert = self.Certificate.query.get_or_404(cert_id)
        if not cert.certificate_file:
            return jsonify({'error': '证书文件不存在'}), 404
            
        # 构建绝对路径，确保相对于项目根目录而不是app目录
        if os.path.isabs(cert.certificate_file):
            file_path = cert.certificate_file
        else:
            # 相对路径，相对于项目根目录
            project_root = os.path.dirname(self.app.root_path)
            file_path = os.path.join(project_root, cert.certificate_file)
            
        if not os.path.exists(file_path):
            return jsonify({'error': '证书文件不存在'}), 404

        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=False,
            download_name=os.path.basename(file_path)
        )

    def download_certificate(self, cert_id):
        """下载证书"""
        cert = self.Certificate.query.get_or_404(cert_id)
        if not cert.certificate_file:
            return jsonify({'error': '证书文件不存在'}), 404
            
        # 构建绝对路径，确保相对于项目根目录而不是app目录  
        if os.path.isabs(cert.certificate_file):
            file_path = cert.certificate_file
        else:
            # 相对路径，相对于项目根目录
            project_root = os.path.dirname(self.app.root_path)
            file_path = os.path.join(project_root, cert.certificate_file)
            
        if not os.path.exists(file_path):
            return jsonify({'error': '证书文件不存在'}), 404

        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=os.path.basename(file_path)
        )

    def download_all_certificates(self, activity_id, unit_name):
        """打包下载单位的所有证书"""
        certs = self.Certificate.query.filter_by(activity_id=activity_id, unit_name=unit_name).all()
        if not certs:
            return jsonify({'error': '未找到证书'}), 404
        
        # 创建内存中的ZIP文件
        memory_file = BytesIO()
        project_root = os.path.dirname(self.app.root_path)
        
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for cert in certs:
                if cert.certificate_file:
                    # 构建绝对路径
                    if os.path.isabs(cert.certificate_file):
                        file_path = cert.certificate_file
                    else:
                        file_path = os.path.join(project_root, cert.certificate_file)
                        
                    if os.path.exists(file_path):
                        zf.write(file_path, os.path.basename(file_path))
        
        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{unit_name}_证书.zip'
        )

    def generate_certificate(self, activity_id, cert_data, image_size='one_inch', backup_image_size='square_small'):
        """生成证书"""
        try:
            # 获取活动信息和模板
            activity = self.Activity.query.get(activity_id)
            if not activity or not activity.template_file:
                return jsonify({'error': '活动或模板不存在'}), 404
                
            # 确保证书生成目录存在
            os.makedirs(self.app.config['GENERATED_CERTIFICATES_FOLDER'], exist_ok=True)
            
            # 生成文件名（使用姓名和证书编号）
            winner_name = cert_data.get('name', 'unknown')
            cert_number = cert_data.get('cert_number', '')
            # 移除文件名中的非法字符
            winner_name = "".join(c for c in winner_name if c.isalnum() or c in (' ', '-', '_'))
            cert_number = "".join(c for c in str(cert_number) if c.isalnum() or c in (' ', '-', '_'))
            filename = f"{winner_name}_{cert_number}.pdf"
            
            # 调用证书生成器，传入图片尺寸参数
            result = self.generator.generate_certificate(activity_id, cert_data, image_size, backup_image_size)
            
            if result.get('error'):
                return jsonify({'error': result['error']}), 500
                
            # 保存证书记录
            certificate = self.Certificate(
                activity_id=activity_id,
                cert_number=cert_data.get('cert_number'),
                unit_name=cert_data.get('unit_name'),
                area=cert_data.get('area'),
                name=cert_data.get('name'),
                id_type=cert_data.get('id_type'),
                id_number=cert_data.get('id_number'),
                gender=cert_data.get('gender'),
                age=cert_data.get('age'),
                birth_date=cert_data.get('birth_date'),
                phone=cert_data.get('phone'),
                identity=cert_data.get('identity'),
                grade_major=cert_data.get('grade_major'),
                image_path=cert_data.get('image_path'),
                image_path_backup=cert_data.get('image_path_backup'),
                project=cert_data.get('project'),
                param_group=cert_data.get('param_group'),
                certificate_file=os.path.join('uploads', 'certificates', filename)
            )

            self.db.session.add(certificate)
            self.db.session.commit()
            
            return jsonify({
                'message': '证书生成成功',
                'cert_id': certificate.id,
                'cert_path': certificate.certificate_file
            })
            
        except Exception as e:
            print(f"证书生成错误: {str(e)}")
            return jsonify({'error': f'证书生成失败: {str(e)}'}), 500 