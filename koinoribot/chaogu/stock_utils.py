import json
import asyncio
from typing import Dict, Any
from .._R import get, userPath
import os

# 复用股票插件中的文件路径和锁
PORTFOLIOS_FILE = os.path.join(userPath, 'chaogu/user_portfolios.json')  # 需要调整为实际路径
portfolio_file_lock = asyncio.Lock()

async def load_json_data(filename, default_data, lock):
    """异步安全地加载JSON数据"""
    async with lock:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default_data

async def get_user_portfolio(user_id: int) -> Dict[str, int]:
    """获取单个用户的持仓数据"""
    portfolios = await load_json_data(
        PORTFOLIOS_FILE, 
        {}, 
        portfolio_file_lock
    )
    return portfolios.get(str(user_id), {})