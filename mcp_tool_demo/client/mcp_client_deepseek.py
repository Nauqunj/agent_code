"""
# 集成 DeepSeek 的 MCP 客户端
#参考官方案例：https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/clients/simple-chatbot/mcp_simple_chatbot/main.py


# 本模块实现了一个模型上下文协议（MCP）客户端，该客户端使用 DeepSeek 的 API
# 来处理查询并与 MCP 工具进行交互。它演示了如何：
# 1. 连接到 MCP 服务器
# 2. 使用 DeepSeek 的 API 来处理查询
# 3. 处理工具调用和响应
# 4. 维护一个交互式聊天循环

# 所需环境变量：
# DEEPSEEK_API_KEY：DeepSeek API 密钥 (格式：sk-xxxx...)
# DEEPSEEK_BASE_URL：DeepSeek API 基础 URL (https://api.deepseek.com)
# DEEPSEEK_MODEL：DeepSeek 模型名称 (例如 deepseek-chat)

"""

import json
import asyncio
import logging
import os
from typing import Optional, Dict, Any, List, Tuple
from contextlib import AsyncExitStack

from openai import OpenAI
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
load_dotenv()
class Configuration:
    """配置管理类，负责管理和验证环境变量"""
    def __init__(self) -> None:
        self.load_env()
        self._validate_env()
    @staticmethod
    def load_env() -> None:
        """从.env文件加载环境变量"""
        load_dotenv()
    
    def _validate_env(self)-> None:
        """验证必需的环境变量是否存在"""
        required_vars = ["DEEPSEEK_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"缺少必需的环境变量: {', '.join(missing_vars)}")
    @property
    def api_key(self) -> str:
        """获取 DeepSeek API 密钥"""
        return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    @property
    def base_url(self) -> str:
        """获取 DeepSeek API 基础 URL"""
        return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    @property
    def model(self) -> str:
        """获取 DeepSeek 模型名称"""
        return os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    
class Tool:
    """MCP 工具类，表示一个具有属性的工具"""
    def __init__(self,name: str, description: str,input_schema: Dict[str, Any] )-> None:
        """
        初始化工具
        
        Args:
            name: 工具名称
            description: 工具描述
            input_schema: 输入参数模式
        """
        self.name = name
        self.description = description
        self.input_schema = input_schema