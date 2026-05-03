import getpass
from dotenv import load_dotenv
import json  # 用于JSON数据处理
import os    # 用于操作系统相关操作
import sys   # 用于系统相关操作
from typing import List, Dict   # 类型提示，提高代码可读性
from openai import OpenAI       # 用于调用OpenAI API

load_dotenv()
# ===========================================
# 工具函数定义 - 智能体可以调用的具体功能
# ===========================================

def list_files()-> List[str]:
    """
    列出当前目录中的所有文件和文件夹

    返回值:
        List[str]: 包含当前目录中所有文件和文件夹名称的列表
    """
    return os.listdir('.')

def read_file(file_name: str)-> str:
    """
    读取指定文件的内容

    参数:
        file_name (str): 要读取的文件名

    返回值:
        str: 文件内容（如果成功）或错误信息（如果失败）
    """
    try:
        with open(file_name) as file:
            return file.read()
    except FileNotFoundError:
        return f"Error: {file_name} not found"
    except Exception as e:
        return f"Error: {str(e)}"

def terminate(message : str) -> None:
    """
    终止智能体循环并显示总结消息

    参数:
        message (str): 要显示给用户的终止消息
    """
    return f"Termination message: {message}"

# ===========================================
# 工具函数映射字典
# ===========================================
# 将工具名称映射到对应的Python函数
# 这样智能体就可以通过工具名称动态调用相应的函数
tool_functions = {
    "list_file": list_files,
    "read_file": read_file,
    "terminate": terminate
}
# ===========================================
# 工具配置 - 定义智能体可以使用的工具
# ===========================================
# 这个配置告诉大语言模型有哪些工具可以使用
# 以及每个工具的参数要求
tools = [
    {
        "type": "function",
        "function":{
            "name": "list_file",
            "description":"Returns a list of files in the directory.",
            "parameters":{"type": "object", "properties": {}, "required": []} 
        }
    },
    {
        "type":"function",
        "function":{
            "name":"read_file",
            "description":"Reads the content of a specified file in the directory.",
            "parameters":{
                "type":"object",
                "properties":{
                    "file_name":{"type":"string"}
                },
                "required":["file_name"]
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name": "terminate",
            "description":"Terminates the conversation. No further actions or interactions are possible after this. Prints the provided message for the user.",
            "parameters": {
                "type":"object",
                "properties":{
                    "message": {"type": "string"}
                },
                "required":["message"]
            }
        }
    }
]
# ===========================================
# 智能体规则和系统提示
# ===========================================
# 定义智能体的行为规则和角色定位
agent_rules = [{
    "role": "system",  # 系统角色，定义智能体的基本行为
    "content": """
    You are an AI agent that can perform tasks by using available tools.

If a user asks about files, documents, or content, first list the files before reading them.

When you are done, terminate the conversation by using the "terminate" tool and I will provide the results to the user.
"""
}]


if __name__ == "__main__":
    print('Agent101/')
    # ===========================================
    # 智能体循环参数初始化
    # ===========================================
    iterations = 0        # 当前迭代次数计数器
    max_iterations = 10   # 最大迭代次数限制，防止无限循环
    # 获取用户任务输入
    user_task = input("What would you like me to do? ")

    # 初始化对话记忆，存储用户的任务
    memory = [{"role": "user", "content": user_task}]
    # ===========================================
    # 智能体主循环 - 核心执行逻辑
    # ===========================================
    while iterations < max_iterations:
        # 构建完整的消息列表：系统规则 + 对话记忆
        messages = agent_rules + memory
        # 调用大语言模型，获取响应
        # 模型会根据用户任务和可用工具决定下一步行动
        client=OpenAI(
            base_url=os.getenv("DEEPSEEK_BASE_URL"),
            api_key=os.getenv("DEEPSEEK_API_KEY"),
        )
        response = client.chat.completions.create(
            model=os.getenv("MODEL_NAME"),  # 指定使用的模型
            messages=messages,      # 发送消息历史
            tools=tools,           # 提供可用工具列表
            max_tokens=1024       # 限制响应长度
        )
        # ===========================================
        # 处理工具调用响应
        # ===========================================
        if response.choices[0].message.tool_calls:
            # 如果模型决定调用工具，提取工具信息
            tool = response.choices[0].message.tool_calls[0]
            tool_name = tool.function.name                    # 获取工具名称
            tool_args = json.loads(tool.function.arguments)  # 解析工具参数
            # 构建动作记录，用于记忆管理
            action = {
                "tool_name": tool_name,
                "args": tool_args
            }
            # ===========================================
            # 工具执行逻辑
            # ===========================================
            if tool_name == "terminate":
                # 如果是终止工具，显示消息并退出循环
                print(f"Termination message: {tool_args['message']}")
                break
            elif tool_name in tool_functions:
                # 如果是已知工具，尝试执行
                try:
                    # 动态调用对应的工具函数
                    result = {"result": tool_functions[tool_name](**tool_args)}
                except Exception as e:
                    # 工具执行出错时的错误处理
                    result = {"error":f"Error executing {tool_name}: {str(e)}"}
            else:
                # 未知工具的错误处理
                result = {"error": f"Unknown tool: {tool_name}"}
            # 显示执行过程和结果
            print(f"Executing: {tool_name} with args {tool_args}")
            print(f"Result: {result}")
            memory.extend([
                {"role": "assistant", "content": json.dumps(action)},  # 记录智能体的动作
                {"role": "user", "content": json.dumps(result)}       # 记录执行结果
            ])
        else:
            # 如果模型没有调用工具，直接返回文本响应
            result = response.choices[0].message.content
            print(f"Response: {result}")
            break  # 结束循环