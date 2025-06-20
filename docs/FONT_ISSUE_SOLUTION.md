# PDF生成字体问题解决方案

## 问题描述

在使用LibreOffice的`soffice`命令将DOCX模板转换为PDF时，中文字体可能会出现以下问题：
1. 中文字符显示为方块或问号
2. 生成的PDF字体与模板字体不一致
3. 字体回退机制不工作，导致中文显示异常

## 根本原因

1. **系统缺少中文字体**：Linux系统默认可能不包含中文字体
2. **字体映射配置不当**：系统无法正确映射中文字体名称
3. **LibreOffice字体嵌入设置**：转换时未正确嵌入字体
4. **环境变量设置**：缺少UTF-8编码支持

## 解决方案

### 1. 运行字体安装脚本

```bash
sudo ./install_fonts.sh
```

这个脚本会：
- 检查现有中文字体
- 创建字体配置文件
- 设置字体回退机制
- 测试LibreOffice转换功能

### 2. 手动安装中文字体

#### 方法1：使用包管理器安装

**CentOS/RHEL:**
```bash
sudo yum install -y wqy-microhei-fonts wqy-zenhei-fonts
# 或者
sudo yum install -y google-noto-sans-cjk-ttc-fonts
```

**Ubuntu/Debian:**
```bash
sudo apt-get install -y fonts-wqy-microhei fonts-wqy-zenhei
# 或者
sudo apt-get install -y fonts-noto-cjk
```

#### 方法2：从Windows复制字体

1. 从Windows系统的`C:\Windows\Fonts`目录复制以下字体文件：
   - `simsun.ttc` (宋体)
   - `simhei.ttf` (黑体)  
   - `simkai.ttf` (楷体)
   - `simfang.ttf` (仿宋)
   - `msyh.ttc` (微软雅黑)

2. 将字体文件复制到Linux系统的`/usr/share/fonts/chinese/`目录

3. 设置权限并刷新字体缓存：
```bash
sudo chmod 644 /usr/share/fonts/chinese/*
sudo fc-cache -fv
```

### 3. 验证字体安装

检查中文字体是否正确安装：
```bash
fc-list :lang=zh
```

### 4. 代码层面的改进

我已经在`certificate_generator.py`中进行了以下改进：

1. **添加环境变量支持**：
```python
env = os.environ.copy()
env['LC_ALL'] = 'C.UTF-8'
env['LANG'] = 'C.UTF-8'
```

2. **改进PDF转换参数**：
```python
'--convert-to', 'pdf:writer_pdf_Export:{"EmbedStandardFonts":true,"UseTaggedPDF":false}'
```

3. **添加回退转换机制**：如果高级转换失败，会尝试简单模式转换

4. **增加超时时间**：从30秒增加到60秒

5. **改进错误处理**：更好的UTF-8错误解码

### 5. 模板制作建议

在制作DOCX模板时：

1. **使用常见中文字体**：
   - 宋体 (SimSun)
   - 微软雅黑 (Microsoft YaHei)
   - 黑体 (SimHei)

2. **避免使用特殊字体**：
   - 避免使用系统可能没有的特殊字体
   - 如果必须使用特殊字体，确保在Word中嵌入字体

3. **测试字体兼容性**：
   - 在Linux环境下测试模板
   - 确保所有中文字符都能正确显示

## 故障排除

### 问题1：仍然显示方块字符

**解决方案：**
1. 检查字体是否正确安装：`fc-list :lang=zh`
2. 重启应用程序
3. 检查模板中使用的字体名称
4. 尝试更换模板字体为系统已安装的字体

### 问题2：PDF生成失败

**解决方案：**
1. 检查LibreOffice是否正确安装：`soffice --version`
2. 检查磁盘空间是否充足
3. 检查临时目录权限
4. 查看错误日志详细信息

### 问题3：字体样式不一致

**解决方案：**
1. 确保模板字体在系统中有对应的字体文件
2. 检查字体配置文件是否正确
3. 考虑在Word模板中嵌入字体

## 测试步骤

1. **创建测试文档**：
```bash
echo '<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body><h1>中文测试</h1><p>这是中文字体测试：你好世界</p></body></html>' > test.html
```

2. **测试转换**：
```bash
soffice --headless --convert-to pdf test.html
```

3. **检查结果**：
查看生成的`test.pdf`文件中的中文是否正确显示

## 相关资源

- [LibreOffice字体文档](https://help.libreoffice.org/7.0/en-US/text/shared/guide/fontwork.html)
- [Fontconfig配置指南](https://www.freedesktop.org/software/fontconfig/fontconfig-user.html)
- [文泉驿字体项目](http://wenq.org/)
- [Google Noto字体](https://www.google.com/get/noto/)

## 联系支持

如果仍有问题，请提供：
1. 操作系统版本
2. LibreOffice版本
3. 字体安装情况 (`fc-list :lang=zh`)
4. 具体错误信息
5. 测试模板文件 