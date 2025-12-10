#!/usr/bin/env python3
"""
验证模板文件中下载链接生成的代码
检查实际运行时使用的模板内容
"""

import os
import re

def check_download_link_code(template_path, template_name):
    """检查模板文件中的下载链接生成代码"""
    print(f"\n{'='*60}")
    print(f"检查模板: {template_name}")
    print(f"{'='*60}")

    if not os.path.exists(template_path):
        print(f"❌ 文件不存在: {template_path}")
        return False

    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找所有与下载链接相关的代码
    patterns = [
        (r"\$\('#download-link'\)\.attr\(['\"]href['\"],\s*['\"]([^'\"]+)['\"]", "直接设置href属性"),
        (r"var downloadUrl\s*=\s*['\"]([^'\"]+)['\"]", "下载URL变量"),
        (r"\.attr\(['\"]href['\"],\s*(.+)\)", "动态设置href"),
    ]

    found_issues = []
    found_correct = []

    for pattern, description in patterns:
        matches = re.finditer(pattern, content, re.MULTILINE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            full_match = match.group(0)
            groups = match.groups()

            print(f"\n[Line {line_num}] {description}")
            print(f"  代码: {full_match[:100]}...")

            if groups:
                first_group = groups[0]
                if '/api/download/' in str(first_group):
                    found_correct.append((line_num, full_match))
                    print(f"  ✅ 包含正确的 /api/download/ 前缀")
                elif '/download/' in str(first_group) and '/api/download/' not in str(first_group):
                    found_issues.append((line_num, full_match))
                    print(f"  ❌ 缺少 /api 前缀!")
                else:
                    print(f"  ℹ️  其他格式: {first_group}")

    # 总结
    print(f"\n{'-'*60}")
    print(f"检查结果:")
    if found_issues:
        print(f"❌ 发现 {len(found_issues)} 个问题代码:")
        for line, code in found_issues:
            print(f"  Line {line}: {code[:80]}...")
    else:
        print(f"✅ 未发现缺少 /api 前缀的代码")

    if found_correct:
        print(f"\n✅ 发现 {len(found_correct)} 个正确代码:")
        for line, code in found_correct:
            print(f"  Line {line}: 正确使用 /api/download/")

    return len(found_issues) == 0

def main():
    print("="*60)
    print("模板下载链接代码验证工具")
    print("="*60)

    templates = [
        ('templates/index.html', '主页模板'),
        ('templates/markdown_translate.html', 'Markdown翻译模板'),
        ('templates/epub_translate.html', 'EPUB翻译模板'),
    ]

    all_correct = True
    for template_path, template_name in templates:
        if not check_download_link_code(template_path, template_name):
            all_correct = False

    print(f"\n{'='*60}")
    print("最终结论:")
    print(f"{'='*60}")
    if all_correct:
        print("✅ 所有模板文件都正确使用了 /api/download/ 前缀")
        print("\n如果用户仍然收到缺少 /api 前缀的链接，可能原因:")
        print("1. 浏览器缓存了旧版本的页面")
        print("2. 用户访问的是不同的页面或路径")
        print("3. 存在JavaScript错误阻止正确设置链接")
        print("4. 用户手动修改了URL")
    else:
        print("❌ 发现模板文件中的问题代码，需要修复!")

if __name__ == '__main__':
    main()
