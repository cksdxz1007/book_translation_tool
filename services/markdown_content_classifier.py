"""
Markdown内容分类器
智能识别和分类Markdown内容，决定哪些内容需要翻译
"""
import re
import logging
from typing import List, Dict, Any, Set

logger = logging.getLogger(__name__)

class MarkdownContentClassifier:
    """Markdown内容分类器"""

    def __init__(self):
        # 代码块模式
        self.code_block_pattern = re.compile(r'```[\s\S]*?```', re.MULTILINE)
        self.inline_code_pattern = re.compile(r'`[^`]+`')

        # URL模式
        self.url_pattern = re.compile(r'https?://[^\s\n]+')
        self.markdown_link_pattern = re.compile(r'\[[^\]]+\]\([^)]+\)')

        # 图片模式
        self.image_pattern = re.compile(r'!\[[^\]]*\]\([^)]+\)')

        # 技术术语模式
        self.technical_terms = {
            'Kubernetes', 'Docker', 'kubectl', 'minikube', 'k3s', 'Helm', 'Portainer',
            'API', 'HTTP', 'JSON', 'XML', 'YAML', 'CLI', 'GUI', 'SSH', 'SSL', 'TLS',
            'DNS', 'IP', 'TCP', 'UDP', 'REST', 'GraphQL', 'WebSocket', 'WebRTC',
            'JavaScript', 'TypeScript', 'Python', 'Java', 'Go', 'Rust', 'C++', 'C#',
            'React', 'Vue', 'Angular', 'Node.js', 'Express', 'Django', 'Flask',
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch', 'Kafka',
            'AWS', 'Azure', 'GCP', 'Kubernetes', 'Docker', 'Terraform', 'Ansible'
        }

    def classify_content(self, markdown_content: str) -> Dict[str, Any]:
        """
        分类Markdown内容

        Args:
            markdown_content: Markdown内容

        Returns:
            分类结果
        """
        try:
            logger.info("开始分类Markdown内容")

            classification = {
                'translatable_sections': [],
                'non_translatable_sections': [],
                'selective_translation_sections': [],
                'structure_summary': self._analyze_structure(markdown_content)
            }

            # 分割内容为段落
            sections = self._split_into_sections(markdown_content)

            for section in sections:
                section_type = self._classify_section(section)

                if section_type == 'non_translatable':
                    classification['non_translatable_sections'].append(section)
                elif section_type == 'selective_translation':
                    classification['selective_translation_sections'].append(section)
                else:
                    classification['translatable_sections'].append(section)

            logger.info(f"分类完成: 可翻译 {len(classification['translatable_sections'])} 个段落, "
                       f"不可翻译 {len(classification['non_translatable_sections'])} 个段落, "
                       f"选择性翻译 {len(classification['selective_translation_sections'])} 个段落")

            return classification

        except Exception as e:
            logger.error(f"分类Markdown内容失败: {e}")
            # 失败时将所有内容标记为可翻译
            return {
                'translatable_sections': [markdown_content],
                'non_translatable_sections': [],
                'selective_translation_sections': [],
                'structure_summary': {}
            }

    def _split_into_sections(self, content: str) -> List[str]:
        """将内容分割为段落"""
        # 按空行分割
        sections = re.split(r'\n\s*\n', content.strip())

        # 过滤空段落
        sections = [section.strip() for section in sections if section.strip()]

        return sections

    def _classify_section(self, section: str) -> str:
        """分类单个段落"""
        # 检查是否为代码块
        if self.code_block_pattern.search(section):
            return 'non_translatable'

        # 检查是否为纯代码行
        if self._is_pure_code(section):
            return 'non_translatable'

        # 检查是否包含大量内联代码
        inline_code_count = len(self.inline_code_pattern.findall(section))
        if inline_code_count > 2:
            return 'selective_translation'

        # 检查是否包含URL或链接
        if self.url_pattern.search(section) or self.markdown_link_pattern.search(section):
            return 'selective_translation'

        # 检查是否包含图片
        if self.image_pattern.search(section):
            return 'selective_translation'

        # 检查是否包含大量技术术语
        if self._has_many_technical_terms(section):
            return 'selective_translation'

        # 默认可翻译
        return 'translatable'

    def _is_pure_code(self, section: str) -> bool:
        """检查是否为纯代码"""
        lines = section.split('\n')

        # 如果段落以代码块开始和结束
        if section.strip().startswith('```') and section.strip().endswith('```'):
            return True

        # 如果大部分行看起来像代码
        code_like_lines = 0
        for line in lines:
            if self._looks_like_code(line):
                code_like_lines += 1

        return code_like_lines / len(lines) > 0.7

    def _looks_like_code(self, line: str) -> bool:
        """检查行是否看起来像代码"""
        line = line.strip()

        # 空行
        if not line:
            return False

        # 代码特征
        code_indicators = [
            # 编程语言关键字
            r'\b(if|else|for|while|def|class|import|from|return|function|var|let|const)\b',
            # 赋值操作
            r'\w+\s*=\s*[^\s]',
            # 函数调用
            r'\w+\s*\([^)]*\)',
            # 注释
            r'^\s*(#|//|\*|--)',
            # 缩进
            r'^\s{4,}\S',
            # 特殊字符
            r'[{}[\];,<>]'
        ]

        for pattern in code_indicators:
            if re.search(pattern, line):
                return True

        return False

    def _has_many_technical_terms(self, section: str) -> bool:
        """检查是否包含大量技术术语"""
        words = re.findall(r'\b\w+\b', section)

        if not words:
            return False

        technical_word_count = sum(1 for word in words if word in self.technical_terms)

        # 如果超过20%的单词是技术术语
        return technical_word_count / len(words) > 0.2

    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """分析文档结构"""
        structure = {
            'total_lines': len(content.split('\n')),
            'code_blocks': len(self.code_block_pattern.findall(content)),
            'inline_code': len(self.inline_code_pattern.findall(content)),
            'links': len(self.markdown_link_pattern.findall(content)),
            'images': len(self.image_pattern.findall(content)),
            'urls': len(self.url_pattern.findall(content)),
            'headings': len(re.findall(r'^#+\s+', content, re.MULTILINE))
        }

        return structure

    def create_translation_plan(self, classification: Dict[str, Any]) -> Dict[str, Any]:
        """创建翻译计划"""
        plan = {
            'total_sections': len(classification['translatable_sections']) +
                            len(classification['non_translatable_sections']) +
                            len(classification['selective_translation_sections']),
            'translation_strategy': {},
            'recommendations': []
        }

        # 翻译策略
        if classification['non_translatable_sections']:
            plan['translation_strategy']['preserve_code_blocks'] = True
            plan['recommendations'].append('代码块将完全保留，不进行翻译')

        if classification['selective_translation_sections']:
            plan['translation_strategy']['selective_translation'] = True
            plan['recommendations'].append('包含技术术语和链接的内容将进行选择性翻译')

        if classification['translatable_sections']:
            plan['translation_strategy']['full_translation'] = True
            plan['recommendations'].append('普通文本内容将进行完整翻译')

        # 性能预估
        translatable_ratio = len(classification['translatable_sections']) / plan['total_sections'] if plan['total_sections'] > 0 else 0
        plan['estimated_translation_ratio'] = round(translatable_ratio * 100, 1)

        return plan

def create_markdown_classifier() -> MarkdownContentClassifier:
    """创建Markdown分类器实例"""
    return MarkdownContentClassifier()