from flask import render_template, request, jsonify
import os
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

@admin_bp.route('/generate', methods=['GET', 'POST'])
@admin_login_required
def admin_generate():
    if request.method == 'GET':
        activities = Activity.query.order_by(Activity.publish_date.desc()).all()
        return render_template('admin/generate.html', 
                            activities=activities, 
                            winners=[],
                            active_page='generate')
    else:
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': '无效的请求数据', 'success': False}), 400
                
            activity_id = data.get('activity_id')
            if not activity_id:
                return jsonify({'error': '未指定活动', 'success': False}), 400
                
            activity = Activity.query.get(activity_id)
            if not activity:
                return jsonify({'error': '活动不存在', 'success': False}), 404
            
            if not activity.template_file or not os.path.exists(activity.template_file):
                return jsonify({'error': '证书模板不存在', 'success': False}), 404
            
            if activity.template_type != 'docx':
                return jsonify({'error': '只支持DOCX格式的证书模板', 'success': False}), 400
            
            generate_all = data.get('generate_all', False)
            winner_ids = data.get('winner_ids') if not generate_all else None
            image_size = data.get('image_size', 'one_inch')  # 获取图片尺寸参数，默认为一寸
            backup_image_size = data.get('backup_image_size', 'square_small')  # 获取备用图片尺寸参数，默认为正方形小
            
            # 获取需要生成证书的获奖者
            query = Certificate.query.filter_by(activity_id=activity_id)
            if not generate_all and winner_ids:
                query = query.filter(Certificate.id.in_(winner_ids))
            
            certificates = query.all()
            
            if not certificates:
                return jsonify({
                    'message': '没有找到需要生成证书的获奖者',
                    'success': False
                }), 404
            
            success_count = 0
            error_messages = []
            
            for cert in certificates:
                try:
                    # 如果已存在证书文件，先删除
                    if cert.certificate_file and os.path.exists(cert.certificate_file):
                        os.remove(cert.certificate_file)
                    
                    cert_data = {
                        'cert_number': cert.cert_number,
                        'unit_name': cert.unit_name,
                        'area': cert.area,
                        'name': cert.name,
                        'id_type': cert.id_type,
                        'id_number': cert.id_number,
                        'gender': cert.gender,
                        'age': cert.age,
                        'birth_date': cert.birth_date,
                        'phone': cert.phone,
                        'identity': cert.identity,
                        'grade_major': cert.grade_major,
                        'image_path': cert.image_path,
                        'image_path_backup': cert.image_path_backup,
                        'project': cert.project,
                        'param_group': cert.param_group
                    }
                    
                    result = certificate_generator.generate_certificate(activity_id, cert_data, image_size, backup_image_size)
                    
                    if result.get('success'):
                        cert.certificate_file = os.path.join('uploads', 'certificates', result.get('filename'))
                        db.session.commit()
                        success_count += 1
                    else:
                        error_message = f'{cert.name or cert.unit_name}: {result.get("error", "未知错误")}'
                        error_messages.append(error_message)
                except Exception as e:
                    error_message = f'{cert.name or cert.unit_name}: {str(e)}'
                    error_messages.append(error_message)
            
            if error_messages:
                return jsonify({
                    'message': f'部分证书生成失败。成功：{success_count}份，失败：{len(error_messages)}份',
                    'errors': error_messages,
                    'success': False
                }), 500
            
            return jsonify({
                'message': f'成功生成 {success_count} 份证书',
                'success': True
            })
            
        except Exception as e:
            app.logger.error(f'生成证书时发生错误: {str(e)}', exc_info=True)
            return jsonify({
                'message': f'生成证书时发生错误: {str(e)}',
                'success': False
            }), 500 