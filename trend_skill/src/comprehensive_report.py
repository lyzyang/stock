#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
from datetime import datetime

from market_data import get_realtime_quote, INDEX_MAP
from technical_indicators import calculate_ma, calculate_macd, calculate_rsi, calculate_kdj, calculate_bollinger
from sentiment_analysis import get_market_breadth, get_limit_up_down, get_north_bound_flow, calculate_sentiment_score
from market_regime import determine_market_regime

def generate_report():
    report = {
        'status': 'success',
        'data': {},
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    report['data']['market_overview'] = {}
    for key, info in INDEX_MAP.items():
        quote = get_realtime_quote(info['code'])
        if quote:
            report['data']['market_overview'][key] = quote
    
    sh_data = []
    try:
        from market_data import get_kline_data
        sh_data = get_kline_data('sh000001', 120)
    except:
        pass
    
    if sh_data:
        report['data']['technical_analysis'] = {
            'MA': calculate_ma(sh_data),
            'MACD': calculate_macd(sh_data),
            'RSI': calculate_rsi(sh_data),
            'KDJ': calculate_kdj(sh_data),
            'Bollinger': calculate_bollinger(sh_data)
        }
    
    breadth = get_market_breadth()
    limit_data = get_limit_up_down()
    north_flow = get_north_bound_flow()
    
    report['data']['sentiment_analysis'] = {
        'breadth': breadth,
        'limit_up_down': limit_data,
        'north_bound_flow': north_flow,
        'sentiment': calculate_sentiment_score(breadth, limit_data, north_flow, None)
    }
    
    regime = determine_market_regime()
    if regime:
        report['data']['market_regime'] = regime
    
    report['data']['summary'] = generate_summary(report)
    
    return report

def generate_summary(report):
    overview = report['data'].get('market_overview', {})
    sentiment = report['data'].get('sentiment_analysis', {}).get('sentiment', {})
    regime = report['data'].get('market_regime', {})
    
    summary = []
    
    if overview:
        sh = overview.get('sh')
        sz = overview.get('sz')
        cy = overview.get('cy')
        
        if sh:
            summary.append(f"上证指数: {sh['price']:.2f} ({'+' if sh['change'] > 0 else ''}{sh['change_percent']:.2f}%)")
        if sz:
            summary.append(f"深证成指: {sz['price']:.2f} ({'+' if sz['change'] > 0 else ''}{sz['change_percent']:.2f}%)")
        if cy:
            summary.append(f"创业板指: {cy['price']:.2f} ({'+' if cy['change'] > 0 else ''}{cy['change_percent']:.2f}%)")
    
    if sentiment:
        summary.append(f"市场情绪: {sentiment.get('level', '未知')} (评分: {sentiment.get('score', 50)}/100)")
    
    if regime:
        regime_map = {
            'strong_bullish': '强势多头',
            'weak_bullish': '弱势多头',
            'bullish': '多头',
            'strong_bearish': '强势空头',
            'weak_bearish': '弱势空头',
            'bearish': '空头',
            'sideways_overbought': '震荡偏强',
            'sideways_oversold': '震荡偏弱',
            'sideways': '震荡'
        }
        summary.append(f"市场状态: {regime_map.get(regime['regime'], '未知')} (置信度: {regime['confidence']*100:.0f}%)")
        summary.append(f"操作策略: {regime['strategy']}")
    
    return '\n'.join(summary)

def format_report(report):
    data = report.get('data', {})
    timestamp = report.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    lines = []
    lines.append(f"大盘分析结果（{timestamp}）")
    lines.append("")
    
    market_overview = data.get('market_overview', {})
    if market_overview:
        lines.append("**指数行情**")
        for key, info in INDEX_MAP.items():
            quote = market_overview.get(key)
            if quote:
                change_sign = '+' if quote['change'] > 0 else ''
                lines.append(f"- {quote['name']}: {quote['price']:.2f}（{change_sign}{quote['change_percent']:.2f}%）")
        lines.append("")
    
    technical = data.get('technical_analysis', {})
    if technical:
        lines.append("**技术指标**")
        ma = technical.get('MA', {})
        if ma:
            ma_values = []
            for period in ['MA5', 'MA10', 'MA20', 'MA60']:
                val = ma.get(period)
                if val:
                    ma_values.append(f"{period}: {val:.2f}")
            if ma_values:
                lines.append(f"- {' / '.join(ma_values)}")
        
        macd = technical.get('MACD', {})
        if macd:
            signal = macd.get('signal', '中性')
            lines.append(f"- MACD：DIF {macd.get('DIF', 0):.2f} / DEA {macd.get('DEA', 0):.2f} / MACD {macd.get('MACD', 0):.2f}，信号：{signal}")
        
        rsi = technical.get('RSI', {})
        if rsi:
            lines.append(f"- RSI：{rsi.get('RSI', 0):.2f}（{rsi.get('status', '中性')}）")
        
        kdj = technical.get('KDJ', {})
        if kdj:
            lines.append(f"- KDJ：K {kdj.get('K', 0):.2f} / D {kdj.get('D', 0):.2f} / J {kdj.get('J', 0):.2f}（{kdj.get('status', '中性')}）")
        
        boll = technical.get('Bollinger', {})
        if boll:
            lines.append(f"- 布林带：上轨 {boll.get('upper', 0):.2f} / 中轨 {boll.get('middle', 0):.2f} / 下轨 {boll.get('lower', 0):.2f}，状态：{boll.get('status', '中性')}")
        lines.append("")
    
    sentiment = data.get('sentiment_analysis', {})
    if sentiment:
        lines.append("**市场情绪**")
        breadth = sentiment.get('breadth', {})
        if breadth:
            lines.append(f"- 涨跌家数：上涨 {breadth.get('up_count', 0)} / 下跌 {breadth.get('down_count', 0)} / 平盘 {breadth.get('flat_count', 0)}")
        
        limit_data = sentiment.get('limit_up_down', {})
        if limit_data:
            lines.append(f"- 涨停/跌停：{limit_data.get('limit_up', 0)} / {limit_data.get('limit_down', 0)}")
        
        north_flow = sentiment.get('north_bound_flow', {})
        if north_flow:
            flow = north_flow.get('north_bound_flow', 0)
            unit = north_flow.get('unit', '万元')
            flow_sign = '+' if flow > 0 else ''
            lines.append(f"- 北向资金净流入：{flow_sign}{flow:.2f} {unit}")
        
        sent = sentiment.get('sentiment', {})
        if sent:
            lines.append(f"- 情绪评分：{sent.get('score', 50)}/100（{sent.get('level', '中性')}）")
        lines.append("")
    
    regime = data.get('market_regime', {})
    if regime:
        lines.append("**市场状态**")
        regime_map = {
            'strong_bullish': '强势多头',
            'weak_bullish': '弱势多头',
            'bullish': '多头',
            'strong_bearish': '强势空头',
            'weak_bearish': '弱势空头',
            'bearish': '空头',
            'sideways_overbought': '震荡偏强',
            'sideways_oversold': '震荡偏弱',
            'sideways': '震荡'
        }
        lines.append(f"- 当前状态：{regime_map.get(regime['regime'], '未知')}（置信度 {regime.get('confidence', 0)*100:.0f}%）")
        lines.append(f"- 操作策略：{regime.get('strategy', '观望')}")
        lines.append("")
    
    summary = data.get('summary', '')
    if summary:
        lines.append("**综合摘要**")
        lines.append(summary)
    
    return '\n'.join(lines)

def main():
    result = generate_report()
    print(format_report(result))

if __name__ == '__main__':
    main()