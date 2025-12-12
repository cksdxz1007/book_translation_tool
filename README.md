# Book Translation Tool

基于Flask的文档翻译工具，支持PDF、EPUB、Markdown等多种文档格式的翻译。

## 功能特性

- **多格式支持**: PDF、EPUB、Markdown、TXT
- **多引擎支持**: BabelDOC（专业PDF翻译）、OpenAI兼容API、Ollama
- **格式保持**: 保持原文格式和结构
- **双语输出**: 支持生成双语对照文档
- **实时进度**: 翻译进度实时追踪
- **安全存储**: 配置信息加密存储

## 系统要求

- Python >= 3.10
- uv（推荐的包管理器）

## 快速开始

### 1. 安装依赖

```bash
# 使用uv安装依赖
uv sync

# 或者安装所有依赖（包括开发工具）
uv sync --all-extras
```

### 2. 启动应用

```bash
# 前台运行
./start_uv.sh

# 后台运行
./start_uv_bg.sh
```

### 3. 访问应用

- 主应用: http://localhost:5001
- 管理界面: http://localhost:5001/admin

## 配置说明

### 翻译服务配置

1. 访问管理界面 `/admin`
2. 添加翻译服务（支持OpenAI兼容API和Ollama）
3. 配置API密钥和服务URL
4. 测试连接并设为默认服务

### 环境变量

复制 `.env.example` 到 `.env` 并配置：

```bash
# Flask配置
FLASK_ENV=development
SECRET_KEY=your-secret-key

# 翻译服务配置
DEFAULT_TRANSLATION_SERVICE=openai
```

## 目录结构

```
book-translation-tool/
├── app.py                 # 主应用
├── admin_routes.py        # 管理界面路由
├── translator.py          # 翻译服务抽象
├── pdf_translator_babeldoc.py  # BabelDOC引擎
├── pyproject.toml         # 项目配置
├── start_uv.sh           # 前台启动脚本
├── start_uv_bg.sh        # 后台启动脚本
├── config/               # 配置管理
│   ├── manager.py
│   └── app_config.py
├── core/                 # 核心功能模块
│   ├── text_utils.py
│   ├── semantic_matcher.py
│   └── bilingual.py
├── routes/               # 路由模块
│   ├── api_routes.py
│   ├── pdf_routes.py
│   ├── markdown_routes.py
│   └── epub_routes.py
├── templates/            # HTML模板
├── static/               # 静态资源
├── data/                 # 数据目录
│   ├── config.db        # 配置数据库
│   └── keys/            # 加密密钥
├── uploads/              # 上传文件
└── results/              # 输出结果
```

## 翻译引擎

### 1. BabelDOC引擎
- 专业PDF翻译
- 保持布局和格式
- 支持复杂文档结构

### 2. 格式保持引擎
- EPUB/Markdown专用
- 保持文档结构和元数据
- 适合文学作品翻译

### 3. 传统文本引擎
- 通用文本翻译
- 简单快速
- 适合纯文本文件

## 开发指南

### 添加新的翻译服务

1. 在 `translator.py` 中实现新的服务类
2. 更新配置管理器
3. 在管理界面添加工具

### 自定义模板

修改 `templates/` 目录下的HTML文件。

### 样式定制

静态文件位于 `static/` 目录，使用Tailwind CSS。

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 更新日志

### v2.0.0
- 重构项目架构，使用Blueprint
- 增强配置管理系统
- 添加实时进度追踪
- 优化文件处理流程
