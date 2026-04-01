#!/usr/bin/env python3
"""
proxy_status.py — CC API Proxy 状态检查工具

功能:
1. 检测 proxy 是否在运行（检查端口 5678）
2. 向 proxy 发一个测试请求验证能否正常翻译
3. 统计信息：显示当前 provider、模型、uptime
4. 用彩色表格输出结果

用法:
  python proxy_status.py
"""

import sys
import json
import socket
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# ANSI 颜色代码（跨平台支持）
class Colors:
    # 前景色
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    # 背景色
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

    # 样式
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    HIDDEN = '\033[8m'

    # 重置
    RESET = '\033[0m'
    RESET_ALL = '\033[0m'

# 检查是否支持颜色输出
def supports_color() -> bool:
    """检查终端是否支持颜色"""
    # Windows 10+ 支持 ANSI 转义序列
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # 检查是否支持虚拟终端序列
        try:
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            STD_OUTPUT_HANDLE = -11
            hOut = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(hOut, ctypes.byref(mode)):
                kernel32.SetConsoleMode(hOut, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
                return True
        except Exception:
            pass
        return False
    else:
        # Unix-like 系统通常支持颜色
        return True

HAS_COLOR = supports_color()

# 代理配置
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 5678
PROXY_URL = f"http://{PROXY_HOST}:{PROXY_PORT}"


def check_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """检查指定端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def get_proxy_info() -> Optional[Dict[str, Any]]:
    """获取代理服务器信息"""
    try:
        # 发送 GET 请求到代理根路径
        req = urllib.request.Request(f"{PROXY_URL}/")
        with urllib.request.urlopen(req, timeout=3) as resp:
            text = resp.read().decode('utf-8')
            # 解析响应文本，格式类似 "CC API Proxy → deepseek"
            if "→" in text:
                provider = text.split("→")[-1].strip()
                return {
                    "provider": provider,
                    "status": "running",
                    "server_header": resp.headers.get('Server', ''),
                    "content_type": resp.headers.get('Content-Type', '')
                }
            return {
                "status": "running",
                "server_header": resp.headers.get('Server', ''),
                "content_type": resp.headers.get('Content-Type', '')
            }
    except Exception as e:
        return None


def get_proxy_models() -> Optional[Dict[str, Any]]:
    """获取代理支持的模型列表"""
    try:
        req = urllib.request.Request(f"{PROXY_URL}/v1/models")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            return data
    except Exception:
        return None


def test_translation() -> Dict[str, Any]:
    """测试代理翻译功能"""
    test_data = {
        "model": "claude-sonnet-4-20250514",
        "messages": [
            {"role": "user", "content": "Hello, translate this to Chinese: 'Good morning!'"}
        ],
        "max_tokens": 100,
        "stream": False
    }

    start_time = time.time()
    try:
        req = urllib.request.Request(
            f"{PROXY_URL}/v1/messages",
            data=json.dumps(test_data).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            response_data = json.loads(resp.read())
            elapsed = time.time() - start_time

            # 检查响应结构
            has_content = bool(response_data.get("content"))
            has_model = bool(response_data.get("model"))

            return {
                "success": True,
                "response_time": round(elapsed * 1000, 2),  # 毫秒
                "has_content": has_content,
                "has_model": has_model,
                "status_code": resp.status
            }
    except urllib.error.HTTPError as e:
        return {
            "success": False,
            "error": f"HTTP {e.code}: {e.reason}",
            "response_time": round((time.time() - start_time) * 1000, 2)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response_time": round((time.time() - start_time) * 1000, 2)
        }


def estimate_uptime() -> Dict[str, Any]:
    """估算代理运行状态"""
    try:
        # 尝试多次连接来检测稳定性
        stable_count = 0
        response_times = []

        for _ in range(3):
            start_time = time.time()
            if check_port_open(PROXY_HOST, PROXY_PORT, 0.5):
                stable_count += 1
                response_times.append((time.time() - start_time) * 1000)  # 毫秒
            time.sleep(0.1)

        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        if stable_count == 3:
            status = "稳定运行"
            color = Colors.GREEN
        elif stable_count > 0:
            status = "间歇性连接"
            color = Colors.YELLOW
        else:
            status = "未运行"
            color = Colors.RED

        return {
            "status": status,
            "color": color,
            "connection_rate": f"{stable_count}/3",
            "avg_response_time": round(avg_response_time, 2)
        }
    except Exception:
        return {
            "status": "未知",
            "color": Colors.YELLOW,
            "connection_rate": "0/3",
            "avg_response_time": 0
        }


def print_colored_table(data: Dict[str, Any]):
    """打印彩色表格"""
    if HAS_COLOR:
        # 定义颜色
        status_color = Colors.GREEN if data.get("port_open") else Colors.RED
        test_color = Colors.GREEN if data.get("test_success") else Colors.RED

        # 表格宽度
        table_width = 60

        # 表格边框
        border = f"{Colors.CYAN}╔{'═'*table_width}╗{Colors.RESET}"
        middle = f"{Colors.CYAN}╠{'═'*table_width}╣{Colors.RESET}"
        bottom = f"{Colors.CYAN}╚{'═'*table_width}╝{Colors.RESET}"

        print(border)
        print(f"{Colors.CYAN}║{Colors.BOLD}{Colors.WHITE}{'CC API Proxy 状态检查':^{table_width}}{Colors.RESET}{Colors.CYAN}║")
        print(middle)

        # 时间戳
        timestamp = data.get('timestamp', '')
        time_text = f"检查时间: {Colors.DIM}{timestamp}{Colors.RESET}"
        print(f"{Colors.CYAN}║ {time_text:<{table_width-1}}{Colors.CYAN}║")
        print(middle)

        # 状态行
        status = data.get('status', '未知')
        status_icon = "●" if data.get('port_open') else "○"
        status_text = f"{status_icon} 代理状态: {status_color}{status}{Colors.RESET}"
        print(f"{Colors.CYAN}║ {status_text:<{table_width-1}}{Colors.CYAN}║")

        # Provider信息
        if data.get('provider'):
            provider_text = f"  Provider: {Colors.YELLOW}{data['provider']}{Colors.RESET}"
            print(f"{Colors.CYAN}║ {provider_text:<{table_width-1}}{Colors.CYAN}║")

        # 模型信息
        if data.get('model'):
            model_text = f"  模型: {Colors.MAGENTA}{data['model']}{Colors.RESET}"
            print(f"{Colors.CYAN}║ {model_text:<{table_width-1}}{Colors.CYAN}║")

        # 测试结果
        if data.get('test_success') is not None:
            test_icon = "✓" if data['test_success'] else "✗"
            test_result = "通过" if data['test_success'] else "失败"
            test_text = f"  {test_icon} 翻译测试: {test_color}{test_result}{Colors.RESET}"
            if data.get('response_time'):
                test_text += f" ({data['response_time']}ms)"
            print(f"{Colors.CYAN}║ {test_text:<{table_width-1}}{Colors.CYAN}║")

        # 运行状态
        if data.get('uptime_info'):
            uptime_info = data['uptime_info']
            uptime_icon = "●" if uptime_info['status'] == "稳定运行" else "○"
            uptime_text = f"  {uptime_icon} 连接状态: {uptime_info['color']}{uptime_info['status']}{Colors.RESET}"
            if uptime_info.get('connection_rate'):
                uptime_text += f" ({uptime_info['connection_rate']})"
            if uptime_info.get('avg_response_time') and uptime_info['avg_response_time'] > 0:
                uptime_text += f" [{uptime_info['avg_response_time']}ms]"
            print(f"{Colors.CYAN}║ {uptime_text:<{table_width-1}}{Colors.CYAN}║")

        # 端口信息
        port_status = "开放" if data.get('port_open') else "关闭"
        port_icon = "✓" if data.get('port_open') else "✗"
        port_text = f"  {port_icon} 端口 {PROXY_PORT}: {port_status}"
        print(f"{Colors.CYAN}║ {port_text:<{table_width-1}}{Colors.CYAN}║")

        # 服务器信息
        if data.get('server_info'):
            server_info = data['server_info']
            if server_info.get('server_header'):
                server_text = f"  服务器: {Colors.CYAN}{server_info['server_header']}{Colors.RESET}"
                print(f"{Colors.CYAN}║ {server_text:<{table_width-1}}{Colors.CYAN}║")

        # 错误信息（如果有）
        if data.get('error'):
            error_text = f"  ✗ 错误: {Colors.RED}{data['error']}{Colors.RESET}"
            # 如果错误信息太长，截断
            if len(error_text) > table_width - 1:
                error_text = error_text[:table_width-4] + "..."
            print(f"{Colors.CYAN}║ {error_text:<{table_width-1}}{Colors.CYAN}║")

        print(bottom)
    else:
        # 无彩色输出
        print("=" * 62)
        print(f"{'CC API Proxy 状态检查':^62}")
        print("=" * 62)
        print(f"检查时间: {data.get('timestamp', '')}")
        print("-" * 62)
        print(f"代理状态: {data.get('status', '未知')}")
        if data.get('provider'):
            print(f"Provider: {data['provider']}")
        if data.get('model'):
            print(f"模型: {data['model']}")
        if data.get('test_success') is not None:
            test_result = "通过" if data['test_success'] else "失败"
            print(f"翻译测试: {test_result}", end="")
            if data.get('response_time'):
                print(f" ({data['response_time']}ms)")
            else:
                print()
        if data.get('uptime_info'):
            uptime_info = data['uptime_info']
            print(f"连接状态: {uptime_info['status']}", end="")
            if uptime_info.get('connection_rate'):
                print(f" ({uptime_info['connection_rate']})", end="")
            if uptime_info.get('avg_response_time') and uptime_info['avg_response_time'] > 0:
                print(f" [{uptime_info['avg_response_time']}ms]")
            else:
                print()
        print(f"端口 {PROXY_PORT}: {'开放' if data.get('port_open') else '关闭'}")
        if data.get('server_info') and data['server_info'].get('server_header'):
            print(f"服务器: {data['server_info']['server_header']}")
        if data.get('error'):
            print(f"错误: {data['error']}")
        print("=" * 62)


def main():
    """主函数"""
    # 设置控制台编码为 UTF-8
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print(f"正在检查 CC API Proxy (http://{PROXY_HOST}:{PROXY_PORT})...")

    # 收集所有信息
    result = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # 1. 检查端口
    port_open = check_port_open(PROXY_HOST, PROXY_PORT)
    result["port_open"] = port_open

    if not port_open:
        result["status"] = "未运行"
        result["error"] = f"端口 {PROXY_PORT} 未开放"
        print_colored_table(result)
        sys.exit(1)

    # 2. 获取代理信息
    proxy_info = get_proxy_info()
    if proxy_info:
        result["status"] = proxy_info.get("status", "运行中")
        result["provider"] = proxy_info.get("provider", "未知")
        result["server_info"] = {
            "server_header": proxy_info.get("server_header", ""),
            "content_type": proxy_info.get("content_type", "")
        }
    else:
        result["status"] = "运行中（无信息）"
        result["server_info"] = {}

    # 3. 获取模型信息
    models_info = get_proxy_models()
    if models_info and models_info.get("data"):
        # 提取第一个模型的显示名称
        first_model = models_info["data"][0]
        display_name = first_model.get("display_name", "")
        if "→" in display_name:
            result["model"] = display_name.split("→")[-1].strip()
        else:
            result["model"] = first_model.get("id", "未知")
    else:
        result["model"] = "未知"

    # 4. 测试翻译功能
    test_result = test_translation()
    result["test_success"] = test_result["success"]
    result["response_time"] = test_result.get("response_time")

    if not test_result["success"]:
        result["error"] = test_result.get("error", "测试失败")

    # 5. 估算运行状态
    result["uptime_info"] = estimate_uptime()

    # 6. 输出结果
    print_colored_table(result)

    # 返回退出码
    if result.get("test_success"):
        print(f"\n{Colors.GREEN if HAS_COLOR else ''}✓ 代理运行正常{Colors.RESET if HAS_COLOR else ''}")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED if HAS_COLOR else ''}✗ 代理存在问题{Colors.RESET if HAS_COLOR else ''}")
        sys.exit(1)


if __name__ == "__main__":
    main()