#!/usr/bin/env python3
"""
测试脚本 - 验证 list_proxy_models.py 的输出
"""

import subprocess
import sys

def test_list_proxy():
    """测试 list_proxy_models.py 脚本"""
    try:
        # 运行 list_proxy_models.py
        result = subprocess.run(
            [sys.executable, "list_proxy_models.py"],
            capture_output=True,
            text=True,
            cwd="D:\\CC\\cloud-code"
        )

        print("脚本输出:")
        print("=" * 80)
        print(result.stdout)

        if result.stderr:
            print("错误输出:")
            print("=" * 80)
            print(result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"运行脚本时出错: {e}")
        return False

if __name__ == "__main__":
    print("测试 list_proxy_models.py 脚本...")
    success = test_list_proxy()

    if success:
        print("\n✅ 测试通过!")
    else:
        print("\n❌ 测试失败!")
        sys.exit(1)