import math

# 扭蛋配置
GACHA_COST = 10  # 每个扭蛋消耗10宝石
GACHA_REWARDS = {
    "普通": {
        "小猫咪": 50,
        "小狗": 50,
    },
    "稀有": {
        "魔法兔": 50,
        "小狐狸": 50
    },
    "史诗": {
        "精灵宝宝": 50,
        "熊猫宝宝": 50
    },
    "传说": {
        "蠢萝莉": 100,
    }
}
GACHA_CONSOLE_PRIZE = 50  # 安慰奖金币数量



#每一阶段所需成长度
growth1 = 250
growth2 = 500
growth3 = math.inf


# 基础宠物类型（幼年体）
BASE_PETS = {
    "小猫咪": {
        "max_hunger": 100,
        "max_energy": 100,
        "max_happiness": 100,
        "growth_rate": 1.2,
        "rarity": "普通",
        "stage": 0,  # 0=幼年体, 1=成长体, 2=成年体
        "growth_required": 100  # 进化到下一阶段需要的成长值
    },
    "小狗": {
        "max_hunger": 100,
        "max_energy": 90,
        "max_happiness": 110,
        "growth_rate": 1.2,
        "rarity": "普通",
        "stage": 0,
        "growth_required": 100
    },
    "魔法兔": {
        "max_hunger": 80,
        "max_energy": 120,
        "max_happiness": 150,
        "growth_rate": 1.3,
        "rarity": "稀有",
        "stage": 0,
        "growth_required": 100
    },
    "蠢萝莉": {
        "max_hunger": 200,
        "max_energy": 200,
        "max_happiness": 200,
        "growth_rate": 1.5,
        "rarity": "传说",
        "stage": 0,
        "growth_required": 100
    },
    "小狐狸": {
        "max_hunger": 80,
        "max_energy": 140,
        "max_happiness": 130,
        "growth_rate": 1.3,
        "rarity": "稀有",
        "stage": 0,
        "growth_required": 100
    },
    "精灵宝宝": {
        "max_hunger": 100,
        "max_energy": 200,
        "max_happiness": 200,
        "growth_rate": 1.4,
        "rarity": "史诗",
        "stage": 0,
        "growth_required": 100
    },
    "熊猫宝宝": {
        "max_hunger": 200,
        "max_energy": 100,
        "max_happiness": 200,
        "growth_rate": 1.4,
        "rarity": "史诗",
        "stage": 0,
        "growth_required": 100
    }
}

# 宠物进化路线
EVOLUTIONS = {
    # 幼年体 -> 成长体 (3个分支)
    "小猫咪": {
        "成长体1": "灵猫",
        "成长体2": "玄猫",
        "成长体3": "小馋猫"
    },
    "小狗": {
        "成长体1": "金毛",
        "成长体2": "哈士奇",
        "成长体3": "柴犬"
    },
    "魔法兔": {
        "成长体1": "月兔",
        "成长体2": "玉兔",
        "成长体3": "魔兔"
    },
    "蠢萝莉": {
        "成长体1": "不那么蠢的萝莉",
        "成长体2": "嘴馋萝莉",
        "成长体3": "傲娇萝莉"
    },
    "小狐狸": {
        "成长体1": "藏狐",
        "成长体2": "赤狐",
        "成长体3": "月光灵狐"
    },
    "精灵宝宝": {
        "成长体1": "花精灵",
        "成长体2": "树精力",
        "成长体3": "元素精灵"
    },
    "熊猫宝宝": {
        "成长体1": "暗夜修女",
        "成长体2": "纯白修女",
        "成长体3": "黑白圣女"
    },
    # 成长体 -> 成年体 (固定路线)
    "灵猫": "猫耳女仆",
    "玄猫": "猫耳公主",
    "小馋猫": "猫耳萝莉",
    "金毛": "金发犬娘",
    "哈士奇": "极地雪狼",
    "柴犬": "神社守护",
    "月兔": "月宫仙子",
    "玉兔": "捣药仙兔",
    "魔兔": "魔法少女",
    "不那么蠢的萝莉": "灵歌少女",
    "嘴馋萝莉": "小萝莉",
    "傲娇萝莉": "大小姐",
    "藏狐": "高原守护",
    "赤狐": "火焰灵狐",
    "月光灵狐": "狐耳巫女",
    "花精灵": "百花少女",
    "树精灵": "森林公主",
    "元素精灵": "元素神女",
    "暗夜修女": "黑天使",
    "纯白修女": "白天使",
    "黑白少女": "黑白神女"
}

# 宠物商店物品
PET_SHOP_ITEMS = {
    "普通料理": {
        "price": 5,
        "hunger": 20,
        "energy": 5,
        "happiness": 1,
        "growth": 0,
        "effect": "恢复宠物饱食度"
    },
    "高级料理": {
        "price": 25,
        "hunger": 50,
        "energy": 15,
        "happiness": 15,
        "growth": 2,
        "effect": "营养丰富，大幅恢复宠物状态,少量提升成长值"
    },
    "玩具球": {
        "price": 10,
        "hunger": -5,
        "energy": -10,
        "happiness": 30,
        "growth": 0,
        "effect": "增加宠物好感度"
    },
    "能量饮料": {
        "price": 15,
        "hunger": 0,
        "energy": 50,
        "happiness": 5,
        "growth": 0,
        "effect": "快速恢复宠物精力"
    },
    "宠物扭蛋": {
        "price": 10,
        "effect": "随机获得一只宠物",
        "type": "gacha"
    },
    "奶油蛋糕": {
        "price": 200,
        "hunger": 0,
        "energy": 0,
        "happiness": 0,
        "growth": 0,
        "effect": "用于进化至成长体",
        "special": "evolve_1"
    },
    "豪华蛋糕": {
        "price": 500,
        "hunger": 0,
        "energy": 0,
        "happiness": 0,
        "growth": 0,
        "effect": "用于进化至成年体",
        "special": "evolve_2"
    },
    "时之泪": {
        "price": 100,
        "hunger": 0,
        "energy": 0,
        "happiness": 0,
        "growth": 0,
        "effect": "让成长体宠物重新随机选择进化分支",
        "special": "reroll_evolution"
    },
    "最初的契约": {
        "price": 75,
        "hunger": 0,
        "energy": 0,
        "happiness": 0,
        "growth": 0,
        "effect": "寻回离家出走的宠物",
        "special": "retrieve_pet"
    }
}

# 宠物状态描述
STATUS_DESCRIPTIONS = {
    "hunger": {
        50: "吃得饱饱的",
        40: "有点饿了",
        30: "非常饥饿",
        0: "饿得不行了"
    },
    "energy": {
        80: "精力充沛",
        50: "有点累了",
        30: "非常疲惫",
        0: "精疲力尽"
    },
    "happiness": {
        80: "非常开心",
        50: "心情一般",
        30: "不太高兴",
        0: "非常沮丧"
    }
}
