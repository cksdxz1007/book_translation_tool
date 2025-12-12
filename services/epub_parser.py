import os
import logging
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def extract_text_from_epub(epub_path):
    """
    从ePub文件中提取文本内容，保留章节结构
    
    Args:
        epub_path: ePub文件路径
        
    Returns:
        str: 提取的文本内容，包含章节标题和内容
    """
    try:
        book = epub.read_epub(epub_path)
        text_content = []
        
        # 遍历所有文档项
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # 解析HTML内容
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                
                # 提取章节标题（如果有）
                title = soup.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if title:
                    text_content.append(f"# {title.get_text().strip()}")
                
                # 提取段落文本
                paragraphs = soup.find_all('p')
                for p in paragraphs:
                    paragraph_text = p.get_text().strip()
                    if paragraph_text:
                        text_content.append(paragraph_text)
                
                # 添加章节分隔符
                text_content.append("\n---\n")
        
        # 合并所有文本内容
        full_text = "\n".join(text_content)
        
        # 清理多余的空白和分隔符
        full_text = full_text.strip()
        full_text = full_text.replace("\n\n\n", "\n\n")
        
        logger.info(f"成功从ePub文件提取文本，长度: {len(full_text)} 字符")
        return full_text
        
    except Exception as e:
        logger.error(f"解析ePub文件失败: {e}")
        raise

def get_epub_metadata(epub_path):
    """
    获取ePub文件的元数据信息
    
    Args:
        epub_path: ePub文件路径
        
    Returns:
        dict: 包含标题、作者等元数据的字典
    """
    try:
        book = epub.read_epub(epub_path)
        metadata = {
            'title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else '未知标题',
            'author': book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else '未知作者',
            'language': book.get_metadata('DC', 'language')[0][0] if book.get_metadata('DC', 'language') else '未知语言',
            'publisher': book.get_metadata('DC', 'publisher')[0][0] if book.get_metadata('DC', 'publisher') else '未知出版社'
        }
        return metadata
    except Exception as e:
        logger.error(f"获取ePub元数据失败: {e}")
        return {'title': '未知', 'author': '未知', 'language': '未知', 'publisher': '未知'}

if __name__ == "__main__":
    # 测试代码
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        epub_file = sys.argv[1]
        if os.path.exists(epub_file):
            metadata = get_epub_metadata(epub_file)
            print(f"标题: {metadata['title']}")
            print(f"作者: {metadata['author']}")
            print(f"语言: {metadata['language']}")
            print(f"出版社: {metadata['publisher']}")
            
            text = extract_text_from_epub(epub_file)
            print(f"\n提取的文本内容（前500字符）:")
            print(text[:500] + "..." if len(text) > 500 else text)
        else:
            print(f"文件不存在: {epub_file}")
    else:
        print("请提供ePub文件路径作为参数")