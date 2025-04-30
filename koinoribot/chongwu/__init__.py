import math
import json
import os
import random
import time
import base64
from datetime import datetime, timedelta
import math
import asyncio
import io
from ..utils import chain_reply
from .._R import get, userPath
from hoshino import Service, priv, R
from hoshino.typing import CQEvent, MessageSegment
from .. import money
from .petconfig import GACHA_COST, GACHA_REWARDS, GACHA_CONSOLE_PRIZE, BASE_PETS, EVOLUTIONS, growth1, growth2, growth3, PET_SHOP_ITEMS, STATUS_DESCRIPTIONS
from .pet import get_pet_data, get_user_pets, save_user_pets, get_user_items, save_user_items, get_user_pet, update_user_pet, remove_user_pet, get_user_item_count 
from .pet import add_user_item, use_user_item, get_status_description, update_pet_status, check_pet_evolution
from hoshino.config import SUPERUSERS

no = get('emotion/no.png').cqcode
ok = get('emotion/ok.png').cqcode
sv = Service('pet_raising', manage_priv=priv.ADMIN, enable_on_default=True)


@sv.on_prefix(('购买宝石', '买宝石'))
async def buy_gem(bot, ev):
    user_id = ev.user_id
    args = ev.message.extract_plain_text().strip().split()
    # 检查参数
    if not args or not args[0].isdigit():
        await bot.send(ev, "请指定要购买的数量！\n例如：购买宝石 5", at_sender=True)
        return
    quantity = int(args[0])
    if quantity <= 0:
        await bot.send(ev, "购买数量必须大于0！", at_sender=True)
        return
    # 计算总价
    price_per_gem = 1000
    total_cost = quantity * price_per_gem
    # 检查用户金币
    user_gold = money.get_user_money(user_id, 'gold')
    if user_gold < total_cost:
        await bot.send(ev, f"金币不足！购买{quantity}个宝石需要{total_cost}金币，你只有{user_gold}金币。{no}", at_sender=True)
        return
    # 执行购买
    if money.reduce_user_money(user_id, 'gold', total_cost):
        money.increase_user_money(user_id, 'kirastone', quantity)
        await bot.send(ev, f"成功购买{quantity}个宝石，花费了{total_cost}金币！{ok}", at_sender=True)
    else:
        await bot.send(ev, "购买失败，请稍后再试！", at_sender=True)


# --- 扭蛋系统 ---
@sv.on_prefix(('购买扭蛋', '买扭蛋'))
async def buy_gacha(bot, ev: CQEvent):
    user_id = ev.user_id
    args = ev.message.extract_plain_text().strip().split()
    try:
        quantity = int(args[0]) if args else 1
        if quantity <= 0:
            await bot.send(ev, "购买数量必须是正整数！", at_sender=True)
            return
    except ValueError:
        await bot.send(ev, "购买数量必须是有效的数字！", at_sender=True)
        return
    
    total_cost = quantity * GACHA_COST
    user_stones = money.get_user_money(user_id, 'kirastone')
    if user_stones < total_cost:
        await bot.send(ev, f"宝石不足！购买{quantity}个扭蛋需要{total_cost}宝石，你只有{user_stones}宝石。", at_sender=True)
        return
    
    # 扣除宝石并添加扭蛋
    if money.reduce_user_money(user_id, 'kirastone', total_cost):
        await add_user_item(user_id, "宠物扭蛋", quantity)
        await bot.send(ev, f"成功购买了{quantity}个宠物扭蛋！使用'开启扭蛋'来试试手气吧！", at_sender=True)
    else:
        await bot.send(ev, "购买失败，请稍后再试！", at_sender=True)

@sv.on_fullmatch(('我的扭蛋', '查看扭蛋'))
async def show_gacha(bot, ev: CQEvent):
    user_id = ev.user_id
    gacha_count = await get_user_item_count(user_id, "宠物扭蛋")
    await bot.send(ev, f"你目前拥有{gacha_count}个宠物扭蛋。使用'开启扭蛋'来试试手气吧！", at_sender=True)

@sv.on_fullmatch('开启扭蛋')
async def open_gacha(bot, ev: CQEvent):
    user_id = ev.user_id
    # 检查是否已有宠物
    if await get_user_pet(user_id):
        await bot.send(ev, "你已经有宠物了，无法开启新扭蛋！", at_sender=True)
        return
    
    # 检查是否有扭蛋
    if not await use_user_item(user_id, "宠物扭蛋"):
        await bot.send(ev, "你没有宠物扭蛋！使用'购买扭蛋'来获取。", at_sender=True)
        return
    
    # 扭蛋结果
    anwei = random.random() * 100
    if anwei < 60:
        money.increase_user_money(user_id, 'gold', GACHA_CONSOLE_PRIZE)
        await bot.send(ev, f"很遗憾，这次没有抽中宠物。你获得了{GACHA_CONSOLE_PRIZE}金币作为安慰奖！", at_sender=True)
        return
    
    roll = random.random() * 100
    pet_type = None
    
    if roll < 50:  # 普通
        pool = GACHA_REWARDS["普通"]
    elif roll < 80:  # 稀有
        pool = GACHA_REWARDS["稀有"]
    elif roll < 95:  # 史诗
        pool = GACHA_REWARDS["史诗"]
    else:  # 传说
        pool = GACHA_REWARDS["传说"]
    
    # 从选择的池中随机宠物
    pet_type = random.choices(list(pool.keys()), weights=list(pool.values()))[0]
    
    if pet_type:
        # 保存临时宠物数据，等待用户确认
        temp_pet = {
            "type": pet_type,
            "temp_data": True,
            "gacha_time": time.time()
        }
        await update_user_pet(user_id, temp_pet)
        pet_data = await get_pet_data()
        rarity = pet_data[pet_type]["rarity"]
        await bot.send(ev, f"恭喜！你抽中了{rarity}宠物【{pet_type}】！\n"
                          f"请在5分钟内使用'领养宠物 [名字]'来领养它，或使用'放弃宠物'放弃。\n否则你将无法开启新扭蛋。", at_sender=True)
    else:
        # 安慰奖
        money.increase_user_money(user_id, 'gold', GACHA_CONSOLE_PRIZE)
        await bot.send(ev, f"很遗憾，这次没有抽中宠物。你获得了{GACHA_CONSOLE_PRIZE}金币作为安慰奖！", at_sender=True)

@sv.on_prefix(('领养宠物', '确认领养'))
async def confirm_adopt(bot, ev: CQEvent):
    user_id = ev.user_id
    pet_name = ev.message.extract_plain_text().strip()
    
    if not pet_name:
        await bot.send(ev, "请为你的宠物取个名字！\n例如：领养宠物 小白", at_sender=True)
        return
    
    if len(pet_name) > 10:
        await bot.send(ev, "宠物名字太长了，最多10个字符！", at_sender=True)
        return
    
    # 检查临时宠物数据
    temp_pet = await get_user_pet(user_id)
    if not temp_pet or not temp_pet.get("temp_data"):
        await bot.send(ev, "你没有待领养的宠物！", at_sender=True)
        return
    
    # 检查是否超时
    if time.time() - temp_pet.get("gacha_time", 0) > 300:
        await remove_user_pet(user_id)
        await bot.send(ev, "领养时间已过期！", at_sender=True)
        return
    
    # 检查名字是否已存在
    user_pets = await get_user_pets()
    for uid, pet in user_pets.items():
        if pet.get("name") == pet_name and uid != str(user_id):
            await bot.send(ev, f"名字'{pet_name}'已经被其他宠物使用了，请换一个名字！", at_sender=True)
            return
    
    # 创建正式宠物
    pet_type = temp_pet["type"]
    pet_data = await get_pet_data()
    base_pet = pet_data[pet_type]
    
    new_pet = {
        "type": pet_type,
        "name": pet_name,
        "hunger": base_pet["max_hunger"],
        "energy": base_pet["max_energy"],
        "happiness": base_pet["max_happiness"],
        "max_hunger": base_pet["max_hunger"],
        "max_energy": base_pet["max_energy"],
        "max_happiness": base_pet["max_happiness"],
        "growth": 0,
        "growth_rate": base_pet["growth_rate"],
        "stage": 0,  # 幼年体
        "growth_required": growth1,  # 进化到成长体需要的成长值
        "skills": [],
        "runaway" : False,
        "last_update": time.time(),
        "adopted_time": time.time()
    }
    
    await update_user_pet(user_id, new_pet)
    await bot.send(ev, f"恭喜！你成功领养了一只{pet_name}({pet_type})！", at_sender=True)

@sv.on_fullmatch(('放弃宠物', '丢弃扭蛋宠物'))
async def cancel_adopt(bot, ev: CQEvent):
    user_id = ev.user_id
    temp_pet = await get_user_pet(user_id)
    if not temp_pet or not temp_pet.get("temp_data"):
        await bot.send(ev, "你没有待领养的宠物！", at_sender=True)
        return
    
    await remove_user_pet(user_id)
    await bot.send(ev, "你放弃了这次扭蛋获得的宠物。", at_sender=True)

# --- 宠物用品系统 ---
@sv.on_prefix(('宠物商店', '购买'))
async def buy_pet_item(bot, ev: CQEvent):
    user_id = ev.user_id
    args = ev.message.extract_plain_text().strip().split()
    
    if not args:
        # 显示商店列表
        item_list = []
        for name, info in PET_SHOP_ITEMS.items():
            price = info["price"]
            effect = info.get("effect", "")
            item_list.append(f"{name} - {price}宝石 ({effect})")
        
        await bot.send(ev, "可购买的宠物用品:\n" + "\n".join(item_list) +
                      "\n使用'购买宠物用品 [名称] [数量]'来购买", at_sender=True)
        return
    
    item_name = args[0]
    try:
        quantity = int(args[1]) if len(args) > 1 else 1
        if quantity <= 0:
            await bot.send(ev, "购买数量必须是正整数！", at_sender=True)
            return
    except ValueError:
        await bot.send(ev, "购买数量必须是有效的数字！", at_sender=True)
        return
    
    if item_name not in PET_SHOP_ITEMS:
        await bot.send(ev, f"没有名为'{item_name}'的宠物用品！", at_sender=True)
        return
    
    price = PET_SHOP_ITEMS[item_name]["price"] * quantity
    user_stones = money.get_user_money(user_id, 'kirastone')
    if user_stones < price:
        await bot.send(ev, f"宝石不足！购买{quantity}个{item_name}需要{price}宝石，你只有{user_stones}宝石。", at_sender=True)
        return
    
    # 扣钱并添加物品
    if money.reduce_user_money(user_id, 'kirastone', price):
        await add_user_item(user_id, item_name, quantity)
        await bot.send(ev, f"成功购买了{quantity}个{item_name}！", at_sender=True)
    else:
        await bot.send(ev, "购买失败，请稍后再试！", at_sender=True)

@sv.on_prefix(('宠物背包', '查看宠物用品'))
async def show_pet_items(bot, ev: CQEvent):
    user_id = ev.user_id
    user_items = (await get_user_items()).get(str(user_id), {})
    
    if not user_items:
        await bot.send(ev, "你目前没有宠物用品。使用'购买宠物用品'来获取。", at_sender=True)
        return
    
    item_list = [f"{name} ×{count}" for name, count in user_items.items()]
    await bot.send(ev, "你拥有的宠物用品:\n" + "\n".join(item_list) +
                  "\n使用'使用宠物用品 [名称]'来使用", at_sender=True)

@sv.on_prefix(('使用宠物用品', '使用'))
async def use_pet_item(bot, ev: CQEvent):
    user_id = ev.user_id
    item_name = ev.message.extract_plain_text().strip()
    
    if not item_name:
        await bot.send(ev, "请指定要使用的物品名称！", at_sender=True)
        return
    
    # 检查是否拥有该物品
    if not await use_user_item(user_id, item_name):
        await bot.send(ev, f"你没有{item_name}或者数量不足！", at_sender=True)
        return
    
    # 检查是否是扭蛋
    if item_name == "宠物扭蛋":
        await bot.send(ev, "请直接使用'开启扭蛋'命令来使用扭蛋。", at_sender=True)
        await add_user_item(user_id, item_name)  # 退回物品
        return
    
    # 检查是否有宠物
    pet = await get_user_pet(user_id)
    if not pet:
        await bot.send(ev, "你还没有宠物！", at_sender=True)
        await add_user_item(user_id, item_name)  # 退回物品
        return
    
    pet = await update_pet_status(pet)
    
    if pet["runaway"] == True: # 
        if item_name != "最初的契约":
            # 如果离家出走且使用的不是最初的契约，则阻止使用
            await bot.send(ev, f"\n你的宠物【{pet['name']}】离家出走了，现在只能使用'最初的契约'来寻回它......", at_sender=True)
            await add_user_item(user_id, item_name) # 退回物品
            return
    
    # 应用物品效果
    if item_name not in PET_SHOP_ITEMS:
        await bot.send(ev, f"无效的物品名称: {item_name}", at_sender=True)
        await add_user_item(user_id, item_name)  # 退回物品
        return
    

    item = PET_SHOP_ITEMS[item_name]
    pet["hunger"] = min(pet["max_hunger"], pet["hunger"] + item.get("hunger", 0))
    pet["energy"] = min(pet["max_energy"], pet["energy"] + item.get("energy", 0))
    pet["happiness"] = min(pet["max_happiness"], pet["happiness"] + item.get("happiness", 0))
    pet["growth"] = min(pet["growth_required"], pet["growth"] + item.get("growth", 0))
    
    # 特殊效果处理
    special_msg = ""
    if "special" in item:
            
        if item["special"] == "evolve_1":
            # 奶油蛋糕 - 进化至成长体
            if pet["stage"] == 0 and pet["growth"] >= pet.get("growth_required", 100):
                # 随机选择进化分支
                evolution_options = EVOLUTIONS[pet["type"]]
                evolution_choice = random.choice(["成长体1", "成长体2", "成长体3"])
                new_type = evolution_options[evolution_choice]
                
                pet["type"] = new_type
                pet["stage"] = 1
                pet["growth"] = 0
                pet["growth_required"] = growth2  # 进化到成年体需要500成长值
                pet["max_hunger"] *= 1.5
                pet["max_energy"] *= 1.5
                pet["max_happiness"] *= 1.5
                
                special_msg = f"宠物进化为了{new_type}！"
            else:
                await bot.send(ev, "宠物还不满足进化条件！需要是幼年体且成长值max。", at_sender=True)
                await add_user_item(user_id, item_name)  # 退回物品
                return
            
        elif item["special"] == "evolve_2":
            # 豪华蛋糕 - 进化至成年体
            if pet["stage"] == 1 and pet["growth"] >= pet.get("growth_required", 200):
                if pet["type"] in EVOLUTIONS:
                    new_type = EVOLUTIONS[pet["type"]]
                    pet["type"] = new_type
                    pet["stage"] = 2
                    pet["growth"] = 0
                    pet["growth_required"] = growth3  # 成年体不再需要成长
                    pet["max_hunger"] *= 1.5
                    pet["max_energy"] *= 1.5
                    pet["max_happiness"] *= 1.5
                    
                    special_msg = f"宠物进化为了{new_type}！"
                else:
                    await bot.send(ev, "该宠物没有后续进化形态！", at_sender=True)
                    await add_user_item(user_id, item_name)  # 退回物品
                    return
            else:
                await bot.send(ev, "宠物还不满足进化条件！需要是成长体且成长值max。", at_sender=True)
                await add_user_item(user_id, item_name)  # 退回物品
                return

        elif item["special"] == "reroll_evolution":
            # 时之泪 - 重新随机选择进化分支
            if pet["stage"] == 1:  # 只有成长体可以使用
                original_type = pet["type"]
                # 60%概率保持原分支，40%概率随机选择
                if random.random() < 0.6:
                   await bot.send(ev, f"{pet['name']}的进化分支没有改变。", at_sender=True)
                else:
                    # 找到原始幼年体类型
                    base_type = None
                    for base, evolutions in EVOLUTIONS.items():
                        if isinstance(evolutions, dict):  # 幼年体的进化选项
                            for evo_name, evo_type in evolutions.items():
                                if evo_type == original_type:
                                    base_type = base
                                    break
                        if base_type:
                            break
                
                    if base_type:
                        # 随机选择新分支(排除当前分支)
                        evolution_options = EVOLUTIONS[base_type]
                        available_choices = [k for k in evolution_options.keys() 
                                            if evolution_options[k] != original_type]
                        if available_choices:
                            evolution_choice = random.choice(available_choices)
                            new_type = evolution_options[evolution_choice]
                            
                            pet["type"] = new_type
                            pet["max_hunger"] = int(pet["max_hunger"] * 1.1)  # 小幅提升属性
                            pet["max_energy"] = int(pet["max_energy"] * 1.1)
                            pet["max_happiness"] = int(pet["max_happiness"] * 1.1)
                        
                            await update_user_pet(user_id, pet)
                            await bot.send(ev, f"{pet['name']}的进化分支改变了！现在是{new_type}！", at_sender=True)
                        else:
                            await bot.send(ev, "没有可用的进化分支改变。", at_sender=True)
                    else:
                        await bot.send(ev, "无法找到原始进化路线。", at_sender=True)
            else:
                await bot.send(ev, "只有成长体宠物可以使用时之泪！", at_sender=True)
                await add_user_item(user_id, item_name)  # 退回物品
                return
    
        elif item["special"] == "retrieve_pet":
            # 最初的契约 - 寻回离家出走的宠物
            if pet["runaway"] == True:
                pet["runaway"] = False
                pet["happiness"] = 50  # 恢复心情到50
                pet["hunger"] = pet["max_hunger"] * 0.5  # 恢复部分饱食度
                pet["energy"] = pet["max_energy"] * 0.5  # 恢复部分精力
            
                await update_user_pet(user_id, pet)
                await bot.send(ev, f"你找回了{pet['name']}，这一次，一定要好好珍惜哦~", at_sender=True)
            else:
                await bot.send(ev, "\n你的宠物没有离家出走，不需要使用这个物品。", at_sender=True)
                await add_user_item(user_id, item_name)  # 退回物品
                return

    await update_user_pet(user_id, pet)
    
    effect_msg = []
    if item.get("hunger", 0) != 0:
        effect_msg.append(f"饱食度: {item['hunger']:+}")
    if item.get("energy", 0) != 0:
        effect_msg.append(f"精力: {item['energy']:+}")
    if item.get("happiness", 0) != 0:
        effect_msg.append(f"好感度: {item['happiness']:+}")
    if item.get("growth", 0) != 0:
        effect_msg.append(f"成长值: {item['growth']:+}")
    
    await bot.send(ev, f"\n你对{pet['name']}使用了{item_name}！" +
                  ("\n" + "\n".join(effect_msg) if effect_msg else "") +
                  (f"\n{special_msg}" if special_msg else ""), at_sender=True)

@sv.on_prefix(('摸摸宠物', '陪伴宠物'))
async def play_with_pet(bot, ev):
    user_id = ev.user_id
    pet = await get_user_pet(user_id)
    if not pet:
        await bot.send(ev, "你还没有宠物！", at_sender=True)
        return
    
    pet = await update_pet_status(pet)
    
    # 检查宠物精力
    if pet["energy"] < 20:
        await bot.send(ev, f"{pet['name']}太累了，需要休息！", at_sender=True)
        return
    
    # 玩耍效果
    pet["energy"] = max(0, pet["energy"] - 15)
    pet["happiness"] = min(pet["max_happiness"], pet["happiness"] + 25)
    await update_user_pet(user_id, pet)
    await bot.send(ev, f"\n{pet['name']}很享受你的抚摸，并用脸蛋轻轻蹭了蹭你的手...\n精力-5\n好感+25", at_sender=True)
    
@sv.on_prefix(('休息', '宠物休息'))
async def rest_pet(bot, ev):
    user_id = ev.user_id
    pet = await get_user_pet(user_id)
    if not pet:
        await bot.send(ev, "你还没有宠物！", at_sender=True)
        return
    
    pet = await update_pet_status(pet)
    
    # 休息效果
    pet["energy"] = min(pet["max_energy"], pet["energy"] + 40)
    pet["happiness"] = max(0, pet["happiness"] - 2)  # 休息会减少一点好感度
    
    await update_user_pet(user_id, pet)
    await bot.send(ev, f"{pet['name']}正在休息，精力恢复了！", at_sender=True)

@sv.on_prefix(('改名', '宠物改名'))
async def rename_pet(bot, ev):
    user_id = ev.user_id
    new_name = ev.message.extract_plain_text().strip()
    
    if not new_name:
        await bot.send(ev, "请提供新的宠物名字！\n例如 宠物改名 [新名字]", at_sender=True)
        return
    
    if len(new_name) > 10:
        await bot.send(ev, "宠物名字太长了，最多10个字符！", at_sender=True)
        return
    
    # 检查名字是否已存在
    user_pets = await get_user_pets()
    for uid, pet in user_pets.items():
        if pet["name"] == new_name and uid != str(user_id):
            await bot.send(ev, f"名字'{new_name}'已经被其他宠物使用了，请换一个名字！", at_sender=True)
            return
    
    pet = await get_user_pet(user_id)
    if not pet:
        await bot.send(ev, "你还没有宠物！", at_sender=True)
        return
    
    old_name = pet["name"]
    pet["name"] = new_name
    await update_user_pet(user_id, pet)
    await bot.send(ev, f"成功将'{old_name}'改名为'{new_name}'！", at_sender=True)

@sv.on_prefix(('进化宠物', '宠物进化'))
async def evolve_pet(bot, ev):
    user_id = ev.user_id
    pet = await get_user_pet(user_id)
    if not pet:
        await bot.send(ev, "你还没有宠物！", at_sender=True)
        return
    
    pet = await update_pet_status(pet)
    
    # 检查进化条件
    if pet["stage"] == 0 and pet["growth"] >= pet.get("growth_required", 100):
        # 幼年体 -> 成长体
        # 检查是否有奶油蛋糕
        if not await use_user_item(user_id, "奶油蛋糕"):
            await bot.send(ev, "进化需要奶油蛋糕！", at_sender=True)
            return
        # 随机选择进化分支
        evolution_options = EVOLUTIONS[pet["type"]]
        evolution_choice = random.choice(["成长体1", "成长体2", "成长体3"])
        new_type = evolution_options[evolution_choice]
        
        pet["type"] = new_type
        pet["stage"] = 1
        pet["growth"] = 0
        pet["growth_required"] = growth2  # 进化到成年体需要500成长值
        pet["max_hunger"] *= 1.5
        pet["max_energy"] *= 1.5
        pet["max_happiness"] *= 1.5
        
        await update_user_pet(user_id, pet)
        await bot.send(ev, f"恭喜！{pet['name']}进化为{new_type}！", at_sender=True)
    
    elif pet["stage"] == 1 and pet["growth"] >= pet.get("growth_required", 200):
        # 成长体 -> 成年体
        # 检查是否有豪华蛋糕
        if not await use_user_item(user_id, "豪华蛋糕"):
            await bot.send(ev, "进化需要豪华蛋糕！", at_sender=True)
            return
        
        if pet["type"] in EVOLUTIONS:
            new_type = EVOLUTIONS[pet["type"]]
            pet["type"] = new_type
            pet["stage"] = 2
            pet["growth"] = 0
            pet["growth_required"] = growth3  # 成年体不再需要成长
            pet["max_hunger"] *= 2.0
            pet["max_energy"] *= 2.0
            pet["max_happiness"] *= 2.0
            
            await update_user_pet(user_id, pet)
            await bot.send(ev, f"恭喜！{pet['name']}进化为{new_type}！", at_sender=True)
        else:
            await bot.send(ev, f"{pet['name']}没有后续进化形态！", at_sender=True)
    else:
        await bot.send(ev, f"{pet['name']}还不满足进化条件！", at_sender=True)

@sv.on_prefix(('我的宠物', '查看宠物'))
async def show_pet(bot, ev):
    user_id = ev.user_id
    pet = await get_user_pet(user_id)
    if not pet:
        await bot.send(ev, "你还没有宠物，使用'领养宠物'来领养一只吧！", at_sender=True)
        return
    
    if pet.get("runaway"):
        await bot.send(ev, f"{pet['name']}已经离家出走了！使用'最初的契约'可以寻回它。", at_sender=True)
        return
    
    # 更新宠物状态
    pet = await update_pet_status(pet)
    await update_user_pet(user_id, pet)
    
    # 检查进化
    evolution = await check_pet_evolution(pet)
    if evolution == "stage1":
        await bot.send(ev, f"你的宠物可以进化为成长体了！使用'进化宠物'来让它进化。", at_sender=True)
    elif evolution == "stage2":
        await bot.send(ev, f"你的宠物可以进化为成年体了！使用'进化宠物'来让它进化。", at_sender=True)
    
    # 显示宠物状态
    hunger_desc = await get_status_description("hunger", pet["hunger"])
    energy_desc = await get_status_description("energy", pet["energy"])
    happiness_desc = await get_status_description("happiness", pet["happiness"])
    adopted_date = datetime.fromtimestamp(pet["adopted_time"]).strftime('%Y-%m-%d')
    
    stage_name = {
        0: "幼年体",
        1: "成长体",
        2: "成年体"
    }.get(pet["stage"], "未知")
    
    message = [
        f"\n宠物名称：{pet['name']}",
        f"种族：{pet['type']} ({stage_name})",
        f"领养日期: {adopted_date}",
        f"成长度: {pet['growth']:.1f}/{pet.get('growth_required', 0)}",
        f"饱食度: {pet['hunger']:.1f}/{pet['max_hunger']} ({hunger_desc})",
        f"精力: {pet['energy']:.1f}/{pet['max_energy']} ({energy_desc})",
        f"好感度: {pet['happiness']:.1f}/{pet['max_happiness']} ({happiness_desc})",
        f"技能: {', '.join(pet['skills']) if pet['skills'] else '暂无'}",
        "投喂食物、或使用'玩耍'或'休息'来照顾她吧~"
    ]
    
    await bot.send(ev, "\n".join(message), at_sender=True)

@sv.on_prefix(('放生宠物', '丢弃宠物'))
async def release_pet(bot, ev):
    user_id = ev.user_id
    pet = await get_user_pet(user_id)
    if not pet:
        await bot.send(ev, "你还没有宠物！", at_sender=True)
        return
    
    # 确认操作
    confirm = ev.message.extract_plain_text().strip().lower()
    if confirm != "确认":
        await bot.send(ev, f"确定要放生{pet['name']}吗？这将永久失去它！\n使用'放生宠物 确认'来确认操作", at_sender=True)
        return
    
    await remove_user_pet(user_id)
    await bot.send(ev, f"你放生了{pet['name']}。", at_sender=True)

@sv.on_fullmatch('宠物排行榜')
async def pet_ranking(bot, ev):
    """显示成长值最高的前10只成年体宠物"""
    user_pets = await get_user_pets()
    
    # 筛选成年体宠物并按成长值排序
    adult_pets = []
    for user_id, pet in user_pets.items():
        if pet.get("stage") == 2:  # 仅成年体
            pet = await update_pet_status(pet)
            adult_pets.append((pet["growth"], pet["name"], pet["type"], user_id))
    
    if not adult_pets:
        await bot.send(ev, "目前还没有成年体宠物上榜哦！", at_sender=True)
        return
    
    # 按成长值降序排序
    adult_pets.sort(reverse=True)
    
    # 构建排行榜消息
    msg = ["\n🏆 宠物排行榜-TOP10 🏆"]
    for rank, (growth, name, pet_type, user_id) in enumerate(adult_pets[:10], 1):
        try:
            user_info = await bot.get_group_member_info(group_id=ev.group_id, user_id=int(user_id))
            nickname = user_info.get("nickname", user_id)
        except:
            nickname = user_id
        msg.append(f"第{rank}名: {name}({pet_type}) \n 成长值:{growth:.1f} ")
    
    await bot.send(ev, "\n".join(msg), at_sender=True)

@sv.on_fullmatch('宠物排名')
async def my_pet_ranking(bot, ev):
    """查看自己宠物的排名"""
    user_id = ev.user_id
    pet = await get_user_pet(user_id)
    if not pet:
        await bot.send(ev, "你还没有宠物！", at_sender=True)
        return
    
    pet = await update_pet_status(pet)
    
    if pet["stage"] != 2:  # 仅成年体可查看排名
        await bot.send(ev, "只有成年体宠物可以查看排名哦！", at_sender=True)
        return
    
    user_pets = await get_user_pets()
    
    # 筛选所有成年体宠物
    adult_pets = []
    for uid, p in user_pets.items():
        if p.get("stage") == 2:
            p = await update_pet_status(p)
            adult_pets.append((p["growth"], uid))
    
    if not adult_pets:
        await bot.send(ev, "目前还没有成年体宠物上榜哦！", at_sender=True)
        return
    
    # 按成长值排序
    adult_pets.sort(reverse=True)
    
    # 查找自己的排名
    my_growth = pet["growth"]
    rank = None
    same_growth_count = 0
    
    for i, (growth, uid) in enumerate(adult_pets):
        if uid == str(user_id):
            rank = i + 1
            break
        if growth == my_growth:
            same_growth_count += 1
    
    if rank is None:
        await bot.send(ev, "你的宠物未上榜！", at_sender=True)
    else:
        total_pets = len(adult_pets)
        await bot.send(ev, f"你的宠物【{pet['name']}】当前排名: 第{rank}名 \n成长值: {my_growth:.1f}", at_sender=True)






# 帮助信息
pet_help = """
宠物养成系统帮助：
【扭蛋系统】
1. 购买扭蛋 [数量] - 购买宠物扭蛋(10宝石/个)
2. 开启扭蛋 - 开启一个扭蛋(可能获得宠物或安慰奖)
3. 领养宠物 [名字] - 领养扭蛋获得的宠物
4. 放弃宠物 - 放弃扭蛋获得的宠物

【宠物用品】
1. 宠物商店 - 查看可购买的宠物用品
2. 购买 [名称] [数量] - 购买指定宠物用品
3. 宠物背包 - 查看拥有的宠物用品
4. 使用 [名称] - 对宠物使用物品

【宠物管理】
1. 我的宠物 - 查看宠物状态
2. 摸摸宠物 - 陪伴宠物（恢复好感）
3. 宠物休息 - 让宠物休息（恢复精力）
4. 宠物改名 [新名字] - 为宠物改名
5. 进化宠物 - 进化符合条件的宠物
6. 放生宠物 确认 - 放生当前宠物

【其他】
1. 买宝石 [数量] - 购买宝石
2. 宠物帮助 - 显示本帮助
3. 宠物排行榜 - 查看成长值最高的成年体宠物
4. 宠物排名 - 查看自己宠物的排名

【温馨提醒】
1. 当饱食度或精力值过低时，好感度会迅速下降
2. 当好感度过低时，宠物会离家出走
3. 离家出走期间，宠物将停止长大
4. 排行榜功能需要宠物成长至完全体才能开启


"""

@sv.on_fullmatch(('宠物帮助', '宠物养成帮助'))
async def pet_help_command(bot, ev):
    chain = []
    await chain_reply(bot, ev, chain, pet_help)
    await bot.send_group_forward_msg(group_id=ev.group_id, messages=chain)
