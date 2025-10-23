# PDF 翻译工具

这是一个基于 Flask 的 Web 应用程序，用于翻译 PDF 文档。支持多种翻译引擎，包括专业的 BabelDOC 和传统翻译方法。

## 功能特点

### 🚀 双翻译引擎支持
- **BabelDOC 引擎**: 专业 PDF 翻译，保持原始布局和格式
- **传统引擎**: 基于文本提取的翻译方法

### 📄 文件格式支持
- PDF 文件翻译
- ePub 电子书翻译
- Markdown 文档翻译
- 文本文件翻译

### 🔧 翻译服务
- 支持 Ollama 本地模型
- 支持 OpenAI 兼容 API
- 自定义翻译服务配置
- 多种模型选择

### ✨ 高级功能
- 页面范围选择
- 实时翻译进度显示
- 双语对比输出（BabelDOC）
- 术语表支持（BabelDOC）
- 批量文件处理
- **API服务预测试**：翻译前自动验证服务连接
- **健壮错误处理**：友好的错误提示和快速失败机制

## BabelDOC 优势

相比传统翻译方法，BabelDOC 提供：

- **专业级翻译质量**: 专为科学论文和技术文档设计
- **完美布局保持**: 保持原始 PDF 的格式、字体和结构
- **科学公式处理**: 专门优化数学公式和符号翻译
- **双语输出**: 可生成原文和译文对比的 PDF
- **高精度识别**: 先进的文档布局分析技术

## 安装要求

- Python 3.12+
- Flask
- BabelDOC 0.5.16+
- PyPDF2
- requests
- fpdf2
- **必须使用 conda 虚拟环境 `books_venv`**

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/cksdxz1007/book_translation_tool.git
```

2. 进入项目目录：
```bash
cd book_translation_tool
```

3. 配置环境变量

   ```bash
   # 复制环境变量模板
   cp .env.example .env

   # 编辑 .env 文件，填写您的 API 密钥
   # DEEPSEEK_API_KEY=您的DeepSeek API密钥
   # ADMIN_ACCESS_KEY=使用 openssl rand -base64 32 生成的管理员密钥
   ```

4. 部署应用

   **必须使用 conda 虚拟环境 `books_venv`**

   ```bash
   # 激活 conda 环境
   conda activate books_venv

   # 验证环境是否正确
   which python
   # 应该显示: /opt/homebrew/Caskroom/miniconda/base/envs/books_venv/bin/python

   # 安装依赖
   pip install -r requirements.txt

   # 安装 BabelDOC 0.5.16+
   pip install BabelDOC==0.5.16

   # 运行应用
   python start_app.py
   ```

5. 访问应用：
   ```
   http://localhost:5001
   ```

## 使用说明

### PDF 翻译

1. **上传 PDF 文件**: 选择要翻译的 PDF 文档
2. **选择翻译引擎**: 
   - BabelDOC: 专业 PDF 翻译，保持原始格式
   - 传统翻译: 基于文本提取的翻译
3. **设置参数**:
   - 页面范围（可选）
   - 目标语言
   - 翻译服务
4. **开始翻译**: 实时查看翻译进度
5. **下载结果**: 翻译完成后下载文件

### 翻译服务配置

通过 Web 管理界面配置翻译服务：

1. 访问管理界面：`http://localhost:5001/admin`
2. 添加/编辑翻译服务
3. 测试服务连接
4. 设置默认服务

支持的服务类型：
- `openai` - OpenAI兼容API (DeepSeek, SiliconFlow等)
- `ollama` - 本地Ollama实例
- `third_party_completion` - 第三方完成API

所有敏感数据使用AES-256加密存储在SQLite数据库中。

### BabelDOC 配置

可以通过 `babeldoc.toml` 文件自定义 BabelDOC 设置：

```toml
[babeldoc]
lang-out = "zh-CN"
watermark-output-mode = "no_watermark"
openai-model = "llama3"
openai-base-url = "http://localhost:11434/v1"
```

## 测试

运行集成测试：

```bash
python test_babeldoc_integration.py
```

## 注意事项

### BabelDOC 使用
- 确保翻译服务正在运行且配置正确
- BabelDOC 主要针对英文到中文翻译优化
- 首次运行会下载必要的模型文件
- 需要较多系统资源进行文档布局分析
- **API服务预测试**：翻译前自动验证服务连接，避免无效翻译
- **健壮错误处理**：友好的错误提示和快速失败机制

### 传统翻译
- 适用于简单的文本翻译需求
- 输出格式为 Markdown
- 处理速度较快，资源占用较少

### 生产环境
- 在生产环境中部署时，请确保适当配置安全措施
- 上传和结果文件存储在 `uploads` 和 `results` 目录中
- 建议定期清理临时文件

## 贡献

欢迎提交问题和拉取请求。对于重大更改，请先开issue讨论您想要更改的内容。

## 许可证

[MIT](https://choosealicense.com/licenses/mit/)