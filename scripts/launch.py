#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask翻译应用启动器

提供应用启动和管理的便捷接口
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

load_dotenv()

def main():
    """主启动函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == 'start':
            """启动应用"""
            print("🚀 启动Flask翻译应用...")
            os.system('./start_uv.sh')
        elif command == 'start-bg':
            """后台启动应用"""
            print("🚀 后台启动Flask翻译应用...")
            os.system('./start_uv_bg.sh')
        elif command == 'test':
            """运行测试"""
            print("🧪 运行测试...")
            os.system('uv run pytest')
        elif command == 'deps':
            """安装依赖"""
            print("📦 安装项目依赖...")
            os.system('uv sync')
        elif command == 'clean':
            """清理缓存"""
            print("🧹 清理缓存...")
            os.system('find . -type d -name "__pycache__" -exec rm -rf {} +')
            os.system('find . -type f -name "*.pyc" -delete')
            print("✅ 清理完成")
        else:
            print(f"❌ 未知命令: {command}")
            print("可用命令: start, start-bg, test, deps, clean")
    else:
        # 默认启动
        print("🚀 启动Flask翻译应用...")
        os.system('./start_uv.sh')

if __name__ == '__main__':
    main()
