#!/usr/bin/env python3
"""
api_proxy.py — Anthropic → OpenAI-compatible API 翻译代理
让编译版CC接入 DeepSeek / GPT / Ollama / 任何 OpenAI 兼容 API

用法:
  python api_proxy.py                          # 默认 DeepSeek
  python api_proxy.py --provider openai        # GPT
  python api_proxy.py --provider ollama        # 本地 Ollama
  python api_proxy.py --provider custom --base-url https://xxx/v1 --api-key sk-xxx

然后启动克隆CC:
  set ANTHROPIC_BASE_URL=http://localhost:5678
  set ANTHROPIC_API_KEY=proxy
  bun dist/cli.js
"""
import json
import sys
import argparse
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

# ── Provider 配置 ──

PROVIDERS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
        "default_key": "sk-6817f4e184194c109f5fa47a87569ebb",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4.1",
        "default_key": "",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key_env": "",
        "default_model": "qwen2.5:7b",
        "default_key": "ollama",
    },
    "custom": {
        "base_url": "",
        "api_key_env": "",
        "default_model": "",
        "default_key": "",
    },
}

# ── Model 名称映射 ──
# CC 发来的 Anthropic model 名 → 实际 provider 的 model 名
MODEL_MAP = {}


def map_model(anthropic_model: str, provider: str, default_model: str) -> str:
    """把 Anthropic model 名映射到 provider 的 model"""
    if anthropic_model in MODEL_MAP:
        return MODEL_MAP[anthropic_model]
    return default_model


# ── 格式翻译：Anthropic → OpenAI ──

def translate_messages(anthropic_msgs: list, system: str | list | None) -> list:
    """Anthropic messages 格式 → OpenAI messages 格式"""
    openai_msgs = []

    # System prompt
    if system:
        if isinstance(system, list):
            # Anthropic 的 system 可以是 [{type: "text", text: "..."}] 数组
            sys_text = "\n".join(
                s["text"] for s in system if s.get("type") == "text"
            )
        else:
            sys_text = str(system)
        if sys_text:
            openai_msgs.append({"role": "system", "content": sys_text})

    for msg in anthropic_msgs:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "assistant":
            # Assistant 消息可能包含 text + tool_use
            if isinstance(content, str):
                openai_msgs.append({"role": "assistant", "content": content})
            elif isinstance(content, list):
                text_parts = []
                tool_calls = []
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block["text"])
                    elif block.get("type") == "tool_use":
                        tool_calls.append({
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(block.get("input", {})),
                            },
                        })
                assistant_msg = {"role": "assistant"}
                if text_parts:
                    assistant_msg["content"] = "\n".join(text_parts)
                else:
                    assistant_msg["content"] = None
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                openai_msgs.append(assistant_msg)

        elif role == "user":
            if isinstance(content, str):
                openai_msgs.append({"role": "user", "content": content})
            elif isinstance(content, list):
                # 可能是 tool_result 数组 或 text/image 数组
                tool_results = [b for b in content if b.get("type") == "tool_result"]
                text_blocks = [b for b in content if b.get("type") == "text"]
                image_blocks = [b for b in content if b.get("type") == "image"]

                if tool_results:
                    for tr in tool_results:
                        tool_content = tr.get("content", "")
                        if isinstance(tool_content, list):
                            tool_content = "\n".join(
                                t.get("text", str(t)) for t in tool_content
                            )
                        openai_msgs.append({
                            "role": "tool",
                            "tool_call_id": tr["tool_use_id"],
                            "content": str(tool_content),
                        })
                elif text_blocks or image_blocks:
                    # 普通 user 消息
                    parts = []
                    for b in content:
                        if b.get("type") == "text":
                            parts.append(b["text"])
                    openai_msgs.append({
                        "role": "user",
                        "content": "\n".join(parts) if parts else "",
                    })
                else:
                    openai_msgs.append({"role": "user", "content": str(content)})

    return openai_msgs


def translate_tools(anthropic_tools: list | None) -> list | None:
    """Anthropic tool 定义 → OpenAI function 定义"""
    if not anthropic_tools:
        return None
    openai_tools = []
    for tool in anthropic_tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {"type": "object"}),
            },
        })
    return openai_tools


def translate_response(openai_resp: dict, anthropic_model: str) -> dict:
    """OpenAI response → Anthropic response"""
    choice = openai_resp.get("choices", [{}])[0]
    message = choice.get("message", {})

    content = []
    # Text content
    if message.get("content"):
        content.append({"type": "text", "text": message["content"]})

    # Tool calls
    tool_calls = message.get("tool_calls", [])
    for tc in tool_calls:
        func = tc.get("function", {})
        try:
            input_data = json.loads(func.get("arguments", "{}"))
        except json.JSONDecodeError:
            input_data = {}
        content.append({
            "type": "tool_use",
            "id": tc.get("id", f"toolu_{id(tc)}"),
            "name": func.get("name", ""),
            "input": input_data,
        })

    stop_reason = "end_turn"
    if tool_calls:
        stop_reason = "tool_use"
    elif choice.get("finish_reason") == "length":
        stop_reason = "max_tokens"

    usage = openai_resp.get("usage", {})

    return {
        "id": openai_resp.get("id", "msg_proxy"),
        "type": "message",
        "role": "assistant",
        "model": anthropic_model,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }


# ── Streaming 翻译 ──

def translate_stream_chunk(line: str, state: dict, anthropic_model: str) -> list[str]:
    """OpenAI SSE chunk → Anthropic SSE events"""
    if not line.startswith("data: "):
        return []
    data = line[6:].strip()
    if data == "[DONE]":
        # 发送 message_delta + message_stop
        events = []
        events.append(f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn' if not state.get('has_tool') else 'tool_use'}, 'usage': {'output_tokens': state.get('tokens', 0)}})}\n")
        events.append(f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n")
        return events

    try:
        chunk = json.loads(data)
    except json.JSONDecodeError:
        return []

    choice = chunk.get("choices", [{}])[0]
    delta = choice.get("delta", {})
    events = []

    # 首次消息 → message_start
    if not state.get("started"):
        state["started"] = True
        state["block_idx"] = 0
        state["tokens"] = 0
        msg_start = {
            "type": "message_start",
            "message": {
                "id": chunk.get("id", "msg_proxy"),
                "type": "message",
                "role": "assistant",
                "model": anthropic_model,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0,
                          "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
            },
        }
        events.append(f"event: message_start\ndata: {json.dumps(msg_start)}\n")

    # Text content
    if delta.get("content"):
        if not state.get("text_block_started"):
            state["text_block_started"] = True
            events.append(f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': state['block_idx'], 'content_block': {'type': 'text', 'text': ''}})}\n")

        text_delta = {
            "type": "content_block_delta",
            "index": state["block_idx"],
            "delta": {"type": "text_delta", "text": delta["content"]},
        }
        events.append(f"event: content_block_delta\ndata: {json.dumps(text_delta)}\n")
        state["tokens"] = state.get("tokens", 0) + 1

    # Tool calls
    if delta.get("tool_calls"):
        for tc in delta["tool_calls"]:
            tc_idx = tc.get("index", 0)
            func = tc.get("function", {})

            if func.get("name"):
                # 新 tool call 开始
                if state.get("text_block_started"):
                    events.append(f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': state['block_idx']})}\n")
                    state["block_idx"] += 1
                    state["text_block_started"] = False

                state["has_tool"] = True
                tool_id = tc.get("id", f"toolu_{tc_idx}")
                state[f"tool_{tc_idx}_id"] = tool_id
                events.append(f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': state['block_idx'], 'content_block': {'type': 'tool_use', 'id': tool_id, 'name': func['name'], 'input': {}}})}\n")

            if func.get("arguments"):
                events.append(f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': state['block_idx'], 'delta': {'type': 'input_json_delta', 'partial_json': func['arguments']}})}\n")

    # Finish
    if choice.get("finish_reason"):
        if state.get("text_block_started") or state.get("has_tool"):
            events.append(f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': state['block_idx']})}\n")

    return events


# ── HTTP 代理服务器 ──

class ProxyHandler(BaseHTTPRequestHandler):
    provider_config = {}
    provider_name = ""

    def log_message(self, format, *args):
        print(f"[proxy] {args[0]}")

    def do_POST(self):
        # 只处理 /v1/messages
        if "/messages" not in self.path:
            self.send_error(404, "Only /v1/messages is proxied")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length))

        anthropic_model = body.get("model", "claude-sonnet-4-20250514")
        target_model = map_model(
            anthropic_model,
            self.provider_name,
            self.provider_config["default_model"],
        )

        print(f"[proxy] {anthropic_model} → {self.provider_name}/{target_model}"
              f" | stream={body.get('stream', False)}"
              f" | tools={len(body.get('tools', []))}")

        # 翻译请求
        openai_msgs = translate_messages(
            body.get("messages", []),
            body.get("system"),
        )
        openai_tools = translate_tools(body.get("tools"))

        openai_body: dict[str, Any] = {
            "model": target_model,
            "messages": openai_msgs,
            "max_tokens": min(body.get("max_tokens", 4096), 8192),
            "temperature": body.get("temperature", 1.0),
            "stream": body.get("stream", False),
        }
        if openai_tools:
            openai_body["tools"] = openai_tools

        # 构建请求
        base_url = self.provider_config["base_url"]
        api_key = self.provider_config.get("api_key", "")
        url = f"{base_url}/chat/completions"

        headers = {
            "Content-Type": "application/json",
        }
        if api_key and api_key != "ollama":
            headers["Authorization"] = f"Bearer {api_key}"

        req_data = json.dumps(openai_body).encode("utf-8")
        req = urllib.request.Request(url, data=req_data, headers=headers)

        try:
            if body.get("stream"):
                self._handle_stream(req, anthropic_model)
            else:
                self._handle_sync(req, anthropic_model)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            print(f"[proxy] 上游错误 {e.code}: {err_body[:200]}")
            self.send_error(e.code, err_body[:500])
        except Exception as e:
            print(f"[proxy] 错误: {e}")
            self.send_error(502, str(e))

    def _handle_sync(self, req, anthropic_model):
        """非 streaming 请求"""
        with urllib.request.urlopen(req, timeout=120) as resp:
            openai_resp = json.loads(resp.read())

        anthropic_resp = translate_response(openai_resp, anthropic_model)
        resp_bytes = json.dumps(anthropic_resp).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)

    def _handle_stream(self, req, anthropic_model):
        """Streaming 请求 — 真正的逐 chunk 转发"""
        with urllib.request.urlopen(req, timeout=300) as resp:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            state = {}
            buffer = ""
            for raw in resp:
                buffer += raw.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    events = translate_stream_chunk(line, state, anthropic_model)
                    for event in events:
                        self.wfile.write(event.encode("utf-8"))
                        self.wfile.write(b"\n")
                        self.wfile.flush()

    def do_GET(self):
        """健康检查 + model list"""
        if "/models" in self.path:
            # 返回假的 Anthropic models 列表
            models = {
                "data": [
                    {"id": "claude-sonnet-4-20250514", "display_name": f"→ {self.provider_config['default_model']}"},
                    {"id": "claude-opus-4-20250514", "display_name": f"→ {self.provider_config['default_model']}"},
                ],
            }
            resp = json.dumps(models).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"CC API Proxy → {self.provider_name}\n".encode())


def main():
    import os
    parser = argparse.ArgumentParser(description="CC API Proxy — Anthropic → OpenAI 翻译")
    parser.add_argument("--provider", default="deepseek",
                        choices=["deepseek", "openai", "ollama", "custom"])
    parser.add_argument("--port", type=int, default=5678)
    parser.add_argument("--base-url", help="Custom provider base URL")
    parser.add_argument("--api-key", help="API key (或用环境变量)")
    parser.add_argument("--model", help="默认模型名")
    parser.add_argument("--model-map", help='模型映射 JSON, 如 \'{"claude-sonnet-4-20250514":"deepseek-chat"}\'')
    args = parser.parse_args()

    # 加载配置
    config = PROVIDERS[args.provider].copy()
    if args.base_url:
        config["base_url"] = args.base_url
    if args.model:
        config["default_model"] = args.model

    # API key 优先级: 命令行 > 环境变量 > 默认值
    if args.api_key:
        config["api_key"] = args.api_key
    elif config.get("api_key_env") and os.environ.get(config["api_key_env"]):
        config["api_key"] = os.environ[config["api_key_env"]]
    else:
        config["api_key"] = config.get("default_key", "")

    if args.model_map:
        MODEL_MAP.update(json.loads(args.model_map))

    # 验证
    if not config["base_url"]:
        print("错误: 需要 --base-url")
        sys.exit(1)
    if not config["default_model"]:
        print("错误: 需要 --model")
        sys.exit(1)

    # 启动服务器
    ProxyHandler.provider_config = config
    ProxyHandler.provider_name = args.provider

    server = HTTPServer(("127.0.0.1", args.port), ProxyHandler)
    print(f"""
╔══════════════════════════════════════════════╗
║  CC API Proxy v1.0                           ║
║  Provider: {args.provider:<33s}║
║  Model:    {config['default_model']:<33s}║
║  Proxy:    http://127.0.0.1:{str(args.port):<19s}║
╠══════════════════════════════════════════════╣
║  启动克隆CC:                                 ║
║  set ANTHROPIC_BASE_URL=http://127.0.0.1:{args.port} ║
║  set ANTHROPIC_API_KEY=proxy                 ║
║  D:\\CC\\cloud-code\\start_cc.bat               ║
╚══════════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[proxy] 已停止")
        server.server_close()


if __name__ == "__main__":
    main()
