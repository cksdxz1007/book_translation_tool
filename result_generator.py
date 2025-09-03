import os
from fpdf import FPDF
import markdown
from bs4 import BeautifulSoup
import re # Import re for text cleaning

# macOS System Font we will try to use for broad Unicode support
# Arial Unicode MS is a good candidate if available.
MACOS_UNICODE_FONT_NAME = "ArialUnicodeMS"
MACOS_UNICODE_FONT_PATH = "/Library/Fonts/Arial Unicode.ttf" # Common path if installed

# Fallback font if the macOS Unicode font cannot be loaded
FALLBACK_FONT = "Helvetica"

def merge_translated_chunks(translated_chunks):
    """
    合并翻译后的文本块
    """
    return "\n\n".join(translated_chunks)

def save_result(merged_text, output_path):
    """
    保存翻译结果到文件（文本和PDF）
    """

    # --- Final Markdown Cleanup --- 
    # 1. Remove lines that only contain specific unwanted characters/patterns (e.g., from model noise)
    #    Regex: Matches lines that, after stripping leading/trailing whitespace, consist only of
    #    a pipe, a colon (English or Chinese), or combinations like | : or : |
    #    These lines are replaced with an empty string to effectively remove them.
    def replace_junk_lines(match):
        line_content = match.group(1).strip()
        # Check if the stripped line content is one of the junk patterns
        if line_content in ['|', ':', '：', '| :', ': |', '|:', ':|']:
            return '' # Replace with empty string to remove the line
        return match.group(0) # Otherwise, keep the original line

    # Iteratively apply for lines that might become junk after previous junk is removed
    # However, a simpler line-by-line approach might be more robust here.
    # Let's refine the regex to be applied once globally and carefully.
    # This regex looks for lines that *only* contain these characters, possibly with whitespace.
    cleaned_md = re.sub(r'^\s*([\|:\uff1a\s]+)\s*$', lambda m: '' if m.group(1).strip() in ['|', ':', '：', '| :', ': |', '|:', ':|', '| '] else m.group(0), merged_text, flags=re.MULTILINE)
    
    # A simpler approach for removing specific junk lines more directly:
    lines = cleaned_md.split('\n')
    cleaned_lines = []
    junk_patterns = ['|', ':', '：', '| :', ': |', '|:', ':|', '| '] # Add more specific junk-only lines here
    for line in lines:
        stripped_line = line.strip()
        if stripped_line in junk_patterns:
            # If the line *only* consists of a junk pattern, skip it (effectively removing it)
            # Or replace with a single space if we want to be sure it doesn't merge paragraphs,
            # but typically these junk lines appear on their own.
            continue 
        cleaned_lines.append(line)
    cleaned_md = '\n'.join(cleaned_lines)

    # 2. Normalize multiple blank lines down to a single blank line
    #    This ensures no more than one blank line between paragraphs/blocks.
    cleaned_md = re.sub(r'\n{3,}', '\n\n', cleaned_md)

    # 3. Remove any leading/trailing whitespace from the entire document again, just in case
    cleaned_md = cleaned_md.strip()
    # --- End Final Markdown Cleanup ---

    # Convert Markdown to HTML first. 
    # nl2br extension converts newlines to <br>, which write_html supports.
    # fenced_code and tables are common useful extensions.
    html_content = markdown.markdown(cleaned_md, extensions=['fenced_code', 'tables', 'nl2br'])

    # Save as text file (stripped of all HTML/Markdown)
    txt_output_path = os.path.splitext(output_path)[0] + '.txt'
    # Use BeautifulSoup to get plain text from HTML
    soup = BeautifulSoup(html_content, "html.parser")
    plain_text_for_txt = soup.get_text(separator="\n") # separator helps maintain paragraph breaks
    with open(txt_output_path, "w", encoding="utf-8") as f:
        f.write(plain_text_for_txt)
    print(f"翻译结果已保存为文本文件：{txt_output_path}")

    # Save as PDF file (passing HTML to be rendered by fpdf2.write_html)
    pdf_output_path = os.path.splitext(output_path)[0] + '.pdf'
    save_as_pdf(html_content, pdf_output_path) # Pass HTML content now
    print(f"翻译结果已保存为PDF文件：{pdf_output_path}")

    return txt_output_path, pdf_output_path

def save_as_pdf(html_content, filename):
    """
    将HTML内容保存为PDF文件，尝试渲染基本HTML样式
    """
    class PDFWithHeader(FPDF):
        current_font_name = FALLBACK_FONT # Default to fallback
        font_styles_loaded = {'R': False, 'B': False, 'I': False}

        def add_system_unicode_font(self):
            """Attempts to load Arial Unicode MS from the system. Sets self.current_font_name."""
            try:
                if os.path.exists(MACOS_UNICODE_FONT_PATH):
                    self.add_font(MACOS_UNICODE_FONT_NAME, "", MACOS_UNICODE_FONT_PATH, uni=True)
                    self.font_styles_loaded['R'] = True
                    # Register the same font file for Bold and Italic to avoid undefined font errors
                    # This won't make it actually bold/italic if the font file doesn't support it inherently
                    # or if FPDF doesn't synthesize it, but it prevents errors with write_html.
                    self.add_font(MACOS_UNICODE_FONT_NAME, "B", MACOS_UNICODE_FONT_PATH, uni=True)
                    self.font_styles_loaded['B'] = True 
                    self.add_font(MACOS_UNICODE_FONT_NAME, "I", MACOS_UNICODE_FONT_PATH, uni=True)
                    self.font_styles_loaded['I'] = True

                    self.current_font_name = MACOS_UNICODE_FONT_NAME
                    print(f"Successfully loaded system Unicode font: {MACOS_UNICODE_FONT_NAME} from {MACOS_UNICODE_FONT_PATH} (registered for R, B, I styles).")
                    return True
                else:
                    print(f"警告: 系统字体文件未找到 '{MACOS_UNICODE_FONT_PATH}'.")
                    self.current_font_name = FALLBACK_FONT
                    # For fallback, FPDF can synthesize B/I for Helvetica
                    self.font_styles_loaded['R'] = True 
                    self.font_styles_loaded['B'] = True 
                    self.font_styles_loaded['I'] = True 
                    return False
            except RuntimeError as e:
                print(f"警告: 无法加载系统字体 '{MACOS_UNICODE_FONT_NAME}'. 错误: {e}. 将回退到 '{FALLBACK_FONT}'. 特殊字符可能无法在 PDF 中正确显示。")
                self.current_font_name = FALLBACK_FONT
                # For fallback, FPDF can synthesize B/I for Helvetica
                self.font_styles_loaded['R'] = True 
                self.font_styles_loaded['B'] = True 
                self.font_styles_loaded['I'] = True 
                return False

        def header(self):
            # Use bold style if available for the current font, else regular
            style = 'B' if self.font_styles_loaded['B'] else '' 
            self.set_font(self.current_font_name, style, 12) 
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            # Use italic style if available for the current font, else regular
            style = 'I' if self.font_styles_loaded['I'] else ''
            self.set_font(self.current_font_name, style, 8)
            self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

    pdf = PDFWithHeader()
    font_loaded_successfully = pdf.add_system_unicode_font()
    
    pdf.set_font(pdf.current_font_name, '', 12) # Set body font (regular style)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    try:
        pdf.write_html(html_content)
    except Exception as e:
        print(f"Error during pdf.write_html: {e}")
        if not font_loaded_successfully:
            print("This might be due to font issues with special characters and the fallback font (Helvetica).")
        else:
            print(f"This might be due to unsupported HTML tags or character issues even with {pdf.current_font_name}.")
        
        # Fallback to writing plain text if HTML rendering fails
        print("Attempting to write plain text to PDF as a fallback...")
        pdf.add_page() 
        pdf.set_font(pdf.current_font_name, '', 10) 
        soup = BeautifulSoup(html_content, "html.parser")
        plain_text = soup.get_text(separator="\n")
        try:
            if pdf.current_font_name == FALLBACK_FONT: # Only try latin-1 for Helvetica
                 plain_text = plain_text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 5, plain_text)
            print("Warning: HTML rendering failed, wrote plain text to PDF instead.")
        except Exception as plain_e:
            print(f"Error writing plain text fallback to PDF: {plain_e}")
            pdf.multi_cell(0, 5, "Error: Could not render content due to character encoding or other issues.")

    pdf.output(filename)