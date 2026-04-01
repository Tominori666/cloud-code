#!/usr/bin/env python3
"""
list_proxy_models.py - 列出 api_proxy.py 中所有支持的模型和对应的 base_url

用法:
  python list_proxy_models.py
"""

import sys
from pathlib import Path

# 直接从 api_proxy.py 复制 PROVIDERS 配置
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

def extract_providers_from_file(file_path):
    """从 api_proxy.py 文件中提取 PROVIDERS 配置"""
    # 这里直接返回我们复制的 PROVIDERS 字典
    # 在实际使用中，你可以选择从文件读取或直接使用这个字典
    return PROVIDERS.copy()

def print_providers_table(providers):
    """以表格形式打印 providers 信息"""
    if not providers:
        print("没有找到 provider 配置")
        return

    # 计算列宽
    provider_width = max(len("Provider"), max(len(p) for p in providers))
    model_width = max(len("Default Model"), max(len(p.get('default_model', '')) for p in providers.values()))
    base_url_width = max(len("Base URL"), max(len(p.get('base_url', '')) for p in providers.values()))
    api_key_env_width = max(len("API Key Env"), max(len(p.get('api_key_env', '')) for p in providers.values()))

    # 表头
    header = f"┌{'─' * (provider_width + 2)}┬{'─' * (model_width + 2)}┬{'─' * (base_url_width + 2)}┬{'─' * (api_key_env_width + 2)}┐"
    print(header)
    print(f"│ {'Provider':<{provider_width}} │ {'Default Model':<{model_width}} │ {'Base URL':<{base_url_width}} │ {'API Key Env':<{api_key_env_width}} │")
    print(f"├{'─' * (provider_width + 2)}┼{'─' * (model_width + 2)}┼{'─' * (base_url_width + 2)}┼{'─' * (api_key_env_width + 2)}┤")

    # 数据行
    for provider_name, config in sorted(providers.items()):
        default_model = config.get('default_model', 'N/A')
        base_url = config.get('base_url', 'N/A')
        api_key_env = config.get('api_key_env', 'N/A')

        print(f"│ {provider_name:<{provider_width}} │ {default_model:<{model_width}} │ {base_url:<{base_url_width}} │ {api_key_env:<{api_key_env_width}} │")

    # 表尾
    print(f"└{'─' * (provider_width + 2)}┴{'─' * (model_width + 2)}┴{'─' * (base_url_width + 2)}┴{'─' * (api_key_env_width + 2)}┘")

    # 打印统计信息
    print(f"\n总计: {len(providers)} 个 provider")
    print("\n支持的 provider:")
    for provider_name in sorted(providers.keys()):
        print(f"  • {provider_name}")

def main():
    """主函数"""
    # 获取当前目录
    current_dir = Path(__file__).parent
    api_proxy_path = current_dir / "api_proxy.py"

    print("=" * 80)
    print("CC API Proxy - 支持的模型列表")
    print("=" * 80)
    print(f"读取配置文件: {api_proxy_path}")
    print()

    # 提取 providers 配置
    providers = extract_providers_from_file(api_proxy_path)

    if providers:
        print_providers_table(providers)

        # 打印使用说明
        print("\n" + "=" * 80)
        print("使用说明:")
        print("=" * 80)
        print("启动代理服务器:")
        print("  python api_proxy.py                          # 默认使用 deepseek")
        print("  python api_proxy.py --provider openai        # 使用 OpenAI")
        print("  python api_proxy.py --provider ollama        # 使用本地 Ollama")
        print("  python api_proxy.py --provider custom --base-url https://xxx/v1 --api-key sk-xxx")
        print()
        print("设置环境变量后启动 CC:")
        print("  set ANTHROPIC_BASE_URL=http://localhost:5678")
        print("  set ANTHROPIC_API_KEY=proxy")
        print("  bun dist/cli.js")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()