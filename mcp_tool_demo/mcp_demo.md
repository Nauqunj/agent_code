# Python MCP 天气查询系统 — 小白逐行教程

---

## 一、整体架构（先有个大局观）

```
┌──────────────────┐          ┌──────────────────┐          ┌──────────────┐
│  你的输入        │  ──►     │  MCP Client      │  ──►     │  MCP Server  │  ──►  和风天气 API
│ "北京天气怎么样" │          │  mcp_client.py    │          │weather_server│      (外部网络)
└──────────────────┘          └──────────────────┘          └──────────────┘
                                    │                              │
                                    │   通过 stdio（标准输入输出）   │
                                    │   启动 server 作为子进程       │
                                    └──────────────────────────────┘
```

**MCP 是什么？** MCP（Model Context Protocol）就像一个"USB 协议"——不管你插什么设备（U盘、键盘、鼠标），电脑都能识别。MCP 让 LLM（大语言模型）能统一地调用各种工具，不用管工具是怎么实现的。

**这个项目里的角色：**
- `weather_server.py`：提供两个"工具"——查天气预警、查天气预报。它就像餐厅厨房。
- `mcp_client.py`：连接厨房，把菜单（工具列表）给你看，你点菜后它把菜端回来。它就像服务员。

---

## 二、Server 端逐行详解（weather_server.py）

服务端是"提供能力"的一方。它把自己注册成一个 MCP 服务，告诉外界"我有两个工具可以用"。

### 第 1-3 行：注释

```python
##[和风天气开发服务](https://dev.qweather.com/)
# https://console.qweather.com/setting?lang=zh
# 免费版API有调用次数限制，详情请参考[和风天气定价页面](https://dev.qweather.com/price/)
```

告诉你要用的外部 API 是什么（和风天气），去哪里注册、拿密钥（API Key）。免费版每天有调用次数限制。

### 第 4-16 行：文档字符串

```python
"""
MCP 服务器可以提供三种主要类型的功能：
资源：客户端可以读取的类似文件的数据（例如 API 响应或文件内容）
工具：可由 LLM 调用的函数（经用户批准）
提示：预先编写的模板，帮助用户完成特定任务
...
"""
```

Python 的 `"""..."""` 是**多行注释**（文档字符串），描述这个文件是干嘛的。这里说明 MCP 服务器可以提供三种东西：Resources（资源）、Tools（工具）、Prompts（提示模板）。这个项目只用到了 **Tools**。

### 第 18-24 行：导入依赖

```python
from typing import Any, Dict, List, Optional, Union   # 类型提示，让代码更清晰
import asyncio                                        # Python 的异步编程库
import httpx                                          # 第三方 HTTP 请求库（比 requests 更现代，支持 async）
import os                                             # 操作系统相关功能，比如读环境变量
from urllib.parse import urljoin                      # 拼接 URL 用的工具函数
from mcp.server.fastmcp import FastMCP                # MCP 框架的核心——快速创建 MCP 服务器
from dotenv import load_dotenv                        # 从 .env 文件加载环境变量
from pathlib import Path                              # 处理文件路径的现代方式
```

**对小白的重要概念：**
- `import xxx`：把别人写好的代码（库/模块）引入到你的代码里直接用。
- `from xxx import yyy`：只从某个库里拿某个具体功能，省得写全名。
- `asyncio`："异步"就是"同时可以做多件事"，不阻塞等待。就像你烧水的同时可以切菜，不用等水开了再切。

### 第 27 行：加载环境变量

```python
load_dotenv()
```

从项目根目录的 `.env` 文件读取配置（比如 API Key），存到系统环境变量里。这样做的好处是：敏感信息（密钥）不写在代码里，而是写在 `.env` 文件里，.env 通常加入 .gitignore 不上传。

### 第 29-33 行：创建 MCP 服务器实例

```python
mcp = FastMCP(
    "weather",         # 服务器名称，随便取
    debug=True,        # 开启调试模式，出错时打印详细信息
    host="0.0.0.0"     # 监听所有网络接口（0.0.0.0 表示本机所有 IP）
)
```

创建了一个名叫 "weather" 的 MCP 服务器对象。之后的所有工具函数，都通过 `@mcp.tool()` 装饰器注册到这个服务器上。

### 第 35-36 行：读取配置

```python
QWEATHER_API_BASE = os.getenv("QWEATHER_API_BASE")  # 和风天气 API 的基础 URL
QWEATHER_API_KEY = os.getenv("QWEATHER_API_KEY")    # 和风天气 API 的密钥
```

`os.getenv("变量名")` = 从环境变量读取值。这些值来自 `.env` 文件（由上面的 `load_dotenv()` 加载）。

### 第 38-49 行：URL 规范化函数

```python
def _normalize_base_url(raw_base: Optional[str])-> str:
    if not raw_base:
        raise RuntimeError("未配置 QWEATHER_API_BASE 环境变量")
    base = raw_base.strip()                        # 去掉首尾空格
    if not base.startswith(("http://","https://")):  # 如果没有 http:// 或 https:// 开头
        base = f"https://{base.lstrip()}"          # 自动补上 https://
    if not base.endswith('/'):                     # 如果结尾没有 /
        base = f"{base}/"                          # 自动补上 /
    return base
```

**逐行解释：**
- `_normalize_base_url`：函数名前面加 `_` 是 Python 约定，表示"这是内部使用的函数，外人别调"。
- `raw_base: Optional[str]`：参数可能是字符串也可能是 None。
- `-> str`：返回值是字符串。
- `raw_base.strip()`：比如 `"  hello  "` → `"hello"`。
- `startswith(tuple)`：检查字符串是不是以某个前缀开头。
- `f"https://{base}"`：f-string，花括号里是变量，会被替换成变量的值。比如 `base="api.com"`，结果就是 `"https://api.com"`。

**为什么需要这个函数？** 因为可能有人在 `.env` 里写 `devapi.qweather.com`（没写协议），或者写了 `https://devapi.qweather.com` 但忘了结尾的 `/`。这个函数统一处理，确保 URL 格式正确。

### 第 51-55 行：初始化基础 URL

```python
try:
    _QWEATHER_BASE_URL = _normalize_base_url(QWEATHER_API_BASE)
except RuntimeError as error:
    print("配置错误")
    _QWEATHER_BASE_URL = None
```

`try...except` = "试着做某事，如果出错就执行 except 里的代码"。如果环境变量没配，就打印错误并把 URL 设为 None（后面请求时会检查、跳过）。

### 第 57-96 行：通用 API 请求函数

```python
async def make_qweather_request(endpoint: str, params: Dict[str,any])-> Optional[Dict[str,any]]:
```

**关键概念：`async def`** = 定义一个"异步函数"。异步函数调用时不会阻塞程序，可以边等网络响应边做别的事。

```python
    if not _QWEATHER_BASE_URL:
        print("QWEATHER_API_BASE 未正确配置，已跳过请求。")
        return None
    if not QWEATHER_API_KEY:
        print("QWEATHER_API_KEY 未设置，已跳过请求。")
        return None
```
如果没配 API 地址或密钥，直接返回 None，不发送请求。

```python
    safe_endpoint = endpoint.lstrip('/')                          # 去掉开头的斜杠
    url = urljoin(_QWEATHER_BASE_URL, safe_endpoint)             # 拼接完整 URL
```
`urljoin("https://api.com/v1/", "weather/3d")` → `"https://api.com/v1/weather/3d"`。用它而不是直接 + 号拼接，因为它能正确处理有没有斜杠的情况。

```python
    headers = {
        "X-QW-Api-Key": QWEATHER_API_KEY
    }
```
HTTP 请求头，把 API Key 放在 Header 里传给和风天气服务器做身份认证。

```python
    async with httpx.AsyncClient() as client:
```
`async with` = 异步上下文管理器。自动创建和关闭 HTTP 客户端，不用手动 `client.close()`。

```python
        try:
            print(f"请求 URL: {url}")
            print(f"请求参数: {params}")
            response = await client.get(url, params=params, headers=headers, timeout=30)
```
- `await` = "等待这个异步操作完成"。在 `async` 函数里调用另一个 `async` 函数必须用 `await`。
- `client.get(...)` = 发送 HTTP GET 请求。
- `timeout=30` = 最多等 30 秒，超时就报错。

```python
            response.raise_for_status()   # 如果 HTTP 状态码不是 200，抛出异常
            result = response.json()      # 把响应的 JSON 字符串转成 Python 字典
            return result
        except httpx.HTTPStatusError as e:
            print(f"HTTP 状态错误: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"API 请求错误: {type(e).__name__}: {e}")
            return None
```
两种错误处理：HTTP 状态错误（如 404 找不到、500 服务器挂了），以及其它所有异常。

### 第 98-119 行：格式化预警信息

```python
def format_warning(warning: Dict[str,any]) -> str:
    return f"""
        预警ID: {warning.get('id', '未知')}
        标题: {warning.get('title', '未知')}
        ...
    """
```

- `warning.get('id', '未知')`：从字典里取 `id` 这个 key 的值，如果不存在就返回 `'未知'`（不会报错）。
- 把 API 返回的原始 JSON 数据转换成人类易读的文本。

### 第 120 行：🌟 最关键的装饰器

```python
@mcp.tool()
```

这是整个 MCP 框架的核心！`@mcp.tool()` 是一个**装饰器**。它做了什么？
- 把下面定义的 Python 函数"注册"到 MCP 服务器上
- 自动提取函数的参数类型、文档字符串，生成工具的 schema（描述）
- 当客户端调用这个工具时，框架自动执行这个函数并返回结果

**说人话：** 你写了一个普通 Python 函数，加一行 `@mcp.tool()`，它就变成了一个可以被远程调用的 MCP 工具。

### 第 121-150 行：工具1——获取天气预警

```python
async def get_weather_warning(location: Union[str,int])-> str:
```

- `Union[str, int]`：参数可以是字符串或整数（比如城市ID `101010100` 可以是整数也可以是字符串）。
- `-> str`：返回字符串。

```python
    location = str(location)                    # 统一转成字符串
    params = {"location": location, "lang": "zh"}  # 构造请求参数，lang=zh 表示中文
    data = await make_qweather_request("v7/warning/now", params)  # 调用和风天气预警 API
    if not data:
        return "无法获取预警信息或API请求失败。"
    if data.get("code") != "200":
        return f"API 返回错误: {data.get('code')}"
    warnings = data.get("warning", [])          # 从响应中取预警列表
    if not warnings:
        return f"当前位置 {location} 没有活动预警。"
    formatted_warnings = [format_warning(w) for w in warnings]  # 列表推导式，逐条格式化
    return "\n---\n".join(formatted_warnings)   # 用 --- 分割线连接多条预警
```

**列表推导式** `[format_warning(w) for w in warnings]`：相当于
```python
result = []
for w in warnings:
    result.append(format_warning(w))
```
一行搞定。

**`"\n---\n".join(list)`**：用 `\n---\n`（换行+分割线+换行）把列表里的所有字符串拼接起来。

### 第 152-173 行：格式化天气预报

跟 `format_warning` 同理，把天气预报的原始数据格式化成人读的文本。字段含义：最高温度、最低温度、白天天气、风向风力、湿度、降水量、紫外线等。

### 第 175-212 行：工具2——获取天气预报

```python
@mcp.tool()
async def get_daily_forecast(location: Union[str, int], days: int = 3) -> str:
```

- `days: int = 3`：默认参数，如果不传天数就默认查 3 天。

```python
    valid_days = [3, 7, 10, 15, 30]
    if days not in valid_days:
        days = 3  # 如果传了无效天数，自动改回 3
    endpoint = f"v7/weather/{days}d"  # 动态构造端点：3d、7d、10d、15d、30d
```

### 第 214-220 行：启动入口

```python
if __name__ == "__main__":
    print("正在启动 MCP 天气服务器...")
    mcp.run(transport='stdio')   # 以 stdio（标准输入输出）模式启动服务器
```

**`if __name__ == "__main__"`**：Python 的特殊变量。当直接运行这个文件时，`__name__` 等于 `"__main__"`，就会执行这里的代码。如果被别人 import，就不执行。这是 Python 的标准入口写法。

**`mcp.run(transport='stdio')`**：
- `transport='stdio'`：通过标准输入输出通信。客户端会把服务器作为子进程启动，通过进程间的 stdin/stdout 来收发消息。
- 这是 MCP 最基础的传输方式，不需要网络端口，直接进程间通信。

---

## 三、Client 端逐行详解（mcp_client.py）

客户端是"使用能力"的一方。它启动 server 作为子进程，通过 stdio 跟 server 通信，获取工具列表，调用工具。

### 第 1-9 行：导入

```python
import asyncio
import json
import os
import subprocess    # 启动子进程用
import sys
from typing import Dict, Any, List, Optional
from contextlib import AsyncExitStack     # 异步资源管理器
from mcp import ClientSession, StdioServerParameters, Tool   # MCP 客户端核心类
from mcp.client.stdio import stdio_client                    # stdio 传输的客户端实现
```

`AsyncExitStack`：一个"资源回收站"。你把各种资源（连接、进程等）注册进去，最后不管正常结束还是出错，它都能自动清理这些资源。

### 第 11-24 行：客户端类初始化

```python
class SimpleClientApp:
    """简单的 MCP 客户端应用"""
    def __init__(self, server_command: List[str]):
        self.server_command = server_command   # 启动服务端的命令，如 ["python", "weather_server.py"]
        self.server_process = None             # 服务端进程对象（初始为 None）
        self.client = None                     # MCP 客户端会话（初始为 None）
        self.tool_definitions = []             # 从服务端获取的工具列表
        self.exit_stack = AsyncExitStack()     # 资源管理器
```

**`class`**：类的定义。"类"就像一个模板/蓝图，用来创建有相同结构的对象。
**`__init__`**：构造函数，当 `SimpleClientApp(...)` 创建实例时自动调用。
**`self`**：代表实例本身。`self.xxx` 是这个实例的属性/变量。

### 第 26-51 行：启动并连接服务器

```python
async def start(self):
    """启动 MCP 客户端并连接到服务器"""
    print("启动 MCP 服务器进程...")

    # Step 1: 配置服务器参数
    server_params = StdioServerParameters(
        command=self.server_command[0],   # 命令：python
        args=self.server_command[1:],     # 参数：["weather_server.py"]
        env=None                          # 环境变量：用当前系统的
    )
```

`StdioServerParameters`：告诉 MCP 框架"怎么启动服务端进程"。这里相当于在命令行执行 `python weather_server.py`。

```python
    # Step 2: 启动子进程，获取通信管道
    # enter_async_context 确保资源能自动释放
    # stdio_client 启动子进程并返回 (读管道, 写管道) 的元组
    read_write = await self.exit_stack.enter_async_context(stdio_client(server_params))
    read, write = read_write    # 解包元组
```

**关键理解 `stdio_client`：**
1. 它在后台执行 `python weather_server.py`
2. 返回两个"管道"：`read`（从这个管道读服务端的输出）、`write`（往这个管道写输入给服务端）
3. 就像两个人用对讲机通信，一个频道听，一个频道说

`exit_stack.enter_async_context(...)`：把这个连接注册到回收站，确保程序退出时自动关闭。

```python
    # Step 3: 建立客户端会话
    self.client = await self.exit_stack.enter_async_context(ClientSession(read, write))
    # Step 4: 初始化连接（握手）
    await self.client.initialize()
    # Step 5: 向服务端请求工具列表
    response = await self.client.list_tools()
    self.tool_definitions = response.tools   # 保存工具列表
```

**流程图解：**
```
Client                              Server
  │                                    │
  │──── stdio_client 启动子进程 ──────►│  (python weather_server.py)
  │                                    │
  │──── ClientSession(read,write) ────►│  (建立会话)
  │                                    │
  │──── initialize() ────────────────►│  (握手："嘿，我连上了")
  │◄─── 握手确认 ─────────────────────│
  │                                    │
  │──── list_tools() ────────────────►│  ("你有什么工具？")
  │◄─── [get_weather_warning,         │
  │      get_daily_forecast] ────────│  ("我有这两个")
```

```python
    print(f"已连接到服务器，可用工具: {len(self.tool_definitions)}")
    for tool in self.tool_definitions:
        print(f"  - {tool.name}: {tool.description}")
```
打印工具列表给用户看。

### 第 53-79 行：执行工具调用

```python
async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Optional[str]:
    # 检查工具是否存在
    tool_def = next((t for t in self.tool_definitions if t.name == tool_name), None)
    if not tool_def:
        return f"错误: 未找到工具 '{tool_name}'"
```

`next((t for t in self.tool_definitions if t.name == tool_name), None)`：
- `(t for t in ... if ...)`：生成器表达式，遍历工具列表找名称匹配的工具
- `next(..., None)`：取第一个匹配的，没有就返回 None

```python
    try:
        result = await self.client.call_tool(tool_name, arguments=params)  # 远程调用工具
        if result and hasattr(result, 'content'):
            return result.content    # 返回工具执行结果的内容
        else:
            return "工具执行未返回任何结果"
    except Exception as e:
        return f"执行过程中出错: {str(e)}"
```

`self.client.call_tool(tool_name, arguments=params)`：这是 MCP 协议的标准调用方式。客户端把工具名和参数发给服务端，服务端执行后返回结果。

### 第 81-103 行：辅助方法

```python
async def stop(self):
    """停止客户端，清理资源"""
    await self.exit_stack.aclose()   # 关闭所有注册的资源（进程、连接等）

def print_help(self):    # 打印帮助信息
def print_tools(self):   # 打印工具列表和参数说明
```

### 第 105-208 行：主函数

```python
async def main():
    # 构造服务端文件路径
    server_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # 项目根目录
        "server",
        "weather_server.py"
    )
```

`os.path.abspath(__file__)`：当前文件的绝对路径。
`os.path.dirname(...)`：取目录部分（去掉文件名）。
两次 `dirname`：第一次去掉 `mcp_client.py` 得到 `client/`，第二次再去掉 `client/` 得到项目根目录。
`os.path.join(...)`：用系统正确的分隔符（Windows 是 `\`，Linux 是 `/`）拼接路径。

```python
    if not os.path.exists(server_path):
        print(f"错误: 服务器文件不存在: {server_path}")
        return  # 直接退出
```

```python
    app = SimpleClientApp(["python", server_path])
    await app.start()

    # 主循环：不断读取用户输入
    while True:
        command = input("\n> ").strip()   # 等待用户输入命令

        if command == "exit":
            break                          # 退出循环（程序结束）
        elif command == "help":
            app.print_help()
        elif command == "list":
            app.print_tools()
        elif command.startswith("call "):
            # 解析 "call 工具名 参数" 格式的命令
            parts = command[5:].strip().split(" ", 1)   # 去掉 "call "，按第一个空格分割
            tool_name = parts[0]
            # 解析参数...
            params = json.loads(params_str)  # 尝试 JSON 格式
            # 如果不是 JSON，手动解析特定工具的格式
            result = await app.execute_tool(tool_name, params)
```

**命令行交互示例：**
```
> list                           # 列出可用工具
> call get_weather_warning {"location": "101010100"}    # JSON 格式传参
> call get_daily_forecast 116.41,39.92 7               # 简单格式：城市坐标 7天
> exit                           # 退出
```

### 第 210-215 行：程序入口

```python
if __name__ == "__main__":
    try:
        asyncio.run(main())        # 运行异步主函数
    except KeyboardInterrupt:      # 用户按 Ctrl+C
        print("\n程序被中断")
        sys.exit(0)
```

`asyncio.run(main())`：Python 中运行 async 函数的标准方式。它创建事件循环，运行你的异步函数。

---

## 四、完整的 MCP 通信流程（核心重点）

```
时间线 ────────────────────────────────────────────────────────────────────────►

1. 用户运行: python mcp_client.py

2. Client 启动
   ├─ SimpleClientApp(["python", "weather_server.py"])
   └─ app.start()

3. Client 启动 Server 子进程
   ├─ stdio_client(StdioServerParameters(command="python", args=["weather_server.py"]))
   └─ Server 的 mcp.run(transport='stdio') 开始监听

4. 建立会话
   ├─ ClientSession(read, write)  包装通信管道
   └─ client.initialize()         发送 MCP 协议的 initialize 请求

5. 能力发现 (Tool Discovery)
   ├─ client.list_tools()         发送 tools/list 请求
   └─ Server 返回:
      [
        {name: "get_weather_warning", description: "...", inputSchema: {...}},
        {name: "get_daily_forecast", description: "...", inputSchema: {...}}
      ]

6. 用户交互循环
   ├─ 用户输入: call get_daily_forecast 101010100
   │
   ├─ client.call_tool("get_daily_forecast", {"location": "101010100"})
   │   └─ 发送 MCP 协议的 tools/call 请求
   │
   ├─ Server 收到请求
   │   ├─ 找到 @mcp.tool() 注册的 get_daily_forecast 函数
   │   ├─ 执行函数: 构造请求 → 调用和风天气 API → 格式化结果
   │   └─ 返回格式化后的天气字符串
   │
   └─ Client 收到结果，打印给用户

7. 用户输入: exit → 清理资源，退出
```

### MCP 协议的底层通信格式（了解即可）

MCP 使用 **JSON-RPC** 格式通信。通过 stdio，消息看起来像：

**Client → Server（请求工具列表）：**
```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
```

**Server → Client（返回工具列表）：**
```json
{"jsonrpc": "2.0", "id": 1, "result": {"tools": [...]}}
```

**Client → Server（调用工具）：**
```json
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_daily_forecast", "arguments": {"location": "101010100"}}}
```

**Server → Client（返回结果）：**
```json
{"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "日期: 2024-01-01\n..."}]}}
```

**你不需要手写这些 JSON！** FastMCP 框架自动帮你处理了。

---

## 五、对比：非 MCP 方式的 Agent（AgentWithTools.py）

项目里还有 `AgentWithTools.py`，它是**不用 MCP 的方式**——直接调用 OpenAI 的 function calling API：

```
AgentWithTools 方式：
  用户输入 → OpenAI API（带 tools 参数）→ LLM 决定调哪个函数 → Python 本地执行函数 → 结果返回 LLM → 循环

MCP 方式：
  用户输入 → Client → (通过 MCP 协议) → Server 执行函数 → 返回 Client → 展示给用户
```

**MCP 的优势：**
- Server 和 Client 是**分离的进程**，可以独立开发、测试、部署
- Server 可以用任何语言写（Python、Node.js、Go 等）
- 一个 Client 可以连多个 Server，聚合各种能力
- 服务端升级不需要改客户端

---

## 六、怎么使用

### 前提条件

```bash
# 1. 安装依赖
pip install mcp httpx python-dotenv openai

# 2. 创建 .env 文件，内容：
QWEATHER_API_BASE=https://devapi.qweather.com/
QWEATHER_API_KEY=你的和风天气密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=你的DeepSeek密钥
MODEL_NAME=deepseek-chat
```

### 运行 MCP 天气系统

```bash
# 在项目根目录执行
python client/mcp_client.py
```

### 交互示例

```
> list
可用工具:
  get_weather_warning - 获取指定位置的天气灾害预警
  get_daily_forecast - 获取指定位置的天气预报

> call get_daily_forecast 101010100 3
正在调用工具...
结果:
日期: 2024-01-01
日出: 07:35  日落: 16:51
最高温度: 5°C  最低温度: -5°C
...
> exit
```

### 城市 ID 参考

| 城市 | ID |
|------|------|
| 北京 | 101010100 |
| 上海 | 101020100 |
| 广州 | 101280101 |
| 深圳 | 101280601 |

也可以直接写经纬度，如 `116.41,39.92`（北京）。

---

## 七、总结

| 概念 | 一句话解释 |
|------|-----------|
| MCP | LLM 调用外部工具的标准化协议 |
| Server | 提供工具的一方（天气查询） |
| Client | 调用工具的一方（命令行交互） |
| stdio 传输 | 通过进程的标准输入输出来通信 |
| `@mcp.tool()` | 把普通函数变成 MCP 工具的"魔法装饰器" |
| `call_tool()` | 客户端远程调用服务端工具的方法 |
| AsyncExitStack | 自动清理资源的"垃圾回收站" |

这套代码的核心流程就是：**Server 用 `@mcp.tool()` 装饰器暴露工具 → Client 启动 Server 子进程 → 通过 stdio 通信 → Client 获取工具列表 → 用户选择工具调用 → Server 执行并返回结果。**
