# BabelDOC 集成文档

## 概述

BabelDOC 是一个专业的 PDF 科学论文翻译和双语对比库，可以作为当前 PDF 翻译工具的高级替代方案。

## 核心特性

- **高质量翻译**: 专为科学论文设计，保持原始布局和格式
- **双语输出**: 支持生成双语对比 PDF 和单语翻译 PDF
- **多种翻译服务**: 支持 OpenAI 兼容的 LLM 服务
- **页面选择**: 可指定翻译特定页面范围
- **术语表支持**: 支持自定义术语表确保翻译一致性
- **批量处理**: 支持多文件批量翻译

## 安装

```bash
# 使用 uv 安装（推荐）
uv tool install --python 3.12 BabelDOC

# 或添加到项目依赖
uv add BabelDOC
```

## 命令行使用

### 基本用法

```bash
# 使用 OpenAI 翻译
babeldoc --openai --openai-model "gpt-4o-mini" \
  --openai-base-url "https://api.openai.com/v1" \
  --openai-api-key "your-api-key" \
  --files example.pdf

# 使用 Ollama（本地模型）
babeldoc --openai --openai-model "llama3" \
  --openai-base-url "http://localhost:11434/v1" \
  --openai-api-key "a" \
  --files example.pdf
```

### 高级选项

```bash
# 指定页面范围和语言
babeldoc --files example.pdf \
  --pages "1-5,10,15-20" \
  --lang-in "en" \
  --lang-out "zh" \
  --output "./results" \
  --openai --openai-model "gpt-4o-mini"

# 使用术语表
babeldoc --files example.pdf \
  --glossary-files "./glossary.csv" \
  --openai --openai-model "gpt-4o-mini"
```

## Python API 集成

### 基本集成示例

```python
import subprocess
import os
from pathlib import Path

def translate_with_babeldoc(
    pdf_path: str,
    output_dir: str = "./results",
    pages: str = None,
    lang_out: str = "zh",
    model: str = "gpt-4o-mini",
    api_key: str = None,
    base_url: str = "http://localhost:11434/v1"
):
    """使用 BabelDOC 翻译 PDF"""
    
    cmd = [
        "babeldoc",
        "--files", pdf_path,
        "--output", output_dir,
        "--lang-out", lang_out,
        "--openai",
        "--openai-model", model,
        "--openai-base-url", base_url,
        "--openai-api-key", api_key or "a"
    ]
    
    if pages:
        cmd.extend(["--pages", pages])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

# 使用示例
success, output = translate_with_babeldoc(
    pdf_path="./uploads/document.pdf",
    pages="1-10",
    api_key="your-openai-key"
)
```

### Flask 应用集成

```python
from flask import Flask, request, jsonify
import os
import subprocess
from pathlib import Path

def integrate_babeldoc_translation(
    file_path: str,
    pages: str = None,
    target_language: str = "zh",
    ollama_url: str = "http://localhost:11434/v1",
    model_name: str = "llama3"
):
    """集成 BabelDOC 到现有翻译流程"""
    
    output_dir = "./results"
    os.makedirs(output_dir, exist_ok=True)
    
    cmd = [
        "babeldoc",
        "--files", file_path,
        "--output", output_dir,
        "--lang-out", target_language,
        "--openai",
        "--openai-model", model_name,
        "--openai-base-url", ollama_url,
        "--openai-api-key", "a",
        "--no-watermark"  # 移除水印
    ]
    
    if pages:
        cmd.extend(["--pages", pages])
    
    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        # 实时获取进度（简化版）
        for line in process.stdout:
            if "Progress:" in line:
                # 可以在这里更新进度
                print(f"Translation progress: {line.strip()}")
        
        process.wait()
        
        if process.returncode == 0:
            # 查找生成的文件
            pdf_name = Path(file_path).stem
            translated_file = f"{output_dir}/{pdf_name}_translated.pdf"
            dual_file = f"{output_dir}/{pdf_name}_dual.pdf"
            
            return {
                "success": True,
                "translated_file": translated_file if os.path.exists(translated_file) else None,
                "dual_file": dual_file if os.path.exists(dual_file) else None
            }
        else:
            return {"success": False, "error": process.stderr.read()}
            
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## 配置文件支持

创建 `babeldoc.toml` 配置文件：

```toml
[babeldoc]
# 基本设置
debug = false
lang-in = "en"
lang-out = "zh-CN"
qps = 4
output = "./results"

# PDF 处理选项
skip-clean = false
dual-translate-first = false
use-alternating-pages-dual = false
watermark-output-mode = "no_watermark"
max-pages-per-part = 50

# 翻译服务
openai = true
openai-model = "llama3"
openai-base-url = "http://localhost:11434/v1"
openai-api-key = "a"

# 输出控制
no-dual = false
no-mono = false
min-text-length = 5
```

使用配置文件：

```bash
babeldoc --config babeldoc.toml --files example.pdf
```

## 术语表功能

创建术语表 CSV 文件 `glossary.csv`：

```csv
source,target,tgt_lng
machine learning,机器学习,zh-CN
neural network,神经网络,zh-CN
deep learning,深度学习,zh-CN
```

## 与现有项目集成建议

1. **替换现有翻译引擎**: 可以将 BabelDOC 作为高质量翻译选项
2. **保持界面兼容**: 现有的页面选择、语言设置等功能可以直接映射到 BabelDOC 参数
3. **进度监控**: 可以通过解析 BabelDOC 输出来实现进度显示
4. **错误处理**: 添加 BabelDOC 特定的错误处理逻辑

## 优势对比

| 特性 | 当前工具 | BabelDOC |
|------|----------|----------|
| 翻译质量 | 基础 | 专业级 |
| 布局保持 | 简单 | 高精度 |
| 科学公式 | 不支持 | 专门优化 |
| 双语输出 | 无 | 支持 |
| 批量处理 | 单文件 | 多文件 |
| 术语表 | 无 | 支持 |

## 注意事项

1. BabelDOC 主要针对英文到中文翻译优化
2. 需要较多系统资源进行文档布局分析
3. 首次运行会下载必要的模型文件
4. 建议在生产环境中使用配置文件管理参数
