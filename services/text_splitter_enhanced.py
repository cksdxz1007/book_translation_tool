import re
import logging
from typing import List

logger = logging.getLogger(__name__)

def split_text_into_chunks(text: str, max_chunk_size: int = 2000, overlap: int = 100) -> List[str]:
    """
    将文本分割成合适大小的块，尽量在句子边界处分割
    
    Args:
        text: 要分割的文本
        max_chunk_size: 每个块的最大字符数
        overlap: 块之间的重叠字符数（用于保持上下文连贯）
        
    Returns:
        List[str]: 分割后的文本块列表
    """
    if not text:
        return []
    
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    current_pos = 0
    text_length = len(text)
    
    while current_pos < text_length:
        # 计算当前块的结束位置
        end_pos = min(current_pos + max_chunk_size, text_length)
        
        # 如果还没到文本末尾，尝试在句子边界处分割
        if end_pos < text_length:
            # 查找最近的句子结束符
            sentence_end = find_sentence_boundary(text, end_pos)
            if sentence_end > current_pos:  # 确保找到有效的边界
                end_pos = sentence_end
        
        # 提取当前块
        chunk = text[current_pos:end_pos].strip()
        if chunk:  # 只添加非空块
            chunks.append(chunk)
        
        # 移动到下一个位置，考虑重叠
        current_pos = end_pos - overlap if end_pos - overlap > current_pos else end_pos
        
        # 确保不会无限循环
        if current_pos <= end_pos:
            current_pos = end_pos
    
    logger.info(f"将文本分割成 {len(chunks)} 个块，最大块大小: {max_chunk_size}")
    return chunks

def find_sentence_boundary(text: str, position: int) -> int:
    """
    在给定位置附近查找最近的句子边界
    
    Args:
        text: 文本内容
        position: 当前位置
        
    Returns:
        int: 句子边界位置
    """
    # 句子结束符：句号、问号、感叹号、换行符等
    sentence_endings = ['.', '?', '!', '。', '？', '！', '\n\n', '\r\n\r\n']
    
    # 向前查找（优先）
    for i in range(position, max(0, position - 50), -1):
        if i < len(text):
            for ending in sentence_endings:
                if text[i:i+len(ending)] == ending:
                    return i + len(ending)
    
    # 向后查找
    for i in range(position, min(len(text), position + 50)):
        for ending in sentence_endings:
            if text[i:i+len(ending)] == ending:
                return i + len(ending)
    
    # 如果没有找到合适的边界，返回原始位置
    return position

def split_markdown_preserving_structure(text: str, max_chunk_size: int = 2000) -> List[str]:
    """
    专门用于Markdown文本的分割，尽量保持结构完整性
    
    Args:
        text: Markdown文本
        max_chunk_size: 每个块的最大字符数
        
    Returns:
        List[str]: 分割后的Markdown块列表
    """
    if not text:
        return []
    
    # 按章节分割（以 # 开头的标题）
    sections = re.split(r'(?=^#+\s)', text, flags=re.MULTILINE)
    
    chunks = []
    current_chunk = ""
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
            
        # 如果当前块加上新章节不会超过限制，就合并
        if len(current_chunk) + len(section) + 2 <= max_chunk_size:
            if current_chunk:
                current_chunk += "\n\n" + section
            else:
                current_chunk = section
        else:
            # 当前块已满，保存并开始新块
            if current_chunk:
                chunks.append(current_chunk)
            
            # 如果单个章节就超过限制，需要进一步分割
            if len(section) > max_chunk_size:
                sub_chunks = split_text_into_chunks(section, max_chunk_size)
                chunks.extend(sub_chunks)
                current_chunk = ""
            else:
                current_chunk = section
    
    # 添加最后一个块
    if current_chunk:
        chunks.append(current_chunk)
    
    logger.info(f"Markdown文本分割成 {len(chunks)} 个结构保持块")
    return chunks

def estimate_optimal_chunk_size(text: str, target_chunks: int = 10) -> int:
    """
    根据文本长度估算合适的块大小
    
    Args:
        text: 文本内容
        target_chunks: 目标块数量
        
    Returns:
        int: 估算的最佳块大小
    """
    if not text or target_chunks <= 0:
        return 2000  # 默认值
    
    text_length = len(text)
    optimal_size = max(500, min(4000, text_length // target_chunks))
    
    logger.info(f"文本长度 {text_length}，估算最佳块大小: {optimal_size}")
    return optimal_size

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试文本
    test_text = """这是一段测试文本。它包含多个句子。
    
    这是另一个段落。文本分割应该尽量在句子边界处进行。
    
    第三段内容，用于测试分割算法的效果。确保分割后的块大小合适且保持语义连贯。""" * 50  # 重复多次以创建长文本
    
    print(f"原始文本长度: {len(test_text)}")
    
    # 测试普通分割
    chunks = split_text_into_chunks(test_text, max_chunk_size=1000)
    print(f"分割成 {len(chunks)} 个块")
    for i, chunk in enumerate(chunks[:3]):  # 只显示前3个块
        print(f"块 {i+1} (长度 {len(chunk)}): {chunk[:100]}...")
    
    # 测试Markdown分割
    markdown_text = """# 第一章
    
    这是第一章的内容。包含多个段落。
    
    ## 第一节
    
    第一节的详细内容。
    
    # 第二章
    
    第二章的开始。""" * 20
    
    md_chunks = split_markdown_preserving_structure(markdown_text, max_chunk_size=500)
    print(f"\nMarkdown分割成 {len(md_chunks)} 个块")
    for i, chunk in enumerate(md_chunks):
        print(f"Markdown块 {i+1} (长度 {len(chunk)}): {chunk[:80]}...")