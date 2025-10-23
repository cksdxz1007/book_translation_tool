import os
import logging
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, NavigableString
import re
from japanese_text_processor import JapaneseTextProcessor

logger = logging.getLogger(__name__)

class FormatPreservingParser:
    """格式保留解析器，支持ePub和Markdown文件的结构化解析和重建"""
    
    def __init__(self):
        self.structure = []
        self.metadata = {}
        self.css_styles = {}
        self.japanese_processor = JapaneseTextProcessor()
    
    def parse_epub_with_structure(self, epub_path):
        """解析ePub文件，保留完整的HTML结构信息"""
        try:
            book = epub.read_epub(epub_path)
            self.metadata = self._extract_epub_metadata(book)
            
            # 提取CSS样式
            self._extract_css_styles(book)
            
            structured_content = []
            
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    chapter_structure = self._parse_html_structure(soup)
                    if chapter_structure:
                        structured_content.append({
                            'type': 'chapter',
                            'id': item.get_id(),
                            'content': chapter_structure
                        })
            
            self.structure = structured_content
            return self._extract_translatable_text()
            
        except Exception as e:
            logger.error(f"解析ePub文件失败: {e}")
            raise
    
    def parse_markdown_with_structure(self, md_path):
        """解析Markdown文件，保留结构信息"""
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析Markdown结构
            lines = content.split('\n')
            structured_content = []
            
            in_code_block = False
            code_block_content = []
            
            for line in lines:
                line_stripped = line.strip()
                
                # 代码块处理
                if line_stripped.startswith('```'):
                    if in_code_block:
                        # 结束代码块
                        code_block_content.append(line)
                        structured_content.append({
                            'type': 'code_block',
                            'content': '\n'.join(code_block_content),
                            'original': '\n'.join(code_block_content)
                        })
                        code_block_content = []
                        in_code_block = False
                    else:
                        # 开始代码块
                        in_code_block = True
                        code_block_content = [line]
                    continue
                
                # 如果在代码块内，收集内容
                if in_code_block:
                    code_block_content.append(line)
                    continue
                
                # 标题处理
                if line_stripped.startswith('#'):
                    level = len(line_stripped) - len(line_stripped.lstrip('#'))
                    title = line_stripped.lstrip('#').strip()
                    structured_content.append({
                        'type': 'heading',
                        'level': level,
                        'text': title,
                        'original': line
                    })
                # 列表项
                elif re.match(r'^[\s]*[-*+]\s', line):
                    structured_content.append({
                        'type': 'list_item',
                        'text': re.sub(r'^[\s]*[-*+]\s', '', line),
                        'original': line,
                        'marker': re.match(r'^([\s]*[-*+]\s)', line).group(1)
                    })
                # 有序列表
                elif re.match(r'^[\s]*\d+\.\s', line):
                    structured_content.append({
                        'type': 'ordered_list',
                        'text': re.sub(r'^[\s]*\d+\.\s', '', line),
                        'original': line,
                        'marker': re.match(r'^([\s]*\d+\.\s)', line).group(1)
                    })
                # 引用
                elif line_stripped.startswith('>'):
                    structured_content.append({
                        'type': 'quote',
                        'text': line_stripped.lstrip('>').strip(),
                        'original': line
                    })
                # 普通段落
                elif line_stripped:
                    structured_content.append({
                        'type': 'paragraph',
                        'text': line_stripped,
                        'original': line
                    })
                # 空行
                else:
                    structured_content.append({
                        'type': 'empty_line',
                        'original': line
                    })
            
            self.structure = structured_content
            return self._extract_translatable_text_from_markdown()
            
        except Exception as e:
            logger.error(f"解析Markdown文件失败: {e}")
            raise
    
    def _parse_html_structure(self, soup):
        """递归解析HTML结构，保留样式信息"""
        structure = []
        
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'span', 'strong', 'em', 'ul', 'ol', 'li']):
            # 提取样式信息
            style_info = self._extract_element_style(element)
            
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                text = element.get_text().strip()
                structure.append({
                    'type': 'heading',
                    'level': int(element.name[1]),
                    'text': text,
                    'tag': element.name,
                    'style': style_info,
                    'is_japanese': self.japanese_processor.is_japanese_text(text),
                    'is_vertical': style_info.get('is_vertical', False)
                })
            elif element.name == 'p':
                text = element.get_text().strip()
                if text:
                    # 日文文本特殊处理
                    if self.japanese_processor.is_japanese_text(text):
                        sentences = self.japanese_processor.split_japanese_sentences(text)
                        for sentence in sentences:
                            structure.append({
                                'type': 'paragraph',
                                'text': sentence,
                                'tag': element.name,
                                'style': style_info,
                                'is_japanese': True,
                                'is_vertical': style_info.get('is_vertical', False)
                            })
                    else:
                        structure.append({
                            'type': 'paragraph',
                            'text': text,
                            'tag': element.name,
                            'style': style_info,
                            'is_japanese': False,
                            'is_vertical': style_info.get('is_vertical', False)
                        })
            elif element.name in ['ul', 'ol']:
                list_items = []
                for li in element.find_all('li', recursive=False):
                    list_items.append(li.get_text().strip())
                structure.append({
                    'type': 'list',
                    'list_type': element.name,
                    'items': list_items,
                    'style': style_info,
                    'is_vertical': style_info.get('is_vertical', False)
                })
        
        return structure
    
    def _extract_epub_metadata(self, book):
        """提取ePub元数据"""
        return {
            'title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else '未知标题',
            'author': book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else '未知作者',
            'language': book.get_metadata('DC', 'language')[0][0] if book.get_metadata('DC', 'language') else '未知语言'
        }
    
    def _extract_css_styles(self, book):
        """提取ePub中的CSS样式"""
        self.css_styles = {}
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_STYLE:
                try:
                    css_content = item.get_content().decode('utf-8')
                    self.css_styles[item.get_id()] = css_content
                except Exception as e:
                    logger.warning(f"解析CSS文件失败: {e}")
    
    def _extract_element_style(self, element):
        """提取元素的样式信息"""
        style_info = {
            'class': element.get('class', []),
            'style': element.get('style', ''),
            'is_vertical': False
        }
        
        # 检测垂直排版
        style_attr = element.get('style', '').lower()
        class_names = ' '.join(element.get('class', [])).lower()
        
        # 检测CSS中的垂直排版属性
        vertical_indicators = [
            'writing-mode: vertical-rl',
            'writing-mode: vertical-lr', 
            'writing-mode: tb-rl',
            'writing-mode: tb-lr',
            '-webkit-writing-mode: vertical-rl',
            '-webkit-writing-mode: vertical-lr'
        ]
        
        for indicator in vertical_indicators:
            if indicator in style_attr:
                style_info['is_vertical'] = True
                break
        
        # 检测class名称中的垂直排版标识
        vertical_class_indicators = ['vertical', 'tate', 'v-text', 'vert']
        for indicator in vertical_class_indicators:
            if indicator in class_names:
                style_info['is_vertical'] = True
                break
        
        # 检测文本内容中的垂直排版标记
        text = element.get_text()
        if self.japanese_processor.detect_vertical_text_markers(text):
            style_info['is_vertical'] = True
        
        return style_info
    
    def _extract_translatable_text(self):
        """从结构化内容中提取可翻译文本"""
        translatable_chunks = []
        
        for chapter in self.structure:
            for item in chapter['content']:
                if item['type'] in ['heading', 'paragraph']:
                    translatable_chunks.append({
                        'text': item['text'],
                        'type': item['type'],
                        'context': item
                    })
                elif item['type'] == 'list':
                    for list_item in item['items']:
                        if list_item.strip():
                            translatable_chunks.append({
                                'text': list_item,
                                'type': 'list_item',
                                'context': item
                            })
        
        return translatable_chunks
    
    def _extract_translatable_text_from_markdown(self):
        """从Markdown结构中提取可翻译文本"""
        translatable_chunks = []
        
        for item in self.structure:
            if item['type'] in ['heading', 'paragraph', 'list_item', 'ordered_list', 'quote']:
                if item['text'].strip():
                    translatable_chunks.append({
                        'text': item['text'],
                        'type': item['type'],
                        'context': item
                    })
        
        return translatable_chunks
    
    def rebuild_epub_content(self, translated_chunks):
        """重建ePub内容，保持原始格式和样式"""
        if not self.structure:
            # 如果没有结构信息，创建简单的HTML内容
            html_content = ['<html><head><meta charset="utf-8"/></head><body>']
            for chunk in translated_chunks:
                if chunk['type'] == 'heading':
                    html_content.append(f'<h1>{chunk["text"]}</h1>')
                else:
                    html_content.append(f'<p>{chunk["text"]}</p>')
            html_content.append('</body></html>')
            return '\n'.join(html_content)
        
        # 使用结构信息重建内容
        html_content = ['<html><head><meta charset="utf-8"/>']
        
        # 添加CSS样式
        if self.css_styles:
            html_content.append('<style>')
            for css_id, css_content in self.css_styles.items():
                html_content.append(css_content)
            html_content.append('</style>')
        
        html_content.append('</head><body>')
        
        chunk_index = 0
        for chapter in self.structure:
            for item in chapter['content']:
                if chunk_index < len(translated_chunks):
                    chunk = translated_chunks[chunk_index]
                    
                    # 构建样式属性
                    style_attrs = self._build_style_attributes(item.get('style', {}))
                    
                    if item['type'] == 'heading':
                        tag = item.get('tag', 'h1')
                        html_content.append(f'<{tag}{style_attrs}>{chunk["text"]}</{tag}>')
                    elif item['type'] == 'paragraph':
                        html_content.append(f'<p{style_attrs}>{chunk["text"]}</p>')
                    elif item['type'] == 'list':
                        list_tag = item.get('list_type', 'ul')
                        html_content.append(f'<{list_tag}{style_attrs}>')
                        for list_item in item['items']:
                            if chunk_index < len(translated_chunks):
                                html_content.append(f'<li>{translated_chunks[chunk_index]["text"]}</li>')
                                chunk_index += 1
                        html_content.append(f'</{list_tag}>')
                        continue
                    
                    chunk_index += 1
        
        html_content.append('</body></html>')
        return '\n'.join(html_content)
    
    def _build_style_attributes(self, style_info):
        """构建HTML样式属性"""
        attrs = []
        
        if style_info.get('class'):
            class_str = ' '.join(style_info['class'])
            attrs.append(f'class="{class_str}"')
        
        if style_info.get('style'):
            attrs.append(f'style="{style_info["style"]}"')
        
        return ' ' + ' '.join(attrs) if attrs else ''
    
    def rebuild_markdown_content(self, translated_chunks):
        """重建Markdown内容，保持原始格式"""
        chunk_index = 0
        rebuilt_lines = []
        
        for item in self.structure:
            if item['type'] == 'heading':
                if chunk_index < len(translated_chunks):
                    translated_text = translated_chunks[chunk_index]['text']
                    rebuilt_lines.append('#' * item['level'] + ' ' + translated_text)
                    chunk_index += 1
            elif item['type'] == 'paragraph':
                if chunk_index < len(translated_chunks):
                    translated_text = translated_chunks[chunk_index]['text']
                    rebuilt_lines.append(translated_text)
                    chunk_index += 1
            elif item['type'] == 'list_item':
                if chunk_index < len(translated_chunks):
                    translated_text = translated_chunks[chunk_index]['text']
                    rebuilt_lines.append(item['marker'] + translated_text)
                    chunk_index += 1
            elif item['type'] == 'ordered_list':
                if chunk_index < len(translated_chunks):
                    translated_text = translated_chunks[chunk_index]['text']
                    rebuilt_lines.append(item['marker'] + translated_text)
                    chunk_index += 1
            elif item['type'] == 'quote':
                if chunk_index < len(translated_chunks):
                    translated_text = translated_chunks[chunk_index]['text']
                    rebuilt_lines.append('> ' + translated_text)
                    chunk_index += 1
            elif item['type'] == 'code_block':
                # 代码块不翻译，保持原样
                rebuilt_lines.append(item['original'])
            elif item['type'] == 'empty_line':
                rebuilt_lines.append('')
        
        return '\n'.join(rebuilt_lines)
