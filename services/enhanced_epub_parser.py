"""
增强的ePub解析器
支持完整的ePub结构解析，包括多章节、CSS样式、媒体资源等
"""
import os
import logging
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import cssutils
from PIL import Image
import io

logger = logging.getLogger(__name__)

class EnhancedEpubParser:
    """增强的ePub解析器，支持完整的ePub结构解析"""

    def __init__(self):
        self.book_structure = {}
        self.css_styles = {}
        self.media_resources = {}
        self.metadata = {}
        self.chapter_hierarchy = []

    def parse_complete_epub(self, epub_path):
        """解析完整的ePub结构"""
        try:
            logger.info(f"开始解析ePub文件: {epub_path}")

            # 1. 解析元数据
            self._parse_metadata(epub_path)

            # 2. 解析章节结构
            self._parse_chapter_structure(epub_path)

            # 3. 提取CSS样式
            self._extract_css_styles(epub_path)

            # 4. 提取媒体资源
            self._extract_media_resources(epub_path)

            # 5. 构建文档AST
            document_ast = self._build_document_ast()

            logger.info(f"ePub解析完成，共 {len(self.chapter_hierarchy)} 个章节")
            return document_ast

        except Exception as e:
            logger.error(f"解析ePub文件失败: {e}")
            raise

    def _parse_metadata(self, epub_path):
        """解析ePub元数据"""
        try:
            book = epub.read_epub(epub_path)

            # 提取基本元数据
            self.metadata = {
                'title': self._get_metadata_value(book, 'DC', 'title', '未知标题'),
                'author': self._get_metadata_value(book, 'DC', 'creator', '未知作者'),
                'language': self._get_metadata_value(book, 'DC', 'language', '未知语言'),
                'publisher': self._get_metadata_value(book, 'DC', 'publisher', ''),
                'date': self._get_metadata_value(book, 'DC', 'date', ''),
                'identifier': self._get_metadata_value(book, 'DC', 'identifier', ''),
                'description': self._get_metadata_value(book, 'DC', 'description', ''),
                'subject': self._get_metadata_value(book, 'DC', 'subject', ''),
            }

            # 提取封面信息
            cover_item = book.get_item_with_id('cover')
            if cover_item:
                self.metadata['cover'] = cover_item.get_id()

            logger.info(f"提取元数据: {self.metadata['title']} - {self.metadata['author']}")

        except Exception as e:
            logger.warning(f"解析元数据失败: {e}")

    def _parse_chapter_structure(self, epub_path):
        """解析章节层次结构"""
        try:
            book = epub.read_epub(epub_path)

            # 获取导航信息
            spine_items = book.spine
            toc_items = book.toc

            # 构建章节层次
            self.chapter_hierarchy = self._build_chapter_hierarchy(toc_items, spine_items)

            # 解析每个章节的内容
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    chapter_id = item.get_id()
                    chapter_content = self._parse_chapter_content(item)

                    # 查找章节在层次结构中的位置
                    chapter_info = self._find_chapter_in_hierarchy(item)
                    if chapter_info:
                        chapter_info['content'] = chapter_content
                        chapter_info['item'] = item

            logger.info(f"解析章节结构完成，共 {len(self.chapter_hierarchy)} 个章节")

        except Exception as e:
            logger.error(f"解析章节结构失败: {e}")
            raise

    def _build_chapter_hierarchy(self, toc_items, spine_items):
        """构建章节层次结构"""
        hierarchy = []

        def process_toc_items(items, parent=None):
            for item in items:
                if isinstance(item, tuple):
                    # 章节项
                    chapter_info = {
                        'id': item[0].href if hasattr(item[0], 'href') else str(hash(item[0])),
                        'title': item[0].title if hasattr(item[0], 'title') else '未知标题',
                        'href': item[0].href if hasattr(item[0], 'href') else '',
                        'children': [],
                        'parent': parent,
                        'level': parent['level'] + 1 if parent else 0
                    }

                    # 递归处理子章节
                    if len(item) > 1:
                        process_toc_items(item[1], chapter_info)

                    hierarchy.append(chapter_info)
                elif isinstance(item, ebooklib.epub.Link):
                    # 链接项
                    chapter_info = {
                        'id': item.href,
                        'title': item.title,
                        'href': item.href,
                        'children': [],
                        'parent': parent,
                        'level': parent['level'] + 1 if parent else 0
                    }
                    hierarchy.append(chapter_info)

        process_toc_items(toc_items)
        return hierarchy

    def _parse_chapter_content(self, item):
        """解析章节内容"""
        try:
            soup = BeautifulSoup(item.get_content(), 'html.parser')

            # 移除脚本和样式标签
            for script in soup(['script', 'style']):
                script.decompose()

            # 解析章节结构
            chapter_structure = {
                'title': self._extract_chapter_title(soup),
                'sections': [],
                'images': [],
                'tables': [],
                'footnotes': []
            }

            # 解析主要内容
            main_content = soup.find('body') or soup
            if main_content:
                chapter_structure['sections'] = self._parse_content_sections(main_content)
                chapter_structure['images'] = self._extract_images(main_content)
                chapter_structure['tables'] = self._extract_tables(main_content)
                chapter_structure['footnotes'] = self._extract_footnotes(main_content)

            return chapter_structure

        except Exception as e:
            logger.warning(f"解析章节内容失败: {e}")
            return {'title': '解析失败', 'sections': []}

    def _parse_content_sections(self, element):
        """解析内容段落"""
        sections = []

        for child in element.children:
            if hasattr(child, 'name') and child.name:
                section_info = {
                    'element': child.name,
                    'text': child.get_text().strip(),
                    'attributes': dict(child.attrs) if hasattr(child, 'attrs') else {},
                    'children': []
                }

                # 处理标题
                if child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    section_info['type'] = 'heading'
                    section_info['level'] = int(child.name[1])

                # 处理段落
                elif child.name == 'p':
                    section_info['type'] = 'paragraph'

                    # 处理内联元素
                    inline_elements = []
                    for inline in child.find_all(['strong', 'em', 'code', 'a']):
                        inline_elements.append({
                            'element': inline.name,
                            'text': inline.get_text(),
                            'attributes': dict(inline.attrs)
                        })
                    section_info['inline_elements'] = inline_elements

                # 处理列表
                elif child.name in ['ul', 'ol']:
                    section_info['type'] = 'list'
                    section_info['list_type'] = child.name
                    section_info['items'] = []

                    for li in child.find_all('li', recursive=False):
                        section_info['items'].append({
                            'text': li.get_text().strip(),
                            'children': self._parse_content_sections(li)
                        })

                # 处理引用
                elif child.name in ['blockquote']:
                    section_info['type'] = 'quote'
                    section_info['children'] = self._parse_content_sections(child)

                # 处理代码块
                elif child.name in ['pre', 'code']:
                    section_info['type'] = 'code'
                    section_info['language'] = child.get('class', [''])[0] if child.get('class') else ''

                # 总是添加有内容的段落，即使没有子元素
                if section_info['text']:
                    sections.append(section_info)

        return sections

    def _extract_chapter_title(self, soup):
        """提取章节标题"""
        # 尝试从h1-h6标签中提取标题
        for level in range(1, 7):
            heading = soup.find(f'h{level}')
            if heading and heading.get_text().strip():
                return heading.get_text().strip()

        # 尝试从title标签中提取
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()

        return '未知标题'

    def _extract_images(self, element):
        """提取图片信息"""
        images = []

        for img in element.find_all('img'):
            image_info = {
                'src': img.get('src', ''),
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
                'width': img.get('width', ''),
                'height': img.get('height', ''),
                'attributes': dict(img.attrs)
            }
            images.append(image_info)

        return images

    def _extract_tables(self, element):
        """提取表格信息"""
        tables = []

        for table in element.find_all('table'):
            table_info = {
                'caption': '',
                'headers': [],
                'rows': [],
                'attributes': dict(table.attrs)
            }

            # 提取表格标题
            caption = table.find('caption')
            if caption:
                table_info['caption'] = caption.get_text().strip()

            # 提取表头
            header_row = table.find('thead')
            if header_row:
                for th in header_row.find_all(['th', 'td']):
                    table_info['headers'].append(th.get_text().strip())

            # 提取表格行
            for tr in table.find_all('tr'):
                row = []
                for td in tr.find_all(['td', 'th']):
                    row.append({
                        'text': td.get_text().strip(),
                        'colspan': int(td.get('colspan', 1)),
                        'rowspan': int(td.get('rowspan', 1)),
                        'attributes': dict(td.attrs)
                    })
                if row:
                    table_info['rows'].append(row)

            tables.append(table_info)

        return tables

    def _extract_footnotes(self, element):
        """提取脚注信息"""
        footnotes = []

        # 查找常见的脚注标记
        footnote_selectors = [
            '[class*="footnote"]',
            '[id*="footnote"]',
            '[class*="note"]',
            '[id*="note"]'
        ]

        for selector in footnote_selectors:
            for footnote in element.select(selector):
                footnote_info = {
                    'id': footnote.get('id', ''),
                    'text': footnote.get_text().strip(),
                    'attributes': dict(footnote.attrs)
                }
                footnotes.append(footnote_info)

        return footnotes

    def _extract_css_styles(self, epub_path):
        """提取完整的CSS样式"""
        try:
            book = epub.read_epub(epub_path)

            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_STYLE:
                    try:
                        css_content = item.get_content().decode('utf-8')
                        css_id = item.get_id()

                        # 使用cssutils解析CSS
                        sheet = cssutils.parseString(css_content)

                        # 提取样式规则
                        styles = {}
                        for rule in sheet:
                            if rule.type == rule.STYLE_RULE:
                                selector = rule.selectorText
                                styles[selector] = {}
                                for prop in rule.style:
                                    styles[selector][prop.name] = prop.value

                        self.css_styles[css_id] = {
                            'raw_css': css_content,
                            'parsed_styles': styles
                        }

                    except Exception as e:
                        logger.warning(f"解析CSS文件 {item.get_id()} 失败: {e}")

            logger.info(f"提取CSS样式完成，共 {len(self.css_styles)} 个样式文件")

        except Exception as e:
            logger.warning(f"提取CSS样式失败: {e}")

    def _extract_media_resources(self, epub_path):
        """提取媒体资源"""
        try:
            book = epub.read_epub(epub_path)

            for item in book.get_items():
                if item.get_type() in [ebooklib.ITEM_IMAGE, ebooklib.ITEM_FONT]:
                    media_info = {
                        'id': item.get_id(),
                        'type': item.get_type(),
                        'media_type': item.media_type,
                        'size': len(item.get_content()),
                        'file_name': item.file_name
                    }

                    # 对于图片，提取基本信息
                    if item.get_type() == ebooklib.ITEM_IMAGE:
                        try:
                            image_data = item.get_content()
                            image = Image.open(io.BytesIO(image_data))
                            media_info.update({
                                'width': image.width,
                                'height': image.height,
                                'format': image.format,
                                'mode': image.mode
                            })
                        except Exception as e:
                            logger.warning(f"处理图片 {item.get_id()} 失败: {e}")

                    self.media_resources[item.get_id()] = media_info

            logger.info(f"提取媒体资源完成，共 {len(self.media_resources)} 个资源")

        except Exception as e:
            logger.warning(f"提取媒体资源失败: {e}")

    def _build_document_ast(self):
        """构建文档抽象语法树"""
        document_ast = {
            'metadata': self.metadata,
            'structure': self.chapter_hierarchy,
            'styles': self.css_styles,
            'resources': self.media_resources,
            'translatable_nodes': self._identify_translatable_nodes()
        }

        return document_ast

    def _identify_translatable_nodes(self):
        """识别可翻译节点"""
        translatable_nodes = []

        for chapter in self.chapter_hierarchy:
            if 'content' in chapter:
                content = chapter['content']

                # 提取标题
                if content.get('title'):
                    translatable_nodes.append({
                        'type': 'heading',
                        'text': content['title'],
                        'context': {
                            'chapter_id': chapter['id'],
                            'chapter_title': chapter['title'],
                            'level': chapter.get('level', 0)
                        }
                    })

                # 提取段落文本
                for section in content.get('sections', []):
                    if section.get('text') and section.get('type') in ['paragraph', 'heading']:
                        translatable_nodes.append({
                            'type': section['type'],
                            'text': section['text'],
                            'context': {
                                'chapter_id': chapter['id'],
                                'chapter_title': chapter['title'],
                                'element': section.get('element'),
                                'attributes': section.get('attributes', {})
                            }
                        })

                    # 处理列表项
                    if section.get('type') == 'list':
                        for item in section.get('items', []):
                            if item.get('text'):
                                translatable_nodes.append({
                                    'type': 'list_item',
                                    'text': item['text'],
                                    'context': {
                                        'chapter_id': chapter['id'],
                                        'chapter_title': chapter['title'],
                                        'list_type': section.get('list_type'),
                                        'element': section.get('element')
                                    }
                                })

        return translatable_nodes

    def _find_chapter_in_hierarchy(self, item):
        """在层次结构中查找章节"""
        for chapter in self.chapter_hierarchy:
            # 匹配文件名或HREF
            if chapter['href'] == item.file_name or chapter['id'] == item.get_id():
                return chapter
        return None

    def _get_metadata_value(self, book, namespace, element, default=''):
        """获取元数据值"""
        try:
            metadata = book.get_metadata(namespace, element)
            if metadata:
                return metadata[0][0]
        except:
            pass
        return default