"""
Gemini 模型连接测试脚本
可通过环境变量 http_proxy / https_proxy 配置代理
"""
import os
from google import genai

from config import GEMINI_API_KEY

# 代理配置（可选，通过环境变量设置）
# os.environ['http_proxy'] = 'http://127.0.0.1:7890'
# os.environ['https_proxy'] = 'http://127.0.0.1:7890'

client = genai.Client(api_key=GEMINI_API_KEY)

try:
    # 使用你列表里有的具体别名，通常这个别名的配额最稳定
    model_id = "gemini-flash-latest"

    print(f"正在尝试连接模型: {model_id}...")

    response = client.models.generate_content(
        model=model_id,
        contents="你好，请回复'连接成功'。"
    )

    print("--- 测试结果 ---")
    print(f"状态: 成功")
    print(f"回复: {response.text}")

except Exception as e:
    print("--- 测试失败 ---")
    print(f"错误详情: {e}")