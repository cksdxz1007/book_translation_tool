"""
Markdown翻译验证器
验证翻译后的Markdown内容质量，确保格式保留和翻译质量
"""
import re
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class MarkdownTranslationValidator:
    """Markdown翻译验证器"""

    def __init__(self):
        # 代码块模式
        self.code_block_pattern = re.compile(r'```[\s\S]*?```', re.MULTILINE)
        self.inline_code_pattern = re.compile(r'`[^`]+`')

        # 链接和图片模式
        self.link_pattern = re.compile(r'\[[^\]]+\]\([^)]+\)')
        self.image_pattern = re.compile(r'!\[[^\]]*\]\([^)]+\)')

        # 标题模式
        self.heading_pattern = re.compile(r'^#+\s+', re.MULTILINE)

        # 列表模式
        self.list_pattern = re.compile(r'^\s*[-*+]\s+', re.MULTILINE)
        self.ordered_list_pattern = re.compile(r'^\s*\d+\.\s+', re.MULTILINE)

    def validate_translation(self, original_content: str, translated_content: str) -> Dict[str, Any]:
        """
        验证翻译质量

        Args:
            original_content: 原始Markdown内容
            translated_content: 翻译后的Markdown内容

        Returns:
            验证结果
        """
        try:
            logger.info("开始验证Markdown翻译质量")

            validation_result = {
                'overall_score': 0,
                'format_preservation_score': 0,
                'translation_quality_score': 0,
                'issues': [],
                'warnings': [],
                'successes': []
            }

            # 验证格式保留
            format_validation = self._validate_format_preservation(original_content, translated_content)
            validation_result['format_preservation_score'] = format_validation['score']
            validation_result['issues'].extend(format_validation['issues'])
            validation_result['warnings'].extend(format_validation['warnings'])
            validation_result['successes'].extend(format_validation['successes'])

            # 验证翻译质量
            translation_validation = self._validate_translation_quality(original_content, translated_content)
            validation_result['translation_quality_score'] = translation_validation['score']
            validation_result['issues'].extend(translation_validation['issues'])
            validation_result['warnings'].extend(translation_validation['warnings'])
            validation_result['successes'].extend(translation_validation['successes'])

            # 计算总体分数
            validation_result['overall_score'] = (
                validation_result['format_preservation_score'] * 0.6 +
                validation_result['translation_quality_score'] * 0.4
            )

            logger.info(f"验证完成: 总体分数 {validation_result['overall_score']:.1f}/10")
            return validation_result

        except Exception as e:
            logger.error(f"验证Markdown翻译失败: {e}")
            return {
                'overall_score': 0,
                'format_preservation_score': 0,
                'translation_quality_score': 0,
                'issues': [f"验证过程出错: {str(e)}"],
                'warnings': [],
                'successes': []
            }

    def _validate_format_preservation(self, original: str, translated: str) -> Dict[str, Any]:
        """验证格式保留情况"""
        result = {
            'score': 10,  # 满分10分
            'issues': [],
            'warnings': [],
            'successes': []
        }

        # 检查代码块数量
        original_code_blocks = len(self.code_block_pattern.findall(original))
        translated_code_blocks = len(self.code_block_pattern.findall(translated))

        if original_code_blocks != translated_code_blocks:
            result['score'] -= 3
            result['issues'].append(f"代码块数量不匹配: 原始 {original_code_blocks} 个，翻译后 {translated_code_blocks} 个")
        else:
            result['successes'].append(f"代码块数量匹配: {original_code_blocks} 个")

        # 检查内联代码
        original_inline_code = len(self.inline_code_pattern.findall(original))
        translated_inline_code = len(self.inline_code_pattern.findall(translated))

        if original_inline_code != translated_inline_code:
            result['score'] -= 1
            result['warnings'].append(f"内联代码数量不匹配: 原始 {original_inline_code} 个，翻译后 {translated_inline_code} 个")
        else:
            result['successes'].append(f"内联代码数量匹配: {original_inline_code} 个")

        # 检查链接
        original_links = len(self.link_pattern.findall(original))
        translated_links = len(self.link_pattern.findall(translated))

        if original_links != translated_links:
            result['score'] -= 1
            result['warnings'].append(f"链接数量不匹配: 原始 {original_links} 个，翻译后 {translated_links} 个")
        else:
            result['successes'].append(f"链接数量匹配: {original_links} 个")

        # 检查图片
        original_images = len(self.image_pattern.findall(original))
        translated_images = len(self.image_pattern.findall(translated))

        if original_images != translated_images:
            result['score'] -= 1
            result['warnings'].append(f"图片数量不匹配: 原始 {original_images} 个，翻译后 {translated_images} 个")
        else:
            result['successes'].append(f"图片数量匹配: {original_images} 个")

        # 检查标题层级
        original_headings = len(self.heading_pattern.findall(original))
        translated_headings = len(self.heading_pattern.findall(translated))

        if original_headings != translated_headings:
            result['score'] -= 1
            result['warnings'].append(f"标题数量不匹配: 原始 {original_headings} 个，翻译后 {translated_headings} 个")
        else:
            result['successes'].append(f"标题数量匹配: {original_headings} 个")

        # 确保分数不低于0
        result['score'] = max(0, result['score'])

        return result

    def _validate_translation_quality(self, original: str, translated: str) -> Dict[str, Any]:
        """验证翻译质量"""
        result = {
            'score': 10,  # 满分10分
            'issues': [],
            'warnings': [],
            'successes': []
        }

        # 基本检查
        if not translated.strip():
            result['score'] = 0
            result['issues'].append("翻译内容为空")
            return result

        # 检查翻译长度（粗略估计）
        original_length = len(original.strip())
        translated_length = len(translated.strip())

        if original_length == 0:
            result['successes'].append("原始内容为空，跳过长度检查")
        else:
            length_ratio = translated_length / original_length

            # 对于中文翻译，通常长度会变短
            if length_ratio < 0.3:
                result['score'] -= 3
                result['issues'].append(f"翻译内容过短: 长度比 {length_ratio:.2f}")
            elif length_ratio < 0.5:
                result['score'] -= 1
                result['warnings'].append(f"翻译内容较短: 长度比 {length_ratio:.2f}")
            elif length_ratio > 2.0:
                result['score'] -= 2
                result['issues'].append(f"翻译内容过长: 长度比 {length_ratio:.2f}")
            else:
                result['successes'].append(f"翻译长度合适: 长度比 {length_ratio:.2f}")

        # 检查常见翻译问题
        common_issues = self._check_common_issues(translated)
        if common_issues:
            result['score'] -= len(common_issues)
            result['issues'].extend(common_issues)

        # 检查代码块内容是否被翻译
        code_issues = self._check_code_block_translation(original, translated)
        if code_issues:
            result['score'] -= len(code_issues) * 2  # 代码翻译是严重问题
            result['issues'].extend(code_issues)

        # 确保分数不低于0
        result['score'] = max(0, result['score'])

        return result

    def _check_common_issues(self, translated: str) -> List[str]:
        """检查常见翻译问题"""
        issues = []

        # 检查翻译注释
        if '（注：' in translated or '(Note:' in translated:
            issues.append("翻译包含不必要的注释")

        # 检查翻译说明
        if '根据翻译准则' in translated or '由于原文' in translated:
            issues.append("翻译包含不必要的说明")

        # 检查未完成的翻译标记
        if '[ERROR:' in translated or '[CHUNK' in translated:
            issues.append("翻译包含错误标记")

        return issues

    def _check_code_block_translation(self, original: str, translated: str) -> List[str]:
        """检查代码块是否被错误翻译"""
        issues = []

        # 提取原始代码块
        original_blocks = self.code_block_pattern.findall(original)
        translated_blocks = self.code_block_pattern.findall(translated)

        # 如果代码块数量相同，检查内容
        if len(original_blocks) == len(translated_blocks):
            for i, (orig_block, trans_block) in enumerate(zip(original_blocks, translated_blocks)):
                # 检查代码块内容是否相同
                if orig_block != trans_block:
                    issues.append(f"代码块 {i+1} 内容被修改")

        return issues

    def generate_validation_report(self, validation_result: Dict[str, Any]) -> str:
        """生成验证报告"""
        report = []
        report.append("# Markdown翻译验证报告")
        report.append("")

        # 总体评分
        overall_score = validation_result['overall_score']
        report.append(f"## 总体评分: {overall_score:.1f}/10")

        if overall_score >= 8:
            report.append("✅ **优秀** - 翻译质量很高")
        elif overall_score >= 6:
            report.append("⚠️ **良好** - 翻译质量可以接受")
        elif overall_score >= 4:
            report.append("⚠️ **一般** - 存在一些问题")
        else:
            report.append("❌ **较差** - 需要重新翻译")

        report.append("")

        # 详细分数
        report.append("## 详细分数")
        report.append(f"- 格式保留分数: {validation_result['format_preservation_score']:.1f}/10")
        report.append(f"- 翻译质量分数: {validation_result['translation_quality_score']:.1f}/10")
        report.append("")

        # 问题列表
        if validation_result['issues']:
            report.append("## ❌ 严重问题")
            for issue in validation_result['issues']:
                report.append(f"- {issue}")
            report.append("")

        # 警告列表
        if validation_result['warnings']:
            report.append("## ⚠️ 警告")
            for warning in validation_result['warnings']:
                report.append(f"- {warning}")
            report.append("")

        # 成功项
        if validation_result['successes']:
            report.append("## ✅ 成功项")
            for success in validation_result['successes']:
                report.append(f"- {success}")

        return '\n'.join(report)

def create_markdown_validator() -> MarkdownTranslationValidator:
    """创建Markdown验证器实例"""
    return MarkdownTranslationValidator()