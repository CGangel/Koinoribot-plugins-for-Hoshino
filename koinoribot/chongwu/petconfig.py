import math

# Ť������
GACHA_COST = 10  # ÿ��Ť������10��ʯ
GACHA_REWARDS = {
    "��ͨ": {
        "Сè��": 50,
        "С��": 50,
    },
    "ϡ��": {
        "ħ����": 50,
        "С����": 50
    },
    "ʷʫ": {
        "������": 10,
        "��è����": 90
    }
}
GACHA_CONSOLE_PRIZE = 50  # ��ο���������



#ÿһ�׶�����ɳ���
growth1 = 250
growth2 = 500
growth3 = math.inf


# �����������ͣ������壩
BASE_PETS = {
    "Сè��": {
        "max_hunger": 100,
        "max_energy": 100,
        "max_happiness": 100,
        "growth_rate": 1.2,
        "rarity": "��ͨ",
        "stage": 0,  # 0=������, 1=�ɳ���, 2=������
        "growth_required": 100  # ��������һ�׶���Ҫ�ĳɳ�ֵ
    },
    "С��": {
        "max_hunger": 120,
        "max_energy": 90,
        "max_happiness": 110,
        "growth_rate": 1.2,
        "rarity": "��ͨ",
        "stage": 0,
        "growth_required": 100
    },
    "ħ����": {
        "max_hunger": 80,
        "max_energy": 120,
        "max_happiness": 150,
        "growth_rate": 1.3,
        "rarity": "ϡ��",
        "stage": 0,
        "growth_required": 100
    },
    "������": {
        "max_hunger": 150,
        "max_energy": 150,
        "max_happiness": 80,
        "growth_rate": 1.4,
        "rarity": "ʷʫ",
        "stage": 0,
        "growth_required": 100
    },
    "С����": {
        "max_hunger": 60,
        "max_energy": 140,
        "max_happiness": 100,
        "growth_rate": 1.3,
        "rarity": "ϡ��",
        "stage": 0,
        "growth_required": 100
    },
    "��è����": {
        "max_hunger": 200,
        "max_energy": 100,
        "max_happiness": 200,
        "growth_rate": 1.4,
        "rarity": "��˵",
        "stage": 0,
        "growth_required": 100
    }
}

# �������·��
EVOLUTIONS = {
    # ������ -> �ɳ��� (3����֧)
    "Сè��": {
        "�ɳ���1": "��è",
        "�ɳ���2": "��è",
        "�ɳ���3": "С��è"
    },
    "С��": {
        "�ɳ���1": "��ë",
        "�ɳ���2": "��ʿ��",
        "�ɳ���3": "��Ȯ"
    },
    "ħ����": {
        "�ɳ���1": "����",
        "�ɳ���2": "����",
        "�ɳ���3": "ħ��"
    },
    "������": {
        "�ɳ���1": "����ô��������",
        "�ɳ���2": "�������",
        "�ɳ���3": "��������"
    },
    "С����": {
        "�ɳ���1": "�غ�",
        "�ɳ���2": "���",
        "�ɳ���3": "�¹����"
    },
    "��è����": {
        "�ɳ���1": "��֮��ʹ",
        "�ɳ���2": "��֮��ʹ",
        "�ɳ���3": "�ڰ���Ů"
    },
    # �ɳ��� -> ������ (�̶�·��)
    "��è": "è��Ů��",
    "��è": "è������",
    "С��è": "è������",
    "��ë": "��Ȯ��",
    "��ʿ��": "����ѩ��",
    "��Ȯ": "�����ػ�",
    "����": "�¹�����",
    "����": "��ҩ����",
    "ħ��": "ħ����Ů",
    "����ô��������": "�����Ů",
    "�������": "С����",
    "��������": "��С��",
    "�غ�": "��ԭ�ػ�",
    "���": "�������",
    "�¹����": "������Ů",
    "��֮��ʹ": "��ҹ��Ů",
    "��֮��ʹ": "������Ů",
    "�ڰ���Ů": "�ڰ�ʥŮ"
}

# �����̵���Ʒ
PET_SHOP_ITEMS = {
    "��ͨ����": {
        "price": 5,
        "hunger": 20,
        "energy": 5,
        "happiness": 1,
        "growth": 0,
        "effect": "�ָ����ﱥʳ��"
    },
    "�߼�����": {
        "price": 25,
        "hunger": 50,
        "energy": 15,
        "happiness": 15,
        "growth": 2,
        "effect": "Ӫ���ḻ������ָ�����״̬,���������ɳ�ֵ"
    },
    "�����": {
        "price": 10,
        "hunger": -5,
        "energy": -10,
        "happiness": 30,
        "growth": 0,
        "effect": "���ӳ���øж�"
    },
    "��������": {
        "price": 15,
        "hunger": 0,
        "energy": 50,
        "happiness": 5,
        "growth": 0,
        "effect": "���ٻָ����ﾫ��"
    },
    "����Ť��": {
        "price": 10,
        "effect": "������һֻ����",
        "type": "gacha"
    },
    "���͵���": {
        "price": 200,
        "hunger": 0,
        "energy": 0,
        "happiness": 0,
        "growth": 0,
        "effect": "���ڽ������ɳ���",
        "special": "evolve_1"
    },
    "��������": {
        "price": 500,
        "hunger": 0,
        "energy": 0,
        "happiness": 0,
        "growth": 0,
        "effect": "���ڽ�����������",
        "special": "evolve_2"
    },
    "ʱ֮��": {
        "price": 100,
        "hunger": 0,
        "energy": 0,
        "happiness": 0,
        "growth": 0,
        "effect": "�óɳ�������������ѡ�������֧",
        "special": "reroll_evolution"
    },
    "�������Լ": {
        "price": 75,
        "hunger": 0,
        "energy": 0,
        "happiness": 0,
        "growth": 0,
        "effect": "Ѱ����ҳ��ߵĳ���",
        "special": "retrieve_pet"
    }
}

# ����״̬����
STATUS_DESCRIPTIONS = {
    "hunger": {
        50: "�Եñ�����",
        40: "�е����",
        30: "�ǳ�����",
        0: "���ò�����"
    },
    "energy": {
        80: "��������",
        50: "�е�����",
        30: "�ǳ�ƣ��",
        0: "��ƣ����"
    },
    "happiness": {
        80: "�ǳ�����",
        50: "����һ��",
        30: "��̫����",
        0: "�ǳ���ɥ"
    }
}