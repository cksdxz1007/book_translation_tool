import requests
import logging # Add logging
import json # New import
import os   # New import
import hashlib # New import
import re # New import for page comment regex
from config_loader import load_service_config, get_api_key_from_config # New imports

logger = logging.getLogger(__name__) # Add logger for this module

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
            all_configs = config_data_for_testing if config_data_for_testing else load_service_config()
            
            if not all_configs or "services" not in all_configs or \
               service_name_from_config not in all_configs["services"]:
                error_msg = f"Service '{service_name_from_config}' not found in configuration or configuration failed to load."
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            service_config = all_configs["services"][service_name_from_config]
            
            self.service_type = service_config.get('service_type')
            self.model_name = service_config.get('model_name')
            self.api_key = get_api_key_from_config(service_config) # Handles direct key or env var
            
            self.ollama_url = service_config.get('ollama_url')
            self.openai_compatible_base_url = service_config.get('openai_compatible_base_url')
            # Check for 'legacy_completion_api_url' first, then 'api_url' for backward compatibility in config
            self.legacy_completion_api_url = service_config.get('legacy_completion_api_url', service_config.get('api_url'))
            # Override defaults from config if present
            self.default_source_language = service_config.get('default_source_language', self.default_source_language)
            self.default_target_language = service_config.get('default_target_language', self.default_target_language)
            effective_prompt_template = service_config.get('custom_prompt_template', custom_prompt_template) # Config overrides direct param

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
                                "ONLY return the translated text, ensuring it is also valid Markdown.\n"
                                "DO NOT add any introductory phrases, explanations, or any text not present in the translated original.\n"
                                "Preserve all original Markdown formatting and structure precisely.\n"
                                "Only translate the textual content. Do not alter or translate Markdown tags (e.g., #, *, **, ```, <!-- Page X -->).\n\n"
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
            response = requests.post(self.ollama_url, json=payload)
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                raise Exception(f"Ollama translation failed ({response.status_code}): {response.text}")

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

            response = requests.post(endpoint, headers=headers, json=payload)
            if response.status_code == 200:
                try:
                    return response.json()["choices"][0]["message"]["content"].strip()
                except (KeyError, IndexError, TypeError) as e:
                    raise Exception(f"Failed to parse response from {self.service_type}: {e} - Response: {response.text}")
            else:
                raise Exception(f"{self.service_type} translation failed ({response.status_code}): {response.text}")
        
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
            response = requests.post(self.legacy_completion_api_url, headers=headers, json=payload)
            if response.status_code == 200:
                try:
                    # Original third_party used this response structure
                    return response.json()["choices"][0]["text"].strip()
                except (KeyError, IndexError, TypeError) as e:
                     raise Exception(f"Failed to parse response from third_party_completion: {e} - Response: {response.text}")
            else:
                raise Exception(f"Third-party (completion) translation failed ({response.status_code}): {response.text}")
        else:
            raise ValueError(f"Unsupported translation service type: {self.service_type}")

def translate_book(chunks, translation_service, 
                   target_language=None, source_language=None, progress_queue=None,
                   cache_file_path=None, force_translate=False, original_pdf_filename="unknown.pdf"):
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
                progress_queue.put(f"{progress_message_prefix} - Page comment, skipped & preserved.")
            continue # Move to the next chunk

        # If not a page comment, proceed with normal caching and translation logic
        if cache_file_path: # Only try to use cache if a path is provided
            cache_key = _get_chunk_cache_key(chunk, eff_source_language, eff_target_language)
            if not force_translate and cache_key in translations_cache:
                cached_translation = translations_cache[cache_key]
                logger.info(f"{progress_message_prefix} - Found in cache: '{chunk[:50]}...' -> '{cached_translation[:50]}...'")
                translated_chunks.append(cached_translation)
                if progress_queue:
                    progress_queue.put(f"{progress_message_prefix} - Loaded from cache.")
                continue # Move to the next chunk
            elif force_translate:
                logger.info(f"{progress_message_prefix} - Force translate enabled, ignoring cache for reading for: '{chunk[:50]}...'")

        # If not in cache or force_translate is True, then translate
        try:
            logger.info(f"{progress_message_prefix} - Translating: '{chunk[:50]}...'")
            if progress_queue:
                progress_queue.put(f"{progress_message_prefix} - Translating...")
            
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
            error_message = f"[CHUNK {i} ERROR: {e}]"
            logger.error(f"{progress_message_prefix} - Error translating chunk: {e}. Original chunk: '{chunk[:100]}...'")
            translated_chunks.append(error_message) # Add error message to list
            # Do not cache errors, or cache them with a special marker if needed later.
            # For now, errors are not cached to allow retries on next run.
            if progress_queue:
                progress_queue.put(f"{progress_message_prefix} - Error: {e}")
        
    # Save updated cache if it has changed
    if cache_file_path and cache_updated:
        _save_translation_cache(cache_file_path, translations_cache, original_pdf_filename)
    elif not cache_file_path:
        logger.info("Cache path not provided, skipping cache save.")

    return translated_chunks