import re
import logging
import mdformat

logger = logging.getLogger(__name__)

def beautify_markdown(markdown_text: str) -> str:
    """
    Cleans up and standardizes a Markdown string using mdformat,
    with special handling for page comments and specific list structures.

    Args:
        markdown_text: The raw Markdown text.

    Returns:
        The beautified Markdown text.
    """
    if not markdown_text:
        return ""

    text = markdown_text

    # 1. Normalize line endings to \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # --- BEGINNING OF CUSTOM LOGIC FOR "专业能力" LISTS ---
    lines = text.split('\n')
    processed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Regex to find lines like "2. 专业能力：" followed by content
        match = re.match(r'^(\d+\.\s*专业能力：)(.*)', line)
        if match:
            leading_part = match.group(1).strip() # e.g., "2. 专业能力："
            content_part = match.group(2).strip() # Content after the colon
            
            processed_lines.append(leading_part) # Add the main title line

            # Split the content by Chinese period "。"
            skills = [skill.strip() for skill in content_part.split('。') if skill.strip()]
            
            if skills:
                # Create a sub-list. mdformat should handle renumbering if number=True.
                # We use "1." for all items; mdformat should renumber them sequentially starting from 1.
                for skill_item in skills:
                    processed_lines.append(f"    1. {skill_item}") # Indent with 4 spaces
            i += 1
        else:
            processed_lines.append(line)
            i += 1
    text = '\n'.join(processed_lines)
    # --- END OF CUSTOM LOGIC FOR "专业能力" LISTS ---

    # 2. Pre-process page comments (before mdformat)
    # Ensure page comments are on their own lines and have appropriate spacing.
    text = re.sub(r'(?<!\n)(<!-- Page \d+ -->)', r'\n\1', text) # Ensure newline before if not present
    text = re.sub(r'(<!-- Page \d+ -->)(?!\n)', r'\1\n', text) # Ensure newline after if not present
    # Ensure one blank line before a page comment if it's not at the start of a line or after another blank line
    text = re.sub(r'(?<!\n\n)([^\n\s])(\n<!-- Page \d+ -->)', r'\1\n\2', text)
    # Ensure one blank line after a page comment if not followed by whitespace or another comment
    text = re.sub(r'(<!-- Page \d+ -->\n)(?!(\s|<!-- Page|\Z))', r'\1\n', text, flags=re.MULTILINE)
    # Collapse multiple blank lines around page comments
    text = re.sub(r'\n{3,}(<!-- Page \d+ -->)', r'\n\n\1', text)
    text = re.sub(r'(<!-- Page \d+ -->)\n{3,}', r'\1\n\n', text)

    # 3. Use mdformat for the main formatting
    try:
        mdformat_options = {
            "number": True,
            "wrap": "no"
        }
        text = mdformat.text(text, options=mdformat_options)
    except Exception as e:
        logger.warning(f"mdformat processing failed: {e}. Proceeding with regex-based beautification for page comments only.")

    # 4. Post-process page comments (after mdformat, as mdformat might change spacing)
    # This re-applies more specific spacing rules for page comments needed by the splitter.
    text = re.sub(r'\n\n(<!-- Page \d+ -->)', r'\n\1', text) # Remove blank line directly before
    text = re.sub(r'(?<!\n)(<!-- Page \d+ -->)', r'\n\1', text) # Ensure on its own line (again)
    text = re.sub(r'(<!-- Page \d+ -->)(?!\n)', r'\1\n', text) # Ensure on its own line (again)
    # Ensure exactly one blank line after, unless followed by another comment or EOF.
    text = re.sub(r'(<!-- Page \d+ -->\n)(?!(\n|<!-- Page|\Z))', r'\1\n', text, flags=re.MULTILINE)
    text = re.sub(r'(<!-- Page \d+ -->\n\n)\n+', r'\1', text, flags=re.MULTILINE) # Remove extra blank lines after

    # 5. Final cleanup: Remove leading/trailing blank lines from the whole document
    text = text.strip('\n')
    if text: # Add a single trailing newline if there's content
        text += '\n'

    return text

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    sample_md_ugly = """
<!-- Page 1 -->
#Header1
Some text immediately after header.
This is a paragraph.   
This is still the same paragraph.

This is another paragraph.


This is a third paragraph with too many newlines before it.
*   List item1 needs space
-List item2 needs space
+ list item3
1.Numbered item needs space

##Header2 with no space
<!-- Page 2 -->
2. 专业能力：熟悉ERP系统的实施管理，有效地将云计算技术并入其中，实现自动化和优化。精通SQL数据库管理和报表开发，有较强的数据技术分析和处理能力。掌握BI及数据仓库系统架构搭建，并熟悉云存储和大数据平台的搭建和管理。
No blank line after this.<!-- Page 3 -->Text after page 3.

<!-- Page 4 -->


Text with too many newlines after page 4.
"""

    print("--- Original Ugly Markdown ---")
    print(sample_md_ugly)
    
    beautified_md = beautify_markdown(sample_md_ugly)
    
    print("\\n--- Beautified Markdown (with mdformat) ---")
    print(beautified_md)

    logger.info("\\nTesting idempotency...")
    beautified_twice = beautify_markdown(beautified_md)
    if beautified_md == beautified_twice:
        logger.info("Beautifier is idempotent for the given sample.")
    else:
        logger.warning("Beautifier is NOT idempotent for the given sample. Differences below:")
        from difflib import unified_diff
        diff = list(unified_diff(beautified_md.splitlines(keepends=True),
                                 beautified_twice.splitlines(keepends=True),
                                 fromfile='once', tofile='twice'))
        for line in diff:
            print(line, end="")

    print("\\n--- Specific Test Cases ---")
    test_cases = {
        "Header": "#MyHeader",
        "List": "*item1\\n- item2\\n1. item3",
        "Spacing": "Line1\\n\\n\\n\\nLine2",
        "Page Comment Inline": "Previous text.<!-- Page 3 -->Next text.",
        "Page Comment Chain": "<!-- Page 1 -->\\n<!-- Page 2 -->\\nText",
        "Page Comment Extra Newlines": "Text before\\n\\n\\n<!-- Page 5 -->\\n\\n\\nText after",
        "Ends with comment": "Some text\\n<!-- Page 1 -->",
        "Starts with comment": "<!-- Page 1 -->\\nSome text",
        "Professional Skills Test": "1. 整体概述：balabala\\n2. 专业能力：技能点A。技能点B。技能点C。\\n3. 其他技能：技能D"
    }

    for name, test_md in test_cases.items():
        print(f"\\nInput ({name}):\\n'{test_md}'")
        print(f"Beautified:\\n'{beautify_markdown(test_md)}'") 