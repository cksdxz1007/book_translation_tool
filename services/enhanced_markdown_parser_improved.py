"""
改进的Markdown解析器
更好地保留内联格式和结构
"""
import os
import logging
import mistune
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ImprovedMarkdownParser:
    """改进的Markdown解析器，更好地保留内联格式"""

    def __init__(self):
        self.ast = None
        self.translatable_nodes = []
        self.markdown_content = ""

        # 创建Mistune解析器
        self.parser = mistune.create_markdown(
            renderer=None,  # 不使用渲染器，直接获取AST
            plugins=['table', 'url', 'strikethrough', 'footnotes', 'mark']
        )

    def parse_with_ast(self, markdown_content: str) -> Dict[str, Any]:
        """使用AST解析Markdown"""
        try:
            logger.info("开始解析Markdown内容")
            self.markdown_content = markdown_content

            # 使用Mistune解析Markdown
            self.ast = self.parser(markdown_content)

            # 标记可翻译节点
            self.translatable_nodes = self._extract_translatable_content()

            # 构建完整的文档结构
            document_structure = {
                'ast': self.ast,
                'translatable_nodes': self.translatable_nodes,
                'metadata': self._extract_metadata(),
                'structure_summary': self._analyze_structure()
            }

            logger.info(f"Markdown解析完成，共 {len(self.translatable_nodes)} 个可翻译节点")
            return document_structure

        except Exception as e:
            logger.error(f"解析Markdown失败: {e}")
            raise

    def _extract_translatable_content(self) -> List[Dict[str, Any]]:
        """提取可翻译内容，保留内联格式信息"""
        translatable_nodes = []

        def traverse_ast(node, context=None):
            """递归遍历AST节点"""
            if context is None:
                context = {'level': 0, 'in_code_block': False, 'in_table': False}

            if isinstance(node, dict):
                node_type = node.get('type')

                # 处理不同类型的节点
                if node_type == 'heading':
                    text_info = self._extract_text_with_formatting(node)
                    if text_info['text']:
                        translatable_nodes.append({
                            'type': 'heading',
                            'text': text_info['text'],
                            'formatting': text_info['formatting'],
                            'level': node.get('level', 1),
                            'context': context.copy(),
                            'original_node': node
                        })

                elif node_type == 'paragraph':
                    text_info = self._extract_text_with_formatting(node)
                    if text_info['text'] and not context['in_code_block']:
                        translatable_nodes.append({
                            'type': 'paragraph',
                            'text': text_info['text'],
                            'formatting': text_info['formatting'],
                            'context': context.copy(),
                            'original_node': node
                        })

                elif node_type == 'list':
                    # 列表处理
                    for child in node.get('children', []):
                        if child.get('type') == 'list_item':
                            text_info = self._extract_text_with_formatting(child)
                            if text_info['text'] and not context['in_code_block']:
                                translatable_nodes.append({
                                    'type': 'list_item',
                                    'text': text_info['text'],
                                    'formatting': text_info['formatting'],
                                    'list_type': node.get('ordered', False) and 'ordered' or 'unordered',
                                    'context': context.copy(),
                                    'original_node': child
                                })

                elif node_type == 'block_code':
                    # 代码块不翻译，直接添加到可翻译节点但标记为不可翻译
                    code_content = node.get('text', '')
                    if code_content:
                        translatable_nodes.append({
                            'type': 'code_block',
                            'text': code_content,
                            'formatting': [],
                            'lang': node.get('lang', ''),
                            'context': context.copy(),
                            'original_node': node,
                            'should_translate': False  # 标记为不可翻译
                        })
                    context['in_code_block'] = True

                elif node_type == 'table':
                    # 表格处理
                    table_context = context.copy()
                    table_context['in_table'] = True

                    # 处理表头
                    header = node.get('header', [])
                    for cell in header:
                        text_info = self._extract_text_with_formatting(cell)
                        if text_info['text']:
                            translatable_nodes.append({
                                'type': 'table_header',
                                'text': text_info['text'],
                                'formatting': text_info['formatting'],
                                'context': table_context.copy(),
                                'original_node': cell
                            })

                    # 处理表格行
                    for row in node.get('children', []):
                        for cell in row.get('children', []):
                            text_info = self._extract_text_with_formatting(cell)
                            if text_info['text']:
                                translatable_nodes.append({
                                    'type': 'table_cell',
                                    'text': text_info['text'],
                                    'formatting': text_info['formatting'],
                                    'context': table_context.copy(),
                                    'original_node': cell
                                })

                elif node_type == 'block_quote':
                    # 引用处理
                    text_info = self._extract_text_with_formatting(node)
                    if text_info['text'] and not context['in_code_block']:
                        translatable_nodes.append({
                            'type': 'quote',
                            'text': text_info['text'],
                            'formatting': text_info['formatting'],
                            'context': context.copy(),
                            'original_node': node
                        })

                # 递归处理子节点
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        traverse_ast(value, context.copy())

            elif isinstance(node, list):
                for item in node:
                    traverse_ast(item, context.copy())

        # 开始遍历AST
        traverse_ast(self.ast)
        return translatable_nodes

    def _extract_text_with_formatting(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """从AST节点中提取文本内容和格式信息"""
        if isinstance(node, dict):
            node_type = node.get('type')

            if node_type == 'text':
                return {
                    'text': node.get('raw', node.get('text', '')),
                    'formatting': []
                }

            elif node_type in ['strong', 'emph', 'codespan']:
                children = node.get('children', [])
                if children:
                    child_text = self._extract_text_with_formatting(children)
                    return {
                        'text': child_text['text'],
                        'formatting': [node_type] + child_text['formatting']
                    }
                return {
                    'text': node.get('raw', node.get('text', '')),
                    'formatting': [node_type]
                }

            elif node_type == 'link':
                children = node.get('children', [])
                if children:
                    child_text = self._extract_text_with_formatting(children)
                    return {
                        'text': child_text['text'],
                        'formatting': [f'link:{node.get("attrs", {}).get("url", "")}'] + child_text['formatting']
                    }
                return {
                    'text': node.get('raw', node.get('text', '')),
                    'formatting': [f'link:{node.get("attrs", {}).get("url", "")}']
                }

            elif node_type in ['paragraph', 'heading', 'list_item', 'table_cell', 'table_header', 'block_text']:
                children = node.get('children', [])
                if children:
                    texts = []
                    formatting_sequence = []
                    for child in children:
                        child_text = self._extract_text_with_formatting(child)
                        if child_text['text']:
                            texts.append(child_text['text'])
                            formatting_sequence.append(child_text['formatting'])
                    return {
                        'text': ' '.join(texts),
                        'formatting': formatting_sequence
                    }

            elif node_type == 'block_quote':
                children = node.get('children', [])
                if children:
                    return self._extract_text_with_formatting(children)

        elif isinstance(node, list):
            texts = []
            formatting_sequence = []
            for item in node:
                item_text = self._extract_text_with_formatting(item)
                if item_text['text']:
                    texts.append(item_text['text'])
                    formatting_sequence.append(item_text['formatting'])
            return {
                'text': ' '.join(texts),
                'formatting': formatting_sequence
            }

        return {'text': '', 'formatting': []}

    def _extract_metadata(self) -> Dict[str, str]:
        """提取Markdown元数据"""
        metadata = {}

        # 检查是否有YAML front matter
        lines = self.markdown_content.split('\n')
        if lines and lines[0].strip() == '---':
            in_front_matter = False
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    break
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()

        # 提取标题
        if not metadata.get('title'):
            # 查找第一个一级标题
            for node in self.translatable_nodes:
                if node['type'] == 'heading' and node['level'] == 1:
                    metadata['title'] = node['text']
                    break

        return metadata

    def _analyze_structure(self) -> Dict[str, Any]:
        """分析文档结构"""
        structure = {
            'headings': [],
            'paragraphs': 0,
            'lists': 0,
            'tables': 0,
            'code_blocks': 0,
            'quotes': 0,
            'images': 0
        }

        def count_elements(node):
            if isinstance(node, dict):
                node_type = node.get('type')

                if node_type == 'heading':
                    structure['headings'].append({
                        'level': node.get('level', 1),
                        'text': self._extract_text_with_formatting(node)['text']
                    })
                elif node_type == 'paragraph':
                    structure['paragraphs'] += 1
                elif node_type == 'list':
                    structure['lists'] += 1
                elif node_type == 'table':
                    structure['tables'] += 1
                elif node_type == 'block_code':
                    structure['code_blocks'] += 1
                elif node_type == 'block_quote':
                    structure['quotes'] += 1
                elif node_type == 'image':
                    structure['images'] += 1

                # 递归处理子节点
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        count_elements(value)

            elif isinstance(node, list):
                for item in node:
                    count_elements(item)

        count_elements(self.ast)
        return structure

    def rebuild_with_translations(self, translated_nodes: List[Dict[str, Any]]) -> str:
        """使用翻译后的节点重建Markdown，保留内联格式"""
        try:
            logger.info("开始重建Markdown内容")

            # 创建翻译映射 - 使用稳定的节点标识符作为键
            translation_map = {}
            for translated_node in translated_nodes:
                original_node = translated_node.get('original_node')
                if original_node:
                    # 使用节点类型和文本内容作为稳定的标识符
                    node_key = self._get_node_key(original_node)
                    translation_map[node_key] = {
                        'text': translated_node['text'],
                        'formatting': translated_node.get('formatting', [])
                    }

            # 重建Markdown
            rebuilt_content = self._rebuild_from_ast_with_formatting(self.ast, translation_map)

            logger.info("Markdown重建完成")
            return rebuilt_content

        except Exception as e:
            logger.error(f"重建Markdown失败: {e}")
            raise

    def _get_node_key(self, node: Dict[str, Any]) -> str:
        """获取节点的唯一标识符"""
        # 使用节点类型和文本内容作为键
        node_type = node.get('type', '')
        text_info = self._extract_text_with_formatting(node)
        return f"{node_type}:{text_info['text']}"

    def _rebuild_from_ast_with_formatting(self, node: Any, translation_map: Dict[str, Dict[str, Any]]) -> str:
        """从AST重建Markdown内容，保留内联格式"""
        if isinstance(node, dict):
            node_type = node.get('type')

            if node_type == 'heading':
                level = node.get('level', 1)
                node_key = self._get_node_key(node)
                translation = translation_map.get(node_key, {'text': self._extract_text_with_formatting(node)['text']})
                formatted_text = self._apply_formatting_to_text(translation['text'], translation.get('formatting', []))
                return '#' * level + ' ' + formatted_text + '\n\n'

            elif node_type == 'paragraph':
                node_key = self._get_node_key(node)
                translation = translation_map.get(node_key, {'text': self._extract_text_with_formatting(node)['text']})

                # 调试输出
                print(f"DEBUG paragraph - 节点键: {node_key}")
                print(f"DEBUG paragraph - 找到翻译: {node_key in translation_map}")
                if node_key in translation_map:
                    print(f"DEBUG paragraph - 翻译文本: {translation['text']}")
                    print(f"DEBUG paragraph - 翻译格式: {translation.get('formatting', [])}")

                formatted_text = self._apply_formatting_to_text(translation['text'], translation.get('formatting', []))
                return formatted_text + '\n\n'

            elif node_type == 'list':
                result = []
                ordered = node.get('ordered', False)
                start = node.get('start', 1)

                for i, item in enumerate(node.get('children', [])):
                    if item.get('type') == 'list_item':
                        node_key = self._get_node_key(item)
                        translation = translation_map.get(node_key, {'text': self._extract_text_with_formatting(item)['text']})
                        formatted_text = self._apply_formatting_to_text(translation['text'], translation.get('formatting', []))

                        if ordered:
                            prefix = f"{start + i}. "
                        else:
                            prefix = "- "

                        result.append(prefix + formatted_text)

                return '\n'.join(result) + '\n\n'

            elif node_type == 'block_code':
                lang = node.get('lang', '')
                # 对于代码块，总是使用原始内容，不进行翻译
                code = node.get('text', '')
                return f"```{lang}\n{code}\n```\n\n"

            elif node_type == 'block_quote':
                node_key = self._get_node_key(node)
                translation = translation_map.get(node_key, {'text': self._extract_text_with_formatting(node)['text']})
                formatted_text = self._apply_formatting_to_text(translation['text'], translation.get('formatting', []))
                lines = formatted_text.split('\n')
                quoted_lines = ['> ' + line for line in lines]
                return '\n'.join(quoted_lines) + '\n\n'

            elif node_type == 'table':
                # 表格重建比较复杂，这里简化处理
                header = node.get('header', [])
                rows = node.get('children', [])

                # 重建表头
                header_row = '| ' + ' | '.join([
                    self._apply_formatting_to_text(
                        translation_map.get(self._get_node_key(cell), {'text': self._extract_text_with_formatting(cell)['text']})['text'],
                        translation_map.get(self._get_node_key(cell), {}).get('formatting', [])
                    )
                    for cell in header
                ]) + ' |'

                # 分隔行
                separator = '| ' + ' | '.join(['---'] * len(header)) + ' |'

                # 数据行
                data_rows = []
                for row in rows:
                    data_row = '| ' + ' | '.join([
                        self._apply_formatting_to_text(
                            translation_map.get(self._get_node_key(cell), {'text': self._extract_text_with_formatting(cell)['text']})['text'],
                            translation_map.get(self._get_node_key(cell), {}).get('formatting', [])
                        )
                        for cell in row.get('children', [])
                    ]) + ' |'
                    data_rows.append(data_row)

                return '\n'.join([header_row, separator] + data_rows) + '\n\n'

            else:
                # 其他节点类型，递归处理
                result = []
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        result.append(self._rebuild_from_ast_with_formatting(value, translation_map))
                return '\n'.join(result)

        elif isinstance(node, list):
            result = []
            for item in node:
                result.append(self._rebuild_from_ast_with_formatting(item, translation_map))
            return '\n'.join(result)

        return ''

    def _apply_formatting_to_text(self, text: str, formatting: List[Any]) -> str:
        """将格式信息应用到文本，正确处理分段格式"""
        if not formatting:
            return text

        # 如果格式信息是单个格式项
        if len(formatting) == 1:
            single_format = formatting[0]

            # 处理字符串格式
            if isinstance(single_format, str):
                if single_format == 'strong':
                    return f'**{text}**'
                elif single_format == 'emph':
                    return f'*{text}*'
                elif single_format == 'codespan':
                    return f'`{text}`'
                elif single_format.startswith('link:'):
                    return f'[{text}]({single_format[5:]})'

            # 处理列表格式（嵌套格式）
            elif isinstance(single_format, list):
                # 递归处理嵌套格式
                result = self._apply_formatting_to_text(text, single_format)
                # 如果递归处理没有改变文本，可能是链接格式的特殊情况
                if result == text:
                    # 检查是否是链接格式
                    for item in single_format:
                        if isinstance(item, str) and item.startswith('link:'):
                            return f'[{text}]({item[5:]})'
                return result

        # 对于复杂的格式序列，需要分段处理
        if isinstance(formatting, list) and len(formatting) > 1:
            # 分割文本为段落
            text_segments = text.split(' ')

            # 如果格式序列长度与文本段数匹配，则逐段应用格式
            if len(formatting) == len(text_segments):
                formatted_segments = []
                for i, (segment, fmt) in enumerate(zip(text_segments, formatting)):
                    if fmt:  # 如果有格式
                        formatted_segment = self._apply_formatting_to_text(segment, fmt)
                        formatted_segments.append(formatted_segment)
                    else:  # 没有格式
                        formatted_segments.append(segment)
                return ' '.join(formatted_segments)
            else:
                # 格式序列与文本段数不匹配，使用简化处理
                # 检查是否有内联格式，但只应用最内层的格式
                has_strong = any('strong' in str(fmt) for fmt in formatting if isinstance(fmt, (str, list)))
                has_emph = any('emph' in str(fmt) for fmt in formatting if isinstance(fmt, (str, list)))
                has_codespan = any('codespan' in str(fmt) for fmt in formatting if isinstance(fmt, (str, list)))
                has_link = any('link:' in str(fmt) for fmt in formatting if isinstance(fmt, (str, list)))

                # 应用检测到的格式，但避免多重嵌套
                # 优先处理代码格式，然后是粗体和斜体，最后是链接
                if has_codespan:
                    text = f'`{text}`'
                elif has_strong:
                    text = f'**{text}**'
                elif has_emph:
                    text = f'*{text}*'
                elif has_link:
                    # 提取链接URL
                    link_url = None
                    for fmt in formatting:
                        if isinstance(fmt, str) and fmt.startswith('link:'):
                            link_url = fmt[5:]
                            break
                        elif isinstance(fmt, list):
                            # 在嵌套列表中查找链接
                            for sub_fmt in fmt:
                                if isinstance(sub_fmt, str) and sub_fmt.startswith('link:'):
                                    link_url = sub_fmt[5:]
                                    break
                            if link_url:
                                break
                    if link_url:
                        text = f'[{text}]({link_url})'

        return text

    def get_translatable_nodes(self) -> List[Dict[str, Any]]:
        """获取可翻译节点列表"""
        return self.translatable_nodes

    def get_document_summary(self) -> Dict[str, Any]:
        """获取文档摘要信息"""
        return {
            'total_nodes': len(self.translatable_nodes),
            'structure': self._analyze_structure(),
            'metadata': self._extract_metadata()
        }