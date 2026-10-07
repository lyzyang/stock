"""
股票T+0决策工具 - 日志工具
所有日志统一输出到 stderr，保证 stdout 只输出 JSON 数据
"""

import sys

from config import DEBUG_MODE


def info(msg: str) -> None:
    if DEBUG_MODE:
        print(f"[INFO] {msg}", file=sys.stderr)


def debug(msg: str) -> None:
    if DEBUG_MODE:
        print(f"[DEBUG] {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    if DEBUG_MODE:
        print(f"[WARN] {msg}", file=sys.stderr)


def error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
