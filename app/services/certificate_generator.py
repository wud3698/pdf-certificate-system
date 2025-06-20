import os
from datetime import datetime
from io import BytesIO
import pandas as pd
import json
import re
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm, Cm
from flask import send_file, jsonify
import zipfile
from .image_service import ImageService

class CertificateGenerator:
    def __init__(self, app, db, Activity, Certificate):
        self.app = app
        self.db = db
        self.Activity = Activity
        self.Certificate = Certificate
        self.image_service = ImageService(app)

    def process_excel_data(self, activity_id, df, field_mapping, excel_file_path=None):
        """处理Excel数据并保存到数据库"""
        success_count = 0
        error_count = 0
        errors = []

        try:
            print(f"开始处理Excel数据，活动ID: {activity_id}")
            print(f"字段映射信息: {field_mapping}")
            
            # 获取活动信息
            activity = self.Activity.query.get(activity_id)
            if not activity:
                print(f"活动不存在，ID: {activity_id}")
                raise Exception('活动不存在')

            # 处理图片列
            image_data = {}
            image_backup_data = {}
            
            # 处理主图片列
            if excel_file_path and 'image_path' in field_mapping:
                image_column = field_mapping['image_path']
                # 找到图片列的索引
                if image_column in df.columns:
                    image_column_index = df.columns.get_loc(image_column)
                    print(f"开始从Excel提取主图片，列: {image_column} (索引: {image_column_index})")
                    image_data = self.image_service.extract_images_from_excel(
                        excel_file_path, image_column_index
                    )
                    print(f"提取到 {len(image_data)} 张主图片")
            
            # 处理备用图片列
            if excel_file_path and 'image_path_backup' in field_mapping:
                backup_image_column = field_mapping['image_path_backup']
                # 找到备用图片列的索引
                if backup_image_column in df.columns:
                    backup_image_column_index = df.columns.get_loc(backup_image_column)
                    print(f"开始从Excel提取备用图片，列: {backup_image_column} (索引: {backup_image_column_index})")
                    image_backup_data = self.image_service.extract_images_from_excel(
                        excel_file_path, backup_image_column_index
                    )
                    print(f"提取到 {len(image_backup_data)} 张备用图片")

            # 遍历Excel数据
            for index, row in df.iterrows():
                print(f"\n处理第{index + 1}行数据:")
                # 为每条记录创建新的事务
                try:
                    # 构建证书数据
                    cert_data = {}
                    for system_field, excel_column in field_mapping.items():
                        if system_field == 'image_path':
                            # 处理主图片字段
                            if index in image_data:
                                cert_data[system_field] = image_data[index]['relative_path']
                                print(f"  {system_field}: {cert_data[system_field]} (来自Excel主图片)")
                            else:
                                # 检查Excel单元格是否有图片路径文本
                                value = row[excel_column] if pd.notna(row[excel_column]) else None
                                cert_data[system_field] = value
                                print(f"  {system_field}: {cert_data[system_field]} (文本路径)")
                        elif system_field == 'image_path_backup':
                            # 处理备用图片字段
                            if index in image_backup_data:
                                cert_data[system_field] = image_backup_data[index]['relative_path']
                                print(f"  {system_field}: {cert_data[system_field]} (来自Excel备用图片)")
                            else:
                                # 检查Excel单元格是否有图片路径文本
                                value = row[excel_column] if pd.notna(row[excel_column]) else None
                                cert_data[system_field] = value
                                print(f"  {system_field}: {cert_data[system_field]} (文本路径)")
                        else:
                            value = row[excel_column]
                            # 特殊处理手机号、年龄和出生日期字段
                            if system_field in ['phone', 'age'] and pd.notna(value):
                                # 如果是数字格式，直接转换为整数字符串
                                if isinstance(value, (int, float)):
                                    value = str(int(value)) if float(value).is_integer() else str(value)
                            elif system_field == 'birth_date' and pd.notna(value):
                                # 处理出生日期格式
                                if isinstance(value, pd.Timestamp):
                                    value = value.date()
                                elif isinstance(value, str):
                                    try:
                                        from datetime import datetime
                                        value = datetime.strptime(value, '%Y-%m-%d').date()
                                    except:
                                        value = None
                            cert_data[system_field] = value if pd.notna(value) else None
                            print(f"  {system_field}: {cert_data[system_field]}")

                    # 检查必要字段
                    if not cert_data.get('name'):
                        print(f"  错误：缺少姓名")
                        raise Exception('缺少姓名')

                    # 使用独立的会话处理数据库操作
                    with self.db.session.begin_nested():
                        # 如果有证书编号，检查是否已存在
                        existing_cert = None
                        if cert_data.get('cert_number'):
                            existing_cert = self.Certificate.query.filter_by(
                                activity_id=activity_id,
                                cert_number=cert_data['cert_number']
                            ).first()

                        if existing_cert:
                            print(f"  发现重复的证书编号: {cert_data['cert_number']}")
                            # 如果设置了覆盖，更新现有记录
                            for key, value in cert_data.items():
                                setattr(existing_cert, key, value)
                            certificate = existing_cert
                        else:
                            # 创建新证书记录
                            certificate = self.Certificate(
                                activity_id=activity_id,
                                **cert_data
                            )
                            self.db.session.add(certificate)
                        
                        success_count += 1
                        print(f"  成功处理第{index + 1}行数据")

                    # 如果成功，提交这条记录的事务
                    self.db.session.commit()

                except Exception as e:
                    # 发生错误时回滚当前记录的事务
                    self.db.session.rollback()
                    error_message = f'第{index + 1}行: {str(e)}'
                    print(f"  错误：{error_message}")
                    if error_message not in errors:  # 避免重复添加错误信息
                        errors.append(error_message)
                        error_count += 1

            print(f"\n处理完成：成功 {success_count} 条，失败 {error_count} 条")
            if errors:
                print("错误列表：")
                for error in errors:
                    print(f"  {error}")

            return {
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors,
                'images_extracted': len(image_data),
                'backup_images_extracted': len(image_backup_data)
            }

        except Exception as e:
            # 发生错误时回滚所有更改
            self.db.session.rollback()
            print(f"处理Excel数据时发生错误：{str(e)}")
            raise Exception(f'处理Excel数据失败：{str(e)}')

    def generate_certificate(self, activity_id, cert_data, image_size='one_inch', backup_image_size='square_small'):
        """生成证书"""
        try:
            # 获取活动信息和模板
            activity = self.Activity.query.get(activity_id)
            if not activity or not activity.template_file:
                return {'error': '活动或模板不存在'}

            print(f"🔍 证书生成调试信息:")
            print(f"   活动ID: {activity_id}")
            print(f"   活动名称: {activity.title}")
            print(f"   模板文件路径: {activity.template_file}")
            print(f"   模板文件存在: {os.path.exists(activity.template_file) if activity.template_file else False}")
            print(f"   模板类型: {getattr(activity, 'template_type', 'unknown')}")
            print(f"   图片尺寸: {image_size}")
            
            # 确保证书生成目录存在
            certificates_folder = self.app.config['GENERATED_CERTIFICATES_FOLDER']
            os.makedirs(certificates_folder, exist_ok=True)

            # 生成文件名（使用姓名和证书编号）
            winner_name = cert_data.get('name') or cert_data.get('unit_name') or 'unknown'
            cert_number = cert_data.get('cert_number', '')
            # 移除文件名中的非法字符 (使用更通用的方式)
            winner_name = "".join(c for c in winner_name if c.isalnum() or c in (' ', '-', '_'))
            cert_number = "".join(c for c in str(cert_number) if c.isalnum() or c in (' ', '-', '_'))
            
            # 使用更短的文件名以避免路径过长问题
            safe_name = winner_name[:20] if len(winner_name) > 20 else winner_name
            filename = f"{safe_name}_{cert_number[-8:]}.pdf"
            cert_path = os.path.join(certificates_folder, filename)
            
            # 如果目标PDF已存在，先删除
            if os.path.exists(cert_path):
                try:
                    os.remove(cert_path)
                except Exception:
                    pass

            # 处理DOCX模板
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    # 生成临时文件名
                    temp_docx = os.path.join(certificates_folder, f"temp_{cert_number[-8:]}_{attempt}.docx")
                    
                    # 确保临时文件不存在
                    if os.path.exists(temp_docx):
                        os.remove(temp_docx)

                    # 渲染模板
                    print(f"📄 开始渲染模板: {activity.template_file}")
                    doc = DocxTemplate(activity.template_file)
                    print(f"✅ DocxTemplate 创建成功")
                    
                    # 处理证书数据，将图片路径转换为InlineImage对象，传入图片尺寸参数
                    processed_cert_data = self._process_cert_data_for_template(cert_data, doc, image_size, backup_image_size)
                    print(f"📋 证书数据处理完成，包含字段: {list(processed_cert_data.keys())}")

                    doc.render(processed_cert_data)
                    print(f"🎨 模板渲染完成")
                    doc.save(temp_docx)
                    print(f"💾 临时文件保存: {temp_docx}")

                    # 预处理DOCX文件，替换字体信息
                    self._preprocess_docx_fonts(temp_docx)

                    try:
                        # 使用LibreOffice转换为PDF，添加字体配置参数
                        import subprocess
                        
                        # 设置环境变量以支持中文字体
                        env = os.environ.copy()
                        env['LC_ALL'] = 'C.UTF-8'
                        env['LANG'] = 'C.UTF-8'
                        env['SAL_USE_VCLPLUGIN'] = 'svp'  # 使用无头模式
                        
                        # 尝试多种转换策略
                        conversion_strategies = [
                            # 策略1：基本转换
                            [
                                'soffice',
                                '--headless',
                                '--invisible',
                                '--nodefault',
                                '--nolockcheck',
                                '--nologo',
                                '--norestore',
                                '--convert-to', 'pdf',
                                '--outdir', certificates_folder,
                                temp_docx
                            ],
                            # 策略2：使用指定字体配置
                            [
                                'soffice',
                                '--headless',
                                '--invisible',
                                '--convert-to', 'pdf:writer_pdf_Export:{"UseTaggedPDF":false,"ExportNotes":false}',
                                '--outdir', certificates_folder,
                                temp_docx
                            ]
                        ]
                        
                        conversion_success = False
                        for strategy_index, cmd in enumerate(conversion_strategies):
                            try:
                                print(f"尝试转换策略 {strategy_index + 1}: {' '.join(cmd[:5])}...")
                                result = subprocess.run(
                                    cmd,
                                    capture_output=True,
                                    text=True,
                                    timeout=60,
                                    env=env,
                                    cwd=os.getcwd()  # 使用当前工作目录而不是证书目录
                                )
                                
                                if result.returncode == 0:
                                    print(f"转换策略 {strategy_index + 1} 成功")
                                    conversion_success = True
                                    break
                                else:
                                    print(f"转换策略 {strategy_index + 1} 失败: {result.stderr}")
                                    
                            except subprocess.TimeoutExpired:
                                print(f"转换策略 {strategy_index + 1} 超时")
                                continue
                            except Exception as e:
                                print(f"转换策略 {strategy_index + 1} 异常: {e}")
                                continue
                        
                        if not conversion_success:
                            raise Exception("所有转换策略都失败了")
                            
                        # 检查PDF文件是否生成成功（基于临时文件名）
                        temp_pdf = temp_docx.replace('.docx', '.pdf')
                        if os.path.exists(temp_pdf):
                            print(f"PDF生成成功: {temp_pdf}")
                            # 重命名为最终文件名
                            try:
                                if os.path.exists(cert_path):
                                    os.remove(cert_path)
                                os.rename(temp_pdf, cert_path)
                                print(f"PDF重命名为: {cert_path}")
                            except Exception as e:
                                print(f"重命名PDF文件失败: {e}")
                                # 如果重命名失败，使用临时文件名
                                cert_path = temp_pdf
                            
                            # 清理临时docx文件
                            try:
                                os.remove(temp_docx)
                            except:
                                pass
                            return {'success': True, 'cert_path': cert_path, 'filename': os.path.basename(cert_path)}
                        else:
                            raise Exception("PDF文件未生成")
                            
                    except Exception as e:
                        last_error = str(e)
                        print(f"第{attempt + 1}次转换失败: {last_error}")
                        # 清理临时文件
                        try:
                            if os.path.exists(temp_docx):
                                os.remove(temp_docx)
                        except:
                            pass
                        
                        if attempt < max_retries - 1:
                            continue
                        else:
                            break

                except Exception as e:
                    last_error = str(e)
                    print(f"第{attempt + 1}次生成失败: {last_error}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        break

            return {'error': f'证书生成失败: {last_error}'}

        except Exception as e:
            print(f"证书生成错误: {str(e)}")
            return {'error': f'证书生成失败: {str(e)}'}

    def _preprocess_docx_fonts(self, docx_path):
        """预处理DOCX文件，替换字体以确保兼容性"""
        try:
            import zipfile
            import tempfile
            import shutil
            
            # 字体映射表 - 将不兼容的字体替换为系统字体
            font_mapping = {
                # 中文字体映射
                '宋体': 'SimSun',
                '黑体': 'SimHei', 
                '微软雅黑': 'Microsoft YaHei',
                '楷体': 'KaiTi',
                '仿宋': 'FangSong',
                '华文宋体': 'STSong',
                '华文黑体': 'STHeiti',
                '华文楷体': 'STKaiti',
                '华文仿宋': 'STFangsong',
                '方正小标宋简体': 'SimSun',
                '方正黑体简体': 'SimHei',
                # 英文字体映射
                'Times New Roman': 'Times New Roman',
                'Arial': 'Arial',
                'Calibri': 'Calibri',
                'Helvetica': 'Arial',
                # 其他常见字体
                'DejaVu Sans': 'Arial',
                'Liberation Sans': 'Arial',
                'Noto Sans CJK SC': 'Microsoft YaHei'
            }
            
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # 解压DOCX文件
                with zipfile.ZipFile(docx_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # 处理需要修改的XML文件
                xml_files = [
                    'word/document.xml',
                    'word/styles.xml',
                    'word/fontTable.xml'
                ]
                
                for xml_file in xml_files:
                    xml_path = os.path.join(temp_dir, xml_file)
                    if os.path.exists(xml_path):
                        self._replace_fonts_in_xml(xml_path, font_mapping)
                
                # 重新打包DOCX文件
                with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arc_name = os.path.relpath(file_path, temp_dir)
                            zip_ref.write(file_path, arc_name)
                            
        except Exception as e:
            print(f"预处理DOCX字体失败: {e}")
            # 如果预处理失败，继续使用原文件
            pass

    def _replace_fonts_in_xml(self, xml_path, font_mapping):
        """替换XML文件中的字体引用"""
        try:
            with open(xml_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换字体引用
            modified = False
            for old_font, new_font in font_mapping.items():
                # 替换各种字体属性
                patterns = [
                    f'w:ascii="{old_font}"',
                    f'w:eastAsia="{old_font}"',
                    f'w:hAnsi="{old_font}"',
                    f'w:cs="{old_font}"',
                    f'w:name="{old_font}"'
                ]
                
                for pattern in patterns:
                    new_pattern = pattern.replace(old_font, new_font)
                    if pattern in content:
                        content = content.replace(pattern, new_pattern)
                        modified = True
                        print(f"替换字体: {old_font} -> {new_font}")
            
            # 如果有修改，写回文件
            if modified:
                with open(xml_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
        except Exception as e:
            print(f"替换XML字体失败: {e}")
            pass

    def _analyze_docx_fonts(self, docx_path):
        """分析DOCX文件中使用的字体（用于调试）"""
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            
            fonts_found = set()
            
            with zipfile.ZipFile(docx_path, 'r') as docx:
                # 检查document.xml中的字体
                if 'word/document.xml' in docx.namelist():
                    content = docx.read('word/document.xml').decode('utf-8')
                    if 'w:rFonts' in content:
                        try:
                            root = ET.fromstring(content)
                            for elem in root.iter():
                                if 'rFonts' in elem.tag:
                                    for attr, value in elem.attrib.items():
                                        if 'ascii' in attr or 'eastAsia' in attr or 'hAnsi' in attr:
                                            fonts_found.add(value)
                        except Exception as e:
                            print(f"解析document.xml失败: {e}")
                
                # 检查styles.xml中的字体
                if 'word/styles.xml' in docx.namelist():
                    content = docx.read('word/styles.xml').decode('utf-8')
                    if 'w:rFonts' in content:
                        try:
                            root = ET.fromstring(content)
                            for elem in root.iter():
                                if 'rFonts' in elem.tag:
                                    for attr, value in elem.attrib.items():
                                        if 'ascii' in attr or 'eastAsia' in attr or 'hAnsi' in attr:
                                            fonts_found.add(value)
                        except Exception as e:
                            print(f"解析styles.xml失败: {e}")
                            
                # 检查字体表文件
                if 'word/fontTable.xml' in docx.namelist():
                    content = docx.read('word/fontTable.xml').decode('utf-8')
                    try:
                        root = ET.fromstring(content)
                        for elem in root.iter():
                            if 'font' in elem.tag and 'name' in elem.attrib:
                                fonts_found.add(elem.attrib['name'])
                    except Exception as e:
                        print(f"解析fontTable.xml失败: {e}")
            
            fonts_list = list(fonts_found)
            if fonts_list:
                print("文档中使用的字体:")
                for i, font in enumerate(sorted(fonts_list), 1):
                    print(f"  {i}. {font}")
            else:
                print("未找到字体信息")
            
            return fonts_list
            
        except Exception as e:
            print(f"分析DOCX文件失败: {e}")
            return []

    def _process_cert_data_for_template(self, cert_data, doc_template, image_size='one_inch', backup_image_size='square_small'):
        """处理证书数据，将图片路径转换为InlineImage对象"""
        processed_data = cert_data.copy()
        
        # 处理图片字段（包括主图片和备用图片）
        image_fields_config = {
            'image_path': {'size': image_size, 'name': '主图片'},
            'image_path_backup': {'size': backup_image_size, 'name': '备用图片'}
        }
        
        for image_field, config in image_fields_config.items():
            if image_field in processed_data and processed_data[image_field]:
                image_path = processed_data[image_field]
                field_size = config['size']
                field_name = config['name']
                
                # 如果是相对路径，转换为绝对路径
                if not os.path.isabs(image_path):
                    # 检查是否包含uploads前缀
                    if not image_path.startswith('uploads'):
                        image_path = os.path.join(self.app.config['UPLOAD_FOLDER'], 'participant_images', os.path.basename(image_path))
                    else:
                        image_path = os.path.join(os.getcwd(), image_path)
                
                # 检查图片文件是否存在
                if os.path.exists(image_path):
                    try:
                        # 验证图片文件
                        is_valid, message = self.image_service.validate_image(image_path)
                        if not is_valid:
                            print(f"⚠️  {field_name}验证失败: {message}")
                            processed_data[image_field] = None
                            continue
                        
                        # 使用传入的DocxTemplate对象和对应的图片尺寸创建InlineImage
                        inline_image = self._create_inline_image(doc_template, image_path, field_size)
                        
                        # 替换图片字段
                        processed_data[image_field] = inline_image
                        
                        print(f"✅ 成功处理{field_name}字段: {image_path} (尺寸: {field_size})")
                        
                    except Exception as e:
                        print(f"⚠️  处理{field_name}字段失败: {e}")
                        # 如果处理失败，移除图片字段以避免模板渲染错误
                        processed_data[image_field] = None
                else:
                    print(f"⚠️  {field_name}文件不存在: {image_path}")
                    processed_data[image_field] = None
        
        return processed_data

    def _create_inline_image(self, doc_template, image_path, image_size='auto'):
        """创建InlineImage对象，支持多种图片尺寸选择"""
        try:
            # 分析图片尺寸和比例
            from PIL import Image
            
            with Image.open(image_path) as img:
                original_width, original_height = img.size
                aspect_ratio = original_width / original_height
                
                print(f"📐 图片分析: {original_width}x{original_height}像素, 宽高比{aspect_ratio:.2f}")
                
                # 预定义的图片尺寸选项
                size_presets = {
                    'one_inch': {'width': 2.5, 'height': 3.5, 'name': '一寸照'},  # 默认
                    'two_inch': {'width': 3.5, 'height': 5.3, 'name': '二寸照'},
                    'small_two_inch': {'width': 3.3, 'height': 4.8, 'name': '小二寸'},
                    'square_small': {'width': 2.5, 'height': 2.5, 'name': '正方形小'},  # 新增：2.5cm x 2.5cm
                    'square_medium': {'width': 3.0, 'height': 3.0, 'name': '正方形中'},  # 新增：3cm x 3cm
                    'square_large': {'width': 4.0, 'height': 4.0, 'name': '正方形大'},  # 新增：4cm x 4cm
                    'custom_small': {'width': 2.0, 'height': 2.8, 'name': '小尺寸'},
                    'custom_medium': {'width': 4.0, 'height': 5.5, 'name': '中等尺寸'},
                    'custom_large': {'width': 5.0, 'height': 7.0, 'name': '大尺寸'},
                    'auto': None  # 智能计算
                }
                
                if image_size == 'auto' or image_size not in size_presets:
                    # 智能计算显示尺寸（原逻辑）
                    target_width_cm = 3.5
                    target_height_cm = target_width_cm / aspect_ratio
                    
                    # 设置最大和最小尺寸限制
                    max_width_cm = 5.0
                    max_height_cm = 6.0
                    min_width_cm = 2.0
                    min_height_cm = 2.0
                    
                    # 如果高度超出限制，调整尺寸
                    if target_height_cm > max_height_cm:
                        target_height_cm = max_height_cm
                        target_width_cm = target_height_cm * aspect_ratio
                    elif target_height_cm < min_height_cm:
                        target_height_cm = min_height_cm
                        target_width_cm = target_height_cm * aspect_ratio
                    
                    # 如果宽度超出限制，再次调整
                    if target_width_cm > max_width_cm:
                        target_width_cm = max_width_cm
                        target_height_cm = target_width_cm / aspect_ratio
                    elif target_width_cm < min_width_cm:
                        target_width_cm = min_width_cm
                        target_height_cm = target_width_cm / aspect_ratio
                        
                    print(f"📏 智能尺寸: {target_width_cm:.1f}cm x {target_height_cm:.1f}cm")
                else:
                    # 使用预设尺寸
                    preset = size_presets[image_size]
                    if preset:
                        target_width_cm = preset['width']
                        target_height_cm = preset['height']
                        print(f"📏 使用预设尺寸 ({preset['name']}): {target_width_cm:.1f}cm x {target_height_cm:.1f}cm")
                    else:
                        # 回退到智能计算
                        target_width_cm = 3.5
                        target_height_cm = target_width_cm / aspect_ratio
                        print(f"📏 回退到智能尺寸: {target_width_cm:.1f}cm x {target_height_cm:.1f}cm")
                
                # 创建InlineImage对象，使用计算出的尺寸
                inline_image = InlineImage(doc_template, image_path, 
                                         width=Cm(target_width_cm), 
                                         height=Cm(target_height_cm))
                
                print(f"✅ InlineImage创建成功 (尺寸: {image_size})")
                return inline_image
                
        except Exception as e:
            print(f"❌ 图片尺寸处理失败: {e}")
            # 如果处理失败，使用默认一寸照片尺寸
            try:
                print("🔄 使用默认一寸照片尺寸...")
                return InlineImage(doc_template, image_path, width=Cm(2.5), height=Cm(3.5))
            except Exception as e2:
                print(f"❌ 默认尺寸也失败: {e2}")
                # 最后尝试不指定尺寸
                try:
                    print("🔄 尝试无尺寸模式...")
                    return InlineImage(doc_template, image_path)
                except Exception as e3:
                    print(f"❌ 无尺寸模式也失败: {e3}")
                    raise e 