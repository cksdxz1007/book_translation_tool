import os
import logging
import ebooklib
from ebooklib import epub
from fpdf import FPDF
import markdown
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class FormatPreservingGenerator:
    """格式保留生成器，支持生成保持原始格式的翻译结果"""
    
    def __init__(self, parser):
        self.parser = parser
    
    def generate_epub(self, translated_chunks, output_path, original_epub_path=None):
        """生成翻译后的ePub文件，保持原始格式"""
        try:
            # 创建新的ePub书籍
            book = epub.EpubBook()
            
            # 设置元数据
            metadata = self.parser.metadata
            book.set_identifier('translated_' + str(hash(output_path)))
            book.set_title(f"{metadata.get('title', '未知标题')} (翻译版)")
            book.set_language('zh-CN')
            book.add_author(metadata.get('author', '未知作者'))
            
            # 创建简单的单章节ePub，避免复杂的结构重建问题
            chapter_html = '''<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>翻译内容</title>
    <meta charset="utf-8"/>
</head>
<body>
'''
            
            for chunk in translated_chunks:
                text = chunk['text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                if chunk['type'] == 'heading':
                    chapter_html += f'<h1>{text}</h1>\n'
                elif chunk['type'] == 'paragraph':
                    chapter_html += f'<p>{text}</p>\n'
                elif chunk['type'] == 'list_item':
                    chapter_html += f'<p>• {text}</p>\n'
                else:
                    chapter_html += f'<p>{text}</p>\n'
            
            chapter_html += '''
</body>
</html>'''
            
            # 创建章节
            chapter = epub.EpubHtml(
                title='翻译内容',
                file_name='chapter_1.xhtml',
                lang='zh-CN'
            )
            chapter.content = chapter_html
            book.add_item(chapter)
            
            # 添加导航
            book.toc = [chapter]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            
            # 设置spine
            book.spine = ['nav', chapter]
            
            # 写入文件
            epub.write_epub(output_path, book, {})
            logger.info(f"成功生成翻译后的ePub文件: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"生成ePub文件失败: {e}")
            raise
    
    def generate_markdown(self, translated_chunks, output_path):
        """生成翻译后的Markdown文件，保持原始格式"""
        try:
            rebuilt_content = self.parser.rebuild_markdown_content(translated_chunks)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(rebuilt_content)
            
            logger.info(f"成功生成翻译后的Markdown文件: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"生成Markdown文件失败: {e}")
            raise
    
    def generate_html(self, translated_chunks, output_path):
        """生成HTML文件"""
        try:
            if hasattr(self.parser, 'structure') and self.parser.structure and len(self.parser.structure) > 0:
                # 检查是否是ePub结构
                if isinstance(self.parser.structure[0], dict) and 'content' in self.parser.structure[0]:
                    # ePub内容转HTML
                    rebuilt_chapters = self.parser.rebuild_epub_content(translated_chunks)
                    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.parser.metadata.get('title', '翻译文档')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        h1, h2, h3, h4, h5, h6 {{ color: #333; }}
        p {{ margin-bottom: 1em; }}
        ul, ol {{ margin-bottom: 1em; }}
        .chapter {{ margin-bottom: 2em; border-bottom: 1px solid #eee; padding-bottom: 1em; }}
    </style>
</head>
<body>
"""
                    for i, chapter in enumerate(rebuilt_chapters):
                        html_content += f'<div class="chapter">{chapter}</div>'
                    
                    html_content += "</body></html>"
                else:
                    # Markdown内容转HTML
                    rebuilt_content = self.parser.rebuild_markdown_content(translated_chunks)
                    html_body = markdown.markdown(rebuilt_content, extensions=['fenced_code', 'tables'])
                    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>翻译文档</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        h1, h2, h3, h4, h5, h6 {{ color: #333; }}
        p {{ margin-bottom: 1em; }}
        ul, ol {{ margin-bottom: 1em; }}
        blockquote {{ border-left: 4px solid #ddd; margin: 1em 0; padding-left: 1em; }}
        code {{ background-color: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
        pre {{ background-color: #f4f4f4; padding: 1em; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
{html_body}
</body>
</html>
"""
            else:
                # 简单文本转HTML
                text_content = '\n\n'.join([chunk['text'] for chunk in translated_chunks])
                html_body = markdown.markdown(text_content)
                html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>翻译文档</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        h1, h2, h3, h4, h5, h6 {{ color: #333; }}
        p {{ margin-bottom: 1em; }}
    </style>
</head>
<body>
{html_body}
</body>
</html>
"""
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"成功生成HTML文件: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"生成HTML文件失败: {e}")
            raise

def save_format_preserving_result(parser, translated_chunks, base_output_path, file_extension):
    """保存格式保留的翻译结果"""
    generator = FormatPreservingGenerator(parser)
    results = []
    
    try:
        if file_extension == '.epub':
            # 生成ePub文件
            epub_path = base_output_path.replace('.txt', '.epub')
            generator.generate_epub(translated_chunks, epub_path)
            results.append(epub_path)
            
            # 同时生成HTML版本用于预览
            html_path = base_output_path.replace('.txt', '.html')
            generator.generate_html(translated_chunks, html_path)
            results.append(html_path)
            
        elif file_extension in ['.md', '.markdown']:
            # 生成Markdown文件
            md_path = base_output_path.replace('.txt', '.md')
            generator.generate_markdown(translated_chunks, md_path)
            results.append(md_path)
            
            # 同时生成HTML版本
            html_path = base_output_path.replace('.txt', '.html')
            generator.generate_html(translated_chunks, html_path)
            results.append(html_path)
            
        else:
            # 对于其他格式，生成Markdown
            md_path = base_output_path.replace('.txt', '.md')
            generator.generate_markdown(translated_chunks, md_path)
            results.append(md_path)
        
        # 始终生成纯文本版本作为备份
        txt_content = '\n\n'.join([chunk['text'] for chunk in translated_chunks])
        with open(base_output_path, 'w', encoding='utf-8') as f:
            f.write(txt_content)
        results.append(base_output_path)
        
        return results
        
    except Exception as e:
        logger.error(f"保存格式保留结果失败: {e}")
        # 降级到纯文本保存
        txt_content = '\n\n'.join([chunk['text'] for chunk in translated_chunks])
        with open(base_output_path, 'w', encoding='utf-8') as f:
            f.write(txt_content)
        return [base_output_path]
