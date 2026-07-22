"""
股票T+0决策工具 - 数据获取
仅使用新浪和腾讯数据源，避免akshare连接失败问题
"""

import pandas as pd
import requests
import time
from datetime import datetime
from typing import Optional

from config import (
    STOCK_CODE, EXCHANGE, KLINE_PERIOD, KLINE_COUNT
)
from logger import info, debug, warn, error


def get_realtime_quote() -> Optional[dict]:
    """
    获取股票实时行情
    返回: {price, high, low, volume, amount, change_pct} 或 None
    """
    fetchers = [
        ("腾讯接口", _get_realtime_tencent),
        ("新浪接口", _get_realtime_sina),
    ]

    for name, fetcher in fetchers:
        try:
            result = fetcher()
            if result and result["price"] > 0:
                info(f"数据源 [{name}] 获取成功: {result['price']}")
                return result
        except Exception as e:
            warn(f"数据源 [{name}] 失败: {e}")
            continue

    error("所有数据源均获取失败")
    return None


def _get_realtime_sina() -> Optional[dict]:
    """数据源1: 新浪财经接口"""
    sina_code = _to_sina_code(STOCK_CODE, EXCHANGE)
    url = f"https://hq.sinajs.cn/list={sina_code}&_={int(time.time()*1000)}"
    headers = {
        "Referer": "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
    }

    resp = requests.get(url, headers=headers, timeout=5)
    resp.encoding = "gbk"

    if not resp.text or len(resp.text) < 10:
        return None

    # 解析新浪数据格式
    try:
        data = resp.text.split('"')[1].split(",")
        # 格式: 名称, 今开, 昨收, 当前价, 最高, 最低, ...
        open_price = float(data[1]) if data[1] else 0
        prev_close = float(data[2]) if data[2] else 0
        price = float(data[3]) if data[3] else 0
        high = float(data[4]) if data[4] else 0
        low = float(data[5]) if data[5] else 0
        volume = float(data[8]) if len(data) > 8 and data[8] else 0  # 手
        amount = float(data[9]) if len(data) > 9 and data[9] else 0  # 万

        change_pct = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0

        return {
            "price": price,
            "high": high,
            "low": low,
            "open": open_price,
            "volume": volume * 100,  # 手转股
            "amount": amount * 10000,  # 万转元
            "change_pct": round(change_pct, 2),
            "time": datetime.now().strftime("%H:%M:%S"),
        }
    except (IndexError, ValueError) as e:
        warn(f"解析新浪数据失败: {e}")
        return None


def _get_realtime_tencent() -> Optional[dict]:
    """数据源2: 腾讯财经接口"""
    tencent_code = _to_tencent_code(STOCK_CODE, EXCHANGE)
    url = f"https://qt.gtimg.cn/q={tencent_code}&_={int(time.time()*1000)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
    }

    resp = requests.get(url, headers=headers, timeout=5)
    resp.encoding = "gbk"

    if not resp.text or len(resp.text) < 10:
        return None

    try:
        data = resp.text.split('"')[1].split(";")[0].split("~")
        # 腾讯API格式 (~分隔):
        # 3=当前价, 4=昨收, 5=今开, 6=成交量(手), 7=外盘, 8=内盘,
        # 9~29=五档买卖, 30=时间, 31=涨跌额, 32=涨跌幅(%), 33=最高, 34=最低
        # 37=成交额(万)
        price = float(data[3]) if len(data) > 3 and data[3] else 0
        prev_close = float(data[4]) if len(data) > 4 and data[4] else 0
        open_price = float(data[5]) if len(data) > 5 and data[5] else 0
        volume = float(data[6]) if len(data) > 6 and data[6] else 0  # 手
        high = float(data[33]) if len(data) > 33 and data[33] else 0
        low = float(data[34]) if len(data) > 34 and data[34] else 0
        change_pct = float(data[32]) if len(data) > 32 and data[32] else 0
        amount = float(data[37]) if len(data) > 37 and data[37] else 0  # 万

        return {
            "price": price,
            "high": high,
            "low": low,
            "open": open_price,
            "volume": volume * 100,
            "amount": amount * 10000,
            "change_pct": change_pct,
            "time": datetime.now().strftime("%H:%M:%S"),
        }
    except (IndexError, ValueError) as e:
        warn(f"解析腾讯数据失败: {e}")
        return None


def _to_sina_code(code: str, exchange: str) -> str:
    """转换为新浪代码格式: sh600030 / sz000001"""
    prefix = "sh" if exchange == "SH" else "sz"
    return f"{prefix}{code}"


def _to_tencent_code(code: str, exchange: str) -> str:
    """转换为腾讯代码格式: sh600030 / sz000001"""
    prefix = "sh" if exchange == "SH" else "sz"
    return f"{prefix}{code}"


def get_kline_data(realtime_price: float = None, max_retries: int = 3) -> Optional[pd.DataFrame]:
    """
    获取K线数据（优先新浪接口）
    参数:
        realtime_price: 实时价格，用于数据新鲜度校验
        max_retries: 数据过期时的最大重试次数
    返回: DataFrame 包含 open, high, low, close, volume 列
    """
    fetchers = [
        ("新浪K线", _get_kline_sina),
    ]

    for attempt in range(max_retries):
        for name, fetcher in fetchers:
            try:
                result = fetcher()
                if result is not None and not result.empty:
                    info(f"K线数据源 [{name}] 获取成功: {len(result)} 条 (尝试 {attempt + 1})")
                    debug(f"K线数据前3条: {result.head(3).to_string(index=False)}")
                    debug(f"K线数据后3条: {result.tail(3).to_string(index=False)}")
                    
                    last_close = result["close"].iloc[-1]
                    debug(f"最新K线收盘价: {last_close}")

                    if realtime_price and realtime_price > 0 and last_close > 0:
                        deviation = abs(last_close - realtime_price) / realtime_price
                        debug(f"K线数据与实时价格偏差: {deviation*100:.2f}%")

                        if deviation > 0.01:
                            warn(f"K线数据可能过期！偏差 {deviation*100:.2f}% > 1%")
                            if attempt < max_retries - 1:
                                info("重新获取K线数据...")
                                time.sleep(1)
                                break

                            info("已达最大重试次数，修正最后一根K线收盘价为实时价格")
                            result.loc[len(result) - 1, "close"] = realtime_price
                            debug(f"修正后K线数据后3条: {result.tail(3).to_string(index=False)}")

                    return result
                else:
                    warn(f"K线数据源 [{name}] 返回空数据 (尝试 {attempt + 1})")
            except Exception as e:
                warn(f"K线数据源 [{name}] 失败: {e} (尝试 {attempt + 1})")
                continue

    error("所有K线数据源均获取失败")
    return None


def _get_kline_sina() -> Optional[pd.DataFrame]:
    """使用新浪接口获取K线数据"""
    sina_code = _to_sina_code(STOCK_CODE, EXCHANGE)

    # scale: 5=5分钟, 15=15分钟, 30=30分钟, 60=60分钟, 240=日线
    scale_map = {
        "1min": "5",
        "5min": "5",
        "15min": "15",
        "30min": "30",
        "60min": "60",
        "daily": "240",
    }
    scale = scale_map.get(KLINE_PERIOD, "5")

    url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sina_code}&scale={scale}&ma=no&datalen={KLINE_COUNT}&_={int(time.time()*1000)}"
    headers = {
        "Referer": "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0",
    }

    resp = requests.get(url, headers=headers, timeout=5)
    if not resp.text or resp.text == "null":
        return None

    import json
    data = json.loads(resp.text)
    if not data:
        return None

    records = []
    for item in data:
        records.append({
            "open": float(item.get("open", 0)),
            "high": float(item.get("high", 0)),
            "low": float(item.get("low", 0)),
            "close": float(item.get("close", 0)),
            "volume": float(item.get("volume", 0)),
        })

    return pd.DataFrame(records).tail(KLINE_COUNT).reset_index(drop=True)


def get_daily_kline() -> Optional[pd.DataFrame]:
    """获取日K线数据"""
    try:
        return _get_daily_sina()
    except Exception as e:
        error(f"获取日K线失败: {e}")
        return None


def _get_kline_tencent() -> Optional[pd.DataFrame]:
    """使用腾讯接口获取K线数据（备用）"""
    tencent_code = _to_tencent_code(STOCK_CODE, EXCHANGE)

    period_map = {
        "1min": "1",
        "5min": "5",
        "15min": "15",
        "30min": "30",
        "60min": "60",
        "daily": "101",
    }
    period = period_map.get(KLINE_PERIOD, "5")

    url = f"https://qt.gtimg.cn/q={tencent_code}&period={period}&num={KLINE_COUNT}&_={int(time.time()*1000)}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
    }

    resp = requests.get(url, headers=headers, timeout=5)
    if not resp.text or len(resp.text) < 50:
        return None

    debug(f"腾讯K线原始数据: {resp.text[:200]}")

    try:
        lines = resp.text.split(";")
        records = []
        for line in lines:
            if line.strip().startswith(f"v_{tencent_code}="):
                data = line.split('"')[1].split("~")
                if len(data) >= 10:
                    records.append({
                        "open": float(data[5]) if data[5] else 0,
                        "high": float(data[33]) if len(data) > 33 and data[33] else 0,
                        "low": float(data[34]) if len(data) > 34 and data[34] else 0,
                        "close": float(data[3]) if data[3] else 0,
                        "volume": float(data[6]) if data[6] else 0,
                    })

        if not records:
            return None

        return pd.DataFrame(records).tail(KLINE_COUNT).reset_index(drop=True)
    except Exception as e:
        warn(f"解析腾讯K线失败: {e}")
        return None


def _get_daily_sina() -> Optional[pd.DataFrame]:
    """使用新浪接口获取日K线"""
    sina_code = _to_sina_code(STOCK_CODE, EXCHANGE)
    url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sina_code}&scale=240&ma=no&datalen=30&_={int(time.time()*1000)}"
    headers = {
        "Referer": "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0",
    }

    resp = requests.get(url, headers=headers, timeout=5)
    if not resp.text or resp.text == "null":
        return None

    import json
    data = json.loads(resp.text)
    if not data:
        return None

    records = []
    for item in data:
        records.append({
            "open": float(item.get("open", 0)),
            "high": float(item.get("high", 0)),
            "low": float(item.get("low", 0)),
            "close": float(item.get("close", 0)),
            "volume": float(item.get("volume", 0)),
        })

    return pd.DataFrame(records).tail(30).reset_index(drop=True)
