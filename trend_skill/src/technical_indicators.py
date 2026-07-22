#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import argparse
import numpy as np
from datetime import datetime

from market_data import get_kline_data

def calculate_ma(data, periods=[5, 10, 20, 60]):
    closes = np.array([d['close'] for d in data])
    result = {}
    for period in periods:
        result[f'MA{period}'] = round(np.mean(closes[-period:]), 2) if len(closes) >= period else None
    return result

def calculate_macd(data):
    closes = np.array([d['close'] for d in data])
    if len(closes) < 26:
        return None
    
    ema12 = np.zeros(len(closes))
    ema26 = np.zeros(len(closes))
    ema12[11] = np.mean(closes[:12])
    ema26[25] = np.mean(closes[:26])
    
    for i in range(12, len(closes)):
        ema12[i] = (closes[i] * 2 / 13) + (ema12[i-1] * 11 / 13)
    for i in range(26, len(closes)):
        ema26[i] = (closes[i] * 2 / 27) + (ema26[i-1] * 25 / 27)
    
    dif = ema12 - ema26
    dea = np.zeros(len(dif))
    for i in range(9, len(dif)):
        dea[i] = (dif[i] * 2 / 10) + (dea[i-1] * 8 / 10)
    
    macd = 2 * (dif - dea)
    
    return {
        'DIF': round(dif[-1], 4) if len(dif) > 0 else None,
        'DEA': round(dea[-1], 4) if len(dea) > 0 else None,
        'MACD': round(macd[-1], 4) if len(macd) > 0 else None,
        'signal': 'golden' if dif[-1] > dea[-1] and dif[-2] <= dea[-2] else 'dead' if dif[-1] < dea[-1] and dif[-2] >= dea[-2] else 'neutral' if len(dif) > 2 else None
    }

def calculate_rsi(data, period=14):
    closes = np.array([d['close'] for d in data])
    if len(closes) < period + 1:
        return None
    
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
    rsi = 100 - (100 / (1 + rs))
    
    return {
        'RSI': round(rsi, 2),
        'status': 'overbought' if rsi > 70 else 'oversold' if rsi < 30 else 'neutral'
    }

def calculate_kdj(data, period=9):
    closes = np.array([d['close'] for d in data])
    highs = np.array([d['high'] for d in data])
    lows = np.array([d['low'] for d in data])
    
    if len(closes) < period:
        return None
    
    k_values = []
    d_values = []
    
    for i in range(period - 1, len(closes)):
        high_range = np.max(highs[i-period+1:i+1])
        low_range = np.min(lows[i-period+1:i+1])
        rsv = (closes[i] - low_range) / (high_range - low_range) * 100 if high_range != low_range else 50
        
        k = (2/3 * k_values[-1] + 1/3 * rsv) if k_values else rsv
        d = (2/3 * d_values[-1] + 1/3 * k) if d_values else k
        
        k_values.append(k)
        d_values.append(d)
    
    j = 3 * np.array(k_values) - 2 * np.array(d_values)
    
    return {
        'K': round(k_values[-1], 2) if k_values else None,
        'D': round(d_values[-1], 2) if d_values else None,
        'J': round(j[-1], 2) if len(j) > 0 else None,
        'signal': 'golden' if k_values[-1] > d_values[-1] and k_values[-2] <= d_values[-2] else 'dead' if k_values[-1] < d_values[-1] and k_values[-2] >= d_values[-2] else 'neutral' if len(k_values) > 2 else None
    }

def calculate_bollinger(data, period=20):
    closes = np.array([d['close'] for d in data])
    if len(closes) < period:
        return None
    
    middle = np.zeros(len(closes))
    for i in range(period - 1, len(closes)):
        middle[i] = np.mean(closes[i-period+1:i+1])
    
    std_dev = np.zeros(len(closes))
    for i in range(period - 1, len(closes)):
        std_dev[i] = np.std(closes[i-period+1:i+1])
    
    upper = middle + 2 * std_dev
    lower = middle - 2 * std_dev
    
    price_position = (closes[-1] - lower[-1]) / (upper[-1] - lower[-1]) if upper[-1] != lower[-1] else 0.5
    
    return {
        'upper': round(upper[-1], 2),
        'middle': round(middle[-1], 2),
        'lower': round(lower[-1], 2),
        'price_position': round(price_position, 4),
        'status': 'overbought' if price_position > 0.8 else 'oversold' if price_position < 0.2 else 'neutral'
    }

def main():
    parser = argparse.ArgumentParser(description='技术指标计算工具')
    parser.add_argument('--symbol', type=str, required=True, help='股票/指数代码')
    parser.add_argument('--indicators', type=str, default='all', help='技术指标列表，逗号分隔: ma,macd,rsi,kdj,boll,all')
    
    args = parser.parse_args()
    
    kline_data = get_kline_data(args.symbol, 120)
    
    if not kline_data:
        print(json.dumps({
            'status': 'error',
            'message': f'无法获取 {args.symbol} 的K线数据',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, ensure_ascii=False, indent=2))
        return
    
    result = {
        'status': 'success',
        'data': {
            'symbol': args.symbol,
            'indicators': {}
        },
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    indicators = args.indicators.split(',')
    
    if 'ma' in indicators or 'all' in indicators:
        result['data']['indicators']['MA'] = calculate_ma(kline_data)
    
    if 'macd' in indicators or 'all' in indicators:
        result['data']['indicators']['MACD'] = calculate_macd(kline_data)
    
    if 'rsi' in indicators or 'all' in indicators:
        result['data']['indicators']['RSI'] = calculate_rsi(kline_data)
    
    if 'kdj' in indicators or 'all' in indicators:
        result['data']['indicators']['KDJ'] = calculate_kdj(kline_data)
    
    if 'boll' in indicators or 'all' in indicators:
        result['data']['indicators']['Bollinger'] = calculate_bollinger(kline_data)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()