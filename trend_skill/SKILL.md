---
name: stock-market-analysis
description: A股大盘分析与市场情绪分析工具，提供实时大盘数据、技术指标计算和市场情绪评估
user-invocable: true
---

# A股大盘分析与情绪分析

专业的A股市场分析工具，提供大盘指数数据、技术指标计算、市场情绪评估等功能。

## 功能概览

| 功能模块 | 描述 |
|---|---|
| 大盘数据 | 获取上证指数、深证成指、创业板指等主要指数的实时行情和历史数据 |
| 技术指标 | 计算MA、MACD、RSI、KDJ、布林带等常用技术指标 |
| 情绪分析 | 分析市场涨跌家数、涨跌停家数、资金流向等情绪指标 |
| 市场状态 | 判断当前市场处于多头、空头还是震荡状态 |

## 使用场景

当用户询问以下内容时使用此技能：
- A股大盘走势、上证指数/深证成指/创业板指行情
- 市场情绪、涨跌家数、涨跌停统计
- 技术指标分析（MA、MACD、RSI、KDJ等）
- 市场状态判断、策略建议

## 可用命令

### 1. 获取大盘行情数据

```bash
python {baseDir}/src/market_data.py --index all
```

获取所有主要指数（上证指数、深证成指、创业板指、沪深300）的最新行情数据。

**参数**：
- `--index`：指定指数，可选值：`sh`（上证指数）、`sz`（深证成指）、`cy`（创业板指）、`hs300`（沪深300）、`all`（全部）

**示例**：
```bash
python {baseDir}/src/market_data.py --index sh
python {baseDir}/src/market_data.py --index all
```

### 2. 获取历史K线数据

```bash
python {baseDir}/src/market_data.py --kline --symbol sh000001 --days 60
```

获取指定股票或指数的历史K线数据。

**参数**：
- `--symbol`：股票/指数代码，沪市前缀`sh`，深市前缀`sz`
- `--days`：获取天数（默认60天）

**示例**：
```bash
python {baseDir}/src/market_data.py --kline --symbol sh000001 --days 120
python {baseDir}/src/market_data.py --kline --symbol sz000001 --days 30
```

### 3. 计算技术指标

```bash
python {baseDir}/src/technical_indicators.py --symbol sh000001 --indicators macd,rsi,ma
```

计算指定股票或指数的技术指标。

**参数**：
- `--symbol`：股票/指数代码
- `--indicators`：技术指标列表，逗号分隔，可选值：`ma`、`macd`、`rsi`、`kdj`、`boll`、`all`

**示例**：
```bash
python {baseDir}/src/technical_indicators.py --symbol sh000001 --indicators all
python {baseDir}/src/technical_indicators.py --symbol sz399006 --indicators macd,rsi
```

### 4. 市场情绪分析

```bash
python {baseDir}/src/sentiment_analysis.py
```

获取市场情绪数据，包括涨跌家数、涨跌停家数、资金流向等。

**示例**：
```bash
python {baseDir}/src/sentiment_analysis.py
```

### 5. 市场状态判断

```bash
python {baseDir}/src/market_regime.py
```

综合分析当前市场状态，判断是多头、空头还是震荡市场，并给出策略建议。

**示例**：
```bash
python {baseDir}/src/market_regime.py
```

### 6. 综合分析报告

```bash
python {baseDir}/src/comprehensive_report.py
```

生成完整的市场分析报告，包含大盘行情、技术指标、情绪分析和市场状态判断。

**示例**：
```bash
python {baseDir}/src/comprehensive_report.py
```

## 数据来源

- **腾讯财经**：实时行情数据、历史K线
- **东方财富**：市场情绪数据（涨跌家数、资金流向）
- **新浪财经**：补充数据

## 注意事项

- 数据仅供参考，不构成投资建议
- 实时行情在交易时段更新，非交易时段显示最新收盘价
- 市场情绪数据在交易日收盘后更新
- 建议在交易时段（9:30-15:00）获取最新数据

## 输出格式

所有命令均输出JSON格式数据，便于AI解析和展示。

**示例输出格式**：
```json
{
  "status": "success",
  "data": {
    "index": "上证指数",
    "code": "sh000001",
    "price": 3200.50,
    "change": 1.25,
    "change_percent": 0.04,
    "volume": 3500000000,
    "market_cap": 55000000000000
  },
  "timestamp": "2024-01-15 10:30:00"
}
```