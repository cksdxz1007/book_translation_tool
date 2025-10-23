#!/usr/bin/env python3
"""
启动 PDF 翻译工具应用
"""

import os
import sys
from pathlib import Path

# 确保使用项目的虚拟环境
project_root = Path(__file__).parent
venv_python = project_root / ".venv" / "bin" / "python"

if venv_python.exists() and sys.executable != str(venv_python):
    print(f"切换到虚拟环境: {venv_python}")
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

# 现在在虚拟环境中运行
from app import app

if __name__ == '__main__':
    print("=== PDF 翻译工具 ===")
    print("功能特性:")
    print("- ✨ BabelDOC 专业 PDF 翻译")
    print("- 📄 传统 PDF 翻译")
    print("- 📚 ePub/Markdown 翻译")
    print("- 🔧 多种翻译服务支持")
    print()
    print("启动应用...")
    print("访问地址: http://localhost:5001")
    print("按 Ctrl+C 停止服务")
    print()
    
    # 确保必要的目录存在
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('results', exist_ok=True)
    
    # 启动应用
    app.run(host='0.0.0.0', port=5001, debug=False)
