#!/bin/bash

# 中文字体安装脚本
# 用于解决LibreOffice PDF生成中文字体问题

echo "开始检查和安装中文字体..."

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "请以root用户权限运行此脚本"
    exit 1
fi

# 创建字体目录
FONT_DIR="/usr/share/fonts/chinese"
mkdir -p "$FONT_DIR"

# 检查是否已安装中文字体
echo "检查现有中文字体..."
fc-list :lang=zh | head -5

# 如果没有中文字体，提供安装方法
if [ $(fc-list :lang=zh | wc -l) -eq 0 ]; then
    echo "未检测到中文字体，需要安装中文字体支持"
    echo "请按照以下步骤操作："
    echo ""
    echo "方法1：安装系统字体包"
    echo "CentOS/RHEL: yum install -y wqy-microhei-fonts wqy-zenhei-fonts"
    echo "Ubuntu/Debian: apt-get install -y fonts-wqy-microhei fonts-wqy-zenhei"
    echo ""
    echo "方法2：从Windows复制字体文件"
    echo "将Windows系统的C:\\Windows\\Fonts目录下的中文字体文件复制到 $FONT_DIR 目录"
    echo "推荐的字体文件："
    echo "- simsun.ttc (宋体)"
    echo "- simhei.ttf (黑体)"
    echo "- simkai.ttf (楷体)"
    echo "- simfang.ttf (仿宋)"
    echo "- msyh.ttc (微软雅黑)"
    echo ""
    echo "复制完字体后，运行以下命令刷新字体缓存："
    echo "fc-cache -fv"
else
    echo "检测到已安装的中文字体："
    fc-list :lang=zh | head -10
fi

# 检查并创建字体配置文件以支持字体回退
FONT_CONF_DIR="/etc/fonts/conf.d"
CONF_FILE="$FONT_CONF_DIR/65-chinese-fonts.conf"

if [ ! -f "$CONF_FILE" ]; then
    echo "创建中文字体配置文件..."
    cat > "$CONF_FILE" << 'EOF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
    <!-- 中文字体配置 -->
    
    <!-- 宋体别名配置 -->
    <alias>
        <family>宋体</family>
        <prefer>
            <family>SimSun</family>
            <family>WenQuanYi Micro Hei</family>
            <family>DejaVu Sans</family>
        </prefer>
    </alias>
    
    <!-- 黑体别名配置 -->
    <alias>
        <family>黑体</family>
        <prefer>
            <family>SimHei</family>
            <family>WenQuanYi Zen Hei</family>
            <family>DejaVu Sans</family>
        </prefer>
    </alias>
    
    <!-- 楷体别名配置 -->
    <alias>
        <family>楷体</family>
        <prefer>
            <family>KaiTi</family>
            <family>SimKai</family>
            <family>WenQuanYi Micro Hei</family>
            <family>DejaVu Sans</family>
        </prefer>
    </alias>
    
    <!-- 仿宋别名配置 -->
    <alias>
        <family>仿宋</family>
        <prefer>
            <family>FangSong</family>
            <family>SimFang</family>
            <family>WenQuanYi Micro Hei</family>
            <family>DejaVu Sans</family>
        </prefer>
    </alias>
    
    <!-- 微软雅黑别名配置 -->
    <alias>
        <family>微软雅黑</family>
        <prefer>
            <family>Microsoft YaHei</family>
            <family>WenQuanYi Micro Hei</family>
            <family>DejaVu Sans</family>
        </prefer>
    </alias>
    
    <!-- 为中文字符提供字体回退 -->
    <match target="pattern">
        <test name="lang">
            <string>zh-cn</string>
        </test>
        <edit name="family" mode="prepend">
            <string>WenQuanYi Micro Hei</string>
            <string>SimSun</string>
            <string>DejaVu Sans</string>
        </edit>
    </match>
    
    <!-- 通用中文字体回退 -->
    <match target="pattern">
        <test name="family">
            <string>serif</string>
        </test>
        <edit name="family" mode="append">
            <string>SimSun</string>
            <string>WenQuanYi Micro Hei</string>
        </edit>
    </match>
    
    <match target="pattern">
        <test name="family">
            <string>sans-serif</string>
        </test>
        <edit name="family" mode="append">
            <string>WenQuanYi Micro Hei</string>
            <string>SimHei</string>
        </edit>
    </match>
</fontconfig>
EOF
    echo "已创建中文字体配置文件: $CONF_FILE"
fi

# 刷新字体缓存
echo "刷新字体缓存..."
fc-cache -fv

# 检查LibreOffice是否已安装
if command -v soffice &> /dev/null; then
    echo "检测到LibreOffice已安装"
    
    # 测试LibreOffice转换功能
    echo "测试LibreOffice PDF转换功能..."
    
    # 创建测试文档
    TEST_DIR="/tmp/libreoffice_test"
    mkdir -p "$TEST_DIR"
    
    # 创建包含中文的测试文档
    cat > "$TEST_DIR/test.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>中文字体测试</title>
</head>
<body>
    <h1>中文字体测试</h1>
    <p>这是一个测试文档，包含中文字符：你好世界！</p>
    <p>字体测试：宋体、黑体、楷体、仿宋</p>
    <p>数字测试：1234567890</p>
    <p>英文测试：Hello World! ABC abc</p>
</body>
</html>
EOF
    
    # 测试转换
    if timeout 30 soffice --headless --convert-to pdf --outdir "$TEST_DIR" "$TEST_DIR/test.html" > /dev/null 2>&1; then
        if [ -f "$TEST_DIR/test.pdf" ]; then
            echo "✓ LibreOffice PDF转换测试成功"
            rm -f "$TEST_DIR/test.pdf"
        else
            echo "✗ LibreOffice PDF转换测试失败：未生成PDF文件"
        fi
    else
        echo "✗ LibreOffice PDF转换测试失败：转换命令执行失败"
    fi
    
    # 清理测试文件
    rm -rf "$TEST_DIR"
else
    echo "⚠ 未检测到LibreOffice，请确保已正确安装"
fi

echo ""
echo "字体安装和配置完成！"
echo "如果仍有字体问题，请："
echo "1. 重启应用程序"
echo "2. 检查模板文档中使用的字体名称"
echo "3. 确保字体文件权限正确 (chmod 644)"
echo ""
echo "可用的中文字体："
fc-list :lang=zh | head -10 