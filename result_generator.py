import os
from fpdf import FPDF

def merge_translated_chunks(translated_chunks):
    """
    合并翻译后的文本块
    """
    return "\n\n".join(translated_chunks)

def save_result(merged_text, output_path):
    """
    保存翻译结果到文件（文本和PDF）
    """
    # 保存为文本文件
    txt_output_path = os.path.splitext(output_path)[0] + '.txt'
    with open(txt_output_path, "w", encoding="utf-8") as f:
        f.write(merged_text)
    print(f"翻译结果已保存为文本文件：{txt_output_path}")

    # 保存为PDF文件
    pdf_output_path = os.path.splitext(output_path)[0] + '.pdf'
    save_as_pdf(merged_text, pdf_output_path)
    print(f"翻译结果已保存为PDF文件：{pdf_output_path}")

    return txt_output_path, pdf_output_path

def save_as_pdf(text, output_path):
    """
    将文本保存为PDF文件
    """
    class PDF(FPDF):
        def header(self):
            self.set_font('SF Pro Display', 'B', 12)
            self.cell(0, 10, 'Translated Document', 0, 1, 'C')

        def footer(self):
            self.set_y(-15)
            self.set_font('SF Pro Display', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    
    # 添加 SF Pro Display 字体支持
    pdf.add_font('SF Pro Display', '', '/System/Library/Fonts/SF-Pro-Display-Regular.otf', uni=True)
    pdf.add_font('SF Pro Display', 'B', '/System/Library/Fonts/SF-Pro-Display-Bold.otf', uni=True)
    pdf.add_font('SF Pro Display', 'I', '/System/Library/Fonts/SF-Pro-Display-Italic.otf', uni=True)
    pdf.set_font('SF Pro Display', '', 12)

    # 分割文本为行
    lines = text.split('\n')

    # 写入每一行
    for line in lines:
        pdf.multi_cell(0, 10, line)

    pdf.output(output_path)