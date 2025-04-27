import json
import os
import random
import time
import base64
from datetime import datetime, timedelta, date
import math
import asyncio # 用于文件锁
import io         # 用于在内存中处理图像
import plotly.graph_objects as go
import plotly.io as pio
from ..utils import chain_reply
from .._R import get, userPath

from hoshino import Service, priv, R
from hoshino.typing import CQEvent, MessageSegment
from .. import money 
from hoshino.config import SUPERUSERS
sv = Service('stock_market', manage_priv=priv.ADMIN, enable_on_default=True)
no = get('emotion/no.png').cqcode
ok = get('emotion/ok.png').cqcode

STOCKS_FILE = os.path.join(userPath, 'chaogu/stock_data.json')
PORTFOLIOS_FILE = os.path.join(userPath, 'chaogu/user_portfolios.json')
GAMBLE_LIMITS_FILE = os.path.join(userPath, 'chaogu/daily_gamble_limits.json')
HISTORY_DURATION_HOURS = 24 # 只保留过去24小时数据

# 锁，防止并发读写JSON文件导致数据损坏
stock_file_lock = asyncio.Lock()
portfolio_file_lock = asyncio.Lock()

# 股票定义 (名称: 初始价格)
STOCKS = {
    "萝莉股": 100.0,
    "猫娘股": 120.0,
    "魔法少女股": 140.0,
    "梦月股": 500.0,
    "梦馨股": 200.0,
    "高达股": 90.0,
    "雾月股": 240.0,
    "傲娇股": 130.0,
    "病娇股": 70.0,
    "梦灵股": 250.0,
    "铃音股": 230.0,
    "音祈股": 1000.0,
    "梦铃股": 500.0,
}

# --- 辅助函数：读写JSON ---

async def load_json_data(filename, default_data, lock):
    """异步安全地加载JSON数据"""
    async with lock:
        if not os.path.exists(filename):
            return default_data
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # 文件损坏或读取错误，返回默认值
            return default_data

async def save_json_data(filename, data, lock):
    """异步安全地保存JSON数据"""
    async with lock:
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
            # 使用临时文件和原子移动来增加保存的安全性
            temp_filename = filename + ".tmp"
            with open(temp_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            os.replace(temp_filename, filename) # 原子操作替换
        except IOError as e:
            print(f"Error saving JSON data to {filename}: {e}")
            # Consider logging the error more formally in a real application
            # pass # Or raise the exception if needed




# 市场事件定义 (类型: {描述, 影响范围, 影响函数})
MARKET_EVENTS = {
    "利好": {
        "templates": [
            "{stock}获得新的市场投资！",
            "{stock}获得异次元政府补贴！",
            "{stock}季度财报超预期！"
        ],
        "scope": "single",  # 影响单只股票
        "effect": lambda price: price * random.uniform(1.10, 1.30)  # 小幅上涨
    },
    "利空": {
        "templates": [
            "{stock}产品力下降！",
            "{stock}产品发现严重缺陷！",
            "{stock}高管突然离职！"
        ],
        "scope": "single",
        "effect": lambda price: price * random.uniform(0.70, 0.90)  # 小幅下跌
    },
    "大盘上涨": {
        "templates": [
            "鹰酱宣布降息，市场普涨！",
            "异次元经济复苏，投资者信心增强！",
            "魔法少女在战争中大捷，领涨大盘！"
        ],
        "scope": "all",  # 影响所有股票
        "effect": lambda price: price * random.uniform(1.1, 1.25)  # 全体上涨
    },
    "大盘下跌": {
        "templates": [
            "异次元国际局势紧张，市场恐慌！",
            "经济数据不及预期，市场普跌！",
            "机构投资者大规模抛售！"
        ],
        "scope": "all",
        "effect": lambda price: price * random.uniform(0.80, 0.95)  # 全体下跌
    },
    "暴涨": {
        "templates": [
            "{stock}成为市场新宠，资金疯狂涌入！",
            "{stock}发现新资源，价值重估！"
        ],
        "scope": "single",
        "effect": lambda price: price * random.uniform(1.25, 2.5)  # 大幅上涨
    },
    "暴跌": {
        "templates": [
            "{stock}被曝财务造假！",
            "{stock}主要产品被禁售！"
        ],
        "scope": "single",
        "effect": lambda price: price * random.uniform(0.40, 0.80)  # 大幅下跌
    }
}

# 在 MARKET_EVENTS 定义后添加
MANUAL_EVENT_TYPES = {
    "利好": "单股上涨",
    "利空": "单股下跌", 
    "暴涨": "单股暴涨",
    "暴跌": "单股暴跌",
    "大盘上涨": "全局上涨",
    "大盘下跌": "全局下跌"
}

# 事件触发概率配置
EVENT_PROBABILITY = 0.99  # 每次价格更新时有99%概率触发事件
EVENT_COOLDOWN = 3500  # 事件冷却时间2小时(秒)

# --- 辅助函数：获取和更新数据 ---
async def get_stock_data():
    """获取所有股票数据"""
    default = {
        name: {"initial_price": price, "history": []}
        for name, price in STOCKS.items()
    }
    return await load_json_data(STOCKS_FILE, default, stock_file_lock)

async def save_stock_data(data):
    """保存所有股票数据"""
    await save_json_data(STOCKS_FILE, data, stock_file_lock)

async def get_user_portfolios():
    """获取所有用户持仓"""
    return await load_json_data(PORTFOLIOS_FILE, {}, portfolio_file_lock)

async def save_user_portfolios(data):
    """保存所有用户持仓"""
    await save_json_data(PORTFOLIOS_FILE, data, portfolio_file_lock)

async def get_current_stock_price(stock_name, stock_data=None):
    """获取指定股票的当前价格"""
    if stock_data is None:
        stock_data = await get_stock_data()
    
    if stock_name not in stock_data or not stock_data[stock_name]["history"]:
        # 如果没有历史记录，返回初始价格
        return stock_data.get(stock_name, {}).get("initial_price")
    
    # 返回最新价格
    return stock_data[stock_name]["history"][-1][1] # history is [(timestamp, price), ...]

async def get_stock_price_history(stock_name, stock_data=None):
    """获取指定股票过去24小时的价格历史"""
    if stock_data is None:
        stock_data = await get_stock_data()
    
    if stock_name not in stock_data:
        return []
        
    cutoff_time = time.time() - HISTORY_DURATION_HOURS * 3600
    history = stock_data[stock_name].get("history", [])
    
    # 筛选出24小时内的数据
    recent_history = [(ts, price) for ts, price in history if ts >= cutoff_time]
    return recent_history

async def get_user_portfolio(user_id):
    """获取单个用户的持仓"""
    portfolios = await get_user_portfolios()
    return portfolios.get(str(user_id), {}) # user_id 转为字符串以匹配JSON键

async def update_user_portfolio(user_id, stock_name, change_amount):
    """更新用户持仓 (正数为买入，负数为卖出)"""
    portfolios = await get_user_portfolios()
    user_id_str = str(user_id)
    
    if user_id_str not in portfolios:
        portfolios[user_id_str] = {}
        
    current_amount = portfolios[user_id_str].get(stock_name, 0)
    new_amount = current_amount + change_amount
    
    if new_amount < 0:
        # This should ideally be checked before calling update_user_portfolio
        print(f"Error: Attempted to make stock {stock_name} amount negative for user {user_id}")
        return False # Indicate failure

    if new_amount == 0:
        # 如果数量归零，从持仓中移除该股票
        if stock_name in portfolios[user_id_str]:
            del portfolios[user_id_str][stock_name]
        # 如果用户不再持有任何股票，可以考虑移除该用户条目（可选）
        # if not portfolios[user_id_str]:
        #     del portfolios[user_id_str]
    else:
        portfolios[user_id_str][stock_name] = new_amount
        
    await save_user_portfolios(portfolios)
    return True # Indicate success
    



@sv.scheduled_job('cron', hour='*', minute='0') # 每小时的0分执行
# async def update_all_stock_prices(): # 函数名用 update_all_stock_prices 更清晰
async def hourly_price_update_job():
    """定时更新所有股票价格"""
    print(f"[{datetime.now()}] Running hourly stock price update...")
    stock_data = await get_stock_data()
    current_time = time.time()
    cutoff_time = current_time - HISTORY_DURATION_HOURS * 3600

    changed = False
    event_triggered = False
    
    # 安全地获取最后事件时间
    try:
        last_event_time = max([
            max([event["time"] for event in stock.get("events", [])], default=0)
            for stock in stock_data.values()
        ], default=0)
    except Exception as e:
        print(f"Error getting last event time: {e}")
        last_event_time = 0
    
    can_trigger_event = (current_time - last_event_time) >= EVENT_COOLDOWN
    # 决定是否触发事件
    if can_trigger_event and random.random() < EVENT_PROBABILITY:
        event_type = random.choice(list(MARKET_EVENTS.keys()))
        event_info = MARKET_EVENTS[event_type]
        event_triggered = True
        
        # 选择受影响的股票
        if event_info["scope"] == "single":
            affected_stocks = [random.choice(list(STOCKS.keys()))]
        else:  # all
            affected_stocks = list(STOCKS.keys())
        
        # 对于大盘事件，只记录一次全局事件
        if event_info["scope"] == "all":
            # 随机选择一只股票作为代表记录事件
            representative_stock = random.choice(affected_stocks)
            template = random.choice(event_info["templates"])
            event_message = template  # 大盘事件不需要format股票名
            
            # 记录到代表股票的事件中
            stock_data[representative_stock]["events"].append({
                "time": current_time,
                "type": event_type,
                "message": event_message,
                "scope": "global",  # 新增字段标记全局事件
                "old_price": None,  # 对于全局事件不记录具体价格
                "new_price": None
            })
            # 清理旧事件 (保留最近10个)
            stock_data[representative_stock]["events"] = stock_data[representative_stock]["events"][-10:]
        
        # 应用事件影响
        for stock_name in affected_stocks:
            if stock_name not in stock_data:
                continue
                
            # 获取当前价格
            if stock_data[stock_name]["history"]:
                current_price = stock_data[stock_name]["history"][-1][1]
            else:
                current_price = stock_data[stock_name]["initial_price"]
            
            # 应用事件影响
            new_price = event_info["effect"](current_price)
            new_price = max(new_price, stock_data[stock_name]["initial_price"] * 0.01)  # 不低于1%
            new_price = min(new_price, stock_data[stock_name]["initial_price"] * 2.00)  # 不高于200%
            new_price = round(new_price, 2)
            
            # 对于单股事件，正常记录
            if event_info["scope"] == "single":
                template = random.choice(event_info["templates"])
                event_message = template.format(stock=stock_name)
                
                stock_data[stock_name]["events"].append({
                    "time": current_time,
                    "type": event_type,
                    "message": event_message,
                    "old_price": current_price,
                    "new_price": new_price
                })
                # 清理旧事件 (保留最近10个)
                stock_data[stock_name]["events"] = stock_data[stock_name]["events"][-10:]
            
            # 更新价格
            stock_data[stock_name]["history"].append((current_time, new_price))
            changed = True
            
        if event_triggered:
            print(f"[{datetime.now()}] Market event triggered: {event_type} affecting {len(affected_stocks)} stocks")

    # 正常价格波动 (如果没有触发事件或事件只影响部分股票)
    for name, data in stock_data.items():
        if event_triggered and name in affected_stocks:
            continue  # 已经由事件处理过
            
        initial_price = data["initial_price"]
        history = data.get("history", [])
        
        # 清理旧数据
        original_len = len(history)
        history = [(ts, price) for ts, price in history if ts >= cutoff_time]
        if len(history) != original_len:
             changed = True

        # 计算新价格
        if not history:
            current_price = initial_price
        else:
            current_price = history[-1][1]

        # 随机波动
        change_percent = random.uniform(-0.15, 0.18)
        regression_factor = 0.05
        change_percent += regression_factor * (initial_price - current_price) / current_price

        new_price = current_price * (1 + change_percent)
        new_price = max(initial_price * 0.01, min(new_price, initial_price * 2.00))
        new_price = round(new_price, 2) 
        
        if not history or history[-1][1] != new_price:
             history.append((current_time, new_price))
             stock_data[name]["history"] = history
             changed = True
        else:
             stock_data[name]["history"] = history

    if changed:
        await save_stock_data(stock_data)
        print(f"[{datetime.now()}] Stock prices updated and saved.")
    else:
        print(f"[{datetime.now()}] Stock prices checked, no significant changes to save.")

# --- 初始化：确保数据文件存在且结构正确 ---
# 可以在机器人启动时运行一次
async def initialize_stock_market():
    """初始化股票市场数据"""
    print("Initializing stock market data...")
    stock_data = await get_stock_data()
    portfolios = await get_user_portfolios()
    
    needs_save = False
    for name, initial_price in STOCKS.items():
        # 确保股票数据结构完整
        if name not in stock_data:
            stock_data[name] = {
                "initial_price": initial_price,
                "history": [],
                "events": []  # 新增事件记录
            }
            needs_save = True
        else:
            # 确保所有必要字段都存在
            if "initial_price" not in stock_data[name]:
                stock_data[name]["initial_price"] = initial_price
                needs_save = True
            if "history" not in stock_data[name]:
                stock_data[name]["history"] = []
                needs_save = True
            if "events" not in stock_data[name]:  # 确保有events字段
                stock_data[name]["events"] = []
                needs_save = True
                
    if needs_save:
        await save_stock_data(stock_data)
        print("Stock data initialized/updated.")
    await save_user_portfolios(portfolios)
    print("Stock market initialization complete.")


def generate_stock_chart(stock_name, history, stock_data=None):
    """使用 Plotly 生成股票历史价格图表的 PNG 图片"""
    if not history:
        return None

    timestamps, prices = zip(*history)
    dates = [datetime.fromtimestamp(ts) for ts in timestamps]

    # 计算时间范围（过去24小时，并延长3小时）
    now = datetime.now()
    start_time = now - timedelta(hours=HISTORY_DURATION_HOURS)
    end_time = now + timedelta(hours=3)  # 延长3小时
    
    # 创建 Plotly Figure
    fig = go.Figure()

    # 添加价格折线图
    fig.add_trace(go.Scatter(
        x=dates,
        y=prices,
        mode='lines+markers',
        marker=dict(size=4),
        line=dict(shape='linear'),
        name='价格'
    ))

    # 如果有事件，在图表上标记
    if stock_data and stock_name in stock_data and "events" in stock_data[stock_name]:
        for event in stock_data[stock_name]["events"]:
            event_time = datetime.fromtimestamp(event["time"])
            # 只显示过去24小时内的事件
            if event_time >= start_time:
                fig.add_vline(
                    x=event_time,
                    line_width=1,
                    line_dash="dash",
                    line_color="orange",
                    opacity=0.7
                )
                # 添加事件注释
                fig.add_annotation(
                    x=event_time,
                    y=event["old_price"],
                    text=event["type"],
                    showarrow=True,
                    arrowhead=1,
                    ax=0,
                    ay=-40
                )

    current_price = history[-1][1]
    initial_price = STOCKS.get(stock_name, 0)

    # 更新图表布局
    fig.update_layout(
        title=f'{stock_name} 过去{HISTORY_DURATION_HOURS}小时价格走势 (初始: {initial_price:.2f})',
        xaxis_title='时间',
        yaxis_title='价格 (金币)',
        xaxis=dict(
            tickformat='%H:%M',
            range=[start_time, end_time]  # 设置X轴范围为过去24小时+3小时
        ),
        hovermode='x unified',
        template='plotly_white',
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    # 调整当前价格标注的位置
    fig.add_annotation(
        x=dates[-1],
        y=current_price,
        xref="x",
        yref="y",
        text=f'当前: {current_price:.2f}',
        showarrow=True,
        arrowhead=1,
        ax=30,  # 减小箭头长度
        ay=-30,
        xanchor='left'  # 确保文本向左对齐
    )

    try:
        img_bytes = pio.to_image(fig, format='png', scale=2)
        buf = io.BytesIO(img_bytes)
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Error generating Plotly chart image for {stock_name}: {e}")
        return None


# --- 命令处理函数 ---

@sv.on_rex(r'^(.+股)走势$')
async def handle_stock_quote(bot, ev):
    match = ev['match']
    stock_name = match[1].strip()

    if stock_name not in STOCKS:
        await bot.send(ev, f'未知股票: {stock_name}。可用的股票有: {", ".join(STOCKS.keys())}')
        return

    stock_data = await get_stock_data()
    history = await get_stock_price_history(stock_name, stock_data)
    
    if not history:
        initial_price = stock_data[stock_name]["initial_price"]
        await bot.send(ev, f'{stock_name} 暂时还没有价格历史记录。初始价格为 {initial_price:.2f} 金币。')
        return

    chart_buf = generate_stock_chart(stock_name, history, stock_data)
    
    if chart_buf:
        image_bytes = chart_buf.getvalue()
        b64_str = base64.b64encode(image_bytes).decode()
        cq_code = f"[CQ:image,file=base64://{b64_str}]"
        await bot.send(ev, cq_code)
        chart_buf.close()

@sv.on_rex(r'^买入\s*(.+股)\s*(\d+)$')
async def handle_buy_stock(bot, ev):
    user_id = ev.user_id
    match = ev['match']
    stock_name = match[1].strip()
    
    try:
        amount_to_buy = int(match[2])
        if amount_to_buy <= 0:
            await bot.send(ev, '购买数量必须是正整数。')
            return
    except ValueError:
        await bot.send(ev, '购买数量无效。')
        return

    if stock_name not in STOCKS:
        await bot.send(ev, f'未知股票: {stock_name}。')
        return

    # 检查用户当前对该股票的持有量
    user_portfolio = await get_user_portfolio(user_id)
    current_holding = user_portfolio.get(stock_name, 0)
    
    # 检查用户当前持有的股票种类数量
    holding_types = len(user_portfolio)
    if holding_types >= 3 and stock_name not in user_portfolio:
        await bot.send(ev, f'\n为了避免垄断性投资，每位用户最多只能持有3种不同的股票。您当前已持有{holding_types}种股票，无法购买新的股票种类。' + no, at_sender=True)
        return
    
    if current_holding >= 2000:
        await bot.send(ev, f'\n为了维护市场稳定，每种股票持有上限为2000股，无法购买更多股票。请先卖出部分股票。' + no, at_sender=True)
        return

    # 检查购买后是否会超过该股票的限制
    if current_holding + amount_to_buy > 2000:
        available = 2000 - current_holding
        await bot.send(ev, f'\n您当前持有 {current_holding} 股{stock_name}，最多只能再购买 {available} 股。'+ no, at_sender=True)
        return

    current_price = await get_current_stock_price(stock_name)
    if current_price is None:
        await bot.send(ev, f'{stock_name} 当前无法交易，请稍后再试。')
        return

    # 计算总成本并添加1%手续费（向上取整）
    base_cost = current_price * amount_to_buy
    fee = math.ceil(base_cost * 0.01)  # 1%手续费
    total_cost = math.ceil(base_cost) + fee  # 股票成本向上取整 + 手续费

    # 检查用户金币
    user_gold = money.get_user_money(user_id, 'gold')
    if user_gold is None:
         await bot.send(ev, '无法获取您的金币信息。')
         return
         
    if user_gold < total_cost:
        await bot.send(ev, f'金币不足！购买 {amount_to_buy} 股 {stock_name} 需要 {total_cost} 金币（含{fee}金币手续费），您只有 {user_gold} 金币。当前单价: {current_price:.2f}')
        return

    # 执行购买
    if money.reduce_user_money(user_id, 'gold', total_cost):
        if await update_user_portfolio(user_id, stock_name, amount_to_buy):
             await bot.send(ev, f'购买成功！您以 {current_price:.2f} 金币/股的价格买入了 {amount_to_buy} 股 {stock_name}，共花费 {total_cost} 金币（含{fee}金币手续费）。', at_sender=True)
        else:
             # 如果更新持仓失败，需要回滚金币（重要！）
             money.increase_user_money(user_id, 'gold', total_cost)
             await bot.send(ev, '购买失败，更新持仓时发生错误。您的金币已退回。')
    else:
        await bot.send(ev, '购买失败，扣除金币时发生错误。')


@sv.on_rex(r'^卖出\s*(.+股)\s*(\d+)$')
async def handle_sell_stock(bot, ev):
    user_id = ev.user_id
    match = ev['match']
    stock_name = match[1].strip()
    
    try:
        amount_to_sell = int(match[2])
        if amount_to_sell <= 0:
            await bot.send(ev, '出售数量必须是正整数。')
            return
    except ValueError:
         await bot.send(ev, '出售数量无效。')
         return

    if stock_name not in STOCKS:
        await bot.send(ev, f'未知股票: {stock_name}。')
        return

    user_portfolio = await get_user_portfolio(user_id)
    current_holding = user_portfolio.get(stock_name, 0)

    if current_holding < amount_to_sell:
        await bot.send(ev, f'您没有足够的 {stock_name} 来出售。您当前持有 {current_holding} 股，尝试出售 {amount_to_sell} 股。', at_sender=True)
        return

    current_price = await get_current_stock_price(stock_name)
    if current_price is None:
        await bot.send(ev, f'{stock_name} 当前无法交易，请稍后再试。')
        return

    # 计算总收入并扣除3%手续费（手续费向下取整）
    base_earnings = current_price * amount_to_sell
    fee = math.floor(base_earnings * 0.03)  # 3%手续费
    total_earnings = math.floor(base_earnings) - fee  # 股票收入向下取整 - 手续费

    # 执行出售
    if await update_user_portfolio(user_id, stock_name, -amount_to_sell): # 传入负数表示减少
        money.increase_user_money(user_id, 'gold', total_earnings)
        await bot.send(ev, f'出售成功！您以 {current_price:.2f} 金币/股的价格卖出了 {amount_to_sell} 股 {stock_name}，共获得 {total_earnings} 金币（扣除{fee}金币手续费）。', at_sender=True)
    else:
        await bot.send(ev, '出售失败，更新持仓时发生错误。')

# 使用 on_prefix 更灵活，可以接受 "我的股仓" 或 "查看股仓" 等
@sv.on_prefix(('我的股仓', '查看股仓'))
async def handle_my_portfolio(bot, ev):
    user_id = ev.user_id
    user_portfolio = await get_user_portfolio(user_id)

    if not user_portfolio:
        await bot.send(ev, '您的股仓是空的，快去买点股票吧！', at_sender=True)
        return

    stock_data = await get_stock_data() # 批量获取一次数据，减少重复加载
    
    report_lines = [f"{ev.sender['nickname']} 的股仓详情:"]
    total_value = 0.0
    stock_details_for_charting = [] # 存储需要画图的股票信息

    for stock_name, amount in user_portfolio.items():
        current_price = await get_current_stock_price(stock_name, stock_data)
        if current_price is None:
            current_price = stock_data.get(stock_name, {}).get("initial_price", 0) # Fallback to initial or 0
            value_str = "???"
        else:
            value = current_price * amount
            value_str = f"{value:.2f}"
            total_value += value
        
        report_lines.append(f"- {stock_name}: {amount} 股, 当前单价: {current_price:.2f}, 总价值: {value_str} 金币")
        
        # 记录下来以便后续生成图表
        stock_details_for_charting.append(stock_name)


    report_lines.append(f"--- 股仓总价值: {total_value:.2f} 金币 ---")
    
    # 先发送文本总结
    await bot.send(ev, "\n".join(report_lines), at_sender=True)
    '''
    sent_charts = 0
    for stock_name in stock_details_for_charting:
        history = await get_stock_price_history(stock_name, stock_data)
        if history:
            chart_buf = generate_stock_chart(stock_name, history)
            if chart_buf:
                # --- 修改开始 ---
                image_bytes = chart_buf.getvalue()
                b64_str = base64.b64encode(image_bytes).decode()
                cq_code = f"[CQ:image,file=base64://{b64_str}]"
                await bot.send(ev, cq_code)
                # --- 修改结束 ---
                sent_charts += 1
            await asyncio.sleep(0.5) # 短暂延迟防止刷屏
    '''

# --- 新增命令：股票列表 ---
@sv.on_prefix(('股票列表')) # 可以使用 "股票列表" 或 "股市行情" 触发
async def handle_stock_list(bot, ev):
    stock_data = await get_stock_data() # 加载所有股票数据

    if not stock_data:
        await bot.send(ev, "暂时无法获取股市数据，请稍后再试。")
        return

    report_lines = ["📈 当前股市行情概览:"]
    # 按股票名称排序，使列表顺序固定
    sorted_stock_names = sorted(stock_data.keys())

    all_prices_found = True
    for stock_name in sorted_stock_names:
        # 从已加载的数据中获取当前价格
        current_price = await get_current_stock_price(stock_name, stock_data)
        initial_price = stock_data[stock_name]["initial_price"]

        if current_price is not None:
            # 获取价格历史
            history = stock_data[stock_name].get("history", [])
            
            # 计算涨跌幅
            if len(history) > 1:
                # 有足够历史数据，计算与前一个价格的涨跌幅
                prev_price = history[-2][1]  # 倒数第二个价格
                change_percent = (current_price - prev_price) / prev_price * 100
            else:
                # 没有足够历史数据，与初始价比较
                change_percent = (current_price - initial_price) / initial_price * 100
            
            # 确定涨跌符号和颜色
            if change_percent >= 0:
                change_symbol = "↑"
                color_code = "FF0000"  # 红色表示上涨
            else:
                change_symbol = "↓"
                color_code = "00FF00"  # 绿色表示下跌
            
            # 格式化输出，保留两位小数，添加涨跌幅
            report_lines.append(
                f"◽ {stock_name}: {current_price:.2f} 金币 [{change_symbol}{abs(change_percent):.1f}%]"
            )
        else:
            # 如果由于某种原因无法获取价格（例如数据文件问题或新添加的股票尚未更新）
            report_lines.append(f"◽ {stock_name}: 价格未知 (初始: {initial_price})")
            all_prices_found = False # 标记一下有价格未找到

    if len(report_lines) == 1: # 如果只有标题行，说明没有股票数据
        await bot.send(ev, "当前市场没有可交易的股票。")
        return

    # 如果所有价格都正常获取，可以添加一个更新时间戳
    if all_prices_found:
        # 尝试获取最新价格的时间戳 (选择第一个股票的最后一个历史点作为代表)
        try:
            first_stock_data = stock_data[sorted_stock_names[0]]
            if first_stock_data.get("history"):
                last_update_ts = first_stock_data["history"][-1][0]
                last_update_time = datetime.fromtimestamp(last_update_ts).strftime('%Y-%m-%d %H:%M:%S')
                report_lines.append(f"\n(数据更新于: {last_update_time})")
            else:
                report_lines.append("\n(部分股票价格为初始价)")
        except (IndexError, KeyError):
             report_lines.append("\n(无法获取准确更新时间)")

    # 发送整合后的列表
    await bot.send(ev, "\n".join(report_lines))

@sv.on_prefix(('市场动态', '股市新闻', '市场事件'))
async def handle_market_events(bot, ev):
    """查看最近的市场事件"""
    stock_data = await get_stock_data()
    current_time = time.time()
    
    # 收集所有事件并按时间排序
    all_events = []
    for stock_name, data in stock_data.items():
        for event in data.get("events", []):
            event["stock"] = stock_name
            all_events.append(event)
    
    # 按时间降序排序
    all_events.sort(key=lambda x: x["time"], reverse=True)
    
    if not all_events:
        await bot.send(ev, "近期没有重大市场事件发生。")
        return
    
    # 只显示最近5个事件
    recent_events = all_events[:5]
    
    event_lines = ["📢 最新市场动态:"]
    for event in recent_events:
        event_time = datetime.fromtimestamp(event["time"]).strftime('%m-%d %H:%M')
        
        # 处理全局事件
        if event.get("scope") == "global":
            event_lines.append(
                f"【{event_time}】{event['message']}\n"
                f"  影响范围: 所有股票"
            )
        # 处理单股事件
        else:
            change_percent = (event["new_price"] - event["old_price"]) / event["old_price"] * 100
            change_direction = "↑" if change_percent >= 0 else "↓"
            
            event_lines.append(
                f"【{event_time}】{event['message']}\n"
                f"  {event['stock']}价格: {event['old_price']:.2f} → {event['new_price']:.2f} "
                f"({change_direction}{abs(change_percent):.1f}%)"
            )
    
    await bot.send(ev, "\n\n".join(event_lines))
    

    
@sv.on_fullmatch('更新股价') # 使用完全匹配，指令必须是 "更新股价"
async def handle_manual_price_update(bot, ev):
    # 1. 权限验证
    if ev.user_id not in SUPERUSERS:
        await bot.send(ev, '权限不足，只有管理员才能手动更新股价。')
        return

    # 发送一个处理中的提示，因为更新可能需要一点时间
    await bot.send(ev, "收到指令，正在手动触发股价更新...", at_sender=True)

    try:
        # 2. 调用核心的股价更新函数
        # 这个函数包含了加载数据、计算新价格、清理旧数据、保存数据的完整逻辑
        await hourly_price_update_job()

        # 3. 发送成功反馈
        # 获取当前时间用于反馈
        now_time_str = datetime.now().strftime('%H:%M:%S')
        await bot.send(ev, f"✅ 股价已于 {now_time_str} 手动更新完成！\n您可以使用 '股票列表' 或具体股票的 '走势' （例如：猫娘股趋势）指令查看最新价格。", at_sender=True)

    except Exception as e:
        # 4. 如果更新过程中出现任何未预料的错误，则捕获并报告
        # 在实际应用中，这里应该有更详细的日志记录
        error_message = f"手动更新股价时遇到错误：{type(e).__name__} - {e}"
        print(f"[ERROR] Manual stock update failed: {error_message}") # 打印到控制台/日志
        # 向管理员发送错误通知
        await bot.send(ev, f"❌ 手动更新股价失败。\n错误详情: {error_message}\n请检查后台日志获取更多信息。", at_sender=True)
        
async def trigger_manual_event(bot, ev, event_type=None, target_stock=None):
    """管理员手动触发市场事件"""
    stock_data = await get_stock_data()
    current_time = time.time()
    
    if event_type not in MARKET_EVENTS:
        await bot.send(ev, f"无效事件类型！可选：{', '.join(MANUAL_EVENT_TYPES.keys())}")
        return False

    event_info = MARKET_EVENTS[event_type]
    
    # 确定影响范围
    if event_info["scope"] == "single":
        if not target_stock:
            target_stock = random.choice(list(STOCKS.keys()))
        affected_stocks = [target_stock]
    else:
        affected_stocks = list(STOCKS.keys())

    # 应用事件影响
    results = []
    for stock_name in affected_stocks:
        if stock_name not in stock_data:
            continue
            
        # 获取当前价格
        if stock_data[stock_name]["history"]:
            current_price = stock_data[stock_name]["history"][-1][1]
        else:
            current_price = stock_data[stock_name]["initial_price"]
        
        # 应用事件影响
        new_price = event_info["effect"](current_price)
        new_price = max(stock_data[stock_name]["initial_price"] * 0.01, 
                       min(new_price, stock_data[stock_name]["initial_price"] * 2.00))
        new_price = round(new_price, 2)
        
        # 记录事件
        template = random.choice(event_info["templates"])
        event_message = template.format(stock=stock_name)
        
        stock_data[stock_name]["events"].append({
            "time": current_time,
            "type": f"手动{event_type}",
            "message": f"[管理员操作] {event_message}",
            "old_price": current_price,
            "new_price": new_price
        })
        
        # 更新价格
        stock_data[stock_name]["history"].append((current_time, new_price))
        
        # 清理旧事件
        stock_data[stock_name]["events"] = stock_data[stock_name]["events"][-10:]
        
        results.append(
            f"{stock_name}: {current_price:.2f} → {new_price:.2f} "
            f"({'+' if new_price >= current_price else ''}{((new_price-current_price)/current_price*100):.1f}%)"
        )

    await save_stock_data(stock_data)
    
    # 发送执行结果
    report = [
        f"🎯 管理员手动触发 [{event_type}] 事件",
        f"📌 影响范围: {len(affected_stocks)} 只股票" if event_info["scope"] == "all" else f"📌 目标股票: {target_stock}",
        "📊 价格变化:",
        *results
    ]
    await bot.send(ev, "\n".join(report))
    return True
    
@sv.on_prefix('更新事件')
async def handle_manual_event(bot, ev):
    """管理员手动触发市场事件"""
    if ev.user_id not in SUPERUSERS:
        await bot.send(ev, "⚠️ 仅管理员可执行此操作")
        return
    
    # 提取纯文本并分割参数
    args = ev.message.extract_plain_text().strip().split()
    if not args:
        event_list = '\n'.join([f"{k} - {v}" for k, v in MANUAL_EVENT_TYPES.items()])
        await bot.send(ev, f"请指定事件类型：\n{event_list}")
        return
    
    event_type = args[0]
    target_stock = args[1] if len(args) > 1 else None
    
    # 验证事件类型
    if event_type not in MARKET_EVENTS:
        await bot.send(ev, f"❌ 无效事件类型！请输入以下之一：\n{', '.join(MARKET_EVENTS.keys())}")
        return
    
    # 验证股票名称（如果是单股事件）
    if target_stock and target_stock not in STOCKS:
        await bot.send(ev, f"❌ 无效股票名称！可选：{', '.join(STOCKS.keys())}")
        return
    
    # 执行事件触发
    try:
        success = await trigger_manual_event(bot, ev, event_type, target_stock)
        if not success:
            await bot.send(ev, "❌ 事件触发失败，请检查日志")
    except Exception as e:
        await bot.send(ev, f"⚠️ 发生错误：{str(e)}")

@sv.on_fullmatch('修复股票数据')
async def fix_stock_data(bot, ev):
    if ev.user_id != ADMIN_UID:
        return
    
    try:
        await initialize_stock_market()
        await bot.send(ev, "✅ 股票数据已修复")
    except Exception as e:
        await bot.send(ev, f"❌ 修复失败: {str(e)}")

help_chaogu = '''
炒股游戏帮助：

温馨提醒：股市有风险，切莫上头。

**指令列表：**
1.  股票列表：查看所有股票的名字和实时价格
2.  买入 [股票名称] [具体数量]：例如：买入 萝莉股 10
3.  卖出 [股票名称] [具体数量]：例如：卖出 萝莉股 10
4.  我的股仓：查看自己现在持有的股票
5.  [股票名称]走势：查看某一股票的价格折线图走势（会炸内存，慎用），例如：萝莉股走势
6.  市场动态/股市新闻/市场事件：查看最近市场上的事件，可能利好或利空
初始股票价格：
    "萝莉股": 100.0,
    "猫娘股": 120.0,
    "魔法少女股": 140.0,
    "梦月股": 500.0,
    "梦馨股": 200.0,
    "高达股": 90.0,
    "雾月股": 240.0,
    "傲娇股": 130.0,
    "病娇股": 70.0,
    "梦灵股": 250.0,
    "铃音股": 230.0,
    "音祈股": 1000.0,
    "梦铃股": 500.0,
'''
@sv.on_fullmatch('炒股帮助')
async def chaogu_help(bot, ev):
    """
        拉取游戏帮助
    """
    chain = []
    await chain_reply(bot, ev, chain, help_chaogu)
    await bot.send_group_forward_msg(group_id=ev.group_id, messages=chain)

    ################################################################################

MAX_GAMBLE_ROUNDS = 5

# 赌博状态管理 (内存中)
# key: user_id, value: {'round': int, 'confirmed': bool, 'active': bool}
gambling_sessions = {}

# 每日限制文件锁
gamble_limit_lock = asyncio.Lock()

async def load_gamble_limits():
    """加载每日赌博限制数据"""
    return await load_json_data(GAMBLE_LIMITS_FILE, {}, gamble_limit_lock)

async def save_gamble_limits(data):
    """保存每日赌博限制数据"""
    await save_json_data(GAMBLE_LIMITS_FILE, data, gamble_limit_lock)

async def check_daily_gamble_limit(user_id):
    """检查用户今天是否已经赌过"""
    user_id_str = str(user_id)
    limits = await load_gamble_limits()
    today_str = date.today().isoformat()
    last_gamble_date = limits.get(user_id_str)
    if last_gamble_date == today_str:
        return False # 今天已经赌过了
    return True # 今天还没赌

async def record_gamble_today(user_id):
    """记录用户今天进行了赌博"""
    user_id_str = str(user_id)
    limits = await load_gamble_limits()
    today_str = date.today().isoformat()
    limits[user_id_str] = today_str
    await save_gamble_limits(limits)

def get_gamble_win_probability(gold):
    """豪赌概率分层 (返回 0 到 1 之间的值)"""
    if gold < 10000:
        return 0.90
    elif gold < 50000:
        return 0.70
    elif gold < 100000:
        return 0.60
    elif gold < 1000000:
        return 0.50
    elif gold < 10000000:
        return 0.30
    else: # 超过一千万
        return 0.10 

async def perform_gamble_round(user_id):
    """执行一轮赌博并更新金币"""
    current_gold = money.get_user_money(user_id, 'gold')
    if current_gold is None or current_gold <= 0:
        return {"success": False, "message": "你没有金币可以用来赌博。"}

    win_prob = get_gamble_win_probability(current_gold)
    win = random.random() < win_prob

    if win:
        new_gold = round(current_gold * 2, 2)
        change = new_gold - current_gold
        money.increase_user_money(user_id, 'gold', change)
        outcome = "胜利"
        multiplier = 2
    else:
        new_gold = round(current_gold * 0.01, 2)
        # 确保金币不会变成负数，虽然 *0.01 不太可能，但以防万一
        if new_gold < 0: new_gold = 0
        change = int(current_gold - new_gold) # 计算减少了多少
        money.reduce_user_money(user_id, 'gold', change)
        outcome = "失败"
        multiplier = 0.01

    return {
        "success": True,
        "outcome": outcome,
        "old_gold": current_gold,
        "new_gold": new_gold,
        "multiplier": multiplier
    }

@sv.on_fullmatch('一场豪赌')
async def handle_start_gamble(bot, ev: CQEvent):
    user_id = ev.user_id

    # 检查是否已在赌局中
    if user_id in gambling_sessions and gambling_sessions[user_id].get('active', False):
        await bot.send(ev, "你正在进行一场豪赌，请先完成或使用 '见好就收' 结束当前赌局。", at_sender=True)
        return

    # 检查每日限制
    if not await check_daily_gamble_limit(user_id):
        await bot.send(ev, "你今天已经赌过了，明天再来吧！人生的大起大落可经不起天天折腾哦。", at_sender=True)
        return

    # 显示规则并请求确认
    rules = f"""🎲 一场豪赌 规则 🎲
你即将开始一场可能改变命运的赌博！
规则如下：
1. 你将进行最多 {MAX_GAMBLE_ROUNDS} 轮赌博。
2. 每一轮，你的现有金币都有几率翻倍，或者骤减。
3. 你可以在任何一轮结束后选择 '见好就收' 带着当前金币离场。
4. 一旦开始，直到完成 {MAX_GAMBLE_ROUNDS} 轮或选择收手，否则无法进行其他操作（包括买卖股票）。
5. 每日仅限一次机会，三思而后行！

"富贵险中求"，确认开始吗？请发送 '确认' 继续。
发送 '算了' 或其他任意内容取消。"""

    # 初始化会话状态
    gambling_sessions[user_id] = {'round': 0, 'confirmed': False, 'active': False} # active=False 表示等待确认
    await bot.send(ev, rules, at_sender=True)

@sv.on_fullmatch('确认')
async def handle_confirm_gamble(bot, ev: CQEvent):
    user_id = ev.user_id

    # 检查用户是否处于待确认状态
    if user_id not in gambling_sessions or gambling_sessions[user_id].get('confirmed', False):
        await bot.send(ev, "请先发送 '一场豪赌' 来开始新的赌局。", at_sender=True)
        return

    # 标记确认，激活会话，记录次数
    gambling_sessions[user_id]['confirmed'] = True
    gambling_sessions[user_id]['active'] = True
    gambling_sessions[user_id]['round'] = 1 # 开始第一轮
    await record_gamble_today(user_id) # 确认后才记录次数

    await bot.send(ev, f"很好，有胆识！第 1 轮赌博开始...", at_sender=True)
    await asyncio.sleep(1) # 增加一点戏剧性

    # 执行第一轮
    result = await perform_gamble_round(user_id)

    if not result["success"]:
        await bot.send(ev, f"赌博失败：{result['message']}", at_sender=True)
        del gambling_sessions[user_id] # 清理会话
        return

    # 发送第一轮结果
    message = f"""第 1 轮结果：【{result['outcome']}】
金币变化：{result['old_gold']:.2f} -> {result['new_gold']:.2f} (x{result['multiplier']})"""

    if result['new_gold'] <= 0:
        message += "\n你已经输光了所有金币...赌局结束。"
        del gambling_sessions[user_id]
    elif gambling_sessions[user_id]['round'] >= MAX_GAMBLE_ROUNDS:
        message += f"\n你已完成全部 {MAX_GAMBLE_ROUNDS} 轮赌博，赌局结束！"
        del gambling_sessions[user_id]
    else:
        message += f"\n发送 '继续' 进行第 {gambling_sessions[user_id]['round'] + 1} 轮，或发送 '见好就收' 离场。"

    await bot.send(ev, message, at_sender=True)


@sv.on_fullmatch('继续')
async def handle_continue_gamble(bot, ev: CQEvent):
    user_id = ev.user_id

    # 检查用户是否在活跃的赌局中且未完成
    if user_id not in gambling_sessions or not gambling_sessions[user_id].get('active', False):
        await bot.send(ev, "你当前没有正在进行的赌局。请先发送 '一场豪赌' 开始。", at_sender=True)
        return

    current_round = gambling_sessions[user_id]['round']
    if current_round >= MAX_GAMBLE_ROUNDS:
        await bot.send(ev, f"你已经完成了全部 {MAX_GAMBLE_ROUNDS} 轮赌博，不能再继续了。", at_sender=True)
        # 可以选择在这里也清理会话
        # if user_id in gambling_sessions: del gambling_sessions[user_id]
        return

    # 检查金币是否足够（虽然 perform_gamble_round 也会检查，这里可以提前告知）
    current_gold = money.get_user_money(user_id, 'gold')
    if current_gold is None or current_gold <= 0:
         await bot.send(ev, "你已经没有金币了，无法继续赌博。", at_sender=True)
         if user_id in gambling_sessions: del gambling_sessions[user_id] # 清理会话
         return

    # 进入下一轮
    next_round = current_round + 1
    gambling_sessions[user_id]['round'] = next_round

    await bot.send(ev, f"第 {next_round} 轮赌博开始...", at_sender=True)
    await asyncio.sleep(1)

    # 执行赌博
    result = await perform_gamble_round(user_id)

    if not result["success"]:
        await bot.send(ev, f"赌博失败：{result['message']}", at_sender=True)
        del gambling_sessions[user_id] # 清理会话
        return

    # 发送结果
    message = f"""第 {next_round} 轮结果：【{result['outcome']}】
金币变化：{result['old_gold']:.2f} -> {result['new_gold']:.2f} (x{result['multiplier']})"""

    if result['new_gold'] <= 0:
        message += "\n你已经输光了所有金币...赌局结束。"
        del gambling_sessions[user_id]
    elif gambling_sessions[user_id]['round'] >= MAX_GAMBLE_ROUNDS:
        message += f"\n你已完成全部 {MAX_GAMBLE_ROUNDS} 轮赌博，赌局结束！"
        del gambling_sessions[user_id]
    else:
        message += f"\n发送 '继续' 进行第 {gambling_sessions[user_id]['round'] + 1} 轮，或发送 '见好就收' 离场。"

    await bot.send(ev, message, at_sender=True)


@sv.on_fullmatch(('见好就收', '算了')) # '算了' 也可以用来取消或收手
async def handle_stop_gamble(bot, ev: CQEvent):
    user_id = ev.user_id

    if user_id not in gambling_sessions:
        # 如果用户输入'算了'但没有赌局，可以给个通用回复
        await bot.send(ev, "你当前没有正在进行的赌局。", at_sender=True)
        return

    # 清理会话状态
    current_round = gambling_sessions[user_id].get('round', 0)
    confirmed = gambling_sessions[user_id].get('confirmed', False)
    del gambling_sessions[user_id]

    if not confirmed: # 如果是在规则确认阶段输入'算了'
         await bot.send(ev, "好吧，谨慎总是好的。赌局已取消。", at_sender=True)
    elif current_round > 0: # 如果是赌了几轮后收手
        final_gold = money.get_user_money(user_id, 'gold')
        await bot.send(ev, f"明智的选择！你在第 {current_round} 轮后选择离场，当前金币为 {final_gold:.2f}。赌局结束。", at_sender=True)
    else: # 理论上不应该到这里，但也处理一下
         await bot.send(ev, "赌局已结束。", at_sender=True)