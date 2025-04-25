import json
import asyncio
from typing import Dict, Any
from .._R import get, userPath
import os

# ���ù�Ʊ����е��ļ�·������
PORTFOLIOS_FILE = os.path.join(userPath, 'chaogu/user_portfolios.json')  # ��Ҫ����Ϊʵ��·��
portfolio_file_lock = asyncio.Lock()

async def load_json_data(filename, default_data, lock):
    """�첽��ȫ�ؼ���JSON����"""
    async with lock:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default_data

async def get_user_portfolio(user_id: int) -> Dict[str, int]:
    """��ȡ�����û��ĳֲ�����"""
    portfolios = await load_json_data(
        PORTFOLIOS_FILE, 
        {}, 
        portfolio_file_lock
    )
    return portfolios.get(str(user_id), {})