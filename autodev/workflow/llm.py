import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 加载 .env 文件中的环境变量
load_dotenv()

# 初始化 DeepSeek 模型
def get_llm():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("请在 .env 文件中配置 DEEPSEEK_API_KEY")
    
    # DeepSeek 完全兼容 OpenAI 的接口，只需要改 base_url 和 model 名字
    return ChatOpenAI(
        model="deepseek-chat",  # deepseek-chat 是 V3 模型，编码和逻辑极强
        api_key=api_key,
        base_url="https://api.deepseek.com",
        max_tokens=4000,
        temperature=0.2  # 架构设计需要严谨，所以 temperature 调低一点
    )