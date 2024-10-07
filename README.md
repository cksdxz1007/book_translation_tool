# PDF 翻译工具

这是一个基于 Flask 的 Web 应用程序，用于翻译 PDF 文档。它使用 Ollama 作为翻译服务，支持自定义 Ollama 服务地址和模型名称。

## 功能特点

- 上传 PDF 文件
- 选择要翻译的页面范围
- 自定义目标语言
- 配置 Ollama 服务地址和模型名称
- 自定义 Ollama 模型选择
- 实时显示翻译进度
- 下载翻译结果

## 安装要求

- Python 3.12+
- Flask
- PyPDF2
- requests
- fpdf2

## 安装

1. 克隆仓库：
```
git clone https://github.com/cksdxz1007/book_translation_tool.git
```

2. 进入项目目录：
```
cd pdf-translation-tool
```

3. 
   方式一：Docker 部署
   ```
   docker-compose up --build
   docker-compose down
   ```
   方式二：直接部署（建议创建虚拟环境）
   ```
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   flask run
   ```

4. 访问应用：
   ```
   http://localhost:5000
   ```


## 注意事项

- 确保 Ollama 服务正在运行，并且已安装所需的模型。
- 可以在 Web 界面上自定义 Ollama 服务地址和模型名称。
- 上传和结果文件存储在 `uploads` 和 `results` 目录中。
- 在生产环境中部署时，请确保适当配置安全措施。

## 贡献

欢迎提交问题和拉取请求。对于重大更改，请先开issue讨论您想要更改的内容。

## 许可证

[MIT](https://choosealicense.com/licenses/mit/)