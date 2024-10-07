import os
import shutil
from uuid import uuid4

def upload_file(file_path, upload_dir):
    """
    上传文件到指定目录，并返回唯一标识符
    """
    file_id = str(uuid4())
    file_name = os.path.basename(file_path)
    destination = os.path.join(upload_dir, f"{file_id}_{file_name}")
    
    shutil.copy2(file_path, destination)
    return file_id, destination

def get_file_format(file_path):
    """
    获取文件格式
    """
    _, extension = os.path.splitext(file_path)
    return extension.lower()[1:]  # 去掉点号