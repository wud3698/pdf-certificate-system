from flask import render_template, request, redirect, url_for, flash
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from app.models import db, CarouselImage
from app.auth import admin_login_required
from . import admin_bp

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/site')
@admin_login_required
def site_settings():
    # 获取所有轮播图，按order排序
    carousel_images = CarouselImage.query.order_by(CarouselImage.order).all()
    
    # 处理图片URL
    images = []
    for img in carousel_images:
        images.append({
            'id': img.id,
            'url': url_for('main.get_carousel_image', image_id=img.id),
            'order': img.order
        })
    
    # 检查帮助文档是否存在
    help_pdf_path = os.path.join('static', 'help.pdf')
    help_pdf_url = url_for('static', filename='help.pdf') if os.path.exists(help_pdf_path) else None
    
    return render_template('admin/site.html', 
                         carousel_images=images,
                         help_pdf_url=help_pdf_url,
                         active_page='site')

@admin_bp.route('/site/upload-carousel', methods=['POST'])
@admin_login_required
def upload_carousel_image():
    if 'carousel_image' not in request.files:
        flash('没有选择文件', 'error')
        return redirect(url_for('admin.site_settings'))
    
    file = request.files['carousel_image']
    if file.filename == '':
        flash('没有选择文件', 'error')
        return redirect(url_for('admin.site_settings'))
    
    if file and allowed_file(file.filename):
        # 生成文件名
        filename = secure_filename(f'carousel_{datetime.now().strftime("%Y%m%d%H%M%S")}{os.path.splitext(file.filename)[1]}')
        file_path = os.path.join(app.config['CAROUSEL_IMAGES_FOLDER'], filename)
        
        # 保存文件
        file.save(file_path)
        
        # 创建数据库记录
        image = CarouselImage(
            image_file=file_path,
            order=request.form.get('image_order', type=int, default=1)
        )
        db.session.add(image)
        db.session.commit()
        
        flash('图片上传成功', 'success')
    else:
        flash('不支持的文件格式', 'error')
    
    return redirect(url_for('admin.site_settings'))

@admin_bp.route('/site/delete-carousel', methods=['POST'])
@admin_login_required
def delete_carousel_image():
    image_id = request.form.get('image_id', type=int)
    if not image_id:
        flash('参数错误', 'error')
        return redirect(url_for('admin.site_settings'))
    
    image = CarouselImage.query.get_or_404(image_id)
    
    # 删除文件
    if image.image_file and os.path.exists(image.image_file):
        os.remove(image.image_file)
    
    # 删除数据库记录
    db.session.delete(image)
    db.session.commit()
    
    flash('图片删除成功', 'success')
    return redirect(url_for('admin.site_settings'))

@admin_bp.route('/site/upload-help-pdf', methods=['POST'])
@admin_login_required
def upload_help_pdf():
    try:
        if 'help_pdf' not in request.files:
            flash('没有选择文件', 'error')
            return redirect(url_for('admin.site_settings'))
        
        file = request.files['help_pdf']
        if file.filename == '':
            flash('没有选择文件', 'error')
            return redirect(url_for('admin.site_settings'))
        
        if file and file.filename.lower().endswith('.pdf'):
            # 确保static目录存在
            if not os.path.exists('static'):
                os.makedirs('static')
            
            # 保存文件
            file_path = os.path.join('static', 'help.pdf')
            
            # 如果已存在旧文件，先删除
            if os.path.exists(file_path):
                os.remove(file_path)
            
            file.save(file_path)
            flash('帮助文档上传成功', 'success')
        else:
            flash('只允许上传PDF文件', 'error')
            
        return redirect(url_for('admin.site_settings'))
    except Exception as e:
        flash(f'上传失败：{str(e)}', 'error')
        return redirect(url_for('admin.site_settings'))

@admin_bp.route('/site/delete-help-pdf', methods=['POST'])
@admin_login_required
def delete_help_pdf():
    try:
        file_path = os.path.join('static', 'help.pdf')
        if os.path.exists(file_path):
            os.remove(file_path)
            flash('帮助文档删除成功', 'success')
        else:
            flash('帮助文档不存在', 'error')
        
        return redirect(url_for('admin.site_settings'))
    except Exception as e:
        flash(f'删除失败：{str(e)}', 'error')
        return redirect(url_for('admin.site_settings')) 