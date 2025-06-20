from flask import render_template, request, jsonify, send_file
import os
from datetime import datetime
from werkzeug.utils import secure_filename
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

@admin_bp.route('/activities')
@admin_login_required
def admin_activities():
    # 获取搜索参数
    title = request.args.get('title', '')
    category = request.args.get('category', '')
    region = request.args.get('region', '')
    publisher = request.args.get('publisher', '')
    status = request.args.get('status', '')

    # 构建查询
    query = Activity.query
    if title:
        query = query.filter(Activity.title.like(f'%{title}%'))
    if category:
        query = query.filter(Activity.category.like(f'%{category}%'))
    if region:
        query = query.filter(Activity.region.like(f'%{region}%'))
    if publisher:
        query = query.filter(Activity.publisher.like(f'%{publisher}%'))
    if status:
        query = query.filter(Activity.status == status)

    # 按发布时间升序排列
    activities = query.order_by(Activity.publish_date.asc()).all()
    return render_template('admin/activities.html', activities=activities, active_page='activities')

@admin_bp.route('/upload')
@admin_login_required
def admin_upload():
    activities = Activity.query.order_by(Activity.publish_date.desc()).all()
    return render_template('admin/upload.html', activities=activities, active_page='upload')

@admin_bp.route('/activity/add', methods=['POST'])
@admin_login_required
def admin_add_activity():
    try:
        # 处理图片上传
        image_file = request.files.get('image')
        image_path = None
        
        if image_file and image_file.filename:
            # 验证文件类型
            allowed_extensions = {'jpg', 'jpeg', 'png'}
            file_ext = os.path.splitext(image_file.filename)[1].lower()
            if file_ext[1:] not in allowed_extensions:
                return jsonify({'error': '只支持jpg、jpeg、png格式的图片'}), 400
            
            # 生成安全的文件名并保存
            filename = secure_filename(f'activity_{datetime.now().strftime("%Y%m%d%H%M%S")}{file_ext}')
            image_path = os.path.join(app.config['ACTIVITY_IMAGES_FOLDER'], filename)
            image_file.save(image_path)

        activity = Activity(
            title=request.form['title'],
            category=request.form['category'],
            region=request.form['region'],
            publisher=request.form['publisher'],
            status=request.form['status'],
            image_file=image_path
        )
        db.session.add(activity)
        db.session.commit()
        return jsonify({'message': '活动添加成功', 'id': activity.id})
    except Exception as e:
        db.session.rollback()
        # 如果图片已保存但数据库操作失败，删除已保存的图片
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        return jsonify({'error': str(e)}), 400

@admin_bp.route('/activity/<int:activity_id>', methods=['PUT'])
@admin_login_required
def admin_update_activity(activity_id):
    try:
        activity = Activity.query.get_or_404(activity_id)
        old_image = activity.image_file
        
        # 处理图片上传
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            # 验证文件类型
            allowed_extensions = {'jpg', 'jpeg', 'png'}
            file_ext = os.path.splitext(image_file.filename)[1].lower()
            if file_ext[1:] not in allowed_extensions:
                return jsonify({'error': '只支持jpg、jpeg、png格式的图片'}), 400
            
            # 生成安全的文件名并保存
            filename = secure_filename(f'activity_{activity_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}{file_ext}')
            image_path = os.path.join(app.config['ACTIVITY_IMAGES_FOLDER'], filename)
            image_file.save(image_path)
            
            # 更新图片路径
            activity.image_file = image_path
            
            # 删除旧图片
            if old_image and os.path.exists(old_image):
                os.remove(old_image)

        activity.title = request.form['title']
        activity.category = request.form['category']
        activity.region = request.form['region']
        activity.publisher = request.form['publisher']
        activity.status = request.form['status']
        
        db.session.commit()
        return jsonify({'message': '活动更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@admin_bp.route('/activity/<int:activity_id>', methods=['DELETE'])
@admin_login_required
def admin_delete_activity(activity_id):
    try:
        activity = Activity.query.get_or_404(activity_id)
        
        # 检查是否存在关联的证书
        certificates = Certificate.query.filter_by(activity_id=activity_id).first()
        if certificates:
            return jsonify({'error': 'has_certificates'}), 400
        
        # 删除活动图片
        if activity.image_file and os.path.exists(activity.image_file):
            os.remove(activity.image_file)
            
        db.session.delete(activity)
        db.session.commit()
        return jsonify({'message': '活动删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@admin_bp.route('/activity/<int:activity_id>/image')
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