#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Favicon 设置脚本

帮助快速为网站设置 favicon（网站图标）

使用方法：
1. 运行此脚本
2. 按照提示输入图标文本或提供图片路径
3. 脚本将自动生成多种尺寸的 favicon 文件
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont
import io

def create_favicon_from_text(text="翻译", output_dir="static/favicon", size=32):
    """从文本创建简单的 favicon"""
    # 创建图像
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 绘制圆形背景
    margin = 2
    draw.ellipse([margin, margin, size-margin, size-margin],
                fill=(66, 133, 244, 255),  # 蓝色背景
                outline=(255, 255, 255, 255),
                width=2)

    # 尝试使用默认字体
    try:
        # 尝试使用系统字体
        font_size = size // 2
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except:
            # 使用默认字体
            font = ImageFont.load_default()

    # 计算文本位置
    if text:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - 2

        # 绘制文本
        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    return img

def generate_favicons(text="翻译"):
    """生成多种尺寸的 favicon"""
    output_dir = "static/favicon"
    os.makedirs(output_dir, exist_ok=True)

    # 生成多种尺寸
    sizes = [16, 32, 48, 180, 192, 512]

    print(f"🎨 正在生成 favicon 图标...")
    print(f"   图标文本: {text}")
    print(f"   输出目录: {output_dir}")
    print()

    for size in sizes:
        img = create_favicon_from_text(text, output_dir, size)

        # 保存为 PNG
        png_path = f"{output_dir}/favicon-{size}x{size}.png"
        img.save(png_path, "PNG")
        print(f"✅ 生成: {png_path} ({size}x{size})")

    # 生成 Apple Touch Icon
    img_apple = create_favicon_from_text(text, output_dir, 180)
    img_apple.save(f"{output_dir}/apple-touch-icon.png", "PNG")
    print(f"✅ 生成: {output_dir}/apple-touch-icon.png (180x180)")

    # 生成 Android Chrome 图标
    img_android = create_favicon_from_text(text, output_dir, 192)
    img_android.save(f"{output_dir}/android-chrome-192x192.png", "PNG")
    print(f"✅ 生成: {output_dir}/android-chrome-192x192.png (192x192)")

    img_android512 = create_favicon_from_text(text, output_dir, 512)
    img_android512.save(f"{output_dir}/android-chrome-512x512.png", "PNG")
    print(f"✅ 生成: {output_dir}/android-chrome-512x512.png (512x512)")

    print()
    print("✨ Favicon 生成完成！")
    print()
    print("📝 接下来需要：")
    print("   1. 将生成的 PNG 文件转换为 ICO 格式（可选）")
    print("   2. 确保 HTML 模板中已添加 favicon 引用")
    print()
    print("💡 提示：")
    print("   - PNG 转 ICO 可以使用在线工具或 ImageMagick")
    print("   - 命令行转换：convert favicon-32x32.png favicon.ico")
    print("   - 在线工具：https://favicon.io/")

def main():
    print("=" * 60)
    print("🚀 Favicon 设置脚本")
    print("=" * 60)
    print()

    # 获取用户输入
    text = input("请输入图标文本（直接回车使用'翻译'）: ").strip()
    if not text:
        text = "翻译"

    print()
    confirm = input(f"确认生成图标文本为 '{text}'？(Y/n): ").strip().lower()
    if confirm == 'n':
        print("❌ 已取消")
        return

    print()

    try:
        generate_favicons(text)
        print()
        print("🎉 设置完成！现在您的网站将有漂亮的 favicon 了！")
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        print()
        print("💡 替代方案：")
        print("   1. 访问 https://favicon.io/favicon-generator/")
        print("   2. 输入 '翻译工具' 或 'Translation'")
        print("   3. 下载并放置到 static/favicon/ 目录")

if __name__ == '__main__':
    # 检查是否安装了 Pillow
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("❌ 错误：需要安装 Pillow 库")
        print()
        print("请运行以下命令安装：")
        print("  pip install Pillow")
        print()
        print("或使用 uv：")
        print("  uv add Pillow")
        sys.exit(1)

    main()
