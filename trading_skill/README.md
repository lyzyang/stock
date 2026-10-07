# 股票T+0智能决策系统

基于技术分析的股票日内交易决策辅助工具。**脚本只负责采集整理数据**（行情、K线、技术指标数值、客观风控状态），输出统一 JSON；**正T（先买后卖）/反T（先卖后买）/观望的判断、预测价与决策原因全部由 LLM 推理完成**，并按 SKILL.md 定义的统一格式输出决策报告。

## 功能特性

- **数据采集**：获取实时行情与多周期K线，计算 MA、RSI、MACD、布林带等指标数值
- **客观风控**：确定性计算盈亏、止盈/止损参考价及触发标志（布尔事实），LLM 必须优先尊重
- **LLM 推理**：开仓方向、预测价、出场时机、决策原因均由 LLM 基于事实数据推理
- **统一输出**：决策/出场/观望共用同一报告模板，确认成交使用独立确认模板
- **状态管理**：entry / exit / done 三阶段状态流转，记录实际入场价

## 快速开始

### 环境要求

- Python 3.8+
- 依赖库：pandas, requests

### 安装依赖

```bash
pip install pandas requests
```

### 配置参数

编辑 `trading_skill/src/config.py`：

```python
# 股票配置
STOCK_CODE = "600030"        # 股票代码
STOCK_NAME = "中信证券"       # 股票名称
EXCHANGE = "SH"              # 交易所

# 持仓配置
HOLDING_SHARES = 200         # 底仓股数

# 策略参数
MAX_POSITION_PCT = 0.5       # 单次T+0使用底仓比例
STOP_LOSS_PCT = 0.02         # 止损比例
TAKE_PROFIT_PCT = 0.015      # 止盈比例
```

### 运行方式

采集数据（输出 `stock-t0-data/v1` JSON，由 LLM 推理后渲染报告）：

```bash
cd trading_skill
python src/main.py
```

用户确认成交（price 为实际成交价格，type 为 LLM 建议的方向）：

```bash
python src/main.py confirm <price> <positive|negative>
```

> 定时场景使用 `bash scripts/run_trading.sh`（含午间休市静默逻辑）。完整的采集→推理→输出规范见 SKILL.md。

## 场景测试

使用 `src/scenarios.py` 脚本构造测试场景，模拟不同交易阶段的状态：

### 场景列表

| 命令 | 场景描述 | 说明 |
|------|----------|------|
| `pre` | 盘前等待建议 | entry 初始状态，等待 LLM 依据数据推理 |
| `pt_buy_wait` | 等待入场确认（正T买入） | entry 状态，LLM 建议在对话中待用户确认 |
| `pt_buy_exec` | 正T已入场 | exit 状态，入场价 28.10，持仓监控中 |
| `pt_sell_wait` | 等待出场确认（正T卖出） | exit 状态，卖出建议在对话中待用户确认 |
| `pt_sell_exec` | 正T完成 | done 状态 |
| `at_sell_wait` | 等待入场确认（反T卖出） | entry 状态，LLM 建议在对话中待用户确认 |
| `at_sell_exec` | 反T已入场 | exit 状态，入场价 28.80，持仓监控中 |
| `at_buy_wait` | 等待出场确认（反T买入接回） | exit 状态，接回建议在对话中待用户确认 |
| `at_buy_exec` | 反T完成 | done 状态 |
| `show` | 显示当前状态 | 查看当前状态文件内容（调试用） |

### 使用示例

#### 场景1：盘前等待建议

```bash
python src/scenarios.py pre
python src/main.py
```

**预期输出：**
- stdout 输出 `stock-t0-data/v1` JSON（行情、指标数值、近期K线）
- LLM 读取 JSON 推理后，按统一模板渲染正T/反T/观望决策报告

#### 场景2：正T交易流程

```bash
# 设置等待入场确认（正T买入）
python src/scenarios.py pt_buy_wait
python src/main.py

# 执行入场（模拟用户回复「执行」）
python src/scenarios.py pt_buy_exec

# 设置等待出场确认（正T卖出）
python src/scenarios.py pt_sell_wait
python src/main.py

# 执行出场（模拟用户回复「执行」）
python src/scenarios.py pt_sell_exec
```

#### 场景3：反T交易流程

```bash
# 设置等待入场确认（反T卖出）
python src/scenarios.py at_sell_wait
python src/main.py

# 执行入场（模拟用户回复「执行」）
python src/scenarios.py at_sell_exec

# 设置等待出场确认（反T买入接回）
python src/scenarios.py at_buy_wait
python src/main.py

# 执行出场（模拟用户回复「执行」）
python src/scenarios.py at_buy_exec
```

### 完整流程模拟示例

**正T完整流程：**
```bash
# 盘前等待建议
python src/scenarios.py pre
python src/main.py

# 设置等待入场确认（正T买入）
python src/scenarios.py pt_buy_wait
python src/main.py

# 执行入场（模拟用户回复「执行」）
python src/scenarios.py pt_buy_exec

# 设置等待出场确认（正T卖出）
python src/scenarios.py pt_sell_wait
python src/main.py

# 执行出场（模拟用户回复「执行」）
python src/scenarios.py pt_sell_exec
```

**反T完整流程：** 
```bash
# 盘前等待建议
python src/scenarios.py pre
python src/main.py

# 设置等待入场确认（反T卖出）
python src/scenarios.py at_sell_wait
python src/main.py

# 执行入场（模拟用户回复「执行」）
python src/scenarios.py at_sell_exec

# 设置等待出场确认（反T买入接回）
python src/scenarios.py at_buy_wait
python src/main.py

# 执行出场（模拟用户回复「执行」）
python src/scenarios.py at_buy_exec
```

## 项目结构

```
trading_skill/
├── src/
│   ├── config.py          # 配置参数
│   ├── analyzer.py        # 技术分析逻辑
│   ├── data_fetcher.py    # 数据获取
│   ├── state_manager.py   # 状态管理
│   ├── main.py            # 主入口
│   └── scenarios.py       # 场景测试脚本
└── state.json             # 状态文件（运行时自动生成）
```

## 用户交互

| 指令 | 说明 |
|------|------|
| 执行 | 确认决策，执行交易操作 |
| 忽略 | 不回复或忽略消息，系统继续监控市场 |

## 注意事项

1. T+0交易需要有足够的底仓，且卖出时需确保有可卖份额
2. 系统仅提供决策建议，实际交易需用户手动在券商APP中操作

## 业务逻辑

详细的业务逻辑、技术指标和流程图请参考 [business_logic_summary.md](file:///d:/workspace/stock/trading_skill/business_logic_summary.md)
