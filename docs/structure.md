# PDF证书管理系统 - 优化后的目录结构

## 项目结构

```
pdf/
├── app/                          # 应用主包
│   ├── __init__.py              # 应用工厂函数
│   ├── config.py                # 配置文件
│   ├── auth.py                  # 认证模块
│   ├── models/                  # 数据模型包
│   │   ├── __init__.py         # 模型初始化
│   │   ├── admin.py            # 管理员模型
│   │   ├── activity.py         # 活动模型
│   │   ├── certificate.py      # 证书模型
│   │   └── carousel_image.py   # 轮播图模型
│   ├── routes/                  # 路由包
│   │   ├── __init__.py         # 路由初始化
│   │   ├── main.py             # 主要前台路由
│   │   └── admin.py            # 管理后台路由
│   └── services/                # 服务层包
│       ├── __init__.py         # 服务初始化
│       ├── certificate_generator.py  # 证书生成服务
│       └── certificate_service.py    # 证书管理服务
├── templates/                   # 模板文件
│   ├── base.html               # 基础模板
│   ├── index.html              # 首页模板
│   ├── activity_detail.html    # 活动详情模板
│   ├── unit_certificates.html  # 单位证书模板
│   ├── help.html               # 帮助页面模板
│   ├── search_results.html     # 搜索结果模板
│   └── admin/                  # 管理后台模板
│       └── ...
├── static/                      # 静态文件
│   ├── fonts/                  # 字体文件
│   └── ...
├── uploads/                     # 上传文件目录
│   ├── templates/              # 证书模板
│   ├── certificates/           # 生成的证书
│   ├── images/                 # 活动图片
│   └── carousel/               # 轮播图
├── migrations/                  # 数据库迁移文件
├── run.py                      # 应用入口文件
├── requirements.txt            # 依赖包列表
└── README.md                   # 项目说明
```

## 主要改进

### 1. 模块化设计
- **models包**: 将所有数据模型分离到独立文件中，便于维护
- **routes包**: 按功能分离路由，前台和后台路由分开
- **services包**: 业务逻辑层，处理复杂的业务操作

### 2. 配置管理
- **config.py**: 统一配置管理，支持多环境配置
- **应用工厂模式**: 便于测试和部署

### 3. 清晰的职责分离
- **路由层**: 只处理HTTP请求和响应
- **服务层**: 处理业务逻辑
- **模型层**: 数据访问和操作

### 4. 更好的可维护性
- 每个模块职责单一
- 代码组织更清晰
- 便于团队协作开发

## 使用方法

### 开发环境启动
```bash
python run.py
```

### 生产环境启动
```bash
export FLASK_CONFIG=production
python run.py
```

### 测试环境
```bash
export FLASK_CONFIG=testing
python run.py
```

## 配置说明

通过环境变量 `FLASK_CONFIG` 可以切换不同的配置：
- `development`: 开发环境（默认）
- `production`: 生产环境
- `testing`: 测试环境

每个环境可以有不同的数据库连接、调试模式等配置。 