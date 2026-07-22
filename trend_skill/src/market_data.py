#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import time
import argparse
import requests
from datetime import datetime, timedelta

INDEX_MAP = {
    'sh': {'code': 'sh000001', 'name': '上证指数'},
    'sz': {'code': 'sz399001', 'name': '深证成指'},
    'cy': {'code': 'sz399006', 'name': '创业板指'},
    'hs300': {'code': 'sh000300', 'name': '沪深300'}
}

def get_realtime_quote(symbol):
    url = f'http://qt.gtimg.cn/q={symbol}'
    try:
        resp = requests.get(url, timeout=10)
        resp.encoding = 'gbk'
        text = resp.text
        
        if text and '=' in text:
            data_str = text.split('=', 1)[1].strip('"')
            fields = data_str.split('~')
            
            if len(fields) >= 45:
                price = float(fields[3]) if fields[3] else 0
                pre_close = float(fields[5]) if fields[5] else 0
                
                return {
                    'code': symbol,
                    'name': fields[1] if fields[1] else INDEX_MAP.get(symbol[:2], {}).get('name', ''),
                    'price': price,
                    'open': float(fields[4]) if fields[4] else 0,
                    'pre_close': pre_close,
                    'high': float(fields[33]) if fields[33] else 0,
                    'low': float(fields[34]) if fields[34] else 0,
                    'volume': int(fields[8]) if fields[8] else 0,
                    'amount': float(fields[45]) * 10000 if fields[45] else 0,
                    'change': float(fields[31]) if fields[31] else 0,
                    'change_percent': float(fields[32]) if fields[32] else 0
                }
        return None
    except Exception as e:
        print(f"Error getting realtime quote for {symbol}: {e}", file=sys.stderr)
        return None

def get_kline_data(symbol, days=60):
    url = f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=5,10,20&datalen={days}'
    
    for retry in range(3):
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            
            if data and isinstance(data, list):
                result = []
                for item in data:
                    result.append({
                        'date': item.get('day', ''),
                        'open': float(item.get('open', 0)),
                        'close': float(item.get('close', 0)),
                        'high': float(item.get('high', 0)),
                        'low': float(item.get('low', 0)),
                        'volume': int(item.get('volume', 0)),
                        'amount': float(item.get('volume', 0)) * float(item.get('close', 1)) / 100
                    })
                return result[-days:] if len(result) > days else result
            return []
        except Exception as e:
            print(f"Error getting kline data for {symbol} (retry {retry+1}): {e}", file=sys.stderr)
            time.sleep(1)
    return []

def main():
    parser = argparse.ArgumentParser(description='A股大盘数据获取工具')
    parser.add_argument('--index', type=str, help='指数类型: sh/sz/cy/hs300/all')
    parser.add_argument('--kline', action='store_true', help='获取K线数据')
    parser.add_argument('--symbol', type=str, help='股票/指数代码')
    parser.add_argument('--days', type=int, default=60, help='K线天数')
    
    args = parser.parse_args()
    
    result = {
        'status': 'success',
        'data': None,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if args.kline and args.symbol:
        kline_data = get_kline_data(args.symbol, args.days)
        result['data'] = {
            'symbol': args.symbol,
            'days': args.days,
            'kline': kline_data
        }
    elif args.index:
        if args.index == 'all':
            quotes = {}
            for key, info in INDEX_MAP.items():
                quote = get_realtime_quote(info['code'])
                if quote:
                    quotes[key] = quote
                time.sleep(0.3)
            result['data'] = quotes
        else:
            info = INDEX_MAP.get(args.index)
            if info:
                quote = get_realtime_quote(info['code'])
                result['data'] = quote
            else:
                result['status'] = 'error'
                result['message'] = f"Unknown index type: {args.index}"
    else:
        result['status'] = 'error'
        result['message'] = 'Please specify --index or --kline with --symbol'
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()