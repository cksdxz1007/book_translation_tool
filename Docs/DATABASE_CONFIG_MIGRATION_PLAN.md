# 全数据库配置管理迁移方案

> 版本: 1.0
> 日期: 2025-12-09
> 状态: 待实施

---

## 一、背景与目标

### 1.1 当前现状

项目当前使用 `.env` 文件存储敏感配置，存在以下问题：

1. **分散管理** - 配置分布在 `.env` 和数据库两处
2. **运维复杂** - 需要手动编辑文件，无法通过界面管理
3. **安全风险** - `.env` 文件可能被意外提交到版本控制
4. **部署不便** - 多环境部署需要手动同步配置文件

### 1.2 目标

- 统一使用 SQLite 数据库管理所有配置
- 通过管理界面实现配置的可视化管理
- 移除对 `.env` 文件的依赖
- 保持现有加密机制，确保敏感数据安全

---

## 二、现状分析

### 2.1 当前 `.env` 配置项

| 配置项 | 用途 | 敏感程度 | 使用位置 |
|--------|------|----------|----------|
| `ADMIN_ACCESS_KEY` | 管理员页面访问密钥 | 高 | `admin_routes.py:16` |
| `FLASK_SECRET_KEY` | Flask会话管理密钥 | 高 | `app.py:983` |
| `DEEPSEEK_API_KEY` | DeepSeek API密钥 | 高 | `monitor_babeldoc_performance.py` |
| `SILICONFLOW_API_KEY` | SiliconFlow API密钥 | 高 | 可选配置 |
| `OPENROUTER_API_KEY` | OpenRouter API密钥 | 高 | 可选配置 |
| `FLASK_ENV` | Flask运行环境 | 低 | 环境配置 |

### 2.2 现有数据库表

```
data/config.db
├── translation_services    # 翻译服务配置（支持加密API Key）
├── system_settings         # 系统设置（支持加密）
└── prompt_templates        # 提示词模板
```

### 2.3 现有加密机制

- 加密算法: AES-256
- 密钥位置: `data/keys/master.key`
- 已在 `ConfigManager` 中实现

---

## 三、迁移方案

### 3.1 方案选择：扩展 `system_settings` 表（推荐）

**理由：**
1. 复用现有加密基础设施
2. 改动最小，风险可控
3. ConfigManager 已支持相关操作
4. 与翻译服务配置管理方式一致

### 3.2 数据库表设计

使用现有 `system_settings` 表，无需修改表结构：

```sql
-- 现有表结构
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value_encrypted BLOB,
    is_sensitive BOOLEAN DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.3 迁移的配置项

| 配置键 | 默认值 | 敏感 | 说明 |
|--------|--------|------|------|
| `admin_access_key` | 自动生成 | 是 | 管理员访问密钥 |
| `flask_secret_key` | 自动生成 | 是 | Flask会话密钥 |
| `app_port` | `5001` | 否 | 应用端口 |
| `debug_mode` | `false` | 否 | 调试模式 |
| `max_upload_size_mb` | `50` | 否 | 最大上传文件大小 |
| `default_target_language` | `Chinese` | 否 | 默认目标语言 |
| `parallel_workers` | `4` | 否 | 并行翻译工作线程数 |

---

## 四、技术实现

### 4.1 配置加载器设计

```python
# config/app_config.py

class AppConfig:
    """应用配置管理器（单例模式）"""

    _instance = None
    _config_cache = {}
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.config_manager = ConfigManager('data/config.db', 'data/keys')
            self._load_all_config()
            self.initialized = True

    def _load_all_config(self):
        """从数据库加载所有配置到内存缓存"""
        with self.config_manager.db.get_connection() as conn:
            cursor = conn.execute("SELECT key, value_encrypted, is_sensitive FROM system_settings")
            for row in cursor.fetchall():
                key = row['key']
                if row['is_sensitive']:
                    self._config_cache[key] = self.config_manager._decrypt(row['value_encrypted'])
                else:
                    self._config_cache[key] = row['value_encrypted'].decode() if row['value_encrypted'] else None

    def get(self, key: str, default=None):
        """获取配置值"""
        return self._config_cache.get(key, default)

    def set(self, key: str, value: str, is_sensitive: bool = False):
        """设置配置值"""
        with self.config_manager.db.get_connection() as conn:
            if is_sensitive:
                encrypted_value = self.config_manager._encrypt(value)
            else:
                encrypted_value = value.encode() if value else None

            conn.execute("""
                INSERT OR REPLACE INTO system_settings (key, value_encrypted, is_sensitive, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (key, encrypted_value, is_sensitive))

        # 更新缓存
        self._config_cache[key] = value

    def reload(self):
        """重新加载配置"""
        self._config_cache.clear()
        self._load_all_config()

# 全局单例
app_config = AppConfig()
```

### 4.2 使用方式

```python
# 之前
ADMIN_ACCESS_KEY = os.getenv('ADMIN_ACCESS_KEY', 'default')

# 之后
from config.app_config import app_config
ADMIN_ACCESS_KEY = app_config.get('admin_access_key')
```

### 4.3 初始化默认配置

> ⚠️ **重要原则：不覆盖现有数据**
>
> 初始化时必须先检查配置项是否已存在，只有不存在时才插入默认值。
> 这确保了用户已配置的 API Key（如 DeepSeek API Key）不会被覆盖。

```python
def _init_default_system_settings(self, conn):
    """初始化默认系统配置"""
    import secrets

    defaults = [
        ('admin_access_key', secrets.token_urlsafe(32), True),
        ('flask_secret_key', secrets.token_urlsafe(32), True),
        ('app_port', '5001', False),
        ('debug_mode', 'false', False),
        ('max_upload_size_mb', '50', False),
        ('default_target_language', 'Chinese', False),
        ('parallel_workers', '4', False),
    ]

    for key, default_value, is_sensitive in defaults:
        # 检查是否已存在
        cursor = conn.execute("SELECT 1 FROM system_settings WHERE key = ?", (key,))
        if not cursor.fetchone():
            if is_sensitive:
                encrypted_value = self._encrypt(default_value)
            else:
                encrypted_value = default_value.encode()

            conn.execute("""
                INSERT INTO system_settings (key, value_encrypted, is_sensitive)
                VALUES (?, ?, ?)
            """, (key, encrypted_value, is_sensitive))
```

---

## 五、数据保护原则

> ⚠️ **核心原则：迁移过程中绝不覆盖现有数据**

### 5.1 受保护的数据

以下数据在迁移过程中必须保留，不能被覆盖或删除：

| 表 | 数据 | 保护原因 |
|----|------|----------|
| `translation_services` | 已配置的翻译服务 | 用户配置的 API Key（如 DeepSeek） |
| `system_settings` | 已存在的设置项 | 用户自定义的配置值 |
| `prompt_templates` | 已修改的模板 | 用户自定义的提示词 |

### 5.2 安全初始化策略

```python
# ❌ 错误做法：直接覆盖
conn.execute("INSERT OR REPLACE INTO system_settings ...")

# ✅ 正确做法：先检查再插入
cursor = conn.execute("SELECT 1 FROM system_settings WHERE key = ?", (key,))
if not cursor.fetchone():
    # 只有不存在时才插入默认值
    conn.execute("INSERT INTO system_settings ...", (key, default_value))
```

### 5.3 迁移前备份

```bash
# 迁移前必须备份数据库
cp data/config.db data/config.db.backup.$(date +%Y%m%d_%H%M%S)
```

### 5.4 验证检查清单

迁移后必须验证以下数据完整性：

- [ ] `translation_services` 表中的服务数量与迁移前一致
- [ ] 已配置的 API Key 可正常使用
- [ ] `prompt_templates` 表中的模板数量与迁移前一致
- [ ] 用户自定义的提示词内容未变化

---

## 六、实施步骤

### Phase 1: 数据库准备（预计 0.5 天）

- [ ] **备份现有数据库** `cp data/config.db data/config.db.backup`
- [ ] 在 `DatabaseManager._init_default_system_settings()` 添加默认配置初始化
- [ ] **使用 INSERT IGNORE 模式，不覆盖现有数据**
- [ ] 确保首次启动时自动生成安全密钥

### Phase 2: 配置加载器（预计 1 天）

- [ ] 创建 `config/app_config.py` 模块
- [ ] 实现 `AppConfig` 单例类
- [ ] 添加配置缓存机制
- [ ] 实现 `get()`, `set()`, `reload()` 方法

### Phase 3: 代码迁移（预计 0.5 天）

- [ ] 修改 `app.py:983` - FLASK_SECRET_KEY
- [ ] 修改 `admin_routes.py:16` - ADMIN_ACCESS_KEY
- [ ] 检查并更新其他 `os.getenv()` 调用

### Phase 4: 管理界面（预计 1 天）

- [ ] 在 `/admin` 添加"系统配置"页面
- [ ] 支持查看所有配置项
- [ ] 支持修改非敏感配置
- [ ] 敏感配置显示为 `****`，支持重置

### Phase 5: 测试与清理（预计 0.5 天）

- [ ] 测试首次启动流程
- [ ] 测试配置修改和热加载
- [ ] 删除 `.env.example` 文件
- [ ] 更新 `README.md` 和 `CLAUDE.md`
- [ ] 更新启动脚本 `launch.py`

---

## 六、安全考虑

### 6.1 加密存储

- 所有敏感配置使用 AES-256 加密存储
- 加密密钥存储在 `data/keys/master.key`
- 密钥文件权限设为 600

### 6.2 数据库文件权限

```bash
chmod 600 data/config.db
chmod 600 data/keys/master.key
```

### 6.3 首次启动安全

- 首次启动自动生成随机密钥
- 无需人工干预
- 避免使用固定默认值

---

## 七、回退机制

### 7.1 数据库不可用

```python
def get(self, key: str, default=None):
    try:
        return self._config_cache.get(key, default)
    except Exception as e:
        logger.warning(f"Failed to get config {key}: {e}, using default")
        return default
```

### 7.2 迁移期间兼容

```python
def get(self, key: str, default=None):
    # 优先从数据库读取
    value = self._config_cache.get(key)
    if value is not None:
        return value

    # 回退到环境变量（迁移期间）
    env_key = key.upper()
    env_value = os.getenv(env_key)
    if env_value:
        logger.info(f"Config {key} loaded from env, consider migrating to database")
        return env_value

    return default
```

---

## 八、管理界面设计

### 8.1 系统配置页面

```
/admin/system-config

┌─────────────────────────────────────────────────────┐
│  系统配置管理                                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│  安全设置                                            │
│  ┌─────────────────────────────────────────────┐   │
│  │ 管理员密钥: ************************ [重置]  │   │
│  │ Flask密钥:  ************************ [重置]  │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  应用设置                                            │
│  ┌─────────────────────────────────────────────┐   │
│  │ 应用端口:     [5001        ]                 │   │
│  │ 调试模式:     [ ] 启用                       │   │
│  │ 最大上传(MB): [50          ]                 │   │
│  │ 默认目标语言: [Chinese     ▼]                │   │
│  │ 并行线程数:   [4           ]                 │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  [保存配置]  [重载配置]                              │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 8.2 API 端点

```
GET  /admin/api/system-config      # 获取所有配置
POST /admin/api/system-config      # 更新配置
POST /admin/api/system-config/reset/{key}  # 重置敏感配置
POST /admin/api/system-config/reload       # 热加载配置
```

---

## 九、文件变更清单

### 新增文件

- `config/app_config.py` - 应用配置管理器
- `templates/admin/system_config.html` - 系统配置页面

### 修改文件

- `config/database.py` - 添加默认配置初始化
- `app.py` - 修改密钥读取方式
- `admin_routes.py` - 修改密钥读取方式，添加配置管理路由
- `README.md` - 更新配置说明
- `CLAUDE.md` - 更新开发指南

### 删除文件

- `.env.example` - 不再需要
- `Docs/ADMIN_SECURITY_GUIDE.md` - 合并到新文档

---

## 十、风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 数据库损坏导致无法启动 | 低 | 高 | 添加回退到默认值机制 |
| 密钥迁移丢失 | 低 | 高 | 迁移前备份，支持环境变量回退 |
| 配置缓存不一致 | 中 | 中 | 提供 reload() 方法，关键操作后自动刷新 |
| 管理界面误操作 | 中 | 中 | 敏感配置需二次确认 |

---

## 十一、验收标准

1. [ ] 首次启动自动生成安全密钥并存入数据库
2. [ ] 应用正常启动，无 `.env` 文件依赖
3. [ ] 管理界面可查看和修改配置
4. [ ] 敏感配置正确加密存储
5. [ ] 配置修改后可热加载生效
6. [ ] 所有原有功能正常工作
