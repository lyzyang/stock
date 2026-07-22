#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import numpy as np
from datetime import datetime

from market_data import get_kline_data
from technical_indicators import calculate_ma, calculate_macd, calculate_rsi

def determine_market_regime():
    sh_data = get_kline_data('sh000001', 120)
    
    if not sh_data:
        return None
    
    closes = np.array([d['close'] for d in sh_data])
    
    ma = calculate_ma(sh_data, [20, 60])
    macd = calculate_macd(sh_data)
    rsi = calculate_rsi(sh_data)
    
    current_price = closes[-1]
    ma20 = ma.get('MA20')
    ma60 = ma.get('MA60')
    
    if ma20 is None or ma60 is None:
        return None
    
    ma20_trend = 'up' if len(closes) >= 40 and np.polyfit(range(20), closes[-20:], 1)[0] > 0 else 'down'
    
    volume = np.array([d['volume'] for d in sh_data])
    avg_volume_20 = np.mean(volume[-20:])
    avg_volume_5 = np.mean(volume[-5:])
    volume_ratio = avg_volume_5 / avg_volume_20 if avg_volume_20 != 0 else 1
    
    conditions = []
    
    if current_price > ma20 and ma20 > ma60 and ma20_trend == 'up':
        conditions.append('bullish_trend')
    elif current_price < ma20 and ma20 < ma60 and ma20_trend == 'down':
        conditions.append('bearish_trend')
    else:
        conditions.append('sideways')
    
    if macd:
        if macd['signal'] == 'golden':
            conditions.append('macd_golden_cross')
        elif macd['signal'] == 'dead':
            conditions.append('macd_dead_cross')
    
    if rsi:
        if rsi['RSI'] > 70:
            conditions.append('overbought')
        elif rsi['RSI'] < 30:
            conditions.append('oversold')
    
    if volume_ratio > 1.2:
        conditions.append('volume_increasing')
    elif volume_ratio < 0.8:
        conditions.append('volume_decreasing')
    
    regime = 'neutral'
    confidence = 0.5
    strategy = '观望'
    
    if 'bullish_trend' in conditions:
        if 'macd_golden_cross' in conditions and 'volume_increasing' in conditions:
            regime = 'strong_bullish'
            confidence = 0.85
            strategy = '趋势跟踪：回踩MA10/MA20可建仓'
        elif 'macd_golden_cross' in conditions or 'volume_increasing' in conditions:
            regime = 'weak_bullish'
            confidence = 0.65
            strategy = '偏多操作：逢低买入，控制仓位'
        else:
            regime = 'bullish'
            confidence = 0.7
            strategy = '趋势跟踪：顺势而为'
    
    elif 'bearish_trend' in conditions:
        if 'macd_dead_cross' in conditions and 'volume_increasing' in conditions:
            regime = 'strong_bearish'
            confidence = 0.85
            strategy = '空仓等待：不做多，可轻仓试空'
        elif 'macd_dead_cross' in conditions or 'volume_increasing' in conditions:
            regime = 'weak_bearish'
            confidence = 0.65
            strategy = '偏空操作：逢高减仓，降低仓位'
        else:
            regime = 'bearish'
            confidence = 0.7
            strategy = '防御为主：减少仓位，等待转机'
    
    else:
        if 'overbought' in conditions:
            regime = 'sideways_overbought'
            confidence = 0.6
            strategy = '震荡偏强：高抛低吸，上方压力位减仓'
        elif 'oversold' in conditions:
            regime = 'sideways_oversold'
            confidence = 0.6
            strategy = '震荡偏弱：低吸高抛，下方支撑位加仓'
        else:
            regime = 'sideways'
            confidence = 0.5
            strategy = '区间操作：高抛低吸，严格止损'
    
    return {
        'regime': regime,
        'confidence': round(confidence, 2),
        'strategy': strategy,
        'indicators': {
            'price_vs_ma20': 'above' if current_price > ma20 else 'below',
            'ma20_vs_ma60': 'above' if ma20 > ma60 else 'below',
            'ma20_trend': ma20_trend,
            'macd_signal': macd['signal'] if macd else None,
            'rsi_status': rsi['status'] if rsi else None,
            'volume_ratio': round(volume_ratio, 2)
        },
        'levels': {
            'current_price': round(current_price, 2),
            'ma20': ma20,
            'ma60': ma60
        }
    }

def main():
    result = {
        'status': 'success',
        'data': None,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    regime = determine_market_regime()
    
    if regime:
        result['data'] = regime
    else:
        result['status'] = 'error'
        result['message'] = '无法获取市场数据进行状态判断'
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()