"""
新的配置加载器 - 替换原有的config_loader.py
"""

from config.manager import ConfigManager

# 全局配置管理器实例
_config_manager = None

def get_config_manager():
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager('data/config.db', 'data/keys')
    return _config_manager

def load_service_config():
    """加载服务配置 - 兼容原有API"""
    manager = get_config_manager()
    services = manager.list_services()
    
    # 转换为原有格式
    config = {
        'services': {},
        'default_service_name': None
    }
    
    for service in services:
        service_data = {
            'service_type': service['service_type'],
            'openai_compatible_base_url': service['base_url'],
            'model_name': service['model_name'],
            'comment': service['description']
        }
        
        config['services'][service['name']] = service_data
        
        if service.get('is_default'):
            config['default_service_name'] = service['name']
    
    return config

def get_api_key_from_config(service_config):
    """获取API密钥 - 兼容原有API"""
    # 新系统中API密钥通过服务ID获取
    # 这里需要根据服务名称查找
    manager = get_config_manager()
    services = manager.list_services()
    
    for service in services:
        if service['name'] == service_config.get('comment', ''):
            full_service = manager.get_service(service['id'])
            return full_service.get('api_key', '') if full_service else ''
    
    return ''
