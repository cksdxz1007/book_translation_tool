import os
import re
import shutil
from file_handler import upload_file, get_file_format
from text_splitter import split_pdf, get_pdf_page_count
from translator import translate_book
from result_generator import merge_translated_chunks, save_result

def sanitize_filename(filename):
    """
    处理文件名，移除不允许的字符
    """
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def get_output_filename(input_path, target_language):
    """
    生成输出文件名，保持原格式并添加翻译后缀
    """
    dir_name, file_name = os.path.split(input_path)
    name, ext = os.path.splitext(file_name)
    translated_name = f"{name}_翻译后_{target_language}{ext}"
    return sanitize_filename(translated_name)

def get_page_range(total_pages):
    """
    获取用户指定的页面范围
    """
    while True:
        user_input = input(f"请输入要翻译的页码范围（1-{total_pages}，直接回车表示全部翻译）：").strip()
        if not user_input:
            return 1, total_pages
        
        if '-' in user_input:
            try:
                start, end = map(int, user_input.split('-'))
                if 1 <= start <= end <= total_pages:
                    return start, end
            except ValueError:
                pass
        else:
            try:
                page = int(user_input)
                if 1 <= page <= total_pages:
                    return page, page
            except ValueError:
                pass
        
        print("输入无效，请重新输入。")

def cleanup_temp_files(upload_dir):
    """
    清理临时文件和目录
    """
    try:
        shutil.rmtree(upload_dir)
        print(f"临时文件已清理：{upload_dir}")
    except Exception as e:
        print(f"清理临时文件时出错：{str(e)}")

def main():
    # 设置目录
    upload_dir = "uploads"
    output_dir = "results"
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    try:
        # 用户输入文件路径
        file_path = input("请输入要翻译的文件路径：")
        
        # 处理文件路径
        file_path = os.path.expanduser(file_path)  # 展开用户目录（如果有的话）
        file_path = os.path.normpath(file_path)    # 规范化路径
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"错误：文件 '{file_path}' 不存在。")
            return
        
        # 上传文件
        file_id, uploaded_file = upload_file(file_path, upload_dir)
        
        # 获取文件格式并处理
        file_format = get_file_format(uploaded_file)
        if file_format == "pdf":
            total_pages = get_pdf_page_count(uploaded_file)
            print(f"PDF文件共有 {total_pages} 页。")
            start_page, end_page = get_page_range(total_pages)
            chunks = split_pdf(uploaded_file, start_page=start_page, end_page=end_page)
            print(f"文件分块成功，共分为 {len(chunks)} 块。")
        else:
            print("暂不支持的文件格式")
            return
        
        # 用户选择目标语言
        target_language = input("请输入目标语言（默认为中文）：") or "Chinese"
        
        # 翻译
        translated_chunks = translate_book(chunks, target_language=target_language)
        
        # 合并结果
        merged_text = merge_translated_chunks(translated_chunks)
        
        # 生成输出文件名并保存结果
        output_filename = get_output_filename(file_path, target_language)
        output_filename = os.path.splitext(output_filename)[0] + '.txt'
        output_path = os.path.join(output_dir, output_filename)
        save_result(merged_text, output_path)
        
        print(f"翻译完成，结果保存在：{output_path}")

    finally:
        # 清理临时文件
        cleanup_temp_files(upload_dir)

if __name__ == "__main__":
    main()