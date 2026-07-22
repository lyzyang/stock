#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import requests
from datetime import datetime

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
                    north_flow = float(fields[43]) if fields[43] else 0
                    return {
                        'north_bound_flow': round(north_flow, 2),
                        'unit': '万元'
                    }
        return None
    except Exception as e:
        print(f"Error getting north bound flow: {e}", file=sys.stderr)
        return None

def get_average_turnover():
    try:
        url = 'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh000001&scale=240&ma=5,10,20&datalen=5'
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        if data and isinstance(data, list) and len(data) > 0:
            total_amount = sum(float(item.get('volume', 0)) * float(item.get('close', 1)) / 100 for item in data)
            return {
                'total_amount': round(total_amount / 10000, 2),
                'unit': '万元'
            }
        return None
    except Exception as e:
        print(f"Error getting average turnover: {e}", file=sys.stderr)
        return None

def calculate_sentiment_score(breadth, limit_data, north_flow, turnover):
    score = 50
    
    if breadth:
        up_ratio = breadth['up_ratio']
        if up_ratio > 70:
            score += 25
        elif up_ratio > 55:
            score += 10
        elif up_ratio < 30:
            score -= 25
        elif up_ratio < 45:
            score -= 10
    
    if limit_data:
        limit_up = limit_data.get('limit_up', 0)
        limit_down = limit_data.get('limit_down', 0)
        if limit_up > limit_down * 3:
            score += 15
        elif limit_down > limit_up * 3:
            score -= 15
    
    if north_flow:
        flow = north_flow['north_bound_flow']
        if flow > 50000:
            score += 10
        elif flow < -50000:
            score -= 10
    
    score = max(0, min(100, score))
    
    if score >= 75:
        level = '极端乐观'
    elif score >= 60:
        level = '偏乐观'
    elif score >= 40:
        level = '中性'
    elif score >= 25:
        level = '偏悲观'
    else:
        level = '极端悲观'
    
    return {
        'score': score,
        'level': level
    }

def main():
    result = {
        'status': 'success',
        'data': {},
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    result['data']['breadth'] = get_market_breadth()
    result['data']['limit_up_down'] = get_limit_up_down()
    result['data']['north_bound_flow'] = get_north_bound_flow()
    result['data']['turnover'] = get_average_turnover()
    
    sentiment = calculate_sentiment_score(
        result['data']['breadth'],
        result['data']['limit_up_down'],
        result['data']['north_bound_flow'],
        result['data']['turnover']
    )
    result['data']['sentiment'] = sentiment
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()