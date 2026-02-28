"""
《暗夜割草者：深渊轮回》 — 局外系统模块
========================================
包含: 图鉴、副本、局外升级、抽卡
========================================
"""

import pygame
import math
import random
import os
import json
import characters
import i18n

# ============================================================
#  引用 (由 init() 注入)
# ============================================================
_screen = None
_font_lg = _font_md = _font_sm = _font_xs = None
WIDTH = 1200
HEIGHT = 800

# 颜色
WHITE  = (255, 255, 255)
BLACK  = (0, 0, 0)
RED    = (255, 68, 68)
GREEN  = (68, 255, 68)
BLUE   = (68, 68, 255)
CYAN   = (78, 205, 196)
YELLOW = (255, 255, 0)
ORANGE = (255, 170, 0)
PINK   = (255, 100, 200)
PURPLE = (170, 68, 255)
GOLD   = (255, 215, 0)
DARK_BG    = (12, 12, 20)

# ---- 描边文字渲染 ----
def _render_outlined(font, text, color, outline_color=(0, 0, 0), offset=1):
    """渲染带黑色描边的文字, 返回 Surface"""
    base = font.render(text, True, color)
    outline = font.render(text, True, outline_color)
    w, h = base.get_size()
    surf = pygame.Surface((w + offset * 2, h + offset * 2), pygame.SRCALPHA)
    for dx in (-offset, 0, offset):
        for dy in (-offset, 0, offset):
            if dx == 0 and dy == 0:
                continue
            surf.blit(outline, (offset + dx, offset + dy))
    surf.blit(base, (offset, offset))
    return surf


def init(screen, font_lg, font_md, font_sm, font_xs, w, h):
    global _screen, _font_lg, _font_md, _font_sm, _font_xs, WIDTH, HEIGHT
    _screen = screen
    _font_lg = font_lg; _font_md = font_md
    _font_sm = font_sm; _font_xs = font_xs
    WIDTH = w; HEIGHT = h


# ============================================================
#  图鉴数据库 —— 所有可收集条目
# ============================================================

# 角色图鉴 (index, name, title, color, desc)
CHARACTER_CODEX = [
    (0, "阿什",  "暗夜猎人",   CYAN,    "平衡型角色，起始武器:魔法飞弹"),
    (1, "莉拉",  "风行者",     GREEN,   "高机动角色，起始武器:回旋镖"),
    (2, "加隆",  "铁壁守卫",   ORANGE,  "坦克角色，起始武器:骨盾环绕"),
    (3, "菲奥",  "炽炎法师",   RED,     "高伤角色，起始武器:火球术"),
    (4, "虚无",  "虚空行者",   PURPLE,  "暗杀角色，起始武器:寒冰新星"),
    (5, "死神",  "收割者",     PINK,    "收割角色，起始武器:圣光鞭"),
]

# 武器图鉴 (name, color, desc)
WEAPON_CODEX = [
    ("魔法飞弹", CYAN,   "自动追踪敌人的魔法弹幕，穿透力强"),
    ("圣光鞭",  GOLD,   "以神圣之力鞭笞前方扇形区域的敌人"),
    ("寒冰新星", (100, 200, 255), "向四面八方释放冰弹，减速命中敌人"),
    ("火球术",  ORANGE, "发射强力火球，爆炸造成范围伤害"),
    ("雷电领域", YELLOW, "在周围生成雷电光圈持续电击敌人"),
    ("骨盾环绕", WHITE,  "召唤骨盾环绕自身，触碰即伤"),
    ("回旋镖",  GREEN,  "投掷回旋镖，去而复返双重伤害"),
    ("大地尖刺", (180, 130, 60), "在敌人脚下召唤地刺进行刺穿"),
]

# 角色初始武器映射 (角色索引 -> 武器图鉴索引)
CHAR_STARTER_WEAPON = {
    0: 0,  # 阿什 → 魔法飞弹
    1: 6,  # 莉拉 → 回旋镖
    2: 5,  # 加隆 → 骨盾环绕
    3: 3,  # 菲奥 → 火球术
    4: 2,  # 虚无 → 寒冰新星
    5: 1,  # 死神 → 圣光鞭
}

# 绘制武器小图标的辅助函数
def _draw_weapon_icon(surface, x, y, weapon_idx, size=16):
    """在指定位置绘制武器小图标"""
    if weapon_idx >= len(WEAPON_CODEX):
        return
    wname, wcolor, _ = WEAPON_CODEX[weapon_idx]
    # 不同武器用不同形状
    if weapon_idx == 0:  # 魔法飞弹 - 小圆球
        pygame.draw.circle(surface, wcolor, (x, y), size // 2)
        pygame.draw.circle(surface, WHITE, (x, y), size // 2, 1)
    elif weapon_idx == 1:  # 圣光鞭 - 弧线
        pygame.draw.arc(surface, wcolor, (x - size, y - size, size * 2, size * 2), 0.3, 2.5, 3)
    elif weapon_idx == 2:  # 寒冰新星 - 星形
        for a in range(6):
            angle = a * math.pi / 3
            ex = x + int(math.cos(angle) * size * 0.7)
            ey = y + int(math.sin(angle) * size * 0.7)
            pygame.draw.line(surface, wcolor, (x, y), (ex, ey), 2)
    elif weapon_idx == 3:  # 火球术 - 火焰球
        pygame.draw.circle(surface, wcolor, (x, y), size // 2)
        pygame.draw.circle(surface, (255, 100, 30), (x, y - 2), size // 3)
    elif weapon_idx == 4:  # 雷电领域 - 闪电
        pts = [(x - 4, y - size//2), (x + 2, y - 2), (x - 2, y + 2), (x + 4, y + size//2)]
        pygame.draw.lines(surface, wcolor, False, pts, 2)
    elif weapon_idx == 5:  # 骨盾环绕 - 三角盾
        pygame.draw.polygon(surface, wcolor, [(x, y - size//2), (x - size//2, y + size//3), (x + size//2, y + size//3)], 2)
    elif weapon_idx == 6:  # 回旋镖 - V形
        pygame.draw.lines(surface, wcolor, False, [(x - size//2, y - size//3), (x, y + size//3), (x + size//2, y - size//3)], 3)
    elif weapon_idx == 7:  # 大地尖刺 - 三角尖刺
        pygame.draw.polygon(surface, wcolor, [(x, y - size//2), (x - size//3, y + size//2), (x + size//3, y + size//2)])

# Boss图鉴 (name, title, color, desc, hp_base)
BOSS_CODEX = [
    ("骷髅王",   "亡灵领主",  PINK,   "召唤亡灵大军的骷髅领主，擅长范围攻击", 3000),
    ("毒液巨兽", "深渊之王",  GREEN,  "喷射剧毒的深渊巨兽，毒雾弥漫战场", 4000),
    ("烈焰魔将", "战场霸主",  ORANGE, "浑身烈焰的魔族将领，火海吞噬一切", 5000),
    ("虚空之眼", "次元裂隙",  PURPLE, "来自虚空的恐怖存在，扭曲时空法则", 6000),
]

# 敌人图鉴 (name, color, desc, special)
ENEMY_CODEX = [
    ("骷髅杂兵",  (200, 200, 180), "最基础的亡灵士兵，数量多但很脆弱", None),
    ("蝙蝠群",    (100, 80, 120),  "高速飞行的蝙蝠群，灵活但血薄", None),
    ("泥沼史莱姆", (80, 200, 80),   "黏糊糊的史莱姆，死后会分裂", "分裂"),
    ("幽灵",      (150, 150, 220), "飘忽不定的亡灵，伤害中等", None),
    ("自爆蜘蛛",  (180, 60, 60),   "靠近后自爆的危险蜘蛛", "自爆"),
    ("骷髅弓箭手", (220, 200, 160), "远程射击的骷髅，保持距离作战", "远程"),
    ("暗影法师",  (120, 50, 180),  "暗影魔法攻击，高伤害远程敌人", "远程"),
    ("精英骑士",  (200, 180, 50),  "全副武装的精英骑士，会冲锋", "冲锋"),
]


# ============================================================
#  副本系统
# ============================================================
DUNGEON_LIST = [
    {
        'id': 'abyss_gate',
        'name': '深渊之门',
        'desc': '通往深渊的第一道裂隙，适合初入深渊者',
        'difficulty': 1,
        'color': GREEN,
        'time_limit': 300,      # 5分钟
        'enemy_mult': 1.0,      # 敌人强度倍率
        'spawn_rate': 1.0,      # 生成速率
        'boss_type': 0,         # 骷髅王
        'boss_at_min': 4,       # 4分钟出Boss
        'rewards': {'gold': (100, 200), 'diamond': 0, 'mat_iron': (3, 6)},
        'unlock_need': 0,       # 前置击杀数
    },
    {
        'id': 'shadow_rift',
        'name': '暗影裂隙',
        'desc': '暗影精华弥漫的异空间，敌人更加强大',
        'difficulty': 2,
        'color': PURPLE,
        'time_limit': 480,
        'enemy_mult': 1.5,
        'spawn_rate': 1.3,
        'boss_type': 1,         # 毒液巨兽
        'boss_at_min': 6,
        'rewards': {'gold': (200, 400), 'diamond': (1, 3), 'mat_shadow': (3, 5)},
        'unlock_need': 100,
    },
    {
        'id': 'flame_domain',
        'name': '炎魔领域',
        'desc': '烈焰魔将统治的火焰地域，高温炙烤',
        'difficulty': 3,
        'color': ORANGE,
        'time_limit': 600,
        'enemy_mult': 2.0,
        'spawn_rate': 1.5,
        'boss_type': 2,         # 烈焰魔将
        'boss_at_min': 8,
        'rewards': {'gold': (400, 800), 'diamond': (3, 6), 'mat_crystal': (2, 4)},
        'unlock_need': 500,
    },
    {
        'id': 'void_core',
        'name': '虚空核心',
        'desc': '虚空之眼栖息的维度核心，终极考验',
        'difficulty': 4,
        'color': (180, 50, 255),
        'time_limit': 900,
        'enemy_mult': 3.0,
        'spawn_rate': 2.0,
        'boss_type': 3,         # 虚空之眼
        'boss_at_min': 12,
        'rewards': {'gold': (800, 1500), 'diamond': (5, 10), 'mat_dragon': (2, 3), 'mat_abyss': (1, 2)},
        'unlock_need': 1500,
    },
    {
        'id': 'endless_abyss',
        'name': '无尽深渊',
        'desc': '没有时间限制的无尽模式，坚持越久奖励越丰',
        'difficulty': 5,
        'color': RED,
        'time_limit': 0,        # 无限
        'enemy_mult': 1.5,
        'spawn_rate': 1.2,
        'boss_type': -1,        # 随机Boss
        'boss_at_min': 10,
        'rewards': {'gold': (50, 100), 'diamond': (1, 2)},  # per boss kill
        'unlock_need': 3000,
    },
]


# ============================================================
#  局外角色升级系统  (满级150, 每10级进阶)
# ============================================================
def get_char_level_cost(level):
    """角色升级到下一级所需金币"""
    if level >= 150: return 0
    base = 50 + level * 20
    # 每10级区间成本增加
    tier = level // 10
    return int(base * (1 + tier * 0.3))

def get_char_ascend_cost(ascend_tier):
    """角色进阶(每10级一次)所需: (金币, 钻石, 材料dict)"""
    costs = [
        (500,    0,  {'iron': 5}),                          # 10级
        (1200,   0,  {'iron': 10}),                         # 20级
        (2500,   2,  {'iron': 10, 'shadow': 5}),            # 30级
        (5000,   5,  {'shadow': 10, 'crystal': 3}),         # 40级
        (8000,   8,  {'shadow': 10, 'crystal': 8}),         # 50级
        (12000, 12,  {'crystal': 10, 'dragon': 3}),         # 60级
        (18000, 18,  {'crystal': 10, 'dragon': 8}),         # 70级
        (25000, 25,  {'dragon': 10, 'abyss': 3}),           # 80级
        (35000, 35,  {'dragon': 15, 'abyss': 5}),           # 90级
        (50000, 50,  {'dragon': 15, 'abyss': 10}),          # 100级
        (70000, 70,  {'abyss': 15}),                        # 110级
        (100000, 100, {'abyss': 20}),                       # 120级
        (150000, 150, {'abyss': 30}),                       # 130级
        (200000, 200, {'abyss': 40}),                       # 140级
    ]
    if ascend_tier < len(costs):
        return costs[ascend_tier]
    return (999999, 999, {'abyss': 99})


def get_char_stat_bonus(level):
    """角色等级带来的永久属性加成"""
    return {
        'max_health': level * 3,
        'dmg_bonus':  round(level * 0.003, 3),
        'armor':      level // 10,
        'crit':       round(min(0.3, level * 0.001), 3),
        'speed_mult': round(min(0.3, level * 0.001), 3),
    }


# ============================================================
#  局外装备升级系统  (满级150, 每10级进阶)
# ============================================================
def get_meta_equip_level_cost(level, rarity):
    """局外装备升级所需金币"""
    if level >= 150: return 0
    rarity_mult = {'common': 1.0, 'uncommon': 1.3, 'rare': 1.6, 'epic': 2.0, 'legendary': 2.5}
    base = 30 + level * 15
    tier = level // 10
    return int(base * (1 + tier * 0.25) * rarity_mult.get(rarity, 1.0))

def get_meta_equip_ascend_cost(ascend_tier, rarity):
    """装备进阶所需: (金币, 钻石, 材料dict)"""
    rarity_mult = {'common': 0.6, 'uncommon': 0.8, 'rare': 1.0, 'epic': 1.4, 'legendary': 2.0}
    rm = rarity_mult.get(rarity, 1.0)
    base_gold, base_dia, base_mats = get_char_ascend_cost(ascend_tier)
    gold = int(base_gold * rm * 0.7)
    dia = max(0, int(base_dia * rm * 0.5))
    mats = {k: max(1, int(v * rm * 0.6)) for k, v in base_mats.items()}
    return (gold, dia, mats)

def get_meta_equip_stat_bonus(level, base_stats):
    """装备等级带来的属性倍率"""
    mult = 1.0 + level * 0.02  # 每级+2%
    stats = {}
    for k, v in base_stats.items():
        if isinstance(v, float):
            stats[k] = round(v * mult, 4)
        else:
            stats[k] = int(v * mult)


def get_equip_sell_price(meq, equipment_db):
    """计算单件装备出售价格"""
    tidx = meq.get('template_idx', 0)
    if tidx >= len(equipment_db):
        return 0
    tpl = equipment_db[tidx]
    rarity = tpl[2]
    eq_lv = meq.get('level', 1)
    base_price = {'common': 15, 'uncommon': 40, 'rare': 100, 'epic': 300, 'legendary': 800}
    price = base_price.get(rarity, 10)
    # 强化等级增加售价
    price += eq_lv * 5
    return price


def batch_sell_equipment(save_data, equipment_db, keep_rarities=None):
    """批量出售装备，保留指定品质。
    keep_rarities: 保留的品质列表, 如 ['legendary'] 或 ['epic','legendary']
    返回 (出售数量, 获得金币)
    """
    if keep_rarities is None:
        keep_rarities = ['legendary']
    meta_equips = save_data.get('meta_equipment', [])
    me = save_data.get('meta_equipped', {})

    # 收集所有已装备的索引
    equipped_idxs = set()
    for ck, cv in me.items():
        for s, wi in cv.items():
            equipped_idxs.add(wi)

    # 找出要出售的
    sell_count = 0
    sell_gold = 0
    keep_indices = set()
    for i, meq in enumerate(meta_equips):
        tidx = meq.get('template_idx', 0)
        if tidx >= len(equipment_db):
            keep_indices.add(i)
            continue
        tpl = equipment_db[tidx]
        rarity = tpl[2]
        if rarity in keep_rarities:
            keep_indices.add(i)
            continue
        if i in equipped_idxs:
            keep_indices.add(i)
            continue
        # 出售
        sell_gold += get_equip_sell_price(meq, equipment_db)
        sell_count += 1

    if sell_count == 0:
        return 0, 0

    # 重建装备列表，更新索引映射
    old_to_new = {}
    new_equips = []
    for old_i, meq in enumerate(meta_equips):
        if old_i in keep_indices:
            old_to_new[old_i] = len(new_equips)
            new_equips.append(meq)

    # 更新装备绑定索引
    new_me = {}
    for ck, cv in me.items():
        new_binds = {}
        for s, wi in cv.items():
            if wi in old_to_new:
                new_binds[s] = old_to_new[wi]
        if new_binds:
            new_me[ck] = new_binds

    save_data['meta_equipment'] = new_equips
    save_data['meta_equipped'] = new_me
    save_data['gold'] = save_data.get('gold', 0) + sell_gold

    return sell_count, sell_gold


def count_sellable_equipment(save_data, equipment_db, keep_rarities=None):
    """统计可出售装备数量和预计金币（不实际出售）"""
    if keep_rarities is None:
        keep_rarities = ['legendary']
    meta_equips = save_data.get('meta_equipment', [])
    me = save_data.get('meta_equipped', {})
    equipped_idxs = set()
    for ck, cv in me.items():
        for s, wi in cv.items():
            equipped_idxs.add(wi)
    count = 0
    gold = 0
    for i, meq in enumerate(meta_equips):
        tidx = meq.get('template_idx', 0)
        if tidx >= len(equipment_db):
            continue
        tpl = equipment_db[tidx]
        if tpl[2] in keep_rarities:
            continue
        if i in equipped_idxs:
            continue
        count += 1
        gold += get_equip_sell_price(meq, equipment_db)
    return count, gold
    return stats


# ============================================================
#  抽卡系统
# ============================================================

# 常规卡池 (金币)
NORMAL_GACHA_COST = 1000
NORMAL_GACHA_10_COST = 9000   # 十连有折扣
NORMAL_GACHA_WEIGHTS = {
    'common': 50, 'uncommon': 30, 'rare': 15, 'epic': 4, 'legendary': 1,
}
# 超级卡池 (钻石)
SUPER_GACHA_COST = 100
SUPER_GACHA_10_COST = 900
SUPER_GACHA_WEIGHTS = {
    'common': 10, 'uncommon': 25, 'rare': 35, 'epic': 22, 'legendary': 8,
}

# 保底机制
PITY_NORMAL_EPIC = 30       # 30抽保底史诗
PITY_SUPER_LEGENDARY = 80   # 80抽保底传说


def do_gacha_pull(pool='normal', save_data=None, equipment_db=None):
    """执行一次抽卡，返回 (template_idx, rarity) 或 None"""
    if pool == 'normal':
        weights = dict(NORMAL_GACHA_WEIGHTS)
        pity_key = 'gacha_pity_normal'
        pity_limit = PITY_NORMAL_EPIC
        pity_rarity = 'epic'
    else:
        weights = dict(SUPER_GACHA_WEIGHTS)
        pity_key = 'gacha_pity_super'
        pity_limit = PITY_SUPER_LEGENDARY
        pity_rarity = 'legendary'

    # 检查保底
    pity_count = save_data.get(pity_key, 0) + 1
    if pity_count >= pity_limit:
        rarity = pity_rarity
        pity_count = 0
    else:
        rarities = list(weights.keys())
        w = list(weights.values())
        rarity = random.choices(rarities, weights=w)[0]
        # 抽到保底品质也重置
        rarity_order = ['common', 'uncommon', 'rare', 'epic', 'legendary']
        if rarity_order.index(rarity) >= rarity_order.index(pity_rarity):
            pity_count = 0

    save_data[pity_key] = pity_count

    # 从装备库选一个该品质的装备
    candidates = [i for i, tpl in enumerate(equipment_db) if tpl[2] == rarity]
    if not candidates:
        return None
    template_idx = random.choice(candidates)
    return template_idx, rarity


# ============================================================
#  存档数据默认结构 (局外)
# ============================================================
def get_default_meta_save():
    """局外系统存档默认值"""
    return {
        # 货币
        'gold': 0,
        'diamond': 0,
        # 角色等级 {char_idx: level}
        'char_levels': {str(i): 1 for i in range(6)},
        # 角色进阶 {char_idx: ascend_tier}  (0=未进阶, 1=已过10级进阶...)
        'char_ascend': {str(i): 0 for i in range(6)},
        # 局外装备仓库  [{template_idx, level, ascend}]
        'meta_equipment': [],
        # 角色装备绑定 {char_idx_str: {slot: equip_warehouse_index}}
        'meta_equipped': {},
        # 材料
        'meta_materials': {'iron': 0, 'shadow': 0, 'crystal': 0, 'dragon': 0, 'abyss': 0},
        # 图鉴解锁
        'codex_chars': [0],       # 已解锁角色索引
        'codex_weapons': [],      # 已使用过的武器名
        'codex_bosses': [],       # 已击败的Boss索引
        'codex_enemies': [0, 1],  # 已遭遇的敌人索引
        'codex_equips': [],       # 已获得过的装备模板索引
        # 副本
        'dungeon_clears': {},     # {dungeon_id: clear_count}
        'total_boss_kills': 0,
        # 角色解锁
        'unlocked_chars': [0],    # 已解锁角色 (0号默认解锁)
        # 抽卡保底
        'gacha_pity_normal': 0,
        'gacha_pity_super': 0,
        'gacha_total_pulls': 0,
    }


# ---- 角色装备绑定工具 ----
def get_char_equipped(save_data, char_idx, equipment_db):
    """获取角色已装备的局外装备, 返回 {slot: (warehouse_idx, template_tuple, level)}"""
    equipped = {}
    me = save_data.get('meta_equipped', {})
    char_key = str(char_idx)
    if char_key not in me:
        return equipped
    meta_equips = save_data.get('meta_equipment', [])
    for slot, widx in me[char_key].items():
        if 0 <= widx < len(meta_equips):
            meq = meta_equips[widx]
            tidx = meq.get('template_idx', 0)
            if tidx < len(equipment_db):
                equipped[slot] = (widx, equipment_db[tidx], meq.get('level', 1))
    return equipped


def equip_meta_item(save_data, char_idx, warehouse_idx, equipment_db):
    """给角色装备一件局外装备, 返回 True/False"""
    meta_equips = save_data.get('meta_equipment', [])
    if warehouse_idx >= len(meta_equips):
        return False
    meq = meta_equips[warehouse_idx]
    tidx = meq.get('template_idx', 0)
    if tidx >= len(equipment_db):
        return False
    tpl = equipment_db[tidx]
    slot = tpl[1]  # weapon/armor/accessory/rune

    me = save_data.setdefault('meta_equipped', {})
    char_key = str(char_idx)
    if char_key not in me:
        me[char_key] = {}

    # 检查该装备是否被其他角色穿着
    for ck, cv in me.items():
        for s, wi in list(cv.items()):
            if wi == warehouse_idx and ck != char_key:
                del cv[s]  # 从其他角色卸下
                break

    # 如果该槽位已有装备且是同一件, 卸下
    if me[char_key].get(slot) == warehouse_idx:
        del me[char_key][slot]
        return True

    me[char_key][slot] = warehouse_idx
    return True


def unequip_meta_item(save_data, char_idx, slot):
    """卸下角色某槽位装备"""
    me = save_data.get('meta_equipped', {})
    char_key = str(char_idx)
    if char_key in me and slot in me[char_key]:
        del me[char_key][slot]
        return True
    return False


def get_meta_equip_stats(save_data, char_idx, equipment_db):
    """计算角色局外装备提供的总属性加成"""
    stats = {}
    equipped = get_char_equipped(save_data, char_idx, equipment_db)
    for slot, (widx, tpl, eq_lv) in equipped.items():
        base_stats = tpl[3]
        mult = 1.0 + (eq_lv - 1) * 0.03  # 每级+3%
        for k, v in base_stats.items():
            bonus = round(v * mult, 3) if isinstance(v, float) else int(v * mult)
            stats[k] = stats.get(k, 0) + bonus
    return stats


# ---- 角色解锁条件 ----
CHAR_UNLOCK_CONDITIONS = {
    0: {'type': 'free', 'desc': '初始角色'},
    1: {'type': 'kills', 'need': 50, 'desc': '累计击杀50'},
    2: {'type': 'kills', 'need': 200, 'desc': '累计击杀200'},
    3: {'type': 'kills', 'need': 500, 'desc': '累计击杀500'},
    4: {'type': 'kills', 'need': 1000, 'desc': '累计击杀1000'},
    5: {'type': 'kills', 'need': 2000, 'desc': '累计击杀2000'},
}

def check_char_unlocks(save_data):
    """检查并解锁满足条件的角色, 返回新解锁角色index列表"""
    unlocked = save_data.get('unlocked_chars', [0])
    best_kills = save_data.get('best_kills', 0)
    newly = []
    for cidx, cond in CHAR_UNLOCK_CONDITIONS.items():
        if cidx in unlocked:
            continue
        if cond['type'] == 'free':
            if cidx not in unlocked:
                unlocked.append(cidx)
                newly.append(cidx)
        elif cond['type'] == 'kills':
            if best_kills >= cond['need']:
                unlocked.append(cidx)
                newly.append(cidx)
    save_data['unlocked_chars'] = unlocked
    return newly


def merge_meta_save(save_data):
    """确保存档包含所有局外字段"""
    default = get_default_meta_save()
    for k, v in default.items():
        if k not in save_data:
            save_data[k] = v
        elif isinstance(v, dict) and isinstance(save_data[k], dict):
            for kk, vv in v.items():
                if kk not in save_data[k]:
                    save_data[k][kk] = vv
    return save_data


# ============================================================
#  结算奖励计算
# ============================================================
def calculate_settlement(run_data, dungeon_info=None, bosses_killed=0):
    """计算局结束后的奖励
    返回 {'gold':, 'diamond':, 'materials': {}, 'equipment': [], 'exp_gained':}
    """
    rewards = {
        'gold': 0, 'diamond': 0,
        'materials': {'iron': 0, 'shadow': 0, 'crystal': 0, 'dragon': 0, 'abyss': 0},
        'equipment': [],  # template_idx list
    }

    # 基础金币: 击杀 + 时间 + 等级
    rewards['gold'] += int(run_data.kills * 2)
    rewards['gold'] += int(run_data.game_time / 60 * 15)   # 每分钟15金
    rewards['gold'] += run_data.level * 5

    # 钻石: 仅击杀Boss获得
    rewards['diamond'] += bosses_killed * 10

    # 材料: 来自局内收集 (部分带出)
    for mk in rewards['materials']:
        has = run_data.materials.get(mk, 0)
        rewards['materials'][mk] += has  # 全部带出

    # 副本额外奖励
    if dungeon_info:
        rew = dungeon_info.get('rewards', {})
        for k, v in rew.items():
            if k == 'gold' and isinstance(v, tuple):
                rewards['gold'] += random.randint(v[0], v[1])
            elif k == 'diamond' and isinstance(v, tuple):
                rewards['diamond'] += random.randint(v[0], v[1])
            elif k.startswith('mat_') and isinstance(v, tuple):
                mat_key = k[4:]  # 去掉 mat_ 前缀
                rewards['materials'][mat_key] = rewards['materials'].get(mat_key, 0) + random.randint(v[0], v[1])

    # 随机掉落装备
    equip_roll_count = 1 + bosses_killed
    for _ in range(equip_roll_count):
        if random.random() < 0.4:  # 40%几率掉装备
            rarities = ['common', 'uncommon', 'rare', 'epic', 'legendary']
            weights = [40, 30, 20, 8, 2]
            if dungeon_info:
                diff = dungeon_info.get('difficulty', 1)
                weights = [max(1, 40-diff*5), 30, 20+diff*3, 8+diff*2, 2+diff]
            rewards['equipment'].append(random.choices(rarities, weights=weights)[0])

    return rewards


def apply_settlement(save_data, rewards, equipment_db):
    """将结算奖励写入存档"""
    save_data['gold'] += rewards['gold']
    save_data['diamond'] += rewards['diamond']

    for mk, mv in rewards['materials'].items():
        save_data['meta_materials'][mk] = save_data['meta_materials'].get(mk, 0) + mv

    # 装备 → 实际生成并存入仓库
    for rarity in rewards.get('equipment', []):
        candidates = [i for i, tpl in enumerate(equipment_db) if tpl[2] == rarity]
        if candidates:
            tidx = random.choice(candidates)
            save_data['meta_equipment'].append({
                'template_idx': tidx,
                'level': 1,
                'ascend': 0,
            })
            if tidx not in save_data['codex_equips']:
                save_data['codex_equips'].append(tidx)


# ============================================================
#  绘制函数
# ============================================================

def draw_button(surface, rect, text, color, font=None, hover_check=True):
    """通用按钮绘制"""
    if font is None:
        font = _font_md
    mx, my = pygame.mouse.get_pos()
    hover = rect.collidepoint(mx, my) if hover_check else False
    bs = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    bc = color if hover else tuple(max(0, c - 60) for c in color)
    pygame.draw.rect(bs, (*bc, 80 if hover else 30), (0, 0, rect.w, rect.h), border_radius=8)
    pygame.draw.rect(bs, (*bc, 200 if hover else 100), (0, 0, rect.w, rect.h), 2, border_radius=8)
    surface.blit(bs, rect.topleft)
    bt = _render_outlined(font, text, color)
    surface.blit(bt, (rect.centerx - bt.get_width() // 2, rect.centery - bt.get_height() // 2))
    return hover


# ---- 结算界面 ----
def draw_settlement_screen(surface, rewards, is_victory=False):
    """绘制结算界面, 返回按钮字典"""
    buttons = {}
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))

    # 标题
    title_text = i18n.t("胜 利 !") if is_victory else i18n.t("挑 战 结 束")
    title_color = GOLD if is_victory else RED
    title = _render_outlined(_font_lg, title_text, title_color)
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 40))

    # 奖励列表
    y = 120
    items = [
        (i18n.t("金币: +{gold}", gold=rewards['gold']), GOLD),
        (i18n.t("钻石: +{diamond}", diamond=rewards['diamond']), CYAN),
    ]
    # 材料
    mat_names = {'iron': i18n.material_name('iron'), 'shadow': i18n.material_name('shadow'),
                 'crystal': i18n.material_name('crystal'), 'dragon': i18n.material_name('dragon'),
                 'abyss': i18n.material_name('abyss')}
    for mk, mv in rewards['materials'].items():
        if mv > 0:
            items.append((f"{mat_names.get(mk, mk)}: +{mv}", ORANGE))
    # 装备
    if rewards.get('equipment'):
        rarity_names = {k: i18n.rarity_name(k) for k in ['common', 'uncommon', 'rare', 'epic', 'legendary']}
        rarity_colors = {'common': (200, 200, 200), 'uncommon': (100, 220, 100),
                         'rare': (80, 150, 255), 'epic': (180, 80, 255), 'legendary': (255, 200, 50)}
        for r in rewards['equipment']:
            items.append((i18n.t("获得{rarity}装备!", rarity=rarity_names.get(r, r)), rarity_colors.get(r, WHITE)))

    for txt, color in items:
        rt = _render_outlined(_font_sm, txt, color)
        surface.blit(rt, (WIDTH // 2 - rt.get_width() // 2, y))
        y += 35

    # 按钮
    btn_y = max(y + 40, HEIGHT - 150)
    btn_w, btn_h = 200, 44
    confirm_rect = pygame.Rect(WIDTH // 2 - btn_w // 2, btn_y, btn_w, btn_h)
    draw_button(surface, confirm_rect, i18n.t("确认"), CYAN, _font_md)
    buttons['confirm'] = confirm_rect

    return buttons


# ---- 图鉴界面 ----
def draw_codex_screen(surface, save_data, tab='characters'):
    """绘制图鉴界面, 返回按钮字典"""
    buttons = {}
    surface.fill((8, 8, 14))

    # 标题
    title = _render_outlined(_font_lg, i18n.t("图 鉴"), GOLD)
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 15))

    # 标签页
    tabs = [
        ('characters', i18n.t('角色')),
        ('weapons',    i18n.t('武器')),
        ('enemies',    i18n.t('敌人')),
        ('bosses',     i18n.t('Boss')),
        ('equipment',  i18n.t('装备')),
    ]
    tab_y = 65
    for i, (tk, tname) in enumerate(tabs):
        tx = 40 + i * 120
        trect = pygame.Rect(tx, tab_y, 110, 30)
        active = (tab == tk)
        tc = CYAN if active else (180, 180, 200)
        bs = pygame.Surface((110, 30), pygame.SRCALPHA)
        if active:
            pygame.draw.rect(bs, (*tc, 50), (0, 0, 110, 30), border_radius=5)
        pygame.draw.rect(bs, (*tc, 160 if active else 80), (0, 0, 110, 30), 2, border_radius=5)
        surface.blit(bs, (tx, tab_y))
        tt = _render_outlined(_font_xs, tname, tc)
        surface.blit(tt, (tx + 55 - tt.get_width() // 2, tab_y + 7))
        buttons[('codex_tab', tk)] = trect

    # 内容区
    content_y = 110
    unlocked = save_data

    if tab == 'characters':
        for i, (idx, name, title_str, color, desc) in enumerate(CHARACTER_CODEX):
            row = i // 3
            col = i % 3
            cx = 40 + col * 380
            cy = content_y + row * 180
            card = pygame.Rect(cx, cy, 360, 160)
            is_unlocked = idx in unlocked.get('codex_chars', [])
            pygame.draw.rect(surface, (*color, 18) if is_unlocked else (20, 20, 30), card, border_radius=8)
            pygame.draw.rect(surface, color if is_unlocked else (55, 55, 65), card, 2, border_radius=8)
            if is_unlocked:
                nt = _render_outlined(_font_sm, f"{i18n.t(title_str)}·{i18n.t(name)}", color)
                surface.blit(nt, (cx + 10, cy + 10))
                dt = _render_outlined(_font_xs, i18n.t(desc), (230, 230, 240))
                surface.blit(dt, (cx + 10, cy + 40))
                # 等级
                char_lv = save_data.get('char_levels', {}).get(str(idx), 1)
                lt = _render_outlined(_font_xs, f"Lv.{char_lv}/150", GOLD)
                surface.blit(lt, (cx + 10, cy + 65))
            else:
                lt = _render_outlined(_font_md, "???", (120, 120, 145))
                surface.blit(lt, (cx + 160, cy + 60))

    elif tab == 'weapons':
        for i, (name, color, desc) in enumerate(WEAPON_CODEX):
            row = i // 2
            col = i % 2
            cx = 40 + col * 580
            cy = content_y + row * 100
            card = pygame.Rect(cx, cy, 560, 85)
            is_unlocked = name in unlocked.get('codex_weapons', [])
            pygame.draw.rect(surface, (*color, 15) if is_unlocked else (18, 18, 28), card, border_radius=6)
            pygame.draw.rect(surface, color if is_unlocked else (50, 50, 60), card, 1, border_radius=6)
            if is_unlocked:
                nt = _render_outlined(_font_sm, i18n.t(name), color)
                surface.blit(nt, (cx + 10, cy + 8))
                dt = _render_outlined(_font_xs, i18n.t(desc), (235, 235, 245))
                surface.blit(dt, (cx + 10, cy + 38))
            else:
                lt = _render_outlined(_font_sm, i18n.t("??? 未发现"), (130, 130, 155))
                surface.blit(lt, (cx + 10, cy + 25))

    elif tab == 'enemies':
        for i, (name, color, desc, spec) in enumerate(ENEMY_CODEX):
            row = i // 2
            col = i % 2
            cx = 40 + col * 580
            cy = content_y + row * 85
            card = pygame.Rect(cx, cy, 560, 75)
            is_unlocked = i in unlocked.get('codex_enemies', [])
            pygame.draw.rect(surface, (*color, 12) if is_unlocked else (18, 18, 28), card, border_radius=6)
            pygame.draw.rect(surface, color if is_unlocked else (50, 50, 60), card, 1, border_radius=6)
            if is_unlocked:
                nt = _render_outlined(_font_sm, i18n.t(name), color)
                surface.blit(nt, (cx + 10, cy + 5))
                dt = _render_outlined(_font_xs, i18n.t(desc), (235, 235, 245))
                surface.blit(dt, (cx + 10, cy + 32))
                if spec:
                    st = _render_outlined(_font_xs, i18n.t("特殊: {spec}", spec=i18n.t(spec)), ORANGE)
                    surface.blit(st, (cx + 10, cy + 52))
            else:
                lt = _render_outlined(_font_sm, i18n.t("??? 未遭遇"), (130, 130, 155))
                surface.blit(lt, (cx + 10, cy + 22))

    elif tab == 'bosses':
        for i, (name, title_str, color, desc, hp) in enumerate(BOSS_CODEX):
            cy = content_y + i * 140
            card = pygame.Rect(40, cy, WIDTH - 80, 120)
            is_unlocked = i in unlocked.get('codex_bosses', [])
            pygame.draw.rect(surface, (*color, 15) if is_unlocked else (18, 18, 28), card, border_radius=8)
            pygame.draw.rect(surface, color if is_unlocked else (50, 50, 60), card, 2, border_radius=8)
            if is_unlocked:
                nt = _render_outlined(_font_md, f"{i18n.t(title_str)}·{i18n.t(name)}", color)
                surface.blit(nt, (60, cy + 10))
                dt = _render_outlined(_font_xs, i18n.t(desc), (235, 235, 245))
                surface.blit(dt, (60, cy + 50))
                ht = _render_outlined(_font_xs, i18n.t("基础HP: {hp}", hp=hp), RED)
                surface.blit(ht, (60, cy + 75))
            else:
                lt = _render_outlined(_font_md, i18n.t("??? 未击败"), (130, 130, 155))
                surface.blit(lt, (60, cy + 40))

    elif tab == 'equipment':
        rarity_names = {k: i18n.rarity_name(k) for k in ['common', 'uncommon', 'rare', 'epic', 'legendary']}
        rarity_colors = {'common': (200, 200, 200), 'uncommon': (100, 220, 100),
                         'rare': (80, 150, 255), 'epic': (180, 80, 255), 'legendary': (255, 200, 50)}
        slot_names = {s: i18n.slot_name(s) for s in ['weapon', 'armor', 'accessory', 'rune']}
        # 需要外部传入 equipment_db, 这里先处理
        codex_equips = unlocked.get('codex_equips', [])
        # 这里仅显示已发现的
        from game_main import EQUIPMENT_DB
        for i, tpl in enumerate(EQUIPMENT_DB):
            row = i // 4
            col = i % 4
            cx = 30 + col * 290
            cy = content_y + row * 80
            card = pygame.Rect(cx, cy, 275, 70)
            is_unlocked = i in codex_equips
            rc = rarity_colors.get(tpl[2], WHITE)
            pygame.draw.rect(surface, (*rc, 12) if is_unlocked else (18, 18, 28), card, border_radius=5)
            pygame.draw.rect(surface, rc if is_unlocked else (50, 50, 60), card, 1, border_radius=5)
            if is_unlocked:
                nt = _render_outlined(_font_xs, f"[{rarity_names.get(tpl[2], '')}] {i18n.t(tpl[0])}", rc)
                surface.blit(nt, (cx + 6, cy + 5))
                st = _render_outlined(_font_xs, i18n.t("部位: {slot}", slot=slot_names.get(tpl[1], tpl[1])), (235, 235, 245))
                surface.blit(st, (cx + 6, cy + 25))
                stats_str = " ".join(f"{i18n.stat_name(k)}:{v}" for k, v in tpl[3].items())
                sst = _render_outlined(_font_xs, stats_str, (225, 225, 240))
                surface.blit(sst, (cx + 6, cy + 45))
            else:
                lt = _render_outlined(_font_xs, "???", (130, 130, 155))
                surface.blit(lt, (cx + 120, cy + 25))

    # 收集进度
    total_chars = len(CHARACTER_CODEX)
    total_weaps = len(WEAPON_CODEX)
    total_enem = len(ENEMY_CODEX)
    total_boss = len(BOSS_CODEX)
    total_equip = 20  # EQUIPMENT_DB
    u_chars = len(unlocked.get('codex_chars', []))
    u_weaps = len(unlocked.get('codex_weapons', []))
    u_enem = len(unlocked.get('codex_enemies', []))
    u_boss = len(unlocked.get('codex_bosses', []))
    u_equip = len(unlocked.get('codex_equips', []))
    total = total_chars + total_weaps + total_enem + total_boss + total_equip
    done = u_chars + u_weaps + u_enem + u_boss + u_equip
    pct = int(done / max(1, total) * 100)
    pt = _render_outlined(_font_xs, i18n.t("收集进度: {done}/{total} ({pct}%)", done=done, total=total, pct=pct), GOLD)
    surface.blit(pt, (WIDTH - pt.get_width() - 20, HEIGHT - 60))

    # 返回按钮
    back_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 50, 200, 36)
    draw_button(surface, back_rect, i18n.t("返回"), (200, 200, 220), _font_sm)
    buttons['back'] = back_rect

    return buttons


# ---- 副本选择界面 ----
def draw_dungeon_select(surface, save_data):
    """副本选择界面, 返回按钮字典"""
    buttons = {}
    surface.fill((8, 6, 14))

    title = _render_outlined(_font_lg, i18n.t("副 本 选 择"), ORANGE)
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 20))

    # 金币钻石
    ct = _render_outlined(
        _font_sm,
        i18n.t("金币: {gold}  钻石: {diamond}", gold=save_data.get('gold', 0), diamond=save_data.get('diamond', 0)),
        GOLD,
    )
    surface.blit(ct, (WIDTH // 2 - ct.get_width() // 2, 70))

    total_kills = save_data.get('best_kills', 0)

    for i, dg in enumerate(DUNGEON_LIST):
        row = i // 3
        col = i % 3
        cx = 30 + col * 390
        cy = 110 + row * 310
        card = pygame.Rect(cx, cy, 370, 280)
        unlocked = total_kills >= dg['unlock_need']

        color = dg['color']
        pygame.draw.rect(surface, (*color, 18) if unlocked else (20, 20, 30), card, border_radius=10)
        pygame.draw.rect(surface, color if unlocked else (60, 60, 75), card, 2, border_radius=10)

        if unlocked:
            nt = _render_outlined(_font_md, i18n.t(dg['name']), color)
            surface.blit(nt, (cx + 15, cy + 10))
            # 难度星星
            stars = "★" * dg['difficulty'] + "☆" * (5 - dg['difficulty'])
            st = _render_outlined(_font_xs, i18n.t("难度: {stars}", stars=stars), ORANGE)
            surface.blit(st, (cx + 15, cy + 45))
            # 描述
            desc_txt = i18n.t(dg['desc'])
            desc_parts = [desc_txt[j:j + 20] for j in range(0, len(desc_txt), 20)]
            for j, part in enumerate(desc_parts[:3]):
                dt = _render_outlined(_font_xs, part, (235, 235, 245))
                surface.blit(dt, (cx + 15, cy + 70 + j * 18))
            # 时限
            if dg['time_limit'] > 0:
                tm = dg['time_limit'] // 60
                tlt = _render_outlined(_font_xs, i18n.t("时限: {minutes}分钟", minutes=tm), YELLOW)
            else:
                tlt = _render_outlined(_font_xs, i18n.t("时限: 无限"), RED)
            surface.blit(tlt, (cx + 15, cy + 135))
            # 通关次数
            clears = save_data.get('dungeon_clears', {}).get(dg['id'], 0)
            clt = _render_outlined(_font_xs, i18n.t("通关: {count}次", count=clears), (235, 235, 245))
            surface.blit(clt, (cx + 15, cy + 160))
            # 奖励预览
            rew_parts = []
            for k, v in dg['rewards'].items():
                if isinstance(v, tuple) and v[1] > 0:
                    rn = {'gold': i18n.t('金币'), 'diamond': i18n.t('钻石'),
                          'mat_iron': i18n.material_short('iron'),
                          'mat_shadow': i18n.material_short('shadow'),
                          'mat_crystal': i18n.material_short('crystal'),
                          'mat_dragon': i18n.material_short('dragon'),
                          'mat_abyss': i18n.material_short('abyss')}.get(k, k)
                    rew_parts.append(f"{rn}:{v[0]}-{v[1]}")
                elif isinstance(v, int) and v > 0:
                    rn = {'gold': i18n.t('金币'), 'diamond': i18n.t('钻石')}.get(k, k)
                    rew_parts.append(f"{rn}:{v}")
            if rew_parts:
                rwt = _render_outlined(_font_xs, i18n.t("奖励: ") + " ".join(rew_parts), GOLD)
                surface.blit(rwt, (cx + 15, cy + 185))
            # 进入按钮
            enter_rect = pygame.Rect(cx + 120, cy + 220, 130, 36)
            draw_button(surface, enter_rect, i18n.t("进入"), color, _font_sm)
            buttons[('dungeon', i)] = enter_rect
        else:
            lt = _render_outlined(_font_md, i18n.t("🔒 未解锁"), (140, 140, 165))
            surface.blit(lt, (cx + 100, cy + 100))
            need = _render_outlined(_font_xs, i18n.t("需要累计击杀 {need}", need=dg['unlock_need']), (170, 170, 200))
            surface.blit(need, (cx + 80, cy + 150))

    # 返回
    back_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 50, 200, 36)
    draw_button(surface, back_rect, i18n.t("返回"), (200, 200, 220), _font_sm)
    buttons['back'] = back_rect
    return buttons


# ---- 角色升级界面 ----
def draw_char_upgrade_screen(surface, save_data, selected_char=0, equipment_db=None, equip_scroll=0):
    """角色局外升级界面, 返回按钮字典"""
    buttons = {}
    hover_tooltip = None  # (text_lines, x, y)
    surface.fill((8, 8, 14))

    title = _render_outlined(_font_lg, i18n.t("角色升级"), CYAN)
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 15))

    # 货币
    ct = _render_outlined(
        _font_sm,
        i18n.t("金币: {gold}  钻石: {diamond}", gold=save_data.get('gold', 0), diamond=save_data.get('diamond', 0)),
        GOLD,
    )
    surface.blit(ct, (WIDTH // 2 - ct.get_width() // 2, 60))

    mx, my = pygame.mouse.get_pos()

    # 角色选项卡
    unlocked_chars = save_data.get('unlocked_chars', [0])
    for i, (idx, name, title_str, color, _) in enumerate(CHARACTER_CODEX):
        tx = 20 + i * 190
        trect = pygame.Rect(tx, 95, 180, 32)
        active = (selected_char == i)
        is_char_unlocked = idx in unlocked_chars
        tc = color if active else (170, 170, 190) if is_char_unlocked else (80, 80, 100)
        bs = pygame.Surface((180, 32), pygame.SRCALPHA)
        pygame.draw.rect(bs, (*tc, 40 if active else 15), (0, 0, 180, 32), border_radius=5)
        pygame.draw.rect(bs, (*tc, 160 if active else 70), (0, 0, 180, 32), 2, border_radius=5)
        surface.blit(bs, (tx, 95))
        label = f"{i18n.t(title_str)}·{i18n.t(name)}" if is_char_unlocked else f"🔒 {i18n.t(name)}"
        nt = _render_outlined(_font_xs, label, tc)
        surface.blit(nt, (tx + 90 - nt.get_width() // 2, 100))
        buttons[('char_tab', i)] = trect

    # 选中角色信息
    cidx = selected_char
    cinfo = CHARACTER_CODEX[cidx]
    real_idx, cname, ctitle, ccolor, cdesc = cinfo
    is_selected_unlocked = real_idx in unlocked_chars
    char_lv = int(save_data.get('char_levels', {}).get(str(cidx), 1))
    char_asc = int(save_data.get('char_ascend', {}).get(str(cidx), 0))

    # 角色大卡
    info_y = 145
    panel = pygame.Rect(30, info_y, 500, 350)
    pygame.draw.rect(surface, (*ccolor, 12), panel, border_radius=10)
    pygame.draw.rect(surface, ccolor, panel, 2, border_radius=10)

    nt = _render_outlined(_font_md, f"{i18n.t(ctitle)}·{i18n.t(cname)}", ccolor)
    surface.blit(nt, (50, info_y + 10))

    # 角色形象预览 (右上角)
    char_preview_x = 430
    char_preview_y = info_y + 80
    try:
        temp_char = characters.create_character(cidx, char_preview_x, char_preview_y)
        temp_char.anim_timer = pygame.time.get_ticks() / 1000.0
        temp_char.draw(surface, (0, 0))
    except Exception:
        pygame.draw.circle(surface, ccolor, (char_preview_x, char_preview_y), 20)
        pygame.draw.circle(surface, WHITE, (char_preview_x, char_preview_y), 20, 2)

    # 初始武器图标
    widx = CHAR_STARTER_WEAPON.get(cidx, 0)
    wname, wcolor_w, _ = WEAPON_CODEX[widx]
    _draw_weapon_icon(surface, char_preview_x, char_preview_y + 40, widx, 18)
    wnt = _render_outlined(_font_xs, i18n.t(wname), wcolor_w)
    surface.blit(wnt, (char_preview_x - wnt.get_width() // 2, char_preview_y + 55))

    if not is_selected_unlocked:
        # 未解锁角色 - 显示解锁条件
        lock_overlay = pygame.Surface((500, 350), pygame.SRCALPHA)
        lock_overlay.fill((0, 0, 0, 120))
        surface.blit(lock_overlay, (30, info_y))
        lt = _render_outlined(_font_md, i18n.t("🔒 角色未解锁"), (180, 80, 80))
        surface.blit(lt, (150, info_y + 100))
        cond = CHAR_UNLOCK_CONDITIONS.get(real_idx, {})
        cond_desc = i18n.t(cond.get('desc', '未知'))
        ct2 = _render_outlined(_font_sm, i18n.t("解锁条件: {cond}", cond=cond_desc), (200, 200, 220))
        surface.blit(ct2, (150, info_y + 145))
        best = save_data.get('best_kills', 0)
        need = cond.get('need', 0)
        pt = _render_outlined(_font_xs, i18n.t("当前进度: {best}/{need}", best=best, need=need), GOLD)
        surface.blit(pt, (150, info_y + 180))
    else:
        lt = _render_outlined(_font_sm, f"Lv.{char_lv} / 150   {i18n.t('进阶')}:{char_asc}", GOLD)
        surface.blit(lt, (50, info_y + 50))

        # 属性加成
        bonus = get_char_stat_bonus(char_lv)
        stat_cn = {'max_health': i18n.t('生命'), 'dmg_bonus': i18n.t('伤害%'), 'armor': i18n.t('护甲'),
                   'crit': i18n.t('暴击%'), 'speed_mult': i18n.t('速度%')}
        sy = info_y + 85
        for sk, sv in bonus.items():
            sn = stat_cn.get(sk, sk)
            sv_str = f"+{sv}" if isinstance(sv, int) else f"+{sv*100:.1f}%"
            st = _render_outlined(_font_xs, f"{sn}: {sv_str}", (240, 245, 255))
            surface.blit(st, (50, sy))
            sy += 22

        # 已装备的局外装备显示
        if equipment_db:
            char_eq = get_char_equipped(save_data, cidx, equipment_db)
            slot_cn = {s: i18n.slot_name(s) for s in ['weapon', 'armor', 'accessory', 'rune']}
            rarity_colors = {'common': (200,200,200), 'uncommon': (100,220,100),
                             'rare': (80,150,255), 'epic': (180,80,255), 'legendary': (255,200,50)}
            eq_y = info_y + 200
            et_label = _render_outlined(_font_xs, i18n.t("已装备:"), (200, 200, 220))
            surface.blit(et_label, (50, eq_y))
            eq_y += 20
            for slot in ['weapon', 'armor', 'accessory', 'rune']:
                slot_rect = pygame.Rect(50, eq_y, 200, 20)
                if slot in char_eq:
                    widx, tpl, eq_lv = char_eq[slot]
                    rc = rarity_colors.get(tpl[2], WHITE)
                    txt = f"{slot_cn[slot]}: {i18n.t(tpl[0])} Lv.{eq_lv}"
                    st = _render_outlined(_font_xs, txt, rc)
                    surface.blit(st, (50, eq_y))
                    # hover tooltip
                    if slot_rect.inflate(100, 4).collidepoint(mx, my):
                        stat_cn2 = {
                            'dmg_bonus': i18n.t('伤害'), 'crit': i18n.t('暴击'), 'crit_dmg': i18n.t('暴伤'),
                            'max_health': i18n.t('生命'), 'armor': i18n.t('护甲'), 'regen': i18n.t('回复'),
                            'speed_mult': i18n.t('速度'), 'dodge': i18n.t('闪避'), 'pickup': i18n.t('拾取'),
                            'cdr': i18n.t('冷却'), 'exp_mult': i18n.t('经验'), 'lifesteal': i18n.t('吸血'),
                        }
                        mult = 1.0 + (eq_lv - 1) * 0.03
                        lines = [f"[{i18n.t(tpl[0])}] Lv.{eq_lv}"]
                        for k, v in tpl[3].items():
                            bv = round(v * mult, 3) if isinstance(v, float) else int(v * mult)
                            kn = stat_cn2.get(k, k)
                            lines.append(f"  {kn}: +{bv}")
                        hover_tooltip = (lines, mx + 15, my)
                    # 卸下按钮
                    ubtn = pygame.Rect(260, eq_y, 50, 18)
                    draw_button(surface, ubtn, i18n.t("卸下"), (200, 100, 100), _font_xs)
                    buttons[('unequip', slot)] = ubtn
                else:
                    st = _render_outlined(_font_xs, f"{slot_cn[slot]}: {i18n.t('-- 空 --')}", (100, 100, 130))
                    surface.blit(st, (50, eq_y))
                eq_y += 22

        # 需要进阶?
        need_ascend = (char_lv > 0 and char_lv % 10 == 0 and char_asc < char_lv // 10)

        # 升级按钮
        btn_y = info_y + 310
        if char_lv < 150:
            if need_ascend:
                asc_tier = char_asc
                gold_cost, dia_cost, mat_cost = get_char_ascend_cost(asc_tier)
                at = _render_outlined(
                    _font_xs,
                    i18n.t("需要进阶(阶{tier}) 金:{gold} 钻:{diamond}", tier=asc_tier + 1, gold=gold_cost, diamond=dia_cost),
                    ORANGE,
                )
                surface.blit(at, (50, btn_y))
                # 显示材料消耗
                mat_cn = {
                    'iron': i18n.material_short('iron'),
                    'shadow': i18n.material_short('shadow'),
                    'crystal': i18n.material_short('crystal'),
                    'dragon': i18n.material_short('dragon'),
                    'abyss': i18n.material_short('abyss'),
                }
                mat_clr = {'iron': (180,180,200), 'shadow': (160,60,200), 'crystal': (80,180,255),
                           'dragon': (230,170,50), 'abyss': (220,40,80)}
                mat_x = 50
                for mk, mv in mat_cost.items():
                    have = save_data.get('meta_materials', {}).get(mk, 0)
                    enough = have >= mv
                    mc = mat_clr.get(mk, ORANGE)
                    mtxt = f"{mat_cn.get(mk, mk)}:{have}/{mv}"
                    mt_r = _render_outlined(_font_xs, mtxt, mc if enough else (180, 60, 60))
                    surface.blit(mt_r, (mat_x, btn_y + 16))
                    mat_x += mt_r.get_width() + 12
                can_asc = (save_data.get('gold',0) >= gold_cost and
                           save_data.get('diamond',0) >= dia_cost and
                           all(save_data.get('meta_materials',{}).get(m,0)>=c for m,c in mat_cost.items()))
                asc_rect = pygame.Rect(50, btn_y + 34, 130, 30)
                draw_button(surface, asc_rect, i18n.t("进阶"), ORANGE if can_asc else (80,80,80), _font_sm)
                if can_asc:
                    buttons['char_ascend'] = asc_rect
            else:
                gold_cost = get_char_level_cost(char_lv)
                can_up = save_data.get('gold',0) >= gold_cost
                ut = _render_outlined(_font_xs, i18n.t("升级: {gold}金币", gold=gold_cost), GOLD)
                surface.blit(ut, (50, btn_y))
                up_rect = pygame.Rect(50, btn_y + 20, 100, 30)
                draw_button(surface, up_rect, i18n.t("升级"), GREEN if can_up else (80,80,80), _font_sm)
                if can_up:
                    buttons['char_levelup'] = up_rect
                cost10 = sum(get_char_level_cost(char_lv + j) for j in range(min(10, 150 - char_lv))
                             if (char_lv + j) % 10 != 0 or char_asc >= (char_lv + j) // 10)
                if cost10 > 0 and save_data.get('gold',0) >= cost10:
                    up10_rect = pygame.Rect(170, btn_y + 20, 140, 30)
                    draw_button(surface, up10_rect, f"x10({cost10})", GREEN, _font_sm)
                    buttons['char_levelup10'] = up10_rect
        else:
            mt = _render_outlined(_font_sm, i18n.t("已满级!"), GOLD)
            surface.blit(mt, (50, btn_y))

    # ---- 右侧: 装备仓库 (可穿戴) ----
    right_x = 560
    et = _render_outlined(_font_sm, i18n.t("装备仓库 (点击装备到当前角色)"), YELLOW)
    surface.blit(et, (right_x, info_y + 5))

    # ---- 批量出售按钮组 ----
    sell_filter_options = [
        ('sell_keep_leg',  i18n.t('保留传说'),   ['legendary']),
        ('sell_keep_ep',   i18n.t('保留史诗+'),  ['epic', 'legendary']),
        ('sell_keep_rare', i18n.t('保留稀有+'),  ['rare', 'epic', 'legendary']),
    ]
    sell_bx = right_x + 330
    sell_label = _render_outlined(_font_xs, i18n.t("快速出售:"), (220, 160, 80))
    surface.blit(sell_label, (sell_bx, info_y + 6))
    for si, (sell_key, sell_text, keep_list) in enumerate(sell_filter_options):
        s_count, s_gold = count_sellable_equipment(save_data, equipment_db, keep_list)
        sbx = sell_bx + si * 115
        sby = info_y + 24
        sb_rect = pygame.Rect(sbx, sby, 110, 32)
        if s_count > 0:
            # 有可出售的
            btn_col = (200, 100, 60)
            draw_button(surface, sb_rect, sell_text, btn_col, _font_xs)
            # 显示数量和金额
            count_txt = _render_outlined(_font_xs, i18n.t("{count}件→{gold}金", count=s_count, gold=s_gold), (255, 200, 100))
            surface.blit(count_txt, (sbx + 2, sby + 17))
            buttons[('batch_sell', sell_key)] = sb_rect
        else:
            # 灰色不可点
            draw_button(surface, sb_rect, sell_text, (60, 60, 70), _font_xs, hover_check=False)
            no_txt = _render_outlined(_font_xs, i18n.t("无可售"), (100, 100, 110))
            surface.blit(no_txt, (sbx + 30, sby + 17))

    meta_equips = save_data.get('meta_equipment', [])
    slot_names = {s: i18n.slot_name(s) for s in ['weapon', 'armor', 'accessory', 'rune']}
    rarity_colors = {'common': (200,200,200), 'uncommon': (100,220,100),
                     'rare': (80,150,255), 'epic': (180,80,255), 'legendary': (255,200,50)}
    rarity_names = {k: i18n.rarity_name(k) for k in ['common', 'uncommon', 'rare', 'epic', 'legendary']}

    # 检查哪些装备已被穿戴
    all_equipped_idxs = set()
    me = save_data.get('meta_equipped', {})
    for ck, cv in me.items():
        for s, wi in cv.items():
            all_equipped_idxs.add(wi)

    # 分页显示, 每页14件
    page_size = 14
    total_equips = len(meta_equips)
    max_scroll = max(0, total_equips - page_size)
    equip_scroll = min(equip_scroll, max_scroll)
    visible = meta_equips[equip_scroll:equip_scroll + page_size]

    for i, meq in enumerate(visible):
        if equipment_db is None:
            break
        real_idx = equip_scroll + i
        tidx = meq.get('template_idx', 0)
        if tidx >= len(equipment_db):
            continue
        tpl = equipment_db[tidx]
        eq_lv = meq.get('level', 1)
        row = i // 2
        col = i % 2
        ex = right_x + col * 310
        ey = info_y + 28 + row * 44
        erect = pygame.Rect(ex, ey, 295, 40)
        rc = rarity_colors.get(tpl[2], WHITE)
        is_worn = real_idx in all_equipped_idxs

        # 品质特效背景
        bg_alpha = 15 if not is_worn else 25
        pygame.draw.rect(surface, (*rc, bg_alpha), erect, border_radius=4)
        border_w = 2 if is_worn else 1
        pygame.draw.rect(surface, rc, erect, border_w, border_radius=4)

        # 品质标识小点
        rarity_idx = ['common','uncommon','rare','epic','legendary'].index(tpl[2])
        for dot_i in range(rarity_idx + 1):
            dot_x = ex + 6 + dot_i * 8
            pygame.draw.circle(surface, rc, (dot_x, ey + 36), 2)

        nt = _render_outlined(_font_xs, f"{i18n.t(tpl[0])} Lv.{eq_lv}", rc)
        surface.blit(nt, (ex + 6, ey + 3))
        sns = slot_names.get(tpl[1], tpl[1])
        rn = rarity_names.get(tpl[2], '')
        st = _render_outlined(_font_xs, f"{sns} [{rn}]", (220, 220, 235))
        surface.blit(st, (ex + 6, ey + 20))

        # 已穿戴标记
        if is_worn:
            worn_label = _render_outlined(_font_xs, i18n.t("已装备"), GREEN)
            surface.blit(worn_label, (ex + 200, ey + 3))

        # 穿戴/升级按钮
        if is_selected_unlocked and not is_worn:
            eq_btn = pygame.Rect(ex + 200, ey + 2, 55, 18)
            draw_button(surface, eq_btn, i18n.t("穿戴"), rc, _font_xs)
            buttons[('meta_equip', real_idx)] = eq_btn

        eq_cost = get_meta_equip_level_cost(eq_lv, tpl[2])
        if eq_lv < 150 and eq_cost > 0:
            can = save_data.get('gold', 0) >= eq_cost
            up_btn = pygame.Rect(ex + 200, ey + 22, 80, 16)
            draw_button(surface, up_btn, f"↑{eq_cost}", GREEN if can else (60,60,60), _font_xs)
            if can:
                buttons[('equip_up', real_idx)] = up_btn

        # hover tooltip
        if erect.collidepoint(mx, my):
            stat_cn = {
                'dmg_bonus': i18n.t('伤害'), 'crit': i18n.t('暴击'), 'crit_dmg': i18n.t('暴伤'),
                'max_health': i18n.t('生命'), 'armor': i18n.t('护甲'), 'regen': i18n.t('回复'),
                'speed_mult': i18n.t('速度'), 'dodge': i18n.t('闪避'), 'pickup': i18n.t('拾取'),
                'cdr': i18n.t('冷却'), 'exp_mult': i18n.t('经验'), 'lifesteal': i18n.t('吸血'),
            }
            mult = 1.0 + (eq_lv - 1) * 0.03
            lines = [f"[{rn}] {i18n.t(tpl[0])}  Lv.{eq_lv}", i18n.t("部位: {slot}", slot=sns)]
            for k, v in tpl[3].items():
                bv = round(v * mult, 3) if isinstance(v, float) else int(v * mult)
                kn = stat_cn.get(k, k)
                lines.append(f"  {kn}: +{bv}")
            hover_tooltip = (lines, mx + 15, my)

    # 翻页按钮
    if equip_scroll > 0:
        prev_btn = pygame.Rect(right_x + 200, info_y + page_size // 2 * 44 + 36, 80, 24)
        draw_button(surface, prev_btn, i18n.t("◀上页"), (180,180,200), _font_xs)
        buttons['equip_prev'] = prev_btn
    if equip_scroll + page_size < total_equips:
        next_btn = pygame.Rect(right_x + 290, info_y + page_size // 2 * 44 + 36, 80, 24)
        draw_button(surface, next_btn, i18n.t("下页▶"), (180,180,200), _font_xs)
        buttons['equip_next'] = next_btn

    pg_text = _render_outlined(_font_xs, f"{equip_scroll+1}-{min(equip_scroll+page_size, total_equips)}/{total_equips}", (160,160,180))
    surface.blit(pg_text, (right_x + 400, info_y + page_size // 2 * 44 + 40))

    # 材料显示
    mi_y = HEIGHT - 70
    mat_names = {
        'iron': i18n.material_short('iron'),
        'shadow': i18n.material_short('shadow'),
        'crystal': i18n.material_short('crystal'),
        'dragon': i18n.material_short('dragon'),
        'abyss': i18n.material_short('abyss'),
    }
    mat_colors = {'iron': (180, 180, 200), 'shadow': (160, 60, 200), 'crystal': (80, 180, 255),
                  'dragon': (230, 170, 50), 'abyss': (220, 40, 80)}
    mmx = 20
    for mk in ['iron', 'shadow', 'crystal', 'dragon', 'abyss']:
        cnt = save_data.get('meta_materials', {}).get(mk, 0)
        mnt = _render_outlined(_font_xs, f"{mat_names[mk]}:{cnt}", mat_colors[mk])
        surface.blit(mnt, (mmx, mi_y))
        mmx += 120

    # 返回
    back_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 45, 200, 36)
    draw_button(surface, back_rect, i18n.t("返回"), (200, 200, 220), _font_sm)
    buttons['back'] = back_rect

    # ---- 绘制悬浮提示 (最后绘制, 在最上层) ----
    if hover_tooltip:
        lines, tx, ty = hover_tooltip
        tw = max(len(l) * 9 + 20 for l in lines)
        th = len(lines) * 18 + 12
        # 防止超出屏幕
        if tx + tw > WIDTH:
            tx = WIDTH - tw - 5
        if ty + th > HEIGHT:
            ty = HEIGHT - th - 5
        tip_surf = pygame.Surface((tw, th), pygame.SRCALPHA)
        pygame.draw.rect(tip_surf, (10, 10, 20, 230), (0, 0, tw, th), border_radius=6)
        pygame.draw.rect(tip_surf, (200, 200, 220, 180), (0, 0, tw, th), 2, border_radius=6)
        for li, line in enumerate(lines):
            color = GOLD if li == 0 else (230, 230, 240)
            lt = _render_outlined(_font_xs, line, color)
            tip_surf.blit(lt, (8, 6 + li * 18))
        surface.blit(tip_surf, (tx, ty))

    return buttons


# ---- 抽卡界面 ----
def draw_gacha_screen(surface, save_data, gacha_results=None):
    """抽卡界面, 返回按钮字典"""
    buttons = {}
    surface.fill((8, 5, 14))

    title = _render_outlined(_font_lg, i18n.t("装备召唤"), PURPLE)
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 20))

    # 货币
    ct = _render_outlined(
        _font_sm,
        i18n.t("金币: {gold}  钻石: {diamond}", gold=save_data.get('gold', 0), diamond=save_data.get('diamond', 0)),
        GOLD,
    )
    surface.blit(ct, (WIDTH // 2 - ct.get_width() // 2, 70))

    # 两个卡池
    pools = [
        ('normal', i18n.t('常规召唤'), GOLD, i18n.t("消耗金币"),
         i18n.t("单抽: {c1}  十连: {c10}", c1=NORMAL_GACHA_COST, c10=NORMAL_GACHA_10_COST),
         i18n.t("普通50% 优秀30% 稀有15% 史诗4% 传说1%"),
         i18n.t("保底: {pity}抽必得史诗", pity=PITY_NORMAL_EPIC)),
        ('super', i18n.t('超级召唤'), CYAN, i18n.t("消耗钻石 (仅Boss掉钻石)"),
         i18n.t("单抽: {c1}  十连: {c10}", c1=SUPER_GACHA_COST, c10=SUPER_GACHA_10_COST),
         i18n.t("普通10% 优秀25% 稀有35% 史诗22% 传说8%"),
         i18n.t("保底: {pity}抽必得传说", pity=PITY_SUPER_LEGENDARY)),
    ]

    for pi, (pool_key, pool_name, color, sub, cost_str, rate_str, pity_str) in enumerate(pools):
        px = 40 + pi * 580
        py = 110
        pw, ph = 550, 280
        panel = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(surface, (*color, 12), panel, border_radius=10)
        pygame.draw.rect(surface, color, panel, 2, border_radius=10)

        nt = _render_outlined(_font_md, pool_name, color)
        surface.blit(nt, (px + pw // 2 - nt.get_width() // 2, py + 10))
        st = _render_outlined(_font_xs, sub, (240, 240, 248))
        surface.blit(st, (px + pw // 2 - st.get_width() // 2, py + 45))
        cst = _render_outlined(_font_xs, cost_str, GOLD)
        surface.blit(cst, (px + pw // 2 - cst.get_width() // 2, py + 70))
        rt = _render_outlined(_font_xs, rate_str, (235, 235, 245))
        surface.blit(rt, (px + pw // 2 - rt.get_width() // 2, py + 95))
        pit = _render_outlined(_font_xs, pity_str, ORANGE)
        surface.blit(pit, (px + pw // 2 - pit.get_width() // 2, py + 118))

        # 当前保底计数
        pity_key = f'gacha_pity_{pool_key}'
        pity_now = save_data.get(pity_key, 0)
        pity_max = PITY_NORMAL_EPIC if pool_key == 'normal' else PITY_SUPER_LEGENDARY
        pt = _render_outlined(_font_xs, i18n.t("已抽: {now}/{max}", now=pity_now, max=pity_max), (235, 235, 245))
        surface.blit(pt, (px + pw // 2 - pt.get_width() // 2, py + 142))

        # 角色装饰形象 (卡池展示)
        showcase_chars = [0, 3, 5] if pi == 0 else [1, 2, 4]
        for sci, sc_idx in enumerate(showcase_chars):
            sc_x = px + 60 + sci * 160
            sc_y = py + 250
            try:
                sc_char = characters.create_character(sc_idx, sc_x, sc_y)
                sc_char.anim_timer = pygame.time.get_ticks() / 1000.0 + sci * 0.5
                sc_char.draw(surface, (0, 0))
            except Exception:
                pass
            # 武器图标
            sc_widx = CHAR_STARTER_WEAPON.get(sc_idx, 0)
            _draw_weapon_icon(surface, sc_x, sc_y + 30, sc_widx, 12)

        # 按钮
        pull1_rect = pygame.Rect(px + 40, py + 175, 200, 40)
        pull10_rect = pygame.Rect(px + 280, py + 175, 220, 40)

        if pool_key == 'normal':
            can1 = save_data.get('gold', 0) >= NORMAL_GACHA_COST
            can10 = save_data.get('gold', 0) >= NORMAL_GACHA_10_COST
        else:
            can1 = save_data.get('diamond', 0) >= SUPER_GACHA_COST
            can10 = save_data.get('diamond', 0) >= SUPER_GACHA_10_COST

        draw_button(surface, pull1_rect, i18n.t("单抽"), color if can1 else (60, 60, 60), _font_sm)
        draw_button(surface, pull10_rect, i18n.t("十连抽!"), color if can10 else (60, 60, 60), _font_sm)
        if can1:
            buttons[(pool_key, 'pull1')] = pull1_rect
        if can10:
            buttons[(pool_key, 'pull10')] = pull10_rect

    # 抽卡结果
    if gacha_results:
        ry = 420
        result_title = _render_outlined(_font_sm, i18n.t("— 召唤结果 —"), GOLD)
        surface.blit(result_title, (WIDTH // 2 - result_title.get_width() // 2, ry))
        ry += 35
        rarity_names = {k: i18n.rarity_name(k) for k in ['common', 'uncommon', 'rare', 'epic', 'legendary']}
        rarity_colors = {'common': (200, 200, 200), 'uncommon': (100, 220, 100),
                         'rare': (80, 150, 255), 'epic': (180, 80, 255), 'legendary': (255, 200, 50)}
        from game_main import EQUIPMENT_DB
        for i, (tidx, rarity) in enumerate(gacha_results):
            col = i % 5
            row = i // 5
            rx = 80 + col * 220
            ry2 = ry + row * 60
            tpl = EQUIPMENT_DB[tidx]
            rc = rarity_colors.get(rarity, WHITE)
            card_rect = pygame.Rect(rx, ry2, 200, 50)
            pygame.draw.rect(surface, (*rc, 15), card_rect, border_radius=5)
            pygame.draw.rect(surface, rc, card_rect, 1, border_radius=5)
            # 品质小点
            rarity_i = ['common','uncommon','rare','epic','legendary'].index(rarity) if rarity in ['common','uncommon','rare','epic','legendary'] else 0
            for dot_j in range(rarity_i + 1):
                pygame.draw.circle(surface, rc, (rx + 8 + dot_j * 7, ry2 + 46), 2)
            # 装备部位图标
            slot_icon_map = {'weapon': 3, 'armor': 5, 'accessory': 0, 'rune': 2}
            slot_widx = slot_icon_map.get(tpl[1], 0)
            _draw_weapon_icon(surface, rx + 185, ry2 + 25, slot_widx, 12)
            nt = _render_outlined(_font_xs, f"[{rarity_names.get(rarity, '')}] {i18n.t(tpl[0])}", rc)
            surface.blit(nt, (rx + 6, ry2 + 6))
            stats_str = " ".join(f"{i18n.stat_name(k)}:{v}" for k, v in tpl[3].items())
            st = _render_outlined(_font_xs, stats_str, (235, 235, 245))
            surface.blit(st, (rx + 6, ry2 + 28))

    # 返回
    back_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 50, 200, 36)
    draw_button(surface, back_rect, i18n.t("返回"), (200, 200, 220), _font_sm)
    buttons['back'] = back_rect

    return buttons
