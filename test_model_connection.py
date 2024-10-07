import requests
import sys

def test_ollama_connection(model_name="qwen2.5:7b"):
    """
    测试与Ollama API的连接并验证模型是否正常工作
    """
    url = "http://localhost:11434/api/generate"
    test_prompt = "Translate this sentence to Chinese: Hello, world!"
    
    payload = {
        "model": model_name,
        "prompt": test_prompt,
        "stream": False
    }
    
    try:
        print(f"正在测试与 {model_name} 模型的连接...")
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()["response"]
            print("连接成功！模型返回的翻译结果：")
            print(result)
            return True
        else:
            print(f"连接失败。HTTP状态码：{response.status_code}")
            print(f"错误信息：{response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"连接错误：{e}")
        return False

def main():
    if len(sys.argv) > 1:
        model_name = sys.argv[1]
    else:
        model_name = "qwen2.5:7b"
    
    success = test_ollama_connection(model_name)
    
    if success:
        print("\n模型连接测试成功！")
    else:
        print("\n模型连接测试失败。请检查Ollama服务是否正在运行，以及模型是否正确安装。")

if __name__ == "__main__":
    main()