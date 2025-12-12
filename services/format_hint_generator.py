"""
格式提示生成器
为翻译生成格式提示和上下文信息，提高翻译质量
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class FormatHintGenerator:
    """格式提示生成器，为翻译提供上下文和格式约束"""

    def __init__(self):
        self.format_hints = []

    def generate_translation_hints(self, content_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为翻译生成格式提示"""
        try:
            logger.info("开始生成翻译格式提示")

            hints = []
            for i, chunk in enumerate(content_chunks):
                hint = {
                    'text': chunk['text'],
                    'type': chunk['type'],
                    'context': self._build_context_hint(chunk, i, content_chunks),
                    'format_constraints': self._get_format_constraints(chunk),
                    'translation_guidelines': self._get_translation_guidelines(chunk),
                    'position_info': self._get_position_info(chunk, i, len(content_chunks))
                }
                hints.append(hint)

            logger.info(f"生成格式提示完成，共 {len(hints)} 个提示")
            return hints

        except Exception as e:
            logger.error(f"生成格式提示失败: {e}")
            return []

    def _build_context_hint(self, chunk: Dict[str, Any], index: int, all_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建上下文提示"""
        context = {
            'current_chunk': {
                'type': chunk['type'],
                'text': chunk['text'],
                'index': index
            },
            'surrounding_context': self._get_surrounding_context(index, all_chunks),
            'structural_context': self._get_structural_context(chunk)
        }

        # 添加特定类型的上下文信息
        if chunk['type'] == 'heading':
            context['heading_info'] = {
                'level': chunk.get('level', 1),
                'is_main_title': chunk.get('level', 1) == 1,
                'heading_hierarchy': self._get_heading_hierarchy(index, all_chunks)
            }

        elif chunk['type'] == 'list_item':
            context['list_info'] = {
                'list_type': chunk.get('list_type', 'unordered'),
                'item_index': self._get_list_item_index(index, all_chunks),
                'is_nested': chunk.get('is_nested', False)
            }

        elif chunk['type'] in ['table_header', 'table_cell']:
            context['table_info'] = {
                'table_position': chunk.get('table_position', {}),
                'is_header': chunk['type'] == 'table_header',
                'column_index': chunk.get('column_index', 0)
            }

        elif chunk['type'] == 'quote':
            context['quote_info'] = {
                'source': chunk.get('source', ''),
                'is_block_quote': True
            }

        return context

    def _get_surrounding_context(self, index: int, all_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取周围上下文"""
        surrounding = {
            'previous': None,
            'next': None
        }

        if index > 0:
            prev_chunk = all_chunks[index - 1]
            surrounding['previous'] = {
                'type': prev_chunk['type'],
                'text': prev_chunk['text'][:100] + '...' if len(prev_chunk['text']) > 100 else prev_chunk['text']
            }

        if index < len(all_chunks) - 1:
            next_chunk = all_chunks[index + 1]
            surrounding['next'] = {
                'type': next_chunk['type'],
                'text': next_chunk['text'][:100] + '...' if len(next_chunk['text']) > 100 else next_chunk['text']
            }

        return surrounding

    def _get_structural_context(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """获取结构上下文"""
        structural = {
            'document_section': self._identify_document_section(chunk),
            'nesting_level': chunk.get('nesting_level', 0),
            'parent_elements': chunk.get('parent_elements', []),
            'sibling_count': chunk.get('sibling_count', 0)
        }

        # 根据类型添加特定结构信息
        if chunk['type'] == 'heading':
            structural['heading_role'] = self._identify_heading_role(chunk)

        elif chunk['type'] in ['list_item', 'ordered_list']:
            structural['list_structure'] = {
                'item_count': chunk.get('item_count', 0),
                'has_nested_lists': chunk.get('has_nested_lists', False)
            }

        return structural

    def _identify_document_section(self, chunk: Dict[str, Any]) -> str:
        """识别文档段落"""
        context = chunk.get('context', {})

        # 根据上下文信息识别段落
        if context.get('in_table'):
            return 'table_content'
        elif context.get('in_code_block'):
            return 'code_block'
        elif chunk['type'] == 'heading':
            level = chunk.get('level', 1)
            if level == 1:
                return 'main_title'
            elif level == 2:
                return 'section_title'
            else:
                return 'subsection_title'
        elif chunk['type'] == 'quote':
            return 'quotation'
        elif chunk['type'] in ['list_item', 'ordered_list']:
            return 'list_content'
        else:
            return 'body_content'

    def _identify_heading_role(self, chunk: Dict[str, Any]) -> str:
        """识别标题角色"""
        text = chunk['text'].lower()

        # 常见标题类型识别
        if any(word in text for word in ['introduction', '前言', '介绍']):
            return 'introduction'
        elif any(word in text for word in ['conclusion', '总结', '结论']):
            return 'conclusion'
        elif any(word in text for word in ['abstract', '摘要']):
            return 'abstract'
        elif any(word in text for word in ['references', '参考文献', '参考']):
            return 'references'
        elif any(word in text for word in ['appendix', '附录']):
            return 'appendix'
        elif any(word in text for word in ['chapter', '章节', '第']):
            return 'chapter_title'
        else:
            return 'section_title'

    def _get_heading_hierarchy(self, index: int, all_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """获取标题层次结构"""
        hierarchy = []
        current_level = all_chunks[index].get('level', 1)

        # 向前查找上级标题
        for i in range(index - 1, -1, -1):
            chunk = all_chunks[i]
            if chunk['type'] == 'heading':
                chunk_level = chunk.get('level', 1)
                if chunk_level < current_level:
                    hierarchy.insert(0, {
                        'level': chunk_level,
                        'text': chunk['text']
                    })
                    current_level = chunk_level

        return hierarchy

    def _get_list_item_index(self, index: int, all_chunks: List[Dict[str, Any]]) -> int:
        """获取列表项索引"""
        item_index = 1

        # 向后查找同一列表中的项目
        for i in range(index - 1, -1, -1):
            chunk = all_chunks[i]
            if chunk['type'] == 'list_item':
                item_index += 1
            else:
                break

        return item_index

    def _get_format_constraints(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """获取格式约束"""
        constraints = {
            'length_guidance': self._get_length_guidance(chunk),
            'style_requirements': self._get_style_requirements(chunk),
            'special_characters': self._get_special_characters_info(chunk),
            'preservation_rules': self._get_preservation_rules(chunk)
        }

        return constraints

    def _get_length_guidance(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """获取长度指导"""
        text_length = len(chunk['text'])
        chunk_type = chunk['type']

        guidance = {
            'original_length': text_length,
            'recommended_range': None,
            'expansion_factor': 1.0
        }

        # 根据内容类型设置推荐长度范围
        if chunk_type == 'heading':
            guidance['recommended_range'] = (text_length * 0.8, text_length * 1.5)
            guidance['expansion_factor'] = 1.2
        elif chunk_type in ['table_header', 'table_cell']:
            guidance['recommended_range'] = (text_length * 0.9, text_length * 1.2)
            guidance['expansion_factor'] = 1.1
        elif chunk_type == 'list_item':
            guidance['recommended_range'] = (text_length * 0.8, text_length * 1.4)
            guidance['expansion_factor'] = 1.3
        else:
            guidance['recommended_range'] = (text_length * 0.7, text_length * 1.6)
            guidance['expansion_factor'] = 1.4

        return guidance

    def _get_style_requirements(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """获取样式要求"""
        requirements = {
            'formality_level': self._determine_formality_level(chunk),
            'tone_guidance': self._determine_tone_guidance(chunk),
            'terminology_consistency': self._check_terminology_consistency(chunk),
            'capitalization_rules': self._get_capitalization_rules(chunk)
        }

        return requirements

    def _determine_formality_level(self, chunk: Dict[str, Any]) -> str:
        """确定正式程度"""
        context = chunk.get('context', {})
        chunk_type = chunk['type']

        if chunk_type in ['heading', 'table_header']:
            return 'formal'
        elif context.get('in_table') or context.get('in_code_block'):
            return 'technical'
        elif chunk_type == 'quote':
            return 'literary'
        else:
            return 'neutral'

    def _determine_tone_guidance(self, chunk: Dict[str, Any]) -> List[str]:
        """确定语气指导"""
        guidance = []

        if chunk['type'] == 'heading':
            guidance.extend(['concise', 'clear', 'descriptive'])
        elif chunk['type'] in ['table_header', 'table_cell']:
            guidance.extend(['precise', 'consistent', 'brief'])
        elif chunk['type'] == 'quote':
            guidance.extend(['faithful', 'literary', 'expressive'])
        else:
            guidance.extend(['natural', 'readable', 'context_appropriate'])

        return guidance

    def _check_terminology_consistency(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """检查术语一致性"""
        # 这里可以集成术语库检查
        return {
            'has_technical_terms': self._has_technical_terms(chunk['text']),
            'potential_terminology': self._extract_potential_terminology(chunk['text']),
            'consistency_check': 'recommended'
        }

    def _has_technical_terms(self, text: str) -> bool:
        """检查是否包含技术术语"""
        # 简单的技术术语检测
        technical_indicators = ['API', 'HTTP', 'JSON', 'XML', 'database', 'algorithm', 'protocol']
        return any(term.lower() in text.lower() for term in technical_indicators)

    def _extract_potential_terminology(self, text: str) -> List[str]:
        """提取潜在术语"""
        # 简单的术语提取逻辑
        words = text.split()
        potential_terms = []

        for word in words:
            # 识别大写字母组合、带连字符的词等
            if (word.isupper() and len(word) > 1) or '-' in word:
                potential_terms.append(word)

        return potential_terms

    def _get_capitalization_rules(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """获取大小写规则"""
        rules = {
            'original_capitalization': self._analyze_capitalization(chunk['text']),
            'recommended_style': 'preserve_original'
        }

        if chunk['type'] == 'heading':
            rules['recommended_style'] = 'title_case'
        elif chunk['type'] in ['table_header']:
            rules['recommended_style'] = 'sentence_case'

        return rules

    def _analyze_capitalization(self, text: str) -> str:
        """分析大小写风格"""
        if text.isupper():
            return 'all_caps'
        elif text.istitle():
            return 'title_case'
        elif text[0].isupper():
            return 'sentence_case'
        else:
            return 'lower_case'

    def _get_special_characters_info(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """获取特殊字符信息"""
        text = chunk['text']

        return {
            'has_special_chars': any(char in text for char in ['@', '#', '$', '%', '&', '*', '+', '=', '<', '>']),
            'has_math_symbols': any(char in text for char in ['+', '-', '×', '÷', '=', '≠', '≈', '≤', '≥']),
            'has_currency_symbols': any(char in text for char in ['$', '€', '£', '¥', '₹']),
            'preservation_required': True
        }

    def _get_preservation_rules(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """获取保留规则"""
        rules = {
            'preserve_numbers': True,
            'preserve_dates': True,
            'preserve_urls': True,
            'preserve_email_addresses': True,
            'preserve_proper_nouns': True
        }

        return rules

    def _get_translation_guidelines(self, chunk: Dict[str, Any]) -> List[str]:
        """获取翻译指导原则"""
        guidelines = []

        # 通用指导原则
        guidelines.extend([
            '保持原文意思准确',
            '确保翻译自然流畅',
            '考虑目标语言的文化习惯'
        ])

        # 特定类型指导原则
        if chunk['type'] == 'heading':
            guidelines.extend([
                '标题应简洁明了',
                '保持标题的层次感',
                '避免过度翻译'
            ])
        elif chunk['type'] in ['table_header', 'table_cell']:
            guidelines.extend([
                '表格内容应保持对齐',
                '术语翻译要一致',
                '保持表格结构清晰'
            ])
        elif chunk['type'] == 'quote':
            guidelines.extend([
                '保持引文的文学性',
                '忠实于原文风格',
                '适当处理文化差异'
            ])

        return guidelines

    def _get_position_info(self, chunk: Dict[str, Any], index: int, total_chunks: int) -> Dict[str, Any]:
        """获取位置信息"""
        return {
            'chunk_index': index,
            'total_chunks': total_chunks,
            'progress_percentage': round((index + 1) / total_chunks * 100, 1),
            'is_first_chunk': index == 0,
            'is_last_chunk': index == total_chunks - 1
        }