from cryptography.fernet import Fernet
import os
import secrets

class SecurityManager:
    def __init__(self, key_dir: str):
        self.key_dir = key_dir
        self.master_key = self._get_or_create_master_key()
        self.fernet = Fernet(self.master_key)
    
    def _get_or_create_master_key(self) -> bytes:
        key_file = os.path.join(self.key_dir, 'master.key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(self.key_dir, exist_ok=True)
            
            with open(key_file, 'wb') as f:
                f.write(key)
            
            os.chmod(key_file, 0o600)
            return key
    
    def encrypt(self, data: str) -> bytes:
        if not data:
            return b''
        return self.fernet.encrypt(data.encode('utf-8'))
    
    def decrypt(self, encrypted_data: bytes) -> str:
        if not encrypted_data:
            return ''
        return self.fernet.decrypt(encrypted_data).decode('utf-8')
