#!/usr/bin/env python3
"""
从旧配置迁移到新SQLite系统
"""

import json
import os
from config.manager import ConfigManager

def migrate_from_old_config():
    """从services.json迁移配置"""
    
    # 初始化新配置管理器
    manager = ConfigManager('data/config.db', 'data/keys')
    
    # 检查是否存在旧配置
    if not os.path.exists('services.json'):
        print("未找到services.json，创建默认配置")
        create_default_config(manager)
        return
    
    # 读取旧配置
    with open('services.json', 'r', encoding='utf-8') as f:
        old_config = json.load(f)
    
    migrated_count = 0
    
    # 迁移服务配置
    for service_id, service_config in old_config.get('services', {}).items():
        try:
            new_config = {
                'name': service_config.get('comment', service_id),
                'service_type': service_config.get('service_type', 'openai'),
                'base_url': (service_config.get('openai_compatible_base_url') or 
                           service_config.get('ollama_url', '')),
                'model_name': service_config.get('model_name', ''),
                'description': f'从 {service_id} 迁移'
            }
            
            # 处理API密钥
            if 'api_key' in service_config:
                new_config['api_key'] = service_config['api_key']
            elif 'api_key_env_var' in service_config:
                env_var = service_config['api_key_env_var']
                api_key = os.getenv(env_var)
                if api_key:
                    new_config['api_key'] = api_key
                    print(f"从环境变量 {env_var} 获取API密钥")
                else:
                    print(f"警告: 环境变量 {env_var} 未设置，跳过此服务")
                    continue
            
            # 创建服务
            new_service_id = manager.create_service(new_config)
            print(f"✓ 迁移服务: {service_id} -> {new_service_id}")
            migrated_count += 1
            
        except Exception as e:
            print(f"✗ 迁移服务 {service_id} 失败: {e}")
    
    print(f"\n迁移完成: {migrated_count} 个服务")

def create_default_config(manager):
    """创建默认配置"""
    default_service = {
        'name': 'Ollama本地服务',
        'description': '本地Ollama服务',
        'service_type': 'ollama',
        'base_url': 'http://localhost:11434',
        'model_name': 'llama3',
        'api_key': ''
    }
    
    service_id = manager.create_service(default_service)
    print(f"✓ 创建默认服务: {service_id}")

if __name__ == '__main__':
    migrate_from_old_config()
