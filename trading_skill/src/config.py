"""
股票T+0决策工具 - 配置文件
根据实际需求修改这里的参数
"""

# ========== 股票配置 ==========
STOCK_CODE = "600030"        # 股票代码（中信证券）
STOCK_NAME = "中信证券"       # 股票名称
EXCHANGE = "SH"              # 交易所: SH=上交所, SZ=深交所

# ========== 持仓配置 ==========
HOLDING_SHARES = 200         # 持有底仓股数

# ========== T+0 策略参数 ==========
# 正T（先买后卖）：股价跌到买入触发位以下时，发出买入信号
# 反T（先卖后买）：股价涨到卖出触发位以上时，发出卖出信号
BUY_TRIGGER_MA_DEVIATION = -0.008   # 买入触发：价格低于某均线 N% 时考虑买入（如 -0.8%）
SELL_TRIGGER_MA_DEVIATION = 0.008  # 卖出触发：价格高于某均线 N% 时考虑卖出（如 +0.8%）

# 技术指标参数
MA_SHORT = 5                 # 短期均线周期（5分钟K线）
MA_LONG = 20                 # 长期均线周期（5分钟K线）
RSI_PERIOD = 14              # RSI 周期
RSI_OVERSOLD = 30            # RSI 超卖阈值
RSI_OVERBOUGHT = 70          # RSI 超买阈值

# 风控参数
MAX_POSITION_PCT = 0.5       # 单次T+0最大使用底仓比例（如 0.3 = 30% 底仓）
STOP_LOSS_PCT = 0.02         # 止损比例 2%
TAKE_PROFIT_PCT = 0.02       # 止盈比例 1.5%

# 出场阶段动态建议参数
EXIT_TRIGGER_RSI = 55        # 出场动态建议 RSI 阈值
EXIT_TRIGGER_BOLLINGER_PCT = 0.004  # 出场动态建议布林带偏离比例

# 反T上涨保护参数
NEGATIVE_T_BOLLINGER_STOP_PCT = 0.003  # 反T卖出后，突破布林上轨一定比例即止损接回

# 预测价参数
RECENT_LOOKBACK = 10          # 近期高低点回看周期
PREDICTED_PRICE_MIN_PCT = 0.005  # 预测价与当前价最小波动幅度（防止无意义预测）

# ========== 运行配置 ==========
KLINE_PERIOD = "5min"        # K线周期: 1min, 5min, 15min, 30min, 60min
KLINE_COUNT = 60             # 获取K线根数
DEBUG_MODE = False           # 调试模式：True=显示详细日志，False=仅显示必要信息（生产环境）

# ========== 输出格式 ==========
# 决策消息模板（使用 \n 换行符，确保微信等通道能正确显示换行）
DECISION_TEMPLATE = "T+0 决策报告（{decision_time}）\n\n**基本信息**\n- 股票: {stock_name} ({stock_code})\n- 当前价格: {current_price}\n- 决策类型: {decision_type}\n\n**操作建议**\n- 建议操作: {suggested_action}\n- 预测价: {predicted_price}\n- 目标价: {target_price}\n- 止损价: {stop_loss_price}\n\n**技术指标**\n- {indicators}\n\n**决策原因**\n{reason}\n\n请回复「执行」确认操作，忽略则继续监控"
