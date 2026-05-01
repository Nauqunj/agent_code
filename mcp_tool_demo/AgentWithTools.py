# 导入必要的模块
import getpass
from dotenv import load_dotenv
import json  # 用于JSON数据处理
import os    # 用于操作系统相关操作
import sys   # 用于系统相关操作
from typing import List, Dict   # 类型提示，提高代码可读性
from openai import OpenAI       # 用于调用OpenAI API
# 加载环境变量
load_dotenv()
# api_key=os.getenv("DEEPSEEK_API_KEY"),
# base_url="https://api.deepseek.com"

def extract_markdown_block(response: str, block_type: str ='json') -> str:
    """
    从LLM响应中提取代码块内容

    参数:
        response: LLM的原始响应文本
        block_type: 要提取的代码块类型，默认为"json"

    返回:
           提取出的代码块内容
    """
    # 检查响应中是否包含代码块标记
    if not '```' in response:
        return response
    # 分割响应并提取第一个代码块
    code_block = response.split('```')[1].strip()
    # 如果代码块以指定类型开头，则移除类型标识
    if code_block.startswith(block_type):
        code_block = code_block[len(block_type):].strip()
    return code_block
    

if __name__ == "__main__":
    print("开始")
    print(os.getenv("DEEPSEEK_API_KEY"))