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
    
def generate_response(messages: List[Dict]) -> str:
    """
    调用LLM生成响应

    参数:
        messages: 消息列表，包含系统提示和对话历史

    返回:
        LLM生成的响应文本
    """
    # 使用LiteLLM调用deepseek
    client = OpenAI(
        base_url=os.getenv("DEEPSEEK_BASE_URL"),
        api_key=os.getenv("DEEPSEEK_API_KEY")
    )
    response = client.chat.completions.create(
        model=os.getenv("MODEL_NAME"),
        messages=messages,
        max_tokens=1024
    )
    return response.choices[0].message.content.strip()

def parse_action(response: str) -> Dict:
    """
    解析LLM响应，提取结构化的工具调用指令

    参数:
        response: LLM的响应文本

    返回:
        包含工具名称和参数的字典
    """
    try:
        # 从响应中提取action代码块
        response = extract_markdown_block(response, "action")
        # 将JSON字符串解析为Python字典
        response_json = json.loads(response)
        # 验证响应格式是否正确
        if "tool_name" in response_json and "args" in response_json:
            return response_json
        else:
            # 如果格式不正确，返回错误信息
            return {"tool_name": "error", "args":{"message": "You must respond with a JSON tool invocation."}}
    except json.JSONDecodeError:
        return {"tool_name":"errot", "args":{"message": "Invalid JSON response. You must respond with a JSON tool invocation."}}

# ===== 智能体可用的工具函数 =====
def list_files()-> List[str]:
    """
    列出当前目录中的所有文件

    返回:
        文件名列表
    """
    return os.listdir()

def read_file(file_name: str)-> str:
    """
    读取指定文件的内容

    参数:
        file_name: 要读取的文件名

    返回:
        文件内容或错误信息
    """
    try:
        with open(file_name,"r") as file:
            return file.read(   )
    except FileNotFoundError:
        return f"Error: {file_name} not Found"
    except Exception as e:
        return f"error: {str(e)}"
# ===== 智能体系统提示词定义 =====
# 这个提示词定义了智能体的行为规则和可用工具

agent_rules = [{
    "role": "system",
    "content": """
    你是一个AI智能体，可以通过使用可用工具来执行任务。
    可用工具:
    ```json
{
    "list_files": {
        "description": "列出当前目录中的所有文件。",
        "parameters": {}
    },
    "read_file": {
        "description": "读取文件的内容。",
        "parameters": {
            "file_name": {
                "type": "string",
                "description": "要读取的文件名。"
            }
        }
    },
    "terminate": {
        "description": "结束智能体循环并提供任务摘要。",
        "parameters": {
            "message": {
                "type": "string",
                "description": "返回给用户的摘要消息。"
            }
        }
    }
}
```
如果用户询问文件、文档或内容，请先列出文件，然后再读取它们。

当你完成任务后，使用"terminate"工具结束对话，我将向用户提供结果。

重要！！！每个响应都必须包含一个动作。
你必须始终按照以下格式响应：

<停下来逐步思考。参数映射到args。在这里插入你逐步思考的丰富描述。>

```action
{
    "tool_name": "插入工具名称",
    "args": {...在这里填入任何必需的参数...}
}```
"""
}]

if __name__ == "__main__":
    print("开始")
    print(os.getenv("DEEPSEEK_API_KEY"))
    # ===== 智能体主循环初始化 =====
    iterations = 0        # 当前迭代次数
    max_iterations = 10   # 最大迭代次数，防止无限循环
    # 获取用户任务
    user_task = input("What would you like me to do? ")

    # 初始化对话记忆，包含用户的任务
    memory = [{"role": "user", "content": user_task}]
    # ===== 智能体主循环 =====
    # 这是智能体的核心工作循环，持续执行直到任务完成或达到最大迭代次数
    while iterations < max_iterations:
        # 1. 构建提示：将智能体规则与对话记忆结合
        prompt = agent_rules + memory
        # 2. 调用LLM生成响应
        print("Agent thinking...")
        response = generate_response(prompt)
        print(f"Agent response: {response}")

        # 3. 解析响应以确定要执行的动作
        action = parse_action(response)
        result = "Action executed"  # 默认结果
        # 4. 根据解析出的动作执行相应的工具函数
        if action["tool_name"] == "list_files":
            result = {"result": list_files()}
        elif action["tool_name"] == "read_file":
            result = {"result": read_file(action["args"]["file_name"])}
        elif action["tool_name"] == "error":
            result = {"error": action["args"]["message"]}
        elif action["tool_name"] == "terminate":
            print(action["args"]["message"])
            break  # 终止循环
        else:
            result = {"error": "Unknown action: " + action["tool_name"]}

        print(f"Action result: {result}")
        # 5. 更新对话记忆，添加智能体响应和执行结果
        memory.extend([
            {"role": "assistant", "content": response},
            {"role": "system", "content": json.dumps(result)}
        ])
        # 6. 检查终止条件
        if action["tool_name"] == "terminate":
            break

        iterations += 1  # 增加迭代计数
