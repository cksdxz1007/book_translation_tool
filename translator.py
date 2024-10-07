import requests

class TranslationService:
    def __init__(self, service_type, api_url=None, api_key=None, model_name=None, ollama_url=None):
        self.service_type = service_type
        self.api_url = api_url
        self.api_key = api_key
        self.model_name = model_name
        self.ollama_url = ollama_url or "http://localhost:11434/api/generate"

    def translate_chunk(self, chunk, target_language):
        if self.service_type == "ollama":
            return self.ollama_translate(chunk, target_language)
        elif self.service_type == "third_party":
            return self.third_party_translate(chunk, target_language)
        else:
            raise ValueError("Unsupported translation service")

    def ollama_translate(self, chunk, target_language):
        payload = {
            "model": self.model_name or "qwen2.5:7b",
            "prompt": f"Translate the following text to {target_language}:\n\n{chunk}",
            "stream": False
        }
        response = requests.post(self.ollama_url, json=payload)
        if response.status_code == 200:
            return response.json()["response"]
        else:
            raise Exception(f"Translation failed: {response.text}")

    def third_party_translate(self, chunk, target_language):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model_name,
            "prompt": f"Translate the following text to {target_language}:\n\n{chunk}",
            "max_tokens": 1000  # 根据需要调整
        }
        response = requests.post(self.api_url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["choices"][0]["text"].strip()
        else:
            raise Exception(f"Translation failed: {response.text}")

def translate_book(chunks, translation_service, target_language="Chinese", progress_queue=None):
    translated_chunks = []
    total_chunks = len(chunks)
    for i, chunk in enumerate(chunks, 1):
        try:
            translated = translation_service.translate_chunk(chunk, target_language)
            translated_chunks.append(translated)
            progress = f"翻译进度: {i}/{total_chunks} ({i/total_chunks*100:.2f}%)"
            print(progress)
            if progress_queue:
                progress_queue.put(('progress', progress))
        except Exception as e:
            error_msg = f"翻译第 {i} 块时出错: {str(e)}"
            print(error_msg)
            if progress_queue:
                progress_queue.put(('progress', error_msg))
    
    return translated_chunks