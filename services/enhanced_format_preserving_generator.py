"""
增强的格式保留生成器
集成新的解析器和格式提示，提供更好的格式保持功能
"""
import os
import logging
import ebooklib
from ebooklib import epub
import markdown
from bs4 import BeautifulSoup
import cssutils
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class EnhancedFormatPreservingGenerator:
    """增强的格式保留生成器，支持完整的格式保持功能"""

    def __init__(self, parser, format_hint_generator=None):
        self.parser = parser
        self.format_hint_generator = format_hint_generator
        self.css_styles = {}
        self.media_resources = {}

    def generate_epub(self, translated_nodes: List[Dict[str, Any]], output_path: str, original_epub_path: str = None) -> str:
        """生成翻译后的ePub文件，保持完整的原始格式"""
        try:
            logger.info(f"开始生成增强的ePub文件: {output_path}")

            # 创建新的ePub书籍
            book = epub.EpubBook()

            # 设置元数据
            if hasattr(self.parser, 'metadata') and self.parser.metadata:
                metadata = self.parser.metadata
                book.set_identifier(metadata.get('identifier', f'translated_{hash(output_path)}'))
                book.set_title(f"{metadata.get('title', '未知标题')} (翻译版)")
                book.set_language(metadata.get('language', 'zh-CN'))
                book.add_author(metadata.get('author', '未知作者'))

                if metadata.get('publisher'):
                    book.add_metadata('DC', 'publisher', metadata['publisher'])
                if metadata.get('date'):
                    book.add_metadata('DC', 'date', metadata['date'])
                if metadata.get('description'):
                    book.add_metadata('DC', 'description', metadata['description'])
            else:
                book.set_identifier(f'translated_{hash(output_path)}')
                book.set_title('翻译文档')
                book.set_language('zh-CN')
                book.add_author('翻译系统')

            # 重建章节结构
            chapters = self._rebuild_epub_chapters(translated_nodes, book)

            # 添加CSS样式
            self._add_css_styles(book)

            # 添加媒体资源
            self._add_media_resources(book)

            # 构建导航
            self._build_navigation(book, chapters)

            # 写入文件
            epub.write_epub(output_path, book, {})
            logger.info(f"成功生成增强的ePub文件: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"生成增强ePub文件失败: {e}")
            # 降级到简单ePub生成
            return self._generate_simple_epub(translated_nodes, output_path)

    def _rebuild_epub_chapters(self, translated_nodes: List[Dict[str, Any]], book: epub.EpubBook) -> List[epub.EpubHtml]:
        """重建ePub章节"""
        chapters = []

        # 检查是否有章节结构信息
        if hasattr(self.parser, 'chapter_hierarchy') and self.parser.chapter_hierarchy:
            # 使用章节结构重建
            for i, chapter_info in enumerate(self.parser.chapter_hierarchy):
                if 'content' in chapter_info:
                    chapter_content = self._rebuild_chapter_content(chapter_info, translated_nodes)

                    chapter = epub.EpubHtml(
                        title=chapter_info.get('title', f'章节 {i+1}'),
                        file_name=f'chapter_{i+1}.xhtml',
                        lang='zh-CN'
                    )
                    chapter.content = chapter_content
                    book.add_item(chapter)
                    chapters.append(chapter)
        else:
            # 降级到单章节模式
            chapter_content = self._rebuild_single_chapter(translated_nodes)
            chapter = epub.EpubHtml(
                title='翻译内容',
                file_name='chapter_1.xhtml',
                lang='zh-CN'
            )
            chapter.content = chapter_content
            book.add_item(chapter)
            chapters.append(chapter)

        return chapters

    def _rebuild_chapter_content(self, chapter_info: Dict[str, Any], translated_nodes: List[Dict[str, Any]]) -> str:
        """重建章节内容"""
        html_content = '''<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>''' + chapter_info.get('title', '章节内容') + '''</title>
    <meta charset="utf-8"/>
</head>
<body>
'''

        # 添加章节标题
        html_content += f'<h1>{chapter_info.get("title", "章节内容")}</h1>\n'

        # 重建章节内容
        if 'content' in chapter_info:
            content = chapter_info['content']

            # 处理段落
            for section in content.get('sections', []):
                html_content += self._rebuild_section(section, translated_nodes)

            # 处理图片
            for image in content.get('images', []):
                html_content += self._rebuild_image(image)

            # 处理表格
            for table in content.get('tables', []):
                html_content += self._rebuild_table(table, translated_nodes)

        html_content += '''
</body>
</html>'''

        return html_content

    def _rebuild_section(self, section: Dict[str, Any], translated_nodes: List[Dict[str, Any]]) -> str:
        """重建段落"""
        section_type = section.get('type', 'paragraph')
        text = section.get('text', '')

        # 查找翻译后的文本
        translated_text = self._find_translated_text(text, translated_nodes)

        if section_type == 'heading':
            level = section.get('level', 1)
            return f'<h{level}>{translated_text}</h{level}>\n'
        elif section_type == 'paragraph':
            # 处理内联元素
            inline_elements = section.get('inline_elements', [])
            if inline_elements:
                processed_text = self._process_inline_elements(translated_text, inline_elements)
                return f'<p>{processed_text}</p>\n'
            else:
                return f'<p>{translated_text}</p>\n'
        elif section_type == 'list':
            list_type = section.get('list_type', 'ul')
            items = section.get('items', [])

            list_html = f'<{list_type}>\n'
            for item in items:
                item_text = self._find_translated_text(item.get('text', ''), translated_nodes)
                list_html += f'<li>{item_text}</li>\n'
            list_html += f'</{list_type}>\n'
            return list_html
        elif section_type == 'quote':
            return f'<blockquote>{translated_text}</blockquote>\n'
        elif section_type == 'code':
            language = section.get('language', '')
            return f'<pre><code class="{language}">{text}</code></pre>\n'
        else:
            return f'<p>{translated_text}</p>\n'

    def _rebuild_image(self, image: Dict[str, Any]) -> str:
        """重建图片"""
        src = image.get('src', '')
        alt = image.get('alt', '')
        title = image.get('title', '')

        img_tag = f'<img src="{src}" alt="{alt}"'
        if title:
            img_tag += f' title="{title}"'
        if image.get('width'):
            img_tag += f' width="{image["width"]}"'
        if image.get('height'):
            img_tag += f' height="{image["height"]}"'

        img_tag += ' />\n'
        return img_tag

    def _rebuild_table(self, table: Dict[str, Any], translated_nodes: List[Dict[str, Any]]) -> str:
        """重建表格"""
        table_html = '<table>\n'

        # 表格标题
        caption = table.get('caption', '')
        if caption:
            translated_caption = self._find_translated_text(caption, translated_nodes)
            table_html += f'<caption>{translated_caption}</caption>\n'

        # 表头
        headers = table.get('headers', [])
        if headers:
            table_html += '<thead>\n<tr>\n'
            for header in headers:
                translated_header = self._find_translated_text(header, translated_nodes)
                table_html += f'<th>{translated_header}</th>\n'
            table_html += '</tr>\n</thead>\n'

        # 表格行
        rows = table.get('rows', [])
        if rows:
            table_html += '<tbody>\n'
            for row in rows:
                table_html += '<tr>\n'
                for cell in row:
                    cell_text = cell.get('text', '')
                    translated_text = self._find_translated_text(cell_text, translated_nodes)

                    cell_tag = 'td'
                    if cell.get('is_header', False):
                        cell_tag = 'th'

                    colspan = cell.get('colspan', 1)
                    rowspan = cell.get('rowspan', 1)

                    cell_html = f'<{cell_tag}'
                    if colspan > 1:
                        cell_html += f' colspan="{colspan}"'
                    if rowspan > 1:
                        cell_html += f' rowspan="{rowspan}"'
                    cell_html += f'>{translated_text}</{cell_tag}>\n'

                    table_html += cell_html
                table_html += '</tr>\n'
            table_html += '</tbody>\n'

        table_html += '</table>\n'
        return table_html

    def _rebuild_single_chapter(self, translated_nodes: List[Dict[str, Any]]) -> str:
        """重建单章节内容（降级模式）"""
        html_content = '''<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>翻译内容</title>
    <meta charset="utf-8"/>
</head>
<body>
'''

        for node in translated_nodes:
            text = node['text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            if node['type'] == 'heading':
                level = node.get('level', 1)
                html_content += f'<h{level}>{text}</h{level}>\n'
            elif node['type'] == 'paragraph':
                html_content += f'<p>{text}</p>\n'
            elif node['type'] == 'list_item':
                html_content += f'<p>• {text}</p>\n'
            else:
                html_content += f'<p>{text}</p>\n'

        html_content += '''
</body>
</html>'''

        return html_content

    def _find_translated_text(self, original_text: str, translated_nodes: List[Dict[str, Any]]) -> str:
        """查找翻译后的文本"""
        # 简化处理：直接使用翻译后的文本
        # 在实际应用中，需要更复杂的匹配逻辑
        for node in translated_nodes:
            # 尝试匹配文本内容
            if node.get('text') and original_text in node['text']:
                return node['text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # 如果没有找到匹配，返回翻译后的第一个节点文本或原始文本
        if translated_nodes:
            return translated_nodes[0]['text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # 如果没有找到翻译，返回原始文本
        return original_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def _process_inline_elements(self, text: str, inline_elements: List[Dict[str, Any]]) -> str:
        """处理内联元素"""
        # 简化的内联元素处理
        processed_text = text

        for element in inline_elements:
            element_type = element.get('element', '')
            element_text = element.get('text', '')

            if element_type == 'strong':
                processed_text = processed_text.replace(element_text, f'<strong>{element_text}</strong>')
            elif element_type == 'em':
                processed_text = processed_text.replace(element_text, f'<em>{element_text}</em>')
            elif element_type == 'code':
                processed_text = processed_text.replace(element_text, f'<code>{element_text}</code>')
            elif element_type == 'a':
                href = element.get('attributes', {}).get('href', '#')
                processed_text = processed_text.replace(element_text, f'<a href="{href}">{element_text}</a>')

        return processed_text

    def _add_css_styles(self, book: epub.EpubBook):
        """添加CSS样式"""
        if hasattr(self.parser, 'css_styles') and self.parser.css_styles:
            for css_id, css_info in self.parser.css_styles.items():
                try:
                    css_content = css_info.get('raw_css', '')
                    if css_content:
                        css_item = epub.EpubItem(
                            uid=css_id,
                            file_name=f'styles/{css_id}.css',
                            media_type='text/css',
                            content=css_content
                        )
                        book.add_item(css_item)
                except Exception as e:
                    logger.warning(f"添加CSS样式失败 {css_id}: {e}")

    def _add_media_resources(self, book: epub.EpubBook):
        """添加媒体资源"""
        if hasattr(self.parser, 'media_resources') and self.parser.media_resources:
            for resource_id, resource_info in self.parser.media_resources.items():
                try:
                    # 这里需要从原始ePub中提取资源内容
                    # 简化处理：只记录资源信息
                    logger.info(f"发现媒体资源: {resource_id} - {resource_info.get('file_name', '')}")
                except Exception as e:
                    logger.warning(f"处理媒体资源失败 {resource_id}: {e}")

    def _build_navigation(self, book: epub.EpubBook, chapters: List[epub.EpubHtml]):
        """构建导航"""
        # 设置目录
        book.toc = chapters

        # 添加导航文件
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # 设置spine
        book.spine = ['nav'] + chapters

    def _generate_simple_epub(self, translated_nodes: List[Dict[str, Any]], output_path: str) -> str:
        """生成简单的ePub文件（降级模式）"""
        try:
            book = epub.EpubBook()

            book.set_identifier(f'simple_translated_{hash(output_path)}')
            book.set_title('翻译文档')
            book.set_language('zh-CN')
            book.add_author('翻译系统')

            # 创建单章节
            chapter_html = '''<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>翻译内容</title>
    <meta charset="utf-8"/>
</head>
<body>
'''

            for node in translated_nodes:
                text = node['text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                if node['type'] == 'heading':
                    chapter_html += f'<h1>{text}</h1>\n'
                else:
                    chapter_html += f'<p>{text}</p>\n'

            chapter_html += '''
</body>
</html>'''

            chapter = epub.EpubHtml(
                title='翻译内容',
                file_name='chapter_1.xhtml',
                lang='zh-CN'
            )
            chapter.content = chapter_html
            book.add_item(chapter)

            book.toc = [chapter]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            book.spine = ['nav', chapter]

            epub.write_epub(output_path, book, {})
            logger.info(f"成功生成简单ePub文件: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"生成简单ePub文件失败: {e}")
            raise

    def generate_markdown(self, translated_nodes: List[Dict[str, Any]], output_path: str) -> str:
        """生成翻译后的Markdown文件，保持原始格式"""
        try:
            logger.info(f"开始生成增强的Markdown文件: {output_path}")

            # 检查是否有增强的Markdown解析器
            if hasattr(self.parser, 'rebuild_with_translations'):
                # 使用增强解析器的重建功能
                rebuilt_content = self.parser.rebuild_with_translations(translated_nodes)
            elif hasattr(self.parser, 'rebuild_markdown_content'):
                # 使用现有解析器的重建功能
                rebuilt_content = self.parser.rebuild_markdown_content(translated_nodes)
            else:
                # 降级到简单重建
                rebuilt_content = self._rebuild_simple_markdown(translated_nodes)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(rebuilt_content)

            logger.info(f"成功生成增强的Markdown文件: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"生成增强Markdown文件失败: {e}")
            # 降级到简单Markdown生成
            return self._generate_simple_markdown(translated_nodes, output_path)

    def _rebuild_simple_markdown(self, translated_nodes: List[Dict[str, Any]]) -> str:
        """重建简单的Markdown内容（降级模式）"""
        markdown_content = ""

        for node in translated_nodes:
            if node['type'] == 'heading':
                level = node.get('level', 1)
                markdown_content += '#' * level + ' ' + node['text'] + '\n\n'
            elif node['type'] == 'paragraph':
                markdown_content += node['text'] + '\n\n'
            elif node['type'] == 'list_item':
                markdown_content += '- ' + node['text'] + '\n'
            else:
                markdown_content += node['text'] + '\n\n'

        return markdown_content

    def _generate_simple_markdown(self, translated_nodes: List[Dict[str, Any]], output_path: str) -> str:
        """生成简单的Markdown文件（降级模式）"""
        try:
            markdown_content = self._rebuild_simple_markdown(translated_nodes)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            logger.info(f"成功生成简单Markdown文件: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"生成简单Markdown文件失败: {e}")
            raise

    def generate_html(self, translated_nodes: List[Dict[str, Any]], output_path: str) -> str:
        """生成HTML文件"""
        try:
            logger.info(f"开始生成HTML文件: {output_path}")

            # 检查是否有章节结构
            if hasattr(self.parser, 'chapter_hierarchy') and self.parser.chapter_hierarchy:
                # 使用章节结构生成HTML
                html_content = self._generate_structured_html(translated_nodes)
            else:
                # 使用简单HTML生成
                html_content = self._generate_simple_html(translated_nodes)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"成功生成HTML文件: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"生成HTML文件失败: {e}")
            raise

    def generate_html_from_content(self, markdown_content: str, output_path: str) -> str:
        """从Markdown内容直接生成HTML文件"""
        try:
            logger.info(f"开始从内容生成HTML文件: {output_path}")

            # 使用markdown库将Markdown内容转换为HTML
            html_body = markdown.markdown(markdown_content, extensions=['fenced_code', 'tables'])

            html_content = f'''
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
'''

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"成功从内容生成HTML文件: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"从内容生成HTML文件失败: {e}")
            raise

    def _generate_structured_html(self, translated_nodes: List[Dict[str, Any]]) -> str:
        """生成结构化的HTML"""
        html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>翻译文档</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }
        h1, h2, h3, h4, h5, h6 { color: #333; }
        p { margin-bottom: 1em; }
        ul, ol { margin-bottom: 1em; }
        blockquote { border-left: 4px solid #ddd; margin: 1em 0; padding-left: 1em; }
        code { background-color: #f4f4f4; padding: 2px 4px; border-radius: 3px; }
        pre { background-color: #f4f4f4; padding: 1em; border-radius: 5px; overflow-x: auto; }
        .chapter { margin-bottom: 2em; border-bottom: 1px solid #eee; padding-bottom: 1em; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 1em; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f4f4f4; }
    </style>
</head>
<body>
'''

        # 添加文档标题
        if hasattr(self.parser, 'metadata') and self.parser.metadata:
            title = self.parser.metadata.get('title', '翻译文档')
            html_content += f'<h1>{title} (翻译版)</h1>\n'

        # 添加章节内容
        if hasattr(self.parser, 'chapter_hierarchy'):
            for i, chapter_info in enumerate(self.parser.chapter_hierarchy):
                if 'content' in chapter_info:
                    chapter_content = self._rebuild_chapter_content(chapter_info, translated_nodes)

                    # 提取body内容
                    soup = BeautifulSoup(chapter_content, 'html.parser')
                    body_content = soup.find('body')
                    if body_content:
                        # 移除body标签，只保留内容
                        body_html = ''.join(str(child) for child in body_content.children)
                        html_content += f'<div class="chapter">\n{body_html}\n</div>\n'

        html_content += '''
</body>
</html>'''

        return html_content

    def _generate_simple_html(self, translated_nodes: List[Dict[str, Any]]) -> str:
        """生成简单的HTML"""
        # 生成Markdown内容
        markdown_content = self._rebuild_simple_markdown(translated_nodes)

        # 转换为HTML
        html_body = markdown.markdown(markdown_content, extensions=['fenced_code', 'tables'])

        html_content = f'''
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
'''

        return html_content

def save_enhanced_format_preserving_result(parser, translated_nodes: List[Dict[str, Any]], base_output_path: str, file_extension: str, format_hint_generator=None) -> List[str]:
    """保存增强的格式保留翻译结果"""
    generator = EnhancedFormatPreservingGenerator(parser, format_hint_generator)
    results = []

    try:
        if file_extension == '.epub':
            # 生成ePub文件
            epub_path = base_output_path.replace('.txt', '.epub')
            generator.generate_epub(translated_nodes, epub_path)
            results.append(epub_path)

            # 同时生成HTML版本用于预览
            html_path = base_output_path.replace('.txt', '.html')
            generator.generate_html(translated_nodes, html_path)
            results.append(html_path)

        elif file_extension in ['.md', '.markdown']:
            # 生成Markdown文件
            md_path = base_output_path.replace('.txt', '.md')
            generator.generate_markdown(translated_nodes, md_path)
            results.append(md_path)

            # 同时生成HTML版本
            html_path = base_output_path.replace('.txt', '.html')
            generator.generate_html(translated_nodes, html_path)
            results.append(html_path)

        else:
            # 对于其他格式，生成Markdown
            md_path = base_output_path.replace('.txt', '.md')
            generator.generate_markdown(translated_nodes, md_path)
            results.append(md_path)

        # 始终生成纯文本版本作为备份
        txt_content = '\n\n'.join([node['text'] for node in translated_nodes])
        with open(base_output_path, 'w', encoding='utf-8') as f:
            f.write(txt_content)
        results.append(base_output_path)

        return results

    except Exception as e:
        logger.error(f"保存增强格式保留结果失败: {e}")
        # 降级到纯文本保存
        txt_content = '\n\n'.join([node['text'] for node in translated_nodes])
        with open(base_output_path, 'w', encoding='utf-8') as f:
            f.write(txt_content)
        return [base_output_path]