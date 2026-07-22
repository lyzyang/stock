# A股数据API文档

## 数据源概览

### 1. 腾讯财经 (web.ifzq.gtimg.cn)

**实时行情接口**
- URL: `http://web.ifzq.gtimg.cn/appstock/app/fqkline/getTimeData?param={symbol},m5,m15,m30,m60,d,w,m,mt`
- 编码: GBK
- 返回格式: JSON

**历史K线接口**
- URL: `http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,{start_date},{end_date},640,fq`
- 编码: GBK
- 返回格式: JSON

### 2. 东方财富 (push2.eastmoney.com)

**市场广度接口**
- URL: `https://push2.eastmoney.com/api/qt/clist/get`
- 参数: 包含A股所有股票列表

**涨跌停数据**
- URL: `https://data.eastmoney.com/bkds/limitUpDown.html`
- 返回格式: HTML中的JavaScript变量

**北向资金接口**
- URL: `https://push2.eastmoney.com/api/qt/qmtot.rtmin/get`

## 指数代码对照表

| 指数名称 | 代码 | 前缀 |
|---|---|---|
| 上证指数 | 000001 | sh |
| 深证成指 | 399001 | sz |
| 创业板指 | 399006 | sz |
| 沪深300 | 000300 | sh |

## 股票代码规则

- 沪市股票: `sh` + 6位代码 (如 sh600519)
- 深市股票: `sz` + 6位代码 (如 sz000858)
- 创业板股票: `sz` + 6位代码 (如 sz300750)

## 返回数据字段说明

### 实时行情数据

| 字段 | 说明 | 示例 |
|---|---|---|
| code | 股票代码 | sh000001 |
| name | 股票名称 | 上证指数 |
| price | 当前价格 | 3200.50 |
| open | 开盘价 | 3180.00 |
| pre_close | 昨收盘价 | 3195.80 |
| high | 最高价 | 3210.00 |
| low | 最低价 | 3175.00 |
| volume | 成交量(手) | 3500000 |
| amount | 成交额(元) | 56000000000 |
| change | 涨跌额 | 4.70 |
| change_percent | 涨跌幅(%) | 0.15 |

### K线数据

| 字段 | 说明 | 示例 |
|---|---|---|
| date | 日期 | 2024-01-15 |
| open | 开盘价 | 3180.00 |
| close | 收盘价 | 3200.50 |
| high | 最高价 | 3210.00 |
| low | 最低价 | 3175.00 |
| volume | 成交量(手) | 3500000 |
| amount | 成交额(元) | 56000000000 |

### 技术指标数据

**MA指标**
| 字段 | 说明 |
|---|---|
| MA5 | 5日均线 |
| MA10 | 10日均线 |
| MA20 | 20日均线 |
| MA60 | 60日均线 |

**MACD指标**
| 字段 | 说明 |
|---|---|
| DIF | 差离值 |
| DEA | 讯号线 |
| MACD | MACD柱状图 |
| signal | 信号: golden/dead/neutral |

**RSI指标**
| 字段 | 说明 |
|---|---|
| RSI | RSI值(0-100) |
| status | 状态: overbought/oversold/neutral |

**KDJ指标**
| 字段 | 说明 |
|---|---|
| K | K值 |
| D | D值 |
| J | J值 |
| signal | 信号: golden/dead/neutral |

**布林带指标**
| 字段 | 说明 |
|---|---|
| upper | 上轨 |
| middle | 中轨(MA20) |
| lower | 下轨 |
| price_position | 价格位置(0-1) |
| status | 状态: overbought/oversold/neutral |

### 情绪数据

**市场广度**
| 字段 | 说明 |
|---|---|
| total | 股票总数 |
| up_count | 上涨家数 |
| down_count | 下跌家数 |
| flat_count | 平盘家数 |
| up_ratio | 上涨比例(%) |
| down_ratio | 下跌比例(%) |

**涨跌停数据**
| 字段 | 说明 |
|---|---|
| limit_up | 涨停家数 |
| limit_down | 跌停家数 |

**北向资金**
| 字段 | 说明 |
|---|---|
| north_bound_flow | 北向资金净流入(万元) |

### 市场状态

| 字段 | 说明 |
|---|---|
| regime | 市场状态 |
| confidence | 置信度(0-1) |
| strategy | 操作策略 |
| indicators | 指标详情 |
| levels | 关键价位 |

## 错误处理

所有API调用均包含错误处理，返回格式统一：

```json
{
  "status": "error",
  "message": "错误描述",
  "timestamp": "2024-01-15 10:30:00"
}
```

## 注意事项

1. 腾讯财经接口返回GBK编码，需显式设置encoding='gbk'
2. 东方财富接口需要设置User-Agent和Referer头
3. 建议在请求之间添加适当延迟，避免被限流
4. 实时行情数据在非交易时段可能不更新