#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""市场情绪数据采集：只采集原始数据，不做评分与分级。

情绪评分、乐观/悲观等级等判断由 LLM 结合
analysis_methodology.md 自行推理，本模块只输出原始采集值。
"""

import sys
import json
from datetime import datetime

import requests


def get_market_breadth():
    try:
        up_count_total = 0
        down_count_total = 0
        flat_count_total = 0

        for page in range(1, 11):
            url = f'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page={page}&num=100&sort=symbol&asc=0&node=hs_a&symbol=&_s_r_a=auto'
            resp = requests.get(url, timeout=10)
            data = resp.json()

            if not data:
                break

            up_count_total += sum(1 for item in data if float(item.get('changepercent', 0)) > 0)
            down_count_total += sum(1 for item in data if float(item.get('changepercent', 0)) < 0)
            flat_count_total += sum(1 for item in data if float(item.get('changepercent', 0)) == 0)

        total = up_count_total + down_count_total + flat_count_total

        if total > 0:
            return {
                'total': total,
                'up_count': up_count_total,
                'down_count': down_count_total,
                'flat_count': flat_count_total,
                'up_ratio': round(up_count_total / total * 100, 2),
                'down_ratio': round(down_count_total / total * 100, 2)
            }
        return None
    except Exception as e:
        print(f"Error getting market breadth: {e}", file=sys.stderr)
        return None


def get_limit_up_down():
    try:
        limit_up_count = 0
        limit_down_count = 0

        for page in range(1, 11):
            url = f'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page={page}&num=100&sort=symbol&asc=0&node=hs_a&symbol=&_s_r_a=auto'
            resp = requests.get(url, timeout=10)
            data = resp.json()

            if not data:
                break

            for item in data:
                change = float(item.get('changepercent', 0))
                if change >= 9.8:
                    limit_up_count += 1
                elif change <= -9.8:
                    limit_down_count += 1

        return {
            'limit_up': limit_up_count,
            'limit_down': limit_down_count
        }
    except Exception as e:
        print(f"Error getting limit up/down data: {e}", file=sys.stderr)
        return None


def get_north_bound_flow():
    try:
        url = 'http://qt.gtimg.cn/q=sh000001,sz399001,sz399006'
        resp = requests.get(url, timeout=10)
        resp.encoding = 'gbk'
        text = resp.text

        lines = text.split('\n')
        for line in lines:
            if line.startswith('v_sz399006'):
                fields = line.split('=', 1)[1].strip('"').split('~')
                if len(fields) >= 45:
                    flow = float(fields[43]) if fields[43] else 0
                    return {
                        'flow': round(flow, 2),
                        'unit': '万元',
                        'note': '来源为腾讯行情扩展字段，非官方北向资金口径，仅供参考'
                    }
        return None
    except Exception as e:
        print(f"Error getting north bound flow: {e}", file=sys.stderr)
        return None


def get_average_turnover():
    try:
        url = 'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh000001&scale=240&ma=5,10,20&datalen=1'
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if data and isinstance(data, list) and len(data) > 0:
            item = data[-1]
            return {
                'date': item.get('day', ''),
                'total_amount': round(float(item.get('volume', 0)) * float(item.get('close', 1)) / 100 / 10000, 2),
                'unit': '万元'
            }
        return None
    except Exception as e:
        print(f"Error getting turnover: {e}", file=sys.stderr)
        return None


def main():
    result = {
        'status': 'success',
        'data': {
            'breadth': get_market_breadth(),
            'limit_up_down': get_limit_up_down(),
            'north_bound_flow': get_north_bound_flow(),
            'turnover': get_average_turnover()
        },
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
