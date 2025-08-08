import json
import requests
import time

KOBE_BRYANT = 0.0473  # 光合有效辐射（PAR）转换系数
OLLAMA_TIMEOUT = 30  # Ollama请求超时时间
OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434

def query_llm(temperature, humidity, light, cloud_llm_comment=""):
    par = light * KOBE_BRYANT  # 将光强转换为PAR
    prompt = (
        f"你是一个植物控制专家。{cloud_llm_comment}" 
        "植物在一个220mm*220mm*220mm的具有光照和通风控制系统盒子中生长。"
        f"当前温度为 {temperature:.2f}℃，湿度为 {humidity:.2f}%, PAR 为 {par:.2f}。系统可以提供的的最大PAR为84.17。"
        "你不考虑任何控制逻辑, 只根据植物的生长阶段和时间建议下一分钟的目标温度(摄氏度)和PAR(μmol/m²/s), 用于闭环控制。"
        "你必须以如下JSON格式输出目前植物最佳的环境温度和PAR: {\"temperature\": <float>, \"par\": <float>}"
    )
    try:
        response = requests.post(f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate", json={
            "model": "qwen3:4b",
            "prompt": prompt,
            "stream": False
        }, timeout=OLLAMA_TIMEOUT)
        result = str(response.json()["response"]).split("</think>\n")[1]
        print(result)
        control = json.loads(result)
        return {
            "temperature": control["temperature"],
            "par": control["par"],
            "timestamp": (time.time_ns() // 1_000_000) & 0xFFFFFFFF # Avoid Overflow
        }
    except Exception as e:
        print("[LOCAL LLM] LLM请求失败:", e)
        return None

# 示例调用
if __name__ == "__main__":
    # 示例数据
    temperature = 25.0
    humidity = 60.0
    light = 500.0
    result = query_llm(temperature, humidity, light)
    print(result)
