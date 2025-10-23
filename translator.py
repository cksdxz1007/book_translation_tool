import requests
import logging # Add logging
import json # New import
import os   # New import
import hashlib # New import
import re # New import for page comment regex
import time
from config.manager import ConfigManager # 使用新配置系统

logger = logging.getLogger(__name__) # Add logger for this module

# 全局配置管理器
config_manager = ConfigManager('data/config.db', 'data/keys')

def get_translation_service():
    """获取翻译服务配置，处理无服务的情况"""
    try:
        default_service = config_manager.get_default_service()
        if not default_service:
            logger.error("未找到可用的翻译服务配置")
            raise ValueError("未配置翻译服务。请访问 /admin 添加翻译服务配置。")
        
        if not default_service.get('api_key') and default_service['service_type'] not in ['ollama']:
            logger.error(f"服务 {default_service['name']} 缺少API密钥")
            raise ValueError(f"翻译服务 '{default_service['name']}' 未配置API密钥。")
        
        return default_service
    except Exception as e:
        logger.error(f"获取翻译服务配置失败: {e}")
        raise

def _clean_translator_notes(text):
    """Remove translator notes and explanatory text that LLMs sometimes add"""
    if not text:
        return text
    
    # Remove Chinese translator notes like （注：...）
    text = re.sub(r'（注：[^）]*）', '', text)
    text = re.sub(r'\(注：[^)]*\)', '', text)
    
    # Remove English translator notes
    text = re.sub(r'\(Note:[^)]*\)', '', text)
    text = re.sub(r'\[Note:[^\]]*\]', '', text)
    
    # Remove common translator explanations
    text = re.sub(r'根据翻译准则[^。]*。', '', text)
    text = re.sub(r'由于原文[^。]*。', '', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()
    
    return text

# --- Retry Decorator ---
def retry_with_backoff(max_retries=3, initial_delay=1, backoff_factor=2):
    """
    重试装饰器，支持指数退避
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")
                        raise
                    
                    logger.warning(f"Retry {retries}/{max_retries} for {func.__name__} after error: {e}")
                    time.sleep(delay)
                    delay *= backoff_factor
            
            raise Exception(f"Failed after {max_retries} retries")
        return wrapper
    return decorator

# --- Cache Helper Functions ---
def _get_chunk_cache_key(chunk_text, source_language, target_language):
    """Generates a unique cache key for a text chunk and language pair."""
    hasher = hashlib.sha256()
    hasher.update(chunk_text.encode('utf-8'))
    chunk_hash = hasher.hexdigest()
    return f"{chunk_hash}_{source_language}_to_{target_language}"

def _load_translation_cache(cache_file_path):
    """Loads the translation cache from a JSON file."""
    if cache_file_path and os.path.exists(cache_file_path):
        try:
            with open(cache_file_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                return cache_data.get("translations", {}) # Return only the translations part
        except (IOError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load or parse cache file '{cache_file_path}': {e}. Starting with an empty cache.")
    return {}

def _save_translation_cache(cache_file_path, translations_map, original_pdf_filename):
    """Saves the translation cache to a JSON file."""
    if not cache_file_path:
        return
    try:
        # Ensure the directory for the cache file exists
        cache_dir = os.path.dirname(cache_file_path)
        if cache_dir: # Check if cache_dir is not an empty string (e.g. if cache_file_path is just a filename)
             os.makedirs(cache_dir, exist_ok=True)
        
        cache_data_to_save = {
            "source_pdf_filename": original_pdf_filename,
            "translations": translations_map
        }
        with open(cache_file_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data_to_save, f, ensure_ascii=False, indent=4)
        logger.info(f"Translation cache saved to '{cache_file_path}'")
    except IOError as e:
        logger.error(f"Could not save cache file '{cache_file_path}': {e}")
# --- End Cache Helper Functions ---

class TranslationService:
    def __init__(self, service_name_from_config=None, # If provided, loads from config
                 config_data_for_testing=None, # For passing pre-loaded config during tests/dev
                 # Direct parameters (used if service_name_from_config is None)
                 service_type=None, 
                 model_name=None, 
                 api_key=None, 
                 ollama_url=None, 
                 openai_compatible_base_url=None, 
                 legacy_completion_api_url=None, 
                 custom_prompt_template=None,
                 default_source_language="auto", # New parameter
                 default_target_language="Chinese"): # New parameter

        self.default_source_language = default_source_language
        self.default_target_language = default_target_language
        
        effective_prompt_template = custom_prompt_template

        if service_name_from_config:
            # 使用新的SQLite配置系统
            try:
                service_config = config_manager.get_service_by_name(service_name_from_config)
                if not service_config:
                    error_msg = f"Service '{service_name_from_config}' not found in configuration."
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                self.service_type = service_config.get('service_type')
                self.model_name = service_config.get('model_name')
                self.api_key = service_config.get('api_key')
                
                self.ollama_url = service_config.get('ollama_url')
                self.openai_compatible_base_url = service_config.get('openai_compatible_base_url', service_config.get('base_url'))
                # Check for 'legacy_completion_api_url' first, then 'api_url' for backward compatibility in config
                self.legacy_completion_api_url = service_config.get('legacy_completion_api_url', service_config.get('api_url'))
                # Override defaults from config if present
                self.default_source_language = service_config.get('default_source_language', self.default_source_language)
                self.default_target_language = service_config.get('default_target_language', self.default_target_language)
                effective_prompt_template = service_config.get('custom_prompt_template', custom_prompt_template) # Config overrides direct param
            except Exception as e:
                logger.error(f"Error loading service configuration for '{service_name_from_config}': {e}")
                raise

            logger.info(f"TranslationService initialized using config: '{service_name_from_config}'")

        else: # Initialize with direct parameters
            self.service_type = service_type
            self.model_name = model_name
            self.api_key = api_key
            self.ollama_url = ollama_url
            self.openai_compatible_base_url = openai_compatible_base_url
            self.legacy_completion_api_url = legacy_completion_api_url
            # default_source_language and default_target_language are already set from params
            logger.info(f"TranslationService initialized using direct parameters for service type: '{self.service_type}'")

        # Normalize and apply defaults
        if self.service_type:
            self.service_type = self.service_type.lower()
    
        self.ollama_url = self.ollama_url or "http://localhost:11434/api/generate"
        # Updated default prompt template to include source language and Markdown instructions
        self.prompt_template = effective_prompt_template or \
                               ("Translate the following Markdown text from {source_language} to {target_language}.\n"
                                "CRITICAL RULES:\n"
                                "1. ONLY return the translated text - no explanations, notes, or commentary\n"
                                "2. DO NOT add translator notes like '（注：...）' or any explanatory text\n"
                                "3. DO NOT explain translation decisions or reasoning\n"
                                "4. Follow strict book translation standards - translate content only\n"
                                "5. Preserve all original Markdown formatting exactly\n"
                                "6. If source and target languages are the same, return original text unchanged\n\n"
                                "Original Markdown:\n```{chunk}```")

        # Basic Validations
        if not self.service_type:
            logger.error("Service type is required for TranslationService.")
            raise ValueError("Service type is required.")
        
        # Type-specific validations
        service_id_for_logging = service_name_from_config or f"(direct init: {self.service_type})"
        if self.service_type in ["siliconflow", "deepseek", "openrouter", "openai_compatible_chat"]:
            if not self.openai_compatible_base_url:
                error_msg = f"Config error: 'openai_compatible_base_url' is missing for service '{service_id_for_logging}' of type '{self.service_type}'."
                logger.error(error_msg)
                raise ValueError(error_msg)
            if not self.model_name:
                logger.warning(f"Config warning: 'model_name' is missing for service '{service_id_for_logging}' of type '{self.service_type}'.")
                # API key might be optional if base_url points to a local model not needing one.
                # If API key is truly needed, the API call will fail later, which is acceptable.
        elif self.service_type == "third_party_completion":
            if not self.legacy_completion_api_url:
                error_msg = f"Config error: 'legacy_completion_api_url' (or 'api_url') is missing for service '{service_id_for_logging}' of type 'third_party_completion'."
                logger.error(error_msg)
                raise ValueError(error_msg)
            if not self.model_name:
                 logger.warning(f"Config warning: 'model_name' is missing for service '{service_id_for_logging}' of type 'third_party_completion'.")
            # api_key also typically required

    def _build_prompt(self, chunk, source_language, target_language):
        # Now includes source_language in the format call
        return self.prompt_template.format(source_language=source_language, target_language=target_language, chunk=chunk)

    @retry_with_backoff(max_retries=3, initial_delay=1, backoff_factor=2)
    def translate_chunk(self, chunk, target_language=None, source_language=None):
        # Use instance defaults if specific languages are not provided
        eff_target_language = target_language or self.default_target_language
        eff_source_language = source_language or self.default_source_language

        user_content_prompt = self._build_prompt(chunk, eff_source_language, eff_target_language)

        if self.service_type == "ollama":
            payload = {
                "model": self.model_name or "qwen2.5:7b",
                "prompt": user_content_prompt,
                "stream": False
            }
            try:
                response = requests.post(self.ollama_url, json=payload, timeout=30)
                if response.status_code == 200:
                    result = response.json().get("response", "")
                    return _clean_translator_notes(result)
                else:
                    raise Exception(f"Ollama translation failed ({response.status_code}): {response.text}")
            except requests.exceptions.Timeout:
                raise Exception("Ollama translation timeout after 30 seconds")
            except requests.exceptions.ConnectionError:
                raise Exception("Cannot connect to Ollama service")

        elif self.service_type in ["siliconflow", "deepseek", "openrouter", "openai_compatible_chat"]:
            if not self.openai_compatible_base_url:
                raise ValueError(f"openai_compatible_base_url not configured for {self.service_type}")
            if not self.api_key:
                logger.warning(f"api_key not configured for {self.service_type}, API call might fail if required.")
            if not self.model_name:
                raise ValueError(f"model_name not configured for {self.service_type}")

            endpoint = f"{self.openai_compatible_base_url.rstrip('/')}/chat/completions"
            
            headers = {"Authorization": f"Bearer {self.api_key}"}
            # Add service-specific headers if needed, e.g. for OpenRouter:
            # if self.service_type == "openrouter":
            #     headers["HTTPAuthorization"] = f"Bearer {self.api_key}" # Example, often "Authorization" works
            #     headers["X-Title"] = "PDF-Translator" # Optional for OpenRouter

            messages = [
                # {"role": "system", "content": "You are an expert translator."}, # Optional system prompt
                {"role": "user", "content": user_content_prompt}
            ]
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": 1000,  # Consider making configurable
                "temperature": 0.7, # Common default, consider making configurable
                "stream": False
                # Add other parameters like top_p, frequency_penalty as needed, potentially from __init__
            }

            try:
                response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    try:
                        result = response.json()["choices"][0]["message"]["content"].strip()
                        return _clean_translator_notes(result)
                    except (KeyError, IndexError, TypeError) as e:
                        raise Exception(f"Failed to parse response from {self.service_type}: {e} - Response: {response.text}")
                else:
                    raise Exception(f"{self.service_type} translation failed ({response.status_code}): {response.text}")
            except requests.exceptions.Timeout:
                raise Exception(f"{self.service_type} translation timeout after 30 seconds")
            except requests.exceptions.ConnectionError:
                raise Exception(f"Cannot connect to {self.service_type} service")
        
        elif self.service_type == "third_party_completion": # Renamed from original "third_party"
            if not self.legacy_completion_api_url:
                raise ValueError(f"api_url (for legacy_completion_api_url) not configured for third_party_completion")
            if not self.api_key: 
                logger.warning(f"api_key not configured for {self.service_type}, API call might fail if required.")
            if not self.model_name:
                raise ValueError(f"model_name not configured for third_party_completion")

            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "model": self.model_name,
                "prompt": user_content_prompt,
                "max_tokens": 1000  # According to original code
            }
            try:
                response = requests.post(self.legacy_completion_api_url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    try:
                        # Original third_party used this response structure
                        result = response.json()["choices"][0]["text"].strip()
                        return _clean_translator_notes(result)
                    except (KeyError, IndexError, TypeError) as e:
                         raise Exception(f"Failed to parse response from third_party_completion: {e} - Response: {response.text}")
                else:
                    raise Exception(f"Third-party (completion) translation failed ({response.status_code}): {response.text}")
            except requests.exceptions.Timeout:
                raise Exception("Third-party translation timeout after 30 seconds")
            except requests.exceptions.ConnectionError:
                raise Exception("Cannot connect to third-party service")
        else:
            raise ValueError(f"Unsupported translation service type: {self.service_type}")

    def test_connection(self):
        """
        测试翻译服务连接是否正常

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # 使用一个简单的测试文本来验证服务连接
            test_text = "Hello, this is a connection test."

            if self.service_type == "ollama":
                # 测试Ollama连接
                payload = {
                    "model": self.model_name or "qwen2.5:7b",
                    "prompt": f"Translate this test sentence: {test_text}",
                    "stream": False
                }
                response = requests.post(self.ollama_url, json=payload, timeout=10)
                if response.status_code == 200:
                    return True, "Ollama服务连接正常"
                else:
                    return False, f"Ollama服务连接失败: {response.status_code} - {response.text}"

            elif self.service_type in ["siliconflow", "deepseek", "openrouter", "openai_compatible_chat"]:
                # 测试OpenAI兼容API连接
                endpoint = f"{self.openai_compatible_base_url.rstrip('/')}/chat/completions"
                headers = {"Authorization": f"Bearer {self.api_key}"}

                messages = [
                    {"role": "user", "content": f"Translate this test sentence: {test_text}"}
                ]

                payload = {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": 50,
                    "temperature": 0.7,
                    "stream": False
                }

                response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
                if response.status_code == 200:
                    return True, f"{self.service_type}服务连接正常"
                elif response.status_code == 401:
                    return False, f"API认证失败 (401): 请检查API密钥是否正确"
                elif response.status_code == 429:
                    return False, f"请求频率限制 (429): 请稍后重试"
                else:
                    return False, f"服务连接失败 ({response.status_code}): {response.text[:200]}"

            elif self.service_type == "third_party_completion":
                # 测试第三方完成API连接
                headers = {"Authorization": f"Bearer {self.api_key}"}
                payload = {
                    "model": self.model_name,
                    "prompt": f"Translate this test sentence: {test_text}",
                    "max_tokens": 50
                }

                response = requests.post(self.legacy_completion_api_url, headers=headers, json=payload, timeout=10)
                if response.status_code == 200:
                    return True, "第三方服务连接正常"
                else:
                    return False, f"第三方服务连接失败 ({response.status_code}): {response.text[:200]}"

            else:
                return False, f"不支持的服务类型: {self.service_type}"

        except requests.exceptions.Timeout:
            return False, "连接超时：服务响应时间过长"
        except requests.exceptions.ConnectionError:
            return False, "连接错误：无法连接到服务"
        except Exception as e:
            return False, f"测试连接时发生错误: {str(e)}"

def translate_book(chunks, translation_service, 
                   target_language=None, source_language=None, progress_queue=None,
                   cache_file_path=None, force_translate=False, original_pdf_filename="unknown.pdf",
                   should_abort_check=None):
    translated_chunks = []
    total_chunks = len(chunks)
    
    eff_target_language = target_language if target_language is not None else translation_service.default_target_language
    eff_source_language = source_language if source_language is not None else translation_service.default_source_language
    
    # Load existing cache if a path is provided
    translations_cache = {}
    if cache_file_path and not force_translate:
        translations_cache = _load_translation_cache(cache_file_path)
        logger.info(f"Loaded {len(translations_cache)} items from cache file: {cache_file_path}")
    elif force_translate:
        logger.info("Cache will be ignored due to --force_translate flag.")

    cache_updated = False
    logger.info(f"Starting book translation: {total_chunks} chunks, from '{eff_source_language}' to '{eff_target_language}'")

    page_comment_pattern = r"^<!-- Page \d+ -->$" # Regex to identify page comments

    for i, chunk in enumerate(chunks, 1):
        # 检查是否应该中止翻译
        if should_abort_check:
            abort_status = should_abort_check()
            logger.debug(f"中止检查: 块 {i}/{total_chunks}, 中止状态: {abort_status}")
            if abort_status:
                logger.warning("翻译被用户中止")
                if progress_queue:
                    progress_queue.put(('progress', "用户中止了翻译任务"))
                # 返回已翻译的部分和剩余未翻译的原文
                remaining_chunks = chunks[i-1:]  # 当前及后续未翻译的块
                # 将未翻译的部分保持原样
                translated_chunks.extend(remaining_chunks)
                break
            
        progress_message_prefix = f"翻译进度: {i}/{total_chunks} ({i/total_chunks*100:.2f}%)"
        translated_text = None # Renamed from 'translated' to avoid confusion
        cache_key = ""

        # Check if the chunk is a page comment
        if re.match(page_comment_pattern, chunk.strip()):
            logger.info(f"{progress_message_prefix} - Chunk is a page comment, skipping translation: '{chunk.strip()}'")
            translated_text = chunk # Use the original chunk as the "translated" text
            translated_chunks.append(translated_text)
            
            # Also add to cache so it's not re-processed unnecessarily if not forcing
            # And so it's part of the saved cache file
            if cache_file_path: # Only try to cache if caching is enabled
                cache_key = _get_chunk_cache_key(chunk, "comment", "comment") # Special lang for comments
                if cache_key not in translations_cache or translations_cache.get(cache_key) != chunk:
                    translations_cache[cache_key] = chunk
                    cache_updated = True

            if progress_queue:
                progress_queue.put(('progress', f"{progress_message_prefix} - Page comment, skipped & preserved."))
            continue # Move to the next chunk

        # If not a page comment, proceed with normal caching and translation logic
        if cache_file_path: # Only try to use cache if a path is provided
            cache_key = _get_chunk_cache_key(chunk, eff_source_language, eff_target_language)
            if not force_translate and cache_key in translations_cache:
                cached_translation = translations_cache[cache_key]
                logger.info(f"{progress_message_prefix} - Found in cache: '{chunk[:50]}...' -> '{cached_translation[:50]}...'")
                translated_chunks.append(cached_translation)
                if progress_queue:
                    progress_queue.put(('progress', f"{progress_message_prefix} - Loaded from cache."))
                continue # Move to the next chunk
            elif force_translate:
                logger.info(f"{progress_message_prefix} - Force translate enabled, ignoring cache for reading for: '{chunk[:50]}...'")

        # If not in cache or force_translate is True, then translate
        try:
            logger.info(f"{progress_message_prefix} - Translating: '{chunk[:50]}...'")
            if progress_queue:
                progress_queue.put(('progress', f"{progress_message_prefix} - Translating..."))
            
            translated_text = translation_service.translate_chunk(
                chunk,
                target_language=eff_target_language,
                source_language=eff_source_language
            )
            translated_chunks.append(translated_text)
            
            # Update cache with new translation if caching is enabled
            if cache_file_path and translated_text is not None: # Also check if translation was successful
                # Ensure the cache_key is generated if it wasn't (e.g., if force_translate was true but no cache_file_path originally)
                # However, cache_key should be set if cache_file_path is true from the block above.
                if not cache_key: # Should ideally not happen if cache_file_path is set
                     cache_key = _get_chunk_cache_key(chunk, eff_source_language, eff_target_language)
                
                if translations_cache.get(cache_key) != translated_text:
                    translations_cache[cache_key] = translated_text
                    cache_updated = True
                logger.info(f"{progress_message_prefix} - Translated and cached: '{chunk[:50]}...' -> '{translated_text[:50]}...'")

        except Exception as e:
            error_message = f"[CHUNK {i} ERROR: {type(e).__name__}: {str(e)[:100]}]"
            logger.error(f"{progress_message_prefix} - Error translating chunk: {e}. Original chunk: '{chunk[:100]}...'")
            
            # 提供更友好的错误信息
            error_type = type(e).__name__
            if "timeout" in str(e).lower() or "Timeout" in error_type:
                user_friendly_error = f"翻译超时，请检查网络连接或服务状态"
            elif "connection" in str(e).lower() or "Connection" in error_type:
                user_friendly_error = f"无法连接到翻译服务，请检查服务地址"
            else:
                user_friendly_error = f"翻译服务错误: {error_type}"
            
            translated_chunks.append(f"[ERROR: {user_friendly_error}] - {chunk[:50]}...")
            # Do not cache errors, or cache them with a special marker if needed later.
            # For now, errors are not cached to allow retries on next run.
            if progress_queue:
                progress_queue.put(('progress', f"{progress_message_prefix} - {user_friendly_error}"))
        
    # Save updated cache if it has changed
    if cache_file_path and cache_updated:
        _save_translation_cache(cache_file_path, translations_cache, original_pdf_filename)
    elif not cache_file_path:
        logger.info("Cache path not provided, skipping cache save.")

    return translated_chunks