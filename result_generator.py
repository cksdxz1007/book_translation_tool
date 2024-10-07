import os

def merge_translated_chunks(translated_chunks):
    """
    合并翻译后的文本块
    """
    return "\n\n".join(translated_chunks)

def save_result(merged_text, output_path):
    """
    保存翻译结果到文本文件
    """
    # 确保输出路径以 .txt 结尾
    if not output_path.lower().endswith('.txt'):
        output_path = os.path.splitext(output_path)[0] + '.txt'

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(merged_text)
    print(f"翻译结果已保存为文本文件：{output_path}")