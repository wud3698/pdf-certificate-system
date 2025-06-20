import os
import json
import pandas as pd
from io import BytesIO
from flask import Blueprint, render_template, request, jsonify, send_file, url_for, session, current_app
from werkzeug.utils import secure_filename

from app.models import db, Activity, Certificate, CarouselImage
from app.auth import login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # 获取轮播图列表
    carousel_images = CarouselImage.query.order_by(CarouselImage.order).all()
    images = []
    for img in carousel_images:
        images.append(url_for('main.get_carousel_image', image_id=img.id))
    
    # 获取搜索参数
    title = request.args.get('title', '')

    # 构建查询
    query = Activity.query
    if title:
        query = query.filter(Activity.title.like(f'%{title}%'))

    # 获取所有活动列表，按发布时间倒序排列
    activities = query.order_by(Activity.publish_date.desc()).all()
    return render_template('index.html', activities=activities, carousel_images=images)

@main_bp.route('/help')
def help():
    return render_template('help.html')

@main_bp.route('/activity/<int:activity_id>')
def activity_detail(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    # 获取该活动的所有获奖单位，并按组别分组
    query = Certificate.query.filter_by(activity_id=activity_id)
    
    # 获取认证状态
    auth_key = f'authenticated_{activity_id}'
    is_authenticated = session.get(auth_key, False)
    
    # 如果已登录当前活动，只显示当前登录单位的证书
    if is_authenticated:
        unit_name = session.get(f'unit_name_{activity_id}')
        query = query.filter_by(unit_name=unit_name)
    
    certificates = query.order_by(Certificate.param_group, Certificate.unit_name).all()
    
    # 按组别和单位名称分组
    groups = {}
    for cert in certificates:
        group_name = cert.param_group or '未分组'  # 如果组别为空，显示为"未分组"
        if group_name not in groups:
            groups[group_name] = {}
        if cert.unit_name not in groups[group_name]:
            groups[group_name][cert.unit_name] = []
        groups[group_name][cert.unit_name].append(cert)  # 添加证书到对应的单位列表中
    
    return render_template('activity_detail.html', 
                         activity=activity, 
                         groups=groups,
                         is_authenticated=is_authenticated,
                         current_unit=session.get(f'unit_name_{activity_id}', ''))

@main_bp.route('/activity/<int:activity_id>/unit/<string:unit_name>')
@login_required
def unit_certificates(activity_id, unit_name):
    activity = Activity.query.get_or_404(activity_id)
    certificates = Certificate.query.filter_by(
        activity_id=activity_id,
        unit_name=unit_name
    ).order_by(Certificate.cert_number).all()
    
    return render_template('unit_certificates.html', 
                         activity=activity, 
                         certificates=certificates, 
                         unit_name=unit_name)

@main_bp.route('/search')
def search():
    activity_id = request.args.get('activity_id')
    unit_name = request.args.get('unit_name')
    name = request.args.get('name')
    phone = request.args.get('phone')
    
    query = Certificate.query
    if activity_id:
        query = query.filter_by(activity_id=activity_id)
    if unit_name:
        query = query.filter_by(unit_name=unit_name)
    if name:
        query = query.filter_by(name=name)
    if phone:
        query = query.filter_by(phone=phone)
    
    certificates = query.all()
    return render_template('search_results.html', certificates=certificates)

@main_bp.route('/preview/<int:cert_id>')
def preview_certificate(cert_id):
    """预览证书"""
    return current_app.certificate_service.preview_certificate(cert_id)

@main_bp.route('/download/<int:cert_id>')
def download_certificate(cert_id):
    """下载证书"""
    return current_app.certificate_service.download_certificate(cert_id)

@main_bp.route('/download_all/<int:activity_id>/<string:unit_name>')
def download_all_certificates(activity_id, unit_name):
    """打包下载单位的所有证书"""
    return current_app.certificate_service.download_all_certificates(activity_id, unit_name)

@main_bp.route('/activity/<int:activity_id>/image')
def get_activity_image(activity_id):
    """获取活动图片"""
    activity = Activity.query.get_or_404(activity_id)
    if not activity.image_file:
        return '', 404
    
    # 确保使用绝对路径
    image_path = activity.image_file
    if not os.path.isabs(image_path):
        # 如果是相对路径，则转换为绝对路径
        image_path = os.path.abspath(image_path)
    
    if not os.path.exists(image_path):
        return '', 404
    
    return send_file(image_path)

@main_bp.route('/upload_template', methods=['POST'])
def upload_template():
    """处理证书模板上传"""
    try:
        activity_id = request.form.get('activity_id')
        
        if not activity_id:
            return jsonify({'error': '未选择活动', 'success': False}), 400
            
        if 'template' not in request.files:
            return jsonify({'error': '未上传文件', 'success': False}), 400
            
        file = request.files['template']
        if file.filename == '':
            return jsonify({'error': '未选择文件', 'success': False}), 400
            
        # 验证文件类型
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext != '.docx':
            return jsonify({'error': '文件类型必须是.docx', 'success': False}), 400
            
        # 获取活动信息
        activity = Activity.query.get(activity_id)
        if not activity:
            return jsonify({'error': '活动不存在', 'success': False}), 404
            
        # 确保目录存在
        os.makedirs(current_app.config['CERTIFICATE_TEMPLATE_FOLDER'], exist_ok=True)
        
        # 生成文件名和保存路径
        filename = f'template_{activity_id}{file_ext}'
        file_path = os.path.join(current_app.config['CERTIFICATE_TEMPLATE_FOLDER'], filename)
        
        # 如果已存在旧模板，先删除
        if activity.template_file and os.path.exists(activity.template_file):
            os.remove(activity.template_file)
            
        # 保存新模板
        file.save(file_path)
        
        # 更新活动记录
        activity.template_file = file_path
        activity.template_type = 'docx'
        db.session.commit()
        
        return jsonify({
            'message': '模板上传成功',
            'success': True
        })
        
    except Exception as e:
        current_app.logger.error(f'模板上传失败：{str(e)}')
        return jsonify({
            'error': f'模板上传失败：{str(e)}',
            'success': False
        }), 500

@main_bp.route('/get_excel_headers', methods=['POST'])
def get_excel_headers():
    if 'file' not in request.files:
        return jsonify({'error': '未找到文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    if not file.filename.endswith('.xlsx'):
        return jsonify({'error': '请上传Excel文件(.xlsx)'}), 400
    
    try:
        # 将文件内容读入内存
        file_content = BytesIO(file.read())
        
        # 从内存中读取Excel文件，确保读取第一行作为表头
        df = pd.read_excel(file_content, engine='openpyxl')
        
        # 确保所有列名都是字符串类型
        df.columns = df.columns.astype(str)
        
        headers = df.columns.tolist()
        
        return jsonify({'headers': headers})
            
    except Exception as e:
        return jsonify({'error': f'读取Excel表头失败：{str(e)}'}), 400

@main_bp.route('/upload', methods=['POST'])
def upload_data():
    """处理Excel数据上传并生成证书"""
    try:
        activity_id = request.form.get('activity_id')
        if not activity_id:
            return jsonify({'error': '未选择活动'}), 400

        # 获取活动信息
        activity = Activity.query.get(activity_id)
        if not activity:
            return jsonify({'error': '活动不存在'}), 404

        if 'file' not in request.files:
            return jsonify({'error': '未上传文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400

        if not file.filename.endswith('.xlsx'):
            return jsonify({'error': '请上传Excel文件(.xlsx)'}), 400

        # 获取字段映射
        field_mapping_str = request.form.get('field_mapping', '{}')
        try:
            field_mapping = json.loads(field_mapping_str)
        except json.JSONDecodeError as e:
            return jsonify({'error': '字段映射格式错误'}), 400

        # 保存Excel文件到临时位置以便图片提取
        temp_excel_path = None
        try:
            # 创建临时目录
            temp_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp')
            os.makedirs(temp_folder, exist_ok=True)
            
            # 保存文件
            filename = secure_filename(file.filename)
            temp_excel_path = os.path.join(temp_folder, f"temp_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
            file.save(temp_excel_path)
            
            # 读取Excel文件
            df = pd.read_excel(temp_excel_path, engine='openpyxl')
        except Exception as e:
            return jsonify({'error': f'读取Excel文件失败：{str(e)}'}), 400

        # 验证必要的字段是否存在
        required_fields = ['name']  # 更新必要字段：只有姓名是必填的
        missing_fields = [field for field in required_fields if field not in field_mapping.keys()]
        if missing_fields:
            return jsonify({'error': f'缺少必要字段：{", ".join(missing_fields)}'}), 400

        # 验证字段映射中的列是否存在于Excel中
        invalid_columns = [col for col in field_mapping.values() if col not in df.columns]
        if invalid_columns:
            return jsonify({'error': f'Excel中不存在以下列：{", ".join(invalid_columns)}'}), 400

        # 处理Excel数据并生成证书（传递Excel文件路径用于图片提取）
        try:
            result = current_app.certificate_generator.process_excel_data(
                activity_id, df, field_mapping, temp_excel_path
            )
        except Exception as e:
            return jsonify({'error': f'处理数据失败：{str(e)}'}), 500
        finally:
            # 清理临时文件
            if temp_excel_path and os.path.exists(temp_excel_path):
                try:
                    os.remove(temp_excel_path)
                except:
                    pass

        # 返回处理结果
        response = {
            'message': f'处理完成。成功：{result["success_count"]}，失败：{result["error_count"]}',
            'success_count': result['success_count'],
            'error_count': result['error_count']
        }
        
        if result.get('images_extracted', 0) > 0:
            response['message'] += f'，提取图片：{result["images_extracted"]}张'
            
        if result.get('errors'):
            response['errors'] = result['errors']

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': f'服务器错误：{str(e)}'}), 500

@main_bp.route('/template_file/<int:activity_id>')
def get_template_file(activity_id):
    try:
        activity = Activity.query.get(activity_id)
        if not activity:
            return jsonify({'error': '活动不存在'}), 404
            
        if not activity.template_file:
            return jsonify({'error': '活动未设置证书模板'}), 404
            
        if not os.path.exists(activity.template_file):
            return jsonify({'error': '模板文件不存在'}), 404
            
        try:
            return send_file(
                activity.template_file,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                as_attachment=False,
                download_name=os.path.basename(activity.template_file)
            )
        except Exception as e:
            current_app.logger.error(f'读取模板文件失败：{str(e)}')
            return jsonify({'error': f'读取模板文件失败：{str(e)}'}), 500
            
    except Exception as e:
        current_app.logger.error(f'获取模板文件失败：{str(e)}')
        return jsonify({'error': f'获取模板文件失败：{str(e)}'}), 500

@main_bp.route('/api/activity_template/<int:activity_id>')
def get_activity_template(activity_id):
    try:
        activity = Activity.query.get(activity_id)
        if not activity:
            return jsonify({
                'error': '活动不存在'
            }), 404
        
        if not activity.template_file:
            return jsonify({
                'error': '活动未设置证书模板'
            }), 404
            
        if not os.path.exists(activity.template_file):
            return jsonify({
                'error': '证书模板文件不存在'
            }), 404
            
        # 构建模板文件的URL
        template_url = url_for('main.get_template_file', activity_id=activity_id)
        template_name = os.path.basename(activity.template_file)
        
        return jsonify({
            'template_url': template_url,
            'template_name': template_name,
            'template_type': 'docx'
        })
    except Exception as e:
        current_app.logger.error(f'获取模板信息失败：{str(e)}')
        return jsonify({
            'error': f'获取模板信息失败：{str(e)}'
        }), 500

@main_bp.route('/api/winners/<int:activity_id>')
def get_winners(activity_id):
    try:
        activity = Activity.query.get(activity_id)
        if not activity:
            return jsonify({'error': '活动不存在'}), 404
            
        certificates = Certificate.query.filter_by(activity_id=activity_id).all()
        winners = [{
            'id': cert.id,
            'name': cert.name or cert.unit_name,
            'award_type': '参赛者',  # 更新：移除奖项字段
            'has_certificate': bool(cert.certificate_file)  # 添加一个标志表示是否已生成证书
        } for cert in certificates]
        
        return jsonify(winners)
    except Exception as e:
        current_app.logger.error(f'获取获奖者列表失败：{str(e)}')
        return jsonify({'error': f'获取获奖者列表失败：{str(e)}'}), 500

@main_bp.route('/api/delete_template/<int:activity_id>', methods=['DELETE'])
def delete_template(activity_id):
    """删除证书模板"""
    try:
        activity = Activity.query.get_or_404(activity_id)
        
        if not activity.template_file:
            return jsonify({
                'error': '活动未设置证书模板',
                'success': False
            }), 404
            
        # 删除模板文件
        if os.path.exists(activity.template_file):
            os.remove(activity.template_file)
            
        # 清除活动的模板文件路径和字段设置
        activity.template_file = None
        activity.field_settings = None
        db.session.commit()
        
        return jsonify({
            'message': '模板删除成功',
            'success': True
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'删除模板失败：{str(e)}')
        return jsonify({
            'error': f'删除模板失败：{str(e)}',
            'success': False
        }), 500

@main_bp.route('/participant_image/<int:cert_id>')
def get_participant_image(cert_id):
    """获取参赛者图片"""
    cert = Certificate.query.get_or_404(cert_id)
    if not cert.image_path:
        return '', 404
    
    # 构建完整的图片路径
    image_path = os.path.join(current_app.root_path, '..', cert.image_path)
    if not os.path.exists(image_path):
        return '', 404
    
    return send_file(image_path)

@main_bp.route('/participant_backup_image/<int:cert_id>')
def get_participant_backup_image(cert_id):
    """获取参赛者备用图片"""
    cert = Certificate.query.get_or_404(cert_id)
    if not cert.image_path_backup:
        return '', 404
    
    # 构建完整的图片路径
    image_path = os.path.join(current_app.root_path, '..', cert.image_path_backup)
    if not os.path.exists(image_path):
        return '', 404
    
    return send_file(image_path)

@main_bp.route('/carousel_image/<int:image_id>')
def get_carousel_image(image_id):
    """获取轮播图图片"""
    image = CarouselImage.query.get_or_404(image_id)
    if not image.image_file:
        return '', 404
    
    # 确保使用绝对路径
    image_path = image.image_file
    if not os.path.isabs(image_path):
        # 如果是相对路径，则转换为绝对路径
        image_path = os.path.abspath(image_path)
    
    if not os.path.exists(image_path):
        return '', 404
    
    return send_file(image_path)

@main_bp.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools_config():
    """静默处理Chrome DevTools配置请求，避免404日志"""
    return '', 204  # 返回No Content状态码 