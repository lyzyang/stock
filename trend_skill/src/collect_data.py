#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A股数据统一采集入口：只采集与整理原始数据，输出统一 JSON。

本脚本不做任何分析结论（无评分、无状态判断、无策略建议）。
LLM 读取输出后，结合 analysis_methodology.md 完成推理，并按
SKILL.md 定义的统一格式输出报告。
"""

import sys
import json
import argparse
from datetime import datetime

from market_data import get_realtime_quote, get_kline_data, INDEX_MAP
from technical_indicators import calculate_all_indicators
from sentiment_analysis import (
    get_market_breadth,
    get_limit_up_down,
    get_north_bound_flow,
    get_average_turnover
)

KLINE_SYMBOL = 'sh000001'
KLINE_DAYS = 120
# 透传给 LLM 的原始K线天数（足够观察趋势，控制输出体积）
KLINE_RAW_DAYS = 30


def collect_market():
    quotes = {}
    for key, info in INDEX_MAP.items():
        quotes[key] = get_realtime_quote(info['code'])
    return {'market_overview': quotes}


def collect_technical():
    kline = get_kline_data(KLINE_SYMBOL, KLINE_DAYS)
    if not kline:
        return {'technical': None}

    return {
        'technical': {
            'symbol': KLINE_SYMBOL,
            'name': INDEX_MAP['sh']['name'],
            'kline_recent': kline[-KLINE_RAW_DAYS:],
            'indicators': calculate_all_indicators(kline)
        }
    }


def collect_sentiment():
    return {
        'sentiment': {
            'breadth': get_market_breadth(),
            'limit_up_down': get_limit_up_down(),
            'north_bound_flow': get_north_bound_flow(),
            'turnover': get_average_turnover()
        }
    }


COLLECTORS = {
    'market': collect_market,
    'technical': collect_technical,
    'sentiment': collect_sentiment
}


def main():
    parser = argparse.ArgumentParser(description='A股数据统一采集（仅采集整理，不含结论）')
    parser.add_argument('--module', type=str, default='all',
                        help='采集模块: market/technical/sentiment/all，默认 all')
    args = parser.parse_args()

    modules = list(COLLECTORS.keys()) if args.module == 'all' else [args.module]
    if args.module != 'all' and args.module not in COLLECTORS:
        print(json.dumps({
            'status': 'error',
            'message': f'Unknown module: {args.module}, 可选: market/technical/sentiment/all',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, ensure_ascii=False, indent=2))
        return

    data = {}
    errors = []
    for module in modules:
        try:
            data.update(COLLECTORS[module]())
        except Exception as e:
            errors.append(f'{module}: {e}')
        if len(modules) > 1:
            import time
            time.sleep(0.3)

    if not data:
        status = 'error'
    elif errors:
        status = 'partial'
    else:
        status = 'success'

    result = {
        'status': status,
        'data': data,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    if errors:
        result['errors'] = errors

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
