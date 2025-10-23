import uuid
from typing import List, Dict, Optional
from .database import DatabaseManager
from .security import SecurityManager

class ConfigManager:
    def __init__(self, db_path: str, key_dir: str):
        self.db = DatabaseManager(db_path)
        self.security = SecurityManager(key_dir)
    
    def create_service(self, config: Dict) -> str:
        service_id = str(uuid.uuid4())
        
        with self.db.get_connection() as conn:
            api_key_encrypted = self.security.encrypt(config.get('api_key', ''))
            
            conn.execute("""
                INSERT INTO translation_services (
                    id, name, description, service_type, base_url,
                    api_key_encrypted, model_name, temperature, max_tokens
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                service_id,
                config['name'],
                config.get('description', ''),
                config['service_type'],
                config['base_url'],
                api_key_encrypted,
                config['model_name'],
                config.get('temperature', 0.3),
                config.get('max_tokens', 4000)
            ))
        
        return service_id
    
    def get_service(self, service_id: str) -> Optional[Dict]:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM translation_services WHERE id = ?',
                (service_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            service = dict(row)
            service['api_key'] = self.security.decrypt(service['api_key_encrypted'])
            service.pop('api_key_encrypted', None)
            
            return service
    
    def list_services(self, active_only: bool = True) -> List[Dict]:
        with self.db.get_connection() as conn:
            query = 'SELECT * FROM translation_services'
            if active_only:
                query += ' WHERE is_active = 1'
            query += ' ORDER BY is_default DESC, name ASC'
            
            cursor = conn.execute(query)
            services = []
            
            for row in cursor.fetchall():
                service = dict(row)
                service.pop('api_key_encrypted', None)
                services.append(service)
            
            return services
    
    def get_default_service(self) -> Optional[Dict]:
        """获取默认服务，处理无服务的情况"""
        with self.db.get_connection() as conn:
            # 首先查找标记为默认的活跃服务
            cursor = conn.execute(
                'SELECT * FROM translation_services WHERE is_default = 1 AND is_active = 1'
            )
            row = cursor.fetchone()
            
            if row:
                return self.get_service(row['id'])
            
            # 如果没有默认服务，返回第一个活跃服务
            cursor = conn.execute(
                'SELECT * FROM translation_services WHERE is_active = 1 ORDER BY created_at ASC LIMIT 1'
            )
            row = cursor.fetchone()
            
            if row:
                return self.get_service(row['id'])
            
            # 没有任何服务
            return None
    
    def get_service_by_name(self, service_name: str) -> Optional[Dict]:
        """根据服务名称获取服务配置"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM translation_services WHERE name = ? AND is_active = 1',
                (service_name,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            service = dict(row)
            service['api_key'] = self.security.decrypt(service['api_key_encrypted'])
            service.pop('api_key_encrypted', None)
            return service
    
    def test_service_connection(self, service_id: str) -> Dict:
        """测试服务连接"""
        service = self.get_service(service_id)
        if not service:
            return {"success": False, "error": "Service not found"}
        
        try:
            if service['service_type'] in ['openai', 'deepseek']:
                result = self._test_openai_service(service)
            elif service['service_type'] == 'ollama':
                result = self._test_ollama_service(service)
            else:
                result = {"success": True, "message": "自定义服务测试跳过"}
            
            # 更新测试状态
            with self.db.get_connection() as conn:
                conn.execute('''
                    UPDATE translation_services 
                    SET last_tested = CURRENT_TIMESTAMP, test_status = ?
                    WHERE id = ?
                ''', (
                    'success' if result['success'] else 'failed',
                    service_id
                ))
            
            return result
            
        except Exception as e:
            with self.db.get_connection() as conn:
                conn.execute('''
                    UPDATE translation_services 
                    SET last_tested = CURRENT_TIMESTAMP, test_status = 'failed'
                    WHERE id = ?
                ''', (service_id,))
            
            return {"success": False, "error": str(e)}
    
    def _test_openai_service(self, service: Dict) -> Dict:
        """测试OpenAI兼容服务"""
        import requests
        
        headers = {
            'Authorization': f'Bearer {service["api_key"]}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': service['model_name'],
            'messages': [{'role': 'user', 'content': 'Hello'}],
            'max_tokens': 10
        }
        
        response = requests.post(
            f"{service['base_url']}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return {"success": True, "message": "连接测试成功"}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:100]}"}
    
    def _test_ollama_service(self, service: Dict) -> Dict:
        """测试Ollama服务"""
        import requests
        
        data = {
            'model': service['model_name'],
            'prompt': 'Hello',
            'stream': False
        }
        
        response = requests.post(
            f"{service['base_url']}/api/generate",
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return {"success": True, "message": "连接测试成功"}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:100]}"}
    
    def update_service(self, service_id: str, config: Dict) -> bool:
        """更新服务配置"""
        with self.db.get_connection() as conn:
            # 检查服务是否存在
            cursor = conn.execute('SELECT id FROM translation_services WHERE id = ?', (service_id,))
            if not cursor.fetchone():
                return False
            
            # 加密敏感字段
            api_key_encrypted = self.security.encrypt(config.get('api_key', ''))
            
            cursor = conn.execute('''
                UPDATE translation_services SET
                    name = ?, description = ?, service_type = ?, base_url = ?,
                    api_key_encrypted = ?, model_name = ?, temperature = ?, max_tokens = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                config['name'],
                config.get('description', ''),
                config['service_type'],
                config['base_url'],
                api_key_encrypted,
                config['model_name'],
                config.get('temperature', 0.3),
                config.get('max_tokens', 4000),
                service_id
            ))
            
            return cursor.rowcount > 0
        """设置默认服务"""
        with self.db.get_connection() as conn:
            # 清除所有默认标记
            conn.execute('UPDATE translation_services SET is_default = 0')
            
            # 设置新的默认服务
            cursor = conn.execute(
                'UPDATE translation_services SET is_default = 1 WHERE id = ?',
                (service_id,)
            )
            
            return cursor.rowcount > 0
