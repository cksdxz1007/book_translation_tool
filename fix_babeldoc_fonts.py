#!/usr/bin/env python3
"""
修复 BabelDOC 字体下载问题
"""

import subprocess
import os
import sys
from pathlib import Path

def fix_babeldoc_fonts():
    """预下载 BabelDOC 字体文件"""
    
    print("=== 修复 BabelDOC 字体问题 ===")
    
    try:
        # 使用 warmup 命令预下载所有必要资源
        print("🔧 预下载 BabelDOC 资源...")
        
        result = subprocess.run([
            "babeldoc", 
            "--warmup"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ BabelDOC 资源预下载成功")
            return True
        else:
            print(f"❌ 预下载失败: {result.stderr}")
            
            # 尝试清理缓存并重试
            print("🧹 清理 BabelDOC 缓存...")
            cache_dir = Path.home() / ".cache" / "babeldoc"
            if cache_dir.exists():
                import shutil
                shutil.rmtree(cache_dir)
                print("✅ 缓存已清理")
                
                # 重试预下载
                print("🔄 重试预下载...")
                result = subprocess.run([
                    "babeldoc", 
                    "--warmup"
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    print("✅ 重试成功")
                    return True
            
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ 预下载超时，可能网络较慢")
        return False
    except Exception as e:
        print(f"❌ 预下载出错: {e}")
        return False

def create_minimal_config():
    """创建最小化配置以减少字体需求"""
    
    config_content = """[babeldoc]
# 最小化配置
debug = false
lang-out = "zh-CN"
watermark-output-mode = "no_watermark"
skip-scanned-detection = true
enhance-compatibility = true

# 翻译服务配置
openai = true
openai-model = "deepseek-chat"
openai-base-url = "https://api.deepseek.com/v1"
"""
    
    config_path = Path("babeldoc_minimal.toml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)
    
    print(f"✅ 创建最小化配置: {config_path}")
    return config_path

if __name__ == "__main__":
    print("开始修复 BabelDOC 字体问题...")
    
    # 方法1: 预下载资源
    if fix_babeldoc_fonts():
        print("🎉 字体问题已修复")
        sys.exit(0)
    
    # 方法2: 创建最小化配置
    print("📝 创建最小化配置作为备选方案...")
    config_path = create_minimal_config()
    
    print("\n💡 建议:")
    print("1. 检查网络连接")
    print("2. 使用最小化配置: --config babeldoc_minimal.toml")
    print("3. 或者使用传统翻译引擎作为备选")
    
    sys.exit(1)
