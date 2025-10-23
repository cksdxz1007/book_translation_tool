#!/usr/bin/env python3
"""
创建测试PDF文件用于性能测试
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pathlib import Path

def create_test_pdf(filename, num_pages=5):
    """创建测试PDF文件"""
    c = canvas.Canvas(filename, pagesize=letter)

    for page_num in range(1, num_pages + 1):
        # 添加标题
        c.drawString(100, 750, f"BabelDOC Performance Test Document")
        c.drawString(100, 730, f"Page {page_num} of {num_pages}")

        # 添加一些测试文本
        c.drawString(100, 700, "This is a test document for BabelDOC performance monitoring.")
        c.drawString(100, 680, "The quick brown fox jumps over the lazy dog.")
        c.drawString(100, 660, "BabelDOC version 0.5.16 provides improved performance.")
        c.drawString(100, 640, "Automatic OCR workaround for scanned documents.")
        c.drawString(100, 620, "Enhanced pool management with 8 worker threads.")

        # 添加更多文本内容
        for i in range(10):
            y_pos = 600 - (i * 20)
            if y_pos > 50:  # 确保不超出页面
                c.drawString(100, y_pos, f"Test line {i+1}: Performance optimization test.")

        # 添加新页面
        if page_num < num_pages:
            c.showPage()

    c.save()
    print(f"Created test PDF: {filename} ({num_pages} pages)")

def main():
    """主函数"""
    test_dir = Path("test_documents")
    test_dir.mkdir(exist_ok=True)

    # 创建不同大小的测试文件
    create_test_pdf(str(test_dir / "small.pdf"), num_pages=3)
    create_test_pdf(str(test_dir / "medium.pdf"), num_pages=10)
    create_test_pdf(str(test_dir / "large.pdf"), num_pages=20)

    print("Test PDF files created successfully!")

if __name__ == "__main__":
    main()