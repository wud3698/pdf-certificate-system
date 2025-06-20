#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体支持和PDF生成诊断工具
用于检查系统字体支持情况和LibreOffice转换功能
"""

import os
import subprocess
import tempfile
import sys
from pathlib import Path

def run_command(cmd, timeout=30):
    """运行shell命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            encoding='utf-8',
            errors='ignore'
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "命令超时"
    except Exception as e:
        return False, "", str(e)

def check_chinese_fonts():
    """检查中文字体安装情况"""
    print("=" * 60)
    print("检查中文字体安装情况")
    print("=" * 60)
    
    success, stdout, stderr = run_command("fc-list :lang=zh")
    if success and stdout.strip():
        fonts = stdout.strip().split('\n')
        print(f"✓ 检测到 {len(fonts)} 个中文字体")
        
        # 显示前10个字体
        print("\n主要中文字体：")
        for i, font in enumerate(fonts[:10]):
            # 提取字体名称
            if ':' in font:
                font_file, font_name = font.split(':', 1)
                print(f"  {i+1}. {font_name.split(':')[0].strip()}")
            else:
                print(f"  {i+1}. {font}")
        
        if len(fonts) > 10:
            print(f"  ... 还有 {len(fonts) - 10} 个字体")
            
        return True
    else:
        print("✗ 未检测到中文字体")
        print("建议安装中文字体包：")
        print("  - Ubuntu/Debian: sudo apt install fonts-wqy-microhei fonts-noto-cjk")
        print("  - CentOS/RHEL: sudo yum install wqy-microhei-fonts google-noto-sans-cjk-ttc-fonts")
        return False

def check_libreoffice():
    """检查LibreOffice安装情况"""
    print("\n" + "=" * 60)
    print("检查LibreOffice安装情况")
    print("=" * 60)
    
    success, stdout, stderr = run_command("soffice --version")
    if success:
        print(f"✓ LibreOffice版本: {stdout.strip()}")
        return True
    else:
        print("✗ LibreOffice未安装或不在PATH中")
        print("请安装LibreOffice:")
        print("  - Ubuntu/Debian: sudo apt install libreoffice")
        print("  - CentOS/RHEL: sudo yum install libreoffice")
        return False

def test_pdf_conversion():
    """测试PDF转换功能"""
    print("\n" + "=" * 60)
    print("测试PDF转换功能")
    print("=" * 60)
    
    # 创建测试文档
    test_content = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>字体测试</title>
    <style>
        body { font-family: "SimHei", "WenQuanYi Micro Hei", "Noto Sans CJK SC", sans-serif; }
        .test-section { margin: 20px 0; padding: 10px; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <h1>中文字体测试报告</h1>
    
    <div class="test-section">
        <h2>基本中文字符测试</h2>
        <p>常用汉字：你好世界，这是一个字体测试文档。</p>
        <p>数字组合：2024年5月28日 星期二</p>
        <p>标点符号：，。；：！？""''（）【】</p>
    </div>
    
    <div class="test-section">
        <h2>不同字体样式测试</h2>
        <p style="font-family: SimSun, serif;">宋体样式：春江潮水连海平，海上明月共潮生。</p>
        <p style="font-family: SimHei, sans-serif;">黑体样式：滚滚长江东逝水，浪花淘尽英雄。</p>
        <p style="font-family: KaiTi, cursive;">楷体样式：山重水复疑无路，柳暗花明又一村。</p>
    </div>
    
    <div class="test-section">
        <h2>混合语言测试</h2>
        <p>中英混合：Hello 世界! Welcome to 中国!</p>
        <p>数字测试：1234567890 一二三四五六七八九十</p>
        <p>特殊字符：@#$%^&*() 《》「」〈〉</p>
    </div>
    
    <div class="test-section">
        <h2>长文本测试</h2>
        <p>这是一段较长的中文文本，用于测试字体在长文本情况下的渲染效果。文本包含了各种常用的汉字字符，以确保字体能够正确显示所有必要的字符。测试内容涵盖了日常使用中可能遇到的各种情况，包括不同的字符组合和标点符号的使用。</p>
    </div>
</body>
</html>'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        html_file = f.name
    
    try:
        # 生成PDF文件名
        pdf_file = html_file.replace('.html', '.pdf')
        
        print("正在转换测试文档...")
        
        # 测试基本转换
        cmd = f'soffice --headless --convert-to pdf --outdir "{os.path.dirname(html_file)}" "{html_file}"'
        success, stdout, stderr = run_command(cmd, timeout=60)
        
        if success and os.path.exists(pdf_file):
            file_size = os.path.getsize(pdf_file)
            print(f"✓ PDF转换成功")
            print(f"  生成文件: {pdf_file}")
            print(f"  文件大小: {file_size} 字节")
            
            # 检查PDF内容（如果有pdfinfo工具）
            success2, stdout2, stderr2 = run_command(f'pdfinfo "{pdf_file}"')
            if success2:
                lines = stdout2.split('\n')
                for line in lines:
                    if 'Pages:' in line or 'Title:' in line or 'Creator:' in line:
                        print(f"  {line.strip()}")
            
            return True, pdf_file
        else:
            print("✗ PDF转换失败")
            if stderr:
                print(f"  错误信息: {stderr}")
            return False, None
            
    finally:
        # 清理临时文件
        try:
            os.unlink(html_file)
        except:
            pass

def test_docx_conversion():
    """测试DOCX转PDF功能"""
    print("\n" + "=" * 60)
    print("测试DOCX转PDF功能")
    print("=" * 60)
    
    # 这里需要一个真实的DOCX文件来测试
    # 检查是否有模板文件
    template_dirs = [
        'uploads/templates',
        'templates',
        '.'
    ]
    
    docx_files = []
    for dir_path in template_dirs:
        if os.path.exists(dir_path):
            for file in os.listdir(dir_path):
                if file.endswith('.docx'):
                    docx_files.append(os.path.join(dir_path, file))
    
    if docx_files:
        test_file = docx_files[0]
        print(f"找到测试文件: {test_file}")
        
        # 创建输出目录
        output_dir = tempfile.mkdtemp()
        
        cmd = f'soffice --headless --convert-to pdf --outdir "{output_dir}" "{test_file}"'
        success, stdout, stderr = run_command(cmd, timeout=60)
        
        expected_pdf = os.path.join(output_dir, os.path.basename(test_file).replace('.docx', '.pdf'))
        
        if success and os.path.exists(expected_pdf):
            file_size = os.path.getsize(expected_pdf)
            print(f"✓ DOCX转PDF成功")
            print(f"  原文件: {test_file}")
            print(f"  生成PDF: {expected_pdf}")
            print(f"  文件大小: {file_size} 字节")
            
            # 清理测试文件
            try:
                os.unlink(expected_pdf)
                os.rmdir(output_dir)
            except:
                pass
                
            return True
        else:
            print("✗ DOCX转PDF失败")
            if stderr:
                print(f"  错误信息: {stderr}")
            return False
    else:
        print("⚠ 未找到DOCX测试文件，跳过DOCX转换测试")
        return None

def check_system_info():
    """检查系统信息"""
    print("\n" + "=" * 60)
    print("系统环境信息")
    print("=" * 60)
    
    # 操作系统信息
    try:
        with open('/etc/os-release', 'r') as f:
            for line in f:
                if line.startswith('PRETTY_NAME='):
                    os_name = line.split('=', 1)[1].strip().strip('"')
                    print(f"操作系统: {os_name}")
                    break
    except:
        print("操作系统: 未知")
    
    # Python版本
    print(f"Python版本: {sys.version.split()[0]}")
    
    # 字体相关环境变量
    env_vars = ['LANG', 'LC_ALL', 'LC_CTYPE']
    for var in env_vars:
        value = os.environ.get(var, '未设置')
        print(f"{var}: {value}")
    
    # 检查字体目录
    font_dirs = [
        '/usr/share/fonts',
        '/usr/local/share/fonts',
        '/home/*/.fonts',
        '/home/*/.local/share/fonts'
    ]
    
    print("\n字体目录:")
    for font_dir in font_dirs:
        if '*' in font_dir:
            continue  # 跳过通配符目录
        if os.path.exists(font_dir):
            try:
                count = sum(1 for f in Path(font_dir).rglob('*') if f.is_file() and f.suffix.lower() in ['.ttf', '.ttc', '.otf'])
                print(f"  {font_dir}: {count} 个字体文件")
            except:
                print(f"  {font_dir}: 无法访问")
        else:
            print(f"  {font_dir}: 不存在")

def generate_report():
    """生成完整的诊断报告"""
    print("字体支持和PDF生成诊断工具")
    print("版本: 1.0")
    print("日期:", subprocess.run(['date'], capture_output=True, text=True).stdout.strip())
    
    # 系统信息
    check_system_info()
    
    # 字体检查
    fonts_ok = check_chinese_fonts()
    
    # LibreOffice检查
    libreoffice_ok = check_libreoffice()
    
    # PDF转换测试
    if libreoffice_ok:
        html_pdf_ok, test_pdf = test_pdf_conversion()
        docx_pdf_ok = test_docx_conversion()
    else:
        html_pdf_ok = False
        docx_pdf_ok = False
        test_pdf = None
    
    # 总结
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)
    
    print(f"中文字体支持: {'✓' if fonts_ok else '✗'}")
    print(f"LibreOffice安装: {'✓' if libreoffice_ok else '✗'}")
    print(f"HTML转PDF: {'✓' if html_pdf_ok else '✗'}")
    print(f"DOCX转PDF: {'✓' if docx_pdf_ok else '✗' if docx_pdf_ok is not None else '未测试'}")
    
    if all([fonts_ok, libreoffice_ok, html_pdf_ok]):
        print("\n🎉 所有测试通过！系统字体和PDF转换功能正常。")
    else:
        print("\n⚠ 发现问题，请根据上述建议进行修复。")
    
    # 清理测试PDF
    if test_pdf and os.path.exists(test_pdf):
        try:
            os.unlink(test_pdf)
        except:
            pass

if __name__ == '__main__':
    try:
        generate_report()
    except KeyboardInterrupt:
        print("\n用户中断了诊断过程")
    except Exception as e:
        print(f"\n诊断过程中出现错误: {e}")
        import traceback
        traceback.print_exc() 