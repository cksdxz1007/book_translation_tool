from PyPDF2 import PdfReader

def get_pdf_page_count(pdf_path):
    """
    获取PDF文件的总页数
    """
    reader = PdfReader(pdf_path)
    return len(reader.pages)

def split_pdf(pdf_path, chunk_size=1000, start_page=None, end_page=None):
    """
    将PDF文件分割成指定大小的文本块，可以指定起始和结束页码
    """
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    if start_page is None:
        start_page = 1
    if end_page is None:
        end_page = total_pages
    
    start_page = max(1, min(start_page, total_pages))
    end_page = max(start_page, min(end_page, total_pages))
    
    chunks = []
    current_chunk = ""

    for page_num in range(start_page - 1, end_page):
        text = reader.pages[page_num].extract_text()
        words = text.split()
        
        for word in words:
            if len(current_chunk) + len(word) + 1 > chunk_size:
                chunks.append(current_chunk.strip())
                current_chunk = word + " "
            else:
                current_chunk += word + " "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks