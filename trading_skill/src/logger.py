"""
股票T+0决策工具 - 日志工具
控制调试输出，生产环境隐藏详细日志
"""

from config import DEBUG_MODE


def info(msg: str) -> None:
    if DEBUG_MODE:
        print(f"[INFO] {msg}")


def debug(msg: str) -> None:
    if DEBUG_MODE:
        print(f"[DEBUG] {msg}")


def warn(msg: str) -> None:
    if DEBUG_MODE:
        print(f"[WARN] {msg}")


def error(msg: str) -> None:
    print(f"[ERROR] {msg}")
