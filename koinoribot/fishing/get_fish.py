import os
import random

import hoshino
from . import config
from ..utils import loadData, saveData
from .serif import no_fish_serif, get_fish_serif
from .. import money
from .._R import userPath


dbPath = os.path.join(userPath, 'fishing/db')
user_info_path = os.path.join(dbPath, 'user_info.json')
fish_list = ['🐟', '🦐', '🦀', '🐡', '🐠', '🔮', '✉', '🍙', '水之心']  # 常见，一般，稀有，罕见，传说，水之心，漂流瓶，鱼饵
fish_price = config.FISH_PRICE  # 价格换算
default_info = {
    'fish': {'🐟': 0, '🦐': 0, '🦀': 0, '🐡': 0, '🐠': 0, '🔮': 0, '✉': 0, '🍙': 0},
    'statis': {'free': 0, 'sell': 0, 'total_fish': 0, 'frags': 0},
    'rod': {'current': 0, 'total_rod': [0]}
}


def getUserInfo(uid):
    """
        获取用户背包，自带初始化
    """
    uid = str(uid)
    total_info = loadData(user_info_path)
    if uid not in total_info:
        user_info = default_info
        total_info[uid] = user_info
        saveData(total_info, user_info_path)
    else:
        user_info = total_info[uid]
    return user_info


def fishing(uid):
    """
        mode=0: 普通鱼竿，
        mode=1: 永不空军，不会钓不到东西
        mode=2: 海之眷顾，更大可能性钓到水之心或漂流瓶
        mode=3：时运，钓上的鱼可能双倍
    """
    user_info = getUserInfo(uid)
    mode = user_info['rod']['current']
    probability = config.PROBABILITY[0 if mode == 3 else mode]  # 第一概率元组
    probability_2 = config.PROBABILITY_2[0 if mode == 3 else mode]  # 第二概率元组

    first_choose = random.randint(1, 1000)  # 第一次掷骰子——选择一种情况

    first_choose = config.STATIC_FC if config.STATIC_FC and config.DEBUG_MODE else first_choose

    if config.DEBUG_MODE:
        hoshino.logger.info(f'{uid}使用钓竿：{mode}，随机数为{first_choose}')

    if first_choose <= probability[0]:
        result = {'code': 1, 'msg': random.choice(no_fish_serif)}
        return result
    elif first_choose <= probability[1]:
        result = {'code': 3, 'msg': '<随机事件case>'}
        return result
    elif first_choose <= probability[2]:
        second_choose = random.randint(1, 1000)  # 第二次掷骰子——钓上不同的鱼
        if second_choose <= probability_2[0]:
            fish = fish_list[0]
        elif second_choose <= probability_2[1]:
            fish = fish_list[1]
        elif second_choose <= probability_2[2]:
            fish = fish_list[2]
        elif second_choose <= probability_2[3]:
            fish = fish_list[3]
        else:
            fish = fish_list[4]
        multi = random.randint(1, 2) if mode == 3 else 1  # 时运竿特别效果
        add_msg = f'另外，鱼竿发动了时运效果，{fish}变成了{multi}条！' if multi > 1 else ''
        increase_value(uid, 'fish', fish, 1 * multi)
        increase_value(uid, 'statis', 'total_fish', 1 * multi)
        msg = f'钓到了一条{fish}~' if random.randint(1, 10) <= 5 else random.choice(get_fish_serif).format(fish)
        msg = msg + add_msg + '\n你将鱼放进了背包。'
        result = {'code': 1, 'msg': msg}
        return result
    elif first_choose <= probability[3]:
        second_choose = random.randint(1, 1000)  # 第二次掷骰子——钓上了金币还是幸运币
        if second_choose <= 800:
            coin_amount = random.randint(1, 30)
            money.increase_user_money(uid, 'gold', coin_amount)
            result = {'code': 1, 'msg': f'你钓到了一个布包，里面有{coin_amount}枚金币，但是没有钓到鱼...'}
            return result
        else:
            coin_amount = random.randint(1, 3)
            money.increase_user_money(uid, 'luckygold', coin_amount)
            result = {'code': 1, 'msg': f'你钓到了一个锦囊，里面有{coin_amount}枚幸运币，但是没有钓到鱼...'}
            return result
    else:
        result = {'code': 2, 'msg': '<漂流瓶case>'}
        return result


def sell_fish(uid, fish, num: int = 1):
    """
        卖鱼

    :param uid: 用户id
    :param fish: 鱼的emoji
    :param num: 出售的鱼数量
    :return: 获得的金币数量
    """
    getUserInfo(uid)
    total_info = loadData(user_info_path)
    uid = str(uid)
    if not total_info[uid]['fish'][fish]:
        return '数量不够喔'
    if num > total_info[uid]['fish'][fish]:
        num = total_info[uid]['fish'][fish]
    decrease_value(uid, 'fish', fish, num)
    get_golds = fish_price[fish] * num
    money.increase_user_money(uid, 'gold', get_golds)
    if fish == '🍙':
        return f'成功退还了{num}个🍙，兑换了{get_golds}枚金币~'
    increase_value(uid, 'statis', 'sell', get_golds)
    return f'成功出售了{num}条{fish}, 得到了{get_golds}枚金币~'


def free_fish(uid, fish, num: int = 1):
    """
        放生鱼

    :param uid: 用户id
    :param fish: 鱼的emoji
    :param num: 放生的鱼数量
    :return: 水之心碎片数量
    """
    getUserInfo(uid)
    total_info = loadData(user_info_path)
    uid = str(uid)
    if not total_info[uid]['fish'][fish]:
        return '数量不足喔'
    if num > total_info[uid]['fish'][fish]:
        num = total_info[uid]['fish'][fish]
    decrease_value(uid, 'fish', fish, num)
    get_frags = fish_price[fish] * num
    increase_value(uid, 'statis', 'frags', get_frags)
    increase_value(uid, 'statis', 'free', num)
    user_frags = getUserInfo(uid)['statis']['frags']
    if user_frags >= config.FRAG_TO_CRYSTAL:
        increase_value(uid, 'fish', '🔮', int(user_frags / config.FRAG_TO_CRYSTAL))
        set_value(uid, 'statis', 'frags', user_frags % config.FRAG_TO_CRYSTAL)
        addition = f'\n一条美人鱼浮出水面！为了表示感谢，TA将{int(user_frags / config.FRAG_TO_CRYSTAL)}颗水之心放入了你的手中~'
    else:
        addition = ''
    classifier = '条' if fish in ['🐟', '🐠'] else '只'
    return f'{num}{classifier}{fish}成功回到了水里，获得{get_frags}个水心碎片~{addition}'


def buy_bait(uid, num = 1):
    """
        买鱼饵
    """
    money.reduce_user_money(uid, 'gold', num * config.BAIT_PRICE)
    increase_value(uid, 'fish', '🍙', num)


def change_fishrod(uid, mode: int):
    """
        更换鱼竿
    """
    user_info = getUserInfo(uid)
    total_info = loadData(user_info_path)
    uid = str(uid)
    if mode not in user_info['rod']['total_rod']:
        return {'code': -1, 'msg': '还没有拿到这个鱼竿喔'}
    total_info[uid]['rod']['current'] = mode - 1
    saveData(total_info, user_info_path)
    return {'code': 1, 'msg': f'已更换为{mode}号鱼竿~'}


def compound_bottle(uid, num: int = 1):
    user_info = getUserInfo(uid)
    total_info = loadData(user_info_path)
    uid = str(uid)
    if user_info['fish']['🔮'] < config.CRYSTAL_TO_BOTTLE:
        return {'code': -1, 'msg': '要三个🔮才可以合成一个漂流瓶体喔'}
    if (num * 3) > user_info['fish']['🔮']:
        num = int(user_info['fish']['🔮'] / 3)
    decrease_value(uid, 'fish', '🔮', num * 3)
    increase_value(uid, 'fish', '✉', num)
    return {'code': 1, 'msg': f'{num * 3}个🔮发出柔和的光芒，融合成了{num}个漂流瓶体！\n可以使用"#扔漂流瓶+内容"来投放漂流瓶了！'}


def decrease_value(uid, mainclass, subclass, num):
    """
        减少某物品的数量
    """
    uid = str(uid)
    getUserInfo(uid)
    total_info = loadData(user_info_path)
    total_info[uid][mainclass][subclass] -= num
    if total_info[uid][mainclass][subclass] < 0:
        total_info[uid][mainclass][subclass] = 0
    saveData(total_info, user_info_path)


def increase_value(uid, mainclass, subclass, num):
    """
        增加某物品的数量
    """
    uid = str(uid)
    getUserInfo(uid)
    total_info = loadData(user_info_path)
    total_info[uid][mainclass][subclass] += num
    saveData(total_info, user_info_path)


def set_value(uid, mainclass, subclass, num):
    """
        直接设置物品数量
    """
    uid = str(uid)
    getUserInfo(uid)
    total_info = loadData(user_info_path)
    total_info[uid][mainclass][subclass] = num
    saveData(total_info, user_info_path)


if __name__ == '__main__':
    pass