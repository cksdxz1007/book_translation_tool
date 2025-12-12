"""
增强的ePub生成器
用于生成格式保留的翻译后ePub文件
"""
import os
import logging
import ebooklib
from ebooklib import epub
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class EnhancedEpubGenerator:
    """增强的ePub生成器"""

    def __init__(self):
        self.book = None

    def create_epub_from_translated_content(self, original_book: epub.EpubBook,
                                          translated_content: Dict[str, Any],
                                          output_path: str) -> bool:
        """
        从翻译后的内容创建ePub文件

        Args:
            original_book: 原始ePub书籍对象
            translated_content: 翻译后的内容
            output_path: 输出文件路径

        Returns:
            是否成功
        """
        try:
            logger.info("开始创建翻译后的ePub文件")

            # 创建新的ePub书籍
            self.book = epub.EpubBook()

            # 复制元数据
            self._copy_metadata(original_book)

            # 处理翻译后的章节
            chapters = translated_content.get('chapters', [])
            spine_items = []
            toc_items = []

            for chapter_info in chapters:
                chapter_file = self._create_translated_chapter(chapter_info)
                if chapter_file:
                    self.book.add_item(chapter_file)
                    spine_items.append(chapter_file)
                    toc_items.append(epub.Link(chapter_file.file_name, chapter_info.get('title', 'Chapter'), chapter_file.id))

            # 设置书籍结构
            self.book.spine = spine_items
            self.book.toc = toc_items

            # 添加导航
            self.book.add_item(epub.EpubNcx())
            self.book.add_item(epub.EpubNav())

            # 写入文件
            epub.write_epub(output_path, self.book, {})

            logger.info(f"翻译后的ePub文件已创建: {output_path}")
            return True

        except Exception as e:
            logger.error(f"创建翻译后的ePub文件失败: {e}")
            return False

    def _copy_metadata(self, original_book: epub.EpubBook):
        """复制元数据"""
        try:
            # 复制基本元数据
            if original_book.title:
                self.book.set_title(original_book.title)

            if original_book.language:
                self.book.set_language(original_book.language)

            # 复制作者信息
            for author in original_book.authors:
                self.book.add_author(author[0])

            # 复制其他元数据
            for key, value in original_book.metadata.items():
                for meta in value:
                    self.book.add_metadata('DC', key, meta[0])

        except Exception as e:
            logger.warning(f"复制元数据时出错: {e}")

    def _create_translated_chapter(self, chapter_info: Dict[str, Any]) -> Optional[epub.EpubHtml]:
        """
        创建翻译后的章节

        Args:
            chapter_info: 章节信息

        Returns:
            ePub章节对象
        """
        try:
            chapter_id = chapter_info.get('id', f"chapter_{len(self.book.items) + 1}")
            chapter_title = chapter_info.get('title', 'Untitled')
            chapter_content = chapter_info.get('content', '')

            # 创建章节
            chapter = epub.EpubHtml(
                title=chapter_title,
                file_name=f'{chapter_id}.xhtml',
                lang='en'  # 假设翻译为英文
            )

            # 构建章节内容
            html_content = self._build_chapter_html(chapter_title, chapter_content)
            chapter.content = html_content.encode('utf-8')

            return chapter

        except Exception as e:
            logger.error(f"创建翻译章节失败: {e}")
            return None

    def _build_chapter_html(self, title: str, content: str) -> str:
        """
        构建章节HTML内容

        Args:
            title: 章节标题
            content: 章节内容

        Returns:
            HTML内容
        """
        html_template = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
  "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>{title}</title>
<style type="text/css">
body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
h1 {{ color: #333; border-bottom: 1px solid #ccc; }}
p {{ margin-bottom: 1em; }}
</style>
</head>
<body>
<h1>{title}</h1>
{content}
</body>
</html>"""

        # 将Markdown内容转换为HTML（简化处理）
        html_content = content.replace('\n', '<br/>')

        return html_template.format(title=title, content=html_content)

    def generate_epub_preview(self, translated_content: Dict[str, Any],
                            output_path: str) -> bool:
        """
        生成ePub预览文件

        Args:
            translated_content: 翻译后的内容
            output_path: 输出文件路径

        Returns:
            是否成功
        """
        try:
            logger.info("开始生成ePub预览文件")

            # 创建预览ePub
            self.book = epub.EpubBook()

            # 设置基本元数据
            self.book.set_title("Translated Book Preview")
            self.book.set_language("en")
            self.book.add_author("Translation System")

            # 添加章节
            chapters = translated_content.get('chapters', [])
            spine_items = []
            toc_items = []

            for i, chapter_info in enumerate(chapters):
                chapter_file = self._create_preview_chapter(chapter_info, i)
                if chapter_file:
                    self.book.add_item(chapter_file)
                    spine_items.append(chapter_file)
                    toc_items.append(epub.Link(chapter_file.file_name, chapter_info.get('title', f'Chapter {i+1}'), chapter_file.id))

            # 设置书籍结构
            self.book.spine = spine_items
            self.book.toc = toc_items

            # 添加导航
            self.book.add_item(epub.EpubNcx())
            self.book.add_item(epub.EpubNav())

            # 写入文件
            epub.write_epub(output_path, self.book, {})

            logger.info(f"ePub预览文件已创建: {output_path}")
            return True

        except Exception as e:
            logger.error(f"生成ePub预览文件失败: {e}")
            return False

    def _create_preview_chapter(self, chapter_info: Dict[str, Any], index: int) -> Optional[epub.EpubHtml]:
        """
        创建预览章节

        Args:
            chapter_info: 章节信息
            index: 章节索引

        Returns:
            ePub章节对象
        """
        try:
            chapter_id = f"chapter_{index + 1}"
            chapter_title = chapter_info.get('title', f'Chapter {index + 1}')
            chapter_content = chapter_info.get('content', '')

            # 创建章节
            chapter = epub.EpubHtml(
                title=chapter_title,
                file_name=f'{chapter_id}.xhtml',
                lang='en'
            )

            # 构建章节内容
            html_content = self._build_preview_html(chapter_title, chapter_content)
            chapter.content = html_content.encode('utf-8')

            return chapter

        except Exception as e:
            logger.error(f"创建预览章节失败: {e}")
            return None

    def _build_preview_html(self, title: str, content: str) -> str:
        """
        构建预览章节HTML内容

        Args:
            title: 章节标题
            content: 章节内容

        Returns:
            HTML内容
        """
        html_template = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
  "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>{title}</title>
<style type="text/css">
body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
p {{ margin-bottom: 1em; }}
.preview-note {{ background-color: #f8f9fa; padding: 10px; border-left: 4px solid #3498db; margin: 10px 0; }}
</style>
</head>
<body>
<div class="preview-note">
<strong>Preview Note:</strong> This is a preview of the translated content.
</div>
<h1>{title}</h1>
{content}
</body>
</html>"""

        # 将Markdown内容转换为HTML（简化处理）
        html_content = content.replace('\n', '<br/>')

        return html_template.format(title=title, content=html_content)