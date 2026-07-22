# 股票T+0智能决策系统

基于技术分析的股票日内交易决策工具，提供正T（先买后卖）和反T（先卖后买）交易建议，支持入场后持续监控止盈止损。决策报告新增预测价字段，基于布林带和近期高低点综合计算目标价位。

## 功能特性

- **盘前分析**：进行技术分析，给出T+0交易建议
- **盘中监控**：入场后持续监控止盈止损、反T上涨保护
- **动态建议**：基于 MA、RSI、MACD、布林带等技术指标给出交易信号
- **预测价计算**：综合布林带和近期高低点，为正T/反T提供目标价位参考
- **状态管理**：支持今日已交易、等待确认、交易完成等状态流转

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

```bash
cd trading_skill
python src/main.py
```

## 场景测试

使用 `src/scenarios.py` 脚本构造测试场景，模拟不同交易阶段的状态：

### 场景列表

| 命令 | 场景描述 | 说明 |
|------|----------|------|
| `pre` | 盘前等待建议 | 初始状态，等待系统生成交易信号 |
| `pt_buy_wait` | 设置等待入场确认（正T买入） | 系统已生成正T买入信号，等待用户确认 |
| `pt_buy_exec` | 执行入场（正T买入） | 模拟用户回复「执行」，执行正T买入 |
| `pt_sell_wait` | 设置等待出场确认（正T卖出） | 正T买入后等待卖出确认 |
| `pt_sell_exec` | 执行出场（正T卖出） | 模拟用户回复「执行」，执行正T卖出 |
| `at_sell_wait` | 设置等待入场确认（反T卖出） | 系统已生成反T卖出信号，等待用户确认 |
| `at_sell_exec` | 执行入场（反T卖出） | 模拟用户回复「执行」，执行反T卖出 |
| `at_buy_wait` | 设置等待出场确认（反T买入接回） | 反T卖出后等待买入接回确认 |
| `at_buy_exec` | 执行出场（反T买入接回） | 模拟用户回复「执行」，执行反T买入接回 |
| `show` | 显示当前状态 | 查看当前状态文件内容（调试用） |

### 使用示例

#### 场景1：盘前等待建议

```bash
python src/scenarios.py pre
python src/main.py
```

**预期输出：**
- 生成正T/反T交易决策报告
- 显示股票信息、操作建议、预测价、目标价、止损价、技术指标

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
