"""
《暗夜割草者：深渊轮回》 — NPC对话系统
========================================
本地离线对话系统，基于预设对话树 + 上下文感知
========================================
"""

import pygame
import random
import math
import i18n

# ============================================================
#  引用 (由 init() 注入)
# ============================================================
_screen = None
_font_lg = _font_md = _font_sm = _font_xs = None
WIDTH = 1200
HEIGHT = 800

WHITE  = (255, 255, 255)
BLACK  = (0, 0, 0)
CYAN   = (0, 220, 255)
GOLD   = (255, 215, 0)
GREEN  = (50, 255, 50)
RED    = (255, 68, 68)
PURPLE = (180, 60, 255)
ORANGE = (255, 165, 0)
PINK   = (255, 100, 180)
YELLOW = (255, 255, 80)


def init(screen, font_lg, font_md, font_sm, font_xs, width=1200, height=800):
    global _screen, _font_lg, _font_md, _font_sm, _font_xs, WIDTH, HEIGHT
    _screen = screen
    _font_lg = font_lg
    _font_md = font_md
    _font_sm = font_sm
    _font_xs = font_xs
    WIDTH = width
    HEIGHT = height


def _render_outlined(font, text, color, outline_color=(0, 0, 0), offset=2):
    """带黑色描边的文字渲染"""
    base = font.render(text, True, color)
    outline = font.render(text, True, outline_color)
    surf = pygame.Surface((base.get_width() + offset*2, base.get_height() + offset*2), pygame.SRCALPHA)
    for dx in range(-offset, offset+1):
        for dy in range(-offset, offset+1):
            if dx == 0 and dy == 0:
                continue
            surf.blit(outline, (dx + offset, dy + offset))
    surf.blit(base, (offset, offset))
    return surf


# ============================================================
#  NPC 定义
# ============================================================

class NPC:
    """NPC角色定义"""
    def __init__(self, npc_id, name, title, color, avatar_fn=None):
        self.npc_id = npc_id
        self.name = name
        self.title = title
        self.color = color
        self.avatar_fn = avatar_fn  # 绘制头像的函数

    def draw_avatar(self, surface, x, y, size=40):
        """绘制NPC头像"""
        if self.avatar_fn:
            self.avatar_fn(surface, x, y, size)
        else:
            pygame.draw.circle(surface, self.color, (x, y), size)
            pygame.draw.circle(surface, WHITE, (x, y), size, 2)


def _draw_merchant_avatar(surface, x, y, size):
    """商人头像"""
    # 身体
    pygame.draw.circle(surface, (180, 140, 80), (x, y), size)
    # 帽子
    pygame.draw.polygon(surface, (120, 80, 40),
                        [(x - size, y - size//2), (x, y - size - 10), (x + size, y - size//2)])
    # 眼睛
    pygame.draw.circle(surface, WHITE, (x - 8, y - 5), 5)
    pygame.draw.circle(surface, WHITE, (x + 8, y - 5), 5)
    pygame.draw.circle(surface, BLACK, (x - 8, y - 5), 2)
    pygame.draw.circle(surface, BLACK, (x + 8, y - 5), 2)
    # 微笑
    pygame.draw.arc(surface, (80, 40, 20), (x - 10, y, 20, 12), 3.14, 6.28, 2)
    pygame.draw.circle(surface, WHITE, (x, y), size, 2)


def _draw_elder_avatar(surface, x, y, size):
    """长老头像"""
    pygame.draw.circle(surface, (100, 80, 140), (x, y), size)
    # 第三只眼
    pygame.draw.circle(surface, PURPLE, (x, y - size//2), 6)
    pygame.draw.circle(surface, WHITE, (x, y - size//2), 6, 1)
    # 胡子
    for i in range(5):
        bx = x - 12 + i * 6
        pygame.draw.line(surface, (200, 200, 220), (bx, y + 8), (bx, y + size - 5), 2)
    # 眼睛
    pygame.draw.circle(surface, (200, 180, 255), (x - 10, y - 3), 5)
    pygame.draw.circle(surface, (200, 180, 255), (x + 10, y - 3), 5)
    pygame.draw.circle(surface, BLACK, (x - 10, y - 3), 2)
    pygame.draw.circle(surface, BLACK, (x + 10, y - 3), 2)
    pygame.draw.circle(surface, WHITE, (x, y), size, 2)


def _draw_blacksmith_avatar(surface, x, y, size):
    """铁匠头像"""
    pygame.draw.circle(surface, (180, 100, 60), (x, y), size)
    # 锤子
    pygame.draw.rect(surface, (150, 150, 170), (x + size//2, y - size, 8, size))
    pygame.draw.rect(surface, (180, 180, 200), (x + size//2 - 4, y - size - 4, 16, 10))
    # 粗眉
    pygame.draw.line(surface, (60, 30, 10), (x - 16, y - 10), (x - 4, y - 12), 3)
    pygame.draw.line(surface, (60, 30, 10), (x + 4, y - 12), (x + 16, y - 10), 3)
    # 眼睛
    pygame.draw.circle(surface, WHITE, (x - 10, y - 3), 4)
    pygame.draw.circle(surface, WHITE, (x + 10, y - 3), 4)
    pygame.draw.circle(surface, BLACK, (x - 10, y - 3), 2)
    pygame.draw.circle(surface, BLACK, (x + 10, y - 3), 2)
    pygame.draw.circle(surface, WHITE, (x, y), size, 2)


def _draw_witch_avatar(surface, x, y, size):
    """女巫头像"""
    pygame.draw.circle(surface, (60, 40, 80), (x, y), size)
    # 尖帽子
    pygame.draw.polygon(surface, (40, 20, 60),
                        [(x - size + 5, y - size//2 + 5), (x, y - size - 18), (x + size - 5, y - size//2 + 5)])
    star_color = (200, 150, 255)
    pygame.draw.circle(surface, star_color, (x - 3, y - size + 2), 3)
    # 眼睛 (发光)
    pygame.draw.circle(surface, (180, 100, 255), (x - 10, y - 3), 6)
    pygame.draw.circle(surface, WHITE, (x - 10, y - 3), 3)
    pygame.draw.circle(surface, (180, 100, 255), (x + 10, y - 3), 6)
    pygame.draw.circle(surface, WHITE, (x + 10, y - 3), 3)
    pygame.draw.circle(surface, (180, 100, 255), (x, y), size, 2)


# NPC 实例
NPCS = {
    'merchant':   NPC('merchant',   '旅行商人·马库斯', '深渊行商', GOLD, _draw_merchant_avatar),
    'elder':      NPC('elder',      '暗夜长老·瑟拉斯', '先知', PURPLE, _draw_elder_avatar),
    'blacksmith': NPC('blacksmith', '铁匠·布鲁诺', '锻造大师', ORANGE, _draw_blacksmith_avatar),
    'witch':      NPC('witch',      '神秘女巫·伊薇', '命运编织者', PINK, _draw_witch_avatar),
}


# ============================================================
#  对话内容数据库 (上下文感知)
# ============================================================

def _get_context_tags(save_data):
    """根据存档数据生成上下文标签"""
    tags = set()
    kills = save_data.get('best_kills', 0)
    runs = save_data.get('total_runs', 0)
    gold = save_data.get('gold', 0)
    souls = save_data.get('soul_shards', 0)
    equip_count = len(save_data.get('meta_equipment', []))

    if runs == 0:
        tags.add('first_time')
    elif runs <= 3:
        tags.add('newbie')
    elif runs <= 10:
        tags.add('experienced')
    else:
        tags.add('veteran')

    if kills >= 1000:
        tags.add('elite_killer')
    elif kills >= 500:
        tags.add('skilled')
    elif kills >= 100:
        tags.add('decent')

    if gold >= 50000:
        tags.add('rich')
    elif gold <= 100:
        tags.add('poor')

    if equip_count >= 10:
        tags.add('well_equipped')
    elif equip_count == 0:
        tags.add('no_equipment')

    if souls >= 1000:
        tags.add('soul_rich')

    unlocked = save_data.get('unlocked_chars', [0])
    if len(unlocked) >= 4:
        tags.add('many_chars')

    return tags


# 每个NPC的对话数据库
# 格式: (优先级标签集合, 对话行列表, 选项列表)
#   标签集合: 如果玩家上下文包含这些标签之一则可触发, 空集=总是可选
#   对话行: [(说话者npc_id或'player', 文本)]
#   选项: [(选项文本, 后续对话行, 效果dict)] 或 None (无选项,自动结束)

DIALOGUE_DB = {
    'merchant': [
        # 通用招呼
        ({'first_time'},
         [('merchant', '哦? 新面孔! 欢迎来到深渊的边缘, 旅行者。'),
          ('merchant', '我是马库斯, 在这片黑暗中做些小生意。'),
          ('merchant', '别被外面的怪物吓到了, 只要你有金币, 我什么都卖。')],
         [('你都卖些什么?', [('merchant', '武器、护甲、稀有符文...只要你出得起价。'),
                              ('merchant', '去"装备召唤"看看吧，碰碰运气说不定有好东西！')], None),
          ('这里安全吗?', [('merchant', '嘿嘿，只要你不欠我钱，这里就是最安全的。'),
                            ('merchant', '不过说真的，深渊的裂隙越来越不稳定了...')], None),
          ('告辞', [], None)]),

        ({'newbie'},
         [('merchant', '又来了? 上次教你的保命技巧用上了吗?'),
          ('merchant', '看你这副样子...大概没用上吧。')],
         [('教我更多技巧', [('merchant', '要诀只有一个: 不要停下脚步!'),
                              ('merchant', '在深渊中站着不动就是等死。持续移动，让武器自动清场。'),
                              ('merchant', '经验宝石要尽量捡, 等级越高武器越强。')], None),
          ('你有什么好货?', [('merchant', '好东西可不便宜哦～'),
                               ('merchant', '去抽卡池碰碰运气, 或者攒到好装备来找铁匠升级。')], None),
          ('下次再说', [], None)]),

        ({'experienced', 'veteran'},
         [('merchant', '欢迎回来, 老朋友!'),
          ('merchant', '生意如何? 最近深渊里的怪物越来越多了。')],
         [('最近有什么新情报?', [('merchant', '你听说了吗? 深渊的最深处好像出现了一道新的裂隙。'),
                                   ('merchant', '据说穿过那里可以到达更危险的领域...'),
                                   ('merchant', '不过回报也会更丰厚。试试副本挑战吧。')], None),
          ('我需要更强的装备', [('merchant', '看你的装备...确实该升级了。'),
                                  ('merchant', '多打几个Boss吧, 钻石可以用来进行超级召唤。'),
                                  ('merchant', '传说品质的装备, 可是每个战士的梦想啊!')], None),
          ('只是路过', [], None)]),

        ({'rich'},
         [('merchant', '哇哦, 大客户驾到!'),
          ('merchant', '看你金光闪闪的钱袋...今天想看点什么?')],
         [('随便看看', [('merchant', '有钱任性啊! 记得多去抽几次十连, 说不定能抽到传说装备!')], None),
          ('告辞', [], None)]),

        ({'poor'},
         [('merchant', '唉, 你看起来也没什么钱的样子。'),
          ('merchant', '不过别灰心, 多打几局副本就有金币了。')],
         [('确实没钱', [('merchant', '去刷刷小怪吧, 实在不行还有灵魂商店。'),
                          ('merchant', '那里用灵魂碎片也能换到不少好东西。')], None),
          ('哼, 走了', [], None)]),

        # 通用兜底
        (set(),
         [('merchant', '嗨, 来了! 今天想要点什么?')],
         [('聊聊天', [('merchant', '深渊啊...说实话我也不知道自己为什么在这做生意。'),
                        ('merchant', '大概是因为只有这里的客人...嗯...不挑剔吧。')],  None),
          ('买东西', [('merchant', '去主菜单的"装备召唤"或"灵魂商店"吧, 我这没有直接卖的。'),
                        ('merchant', '不过如果你装备够多, 去"角色升级"里可以穿戴上哟。')], None),
          ('离开', [], None)]),
    ],

    'elder': [
        ({'first_time'},
         [('elder', '...你终于来了。'),
          ('elder', '我等这一刻已经很久了, 暗夜猎人。'),
          ('elder', '深渊的力量正在侵蚀这片大地, 而你是唯一的希望。')],
         [('我是谁?', [('elder', '你是被深渊选中的人。每次死亡, 你都会从轮回中归来。'),
                         ('elder', '这既是诅咒, 也是祝福。'),
                         ('elder', '利用每次轮回积累的力量, 终有一天你能击败深渊之王。')], None),
          ('深渊是什么?', [('elder', '深渊...是另一个维度的裂隙。'),
                             ('elder', '它吞噬生命, 扭曲现实, 不断向我们的世界渗透。'),
                             ('elder', '那些怪物, 都是从裂隙中涌出的深渊造物。')], None),
          ('...', [], None)]),

        ({'newbie'},
         [('elder', '轮回者, 你的旅程才刚刚开始。'),
          ('elder', '不要气馁, 每一次死亡都让你变得更强。')],
         [('我该怎么做?', [('elder', '升级你的角色, 强化你的装备。'),
                             ('elder', '灵魂商店中的永久加成对你大有裨益。'),
                             ('elder', '当你准备好了, 挑战更深层的副本。')], None),
          ('你是谁?', [('elder', '我是瑟拉斯, 这片灰暗之地最后的守望者。'),
                         ('elder', '在深渊吞噬一切之前, 我会尽我所能指引你。')], None),
          ('我知道了', [], None)]),

        ({'elite_killer'},
         [('elder', '你的力量...已经超越了我的预期。'),
          ('elder', '千魂之杀, 你已经证明了自己的实力。')],
         [('最终的敌人在哪?', [('elder', '在深渊的最深处, 有一个存在...'),
                                  ('elder', '"虚空之眼"...它是一切混沌的源头。'),
                                  ('elder', '当你的力量足够时, 它会出现在你面前。')], None),
          ('我还能更强吗?', [('elder', '力量没有尽头, 但代价也是如此。'),
                               ('elder', '不断轮回下去, 你终将达到凡人的极限...'),
                               ('elder', '然后, 超越它。')], None),
          ('...', [], None)]),

        ({'veteran'},
         [('elder', '老朋友, 你看起来疲惫了。'),
          ('elder', '在深渊中战斗这么久, 你有没有想过放弃?')],
         [('从未想过', [('elder', '...好。这就是你被选中的原因。'),
                          ('elder', '坚定的意志, 比任何武器都锋利。')], None),
          ('有时候会', [('elder', '这很正常。连我也曾动摇过。'),
                          ('elder', '但请记住, 你守护的不只是自己。'),
                          ('elder', '每一个被深渊吞噬的灵魂, 都在等你拯救。')], None),
          ('你说多了', [], None)]),

        (set(),
         [('elder', '命运的齿轮在转动...'),
          ('elder', '做好准备, 暗夜猎人。')],
         [('有什么建议?', [('elder', '多多收集材料, 强化你的角色。'),
                             ('elder', '铁矿、暗影精华、水晶...这些都是进阶所需。'),
                             ('elder', '副本深处有更稀有的龙鳞和深渊结晶。')], None),
          ('告辞', [], None)]),
    ],

    'blacksmith': [
        ({'no_equipment'},
         [('blacksmith', '嘿! 你连件像样的装备都没有?!'),
          ('blacksmith', '赶紧去抽几件来, 我好给你打造打造!')],
         [('去哪弄装备?', [('blacksmith', '主菜单有"装备召唤", 花点金币或钻石就行。'),
                              ('blacksmith', '抽到装备后到"角色升级"界面, 就能穿上了!'),
                              ('blacksmith', '有好装备再来找我升级!')], None),
          ('好的', [], None)]),

        ({'well_equipped'},
         [('blacksmith', '噢! 这些装备...品质不错啊!'),
          ('blacksmith', '想让我帮你锻造升级吗?')],
         [('怎么升级装备?', [('blacksmith', '在"角色升级"界面, 每件装备旁边有升级按钮。'),
                                ('blacksmith', '花点金币就能提升装备等级, 属性会越来越强。'),
                                ('blacksmith', '史诗和传说品质的装备提升幅度最大!')], None),
          ('材料怎么获得?', [('blacksmith', '打怪会掉铁矿, 这是最基础的材料。'),
                                ('blacksmith', '暗影精华要打更强的怪, 水晶在副本里比较多。'),
                                ('blacksmith', '龙鳞和深渊结晶...只有高级副本的Boss才会掉。')], None),
          ('改天再来', [], None)]),

        (set(),
         [('blacksmith', '欢迎来到我的锻造铺! 有什么要修理的?')],
         [('聊聊锻造', [('blacksmith', '锻造嘛, 就是我的命。'),
                          ('blacksmith', '给我材料和金币, 没有我打不出的装备!'),
                          ('blacksmith', '不过最好的装备...还是得靠召唤池碰运气。')], None),
          ('你看起来很壮', [('blacksmith', '哈哈! 每天抡锤子, 想不壮都难!'),
                               ('blacksmith', '深渊里的怪物? 给我一把好锤子, 我也能打!')], None),
          ('走了', [], None)]),
    ],

    'witch': [
        ({'first_time', 'newbie'},
         [('witch', '呵呵呵...一个新的灵魂来到了深渊的边缘。'),
          ('witch', '命运之线在你身上缠绕...有趣。')],
         [('你是谁?', [('witch', '我? 我是伊薇, 有人叫我女巫, 有人叫我预言者。'),
                         ('witch', '我编织命运之线, 也解读它们的走向。'),
                         ('witch', '你的线...很特别。缠绕着死亡, 却每次都重新连接。')], None),
          ('你能帮我吗?', [('witch', '帮你? 我能给你的只有预言。'),
                              ('witch', '第一个预言: 不要贪恋经验, 有时候躲避比升级更重要。'),
                              ('witch', '第二个预言: Boss出现前, 准备好你最强的武器组合。')], None),
          ('...有点害怕', [('witch', '呵呵呵...怕我? 你应该怕的是深渊本身。'),
                              ('witch', '去吧, 年轻人。命运会指引你的。')], None)]),

        ({'skilled', 'elite_killer'},
         [('witch', '你身上的深渊气息越来越浓了...'),
          ('witch', '你知道吗? 杀戮太多深渊造物, 你自己也会被侵蚀。')],
         [('有办法抵抗吗?', [('witch', '唯一的办法是...变得更强。'),
                                ('witch', '当你的力量超越深渊, 侵蚀就无法触及你。'),
                                ('witch', '角色进阶可以增强你的抗性...多收集些材料吧。')], None),
          ('我不在乎', [('witch', '...真是无畏。或者说, 无知?'),
                          ('witch', '不过, 也许正是这种无畏...才是你最强的武器。')], None),
          ('...', [], None)]),

        ({'soul_rich'},
         [('witch', '这么多灵魂碎片...你收割了不少生命啊。'),
          ('witch', '灵魂商店的升级能让你获得永久的力量。')],
         [('哪个路线最好?', [('witch', '如果你喜欢硬抗, 走"求生之道"...'),
                                ('witch', '如果你喜欢爆发, 走"战斗之路"...'),
                                ('witch', '但我个人推荐..."命运之轮"。'),
                                ('witch', '它很贵, 但效果是最独特的。')], None),
          ('灵魂碎片的来源?', [('witch', '每次轮回结束, 你的击杀和存活时间都会化为碎片。'),
                                   ('witch', '杀的越多、活的越久, 碎片就越多。'),
                                   ('witch', 'Boss也会额外掉落一些。')], None),
          ('告辞', [], None)]),

        (set(),
         [('witch', '又见面了...命运之线依然缠绕在你身上。'),
          ('witch', '今天想知道什么?')],
         [('今天运气如何?', [('witch', random.choice([
              '星象显示...今天适合抽卡! 去试试十连吧。',
              '嗯...今天的运势一般, 还是老老实实刷副本吧。',
              '哦? 今天的命运之线异常活跃...会有好事发生!',
              '小心...今天深渊的力量格外强烈。',
              '去升级你的角色吧, 今天适合修炼。',
          ]))], None),
          ('告诉我个秘密', [('witch', random.choice([
              '秘密? 呵呵...暴击和吸血是最强的组合。',
              '你知道吗? 每8种武器都有隐藏的协同效果。',
              '深渊裂隙每10分钟会涌出一波精英怪...做好准备。',
              '传说品质的符文...能让你的冷却近乎消失。',
              '铁匠他...以前也是个深渊猎人, 只是不愿承认。',
          ]))], None),
          ('走了', [], None)]),
    ],
}


# ============================================================
#  对话状态管理
# ============================================================

class DialogueState:
    """管理当前对话状态"""
    def __init__(self):
        self.active = False
        self.npc_id = None
        self.lines = []         # 当前对话行 [(speaker, text)]
        self.line_index = 0     # 当前显示到第几行
        self.choices = None     # 当前可选选项 [(text, follow_lines, effect)]
        self.showing_choices = False
        self.char_reveal = 0    # 打字机效果: 已显示字符数
        self.char_timer = 0
        self.history = []       # 已经显示过的对话行

    def start(self, npc_id, save_data):
        """开始一段对话"""
        self.active = True
        self.npc_id = npc_id
        self.history = []
        self.char_reveal = 0
        self.char_timer = 0

        # 根据上下文选择对话
        tags = _get_context_tags(save_data)
        dialogues = DIALOGUE_DB.get(npc_id, [])

        # 按优先级匹配
        matched = None
        for req_tags, lines, choices in dialogues:
            if req_tags and req_tags & tags:
                matched = (lines, choices)
                break
        if not matched:
            # 用最后一个兜底
            for req_tags, lines, choices in reversed(dialogues):
                if not req_tags:
                    matched = (lines, choices)
                    break
        if not matched and dialogues:
            matched = (dialogues[-1][1], dialogues[-1][2])

        if matched:
            self.lines = matched[0]
            self.choices = matched[1]
        else:
            self.lines = [('???', '......')]
            self.choices = None

        self.line_index = 0
        self.showing_choices = False

    def advance(self):
        """推进对话 (点击继续)"""
        if not self.active:
            return

        current_line = self.lines[self.line_index] if self.line_index < len(self.lines) else None
        if current_line:
            full_text = current_line[1]
            if self.char_reveal < len(full_text):
                # 跳过打字效果, 直接显示全文
                self.char_reveal = len(full_text)
                return

        self.line_index += 1
        self.char_reveal = 0
        self.char_timer = 0

        if self.line_index >= len(self.lines):
            # 对话行完毕
            if self.choices and not self.showing_choices:
                self.showing_choices = True
            else:
                self.active = False

    def select_choice(self, idx):
        """选择选项"""
        if not self.showing_choices or not self.choices:
            return
        if idx >= len(self.choices):
            return

        text, follow_lines, effect = self.choices[idx]

        if follow_lines:
            self.lines = follow_lines
            self.line_index = 0
            self.char_reveal = 0
            self.char_timer = 0
            self.showing_choices = False
            self.choices = None  # 后续对话没有更多选项
        else:
            self.active = False

    def update(self, dt):
        """更新打字机效果"""
        if not self.active or self.showing_choices:
            return
        if self.line_index < len(self.lines):
            full_text = self.lines[self.line_index][1]
            if self.char_reveal < len(full_text):
                self.char_timer += dt
                # 每0.03秒显示一个字符
                chars_to_show = int(self.char_timer / 0.03)
                self.char_reveal = min(chars_to_show, len(full_text))


# 全局对话状态
dialogue_state = DialogueState()


# ============================================================
#  绘制系统
# ============================================================

def draw_dialogue_box(surface, save_data):
    """绘制对话框UI, 返回按钮字典"""
    buttons = {}
    ds = dialogue_state

    if not ds.active:
        return buttons

    npc = NPCS.get(ds.npc_id)
    if not npc:
        ds.active = False
        return buttons

    # 半透明遮罩
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    surface.blit(overlay, (0, 0))

    # 对话框背景
    box_w = 900
    box_h = 260
    box_x = WIDTH // 2 - box_w // 2
    box_y = HEIGHT - box_h - 30
    box_rect = pygame.Rect(box_x, box_y, box_w, box_h)

    # 绘制对话框
    box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    pygame.draw.rect(box_surf, (12, 10, 25, 220), (0, 0, box_w, box_h), border_radius=12)
    pygame.draw.rect(box_surf, (*npc.color, 150), (0, 0, box_w, box_h), 3, border_radius=12)
    # 内发光效果
    glow = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    pygame.draw.rect(glow, (*npc.color, 15), (4, 4, box_w - 8, box_h - 8), border_radius=10)
    box_surf.blit(glow, (0, 0))
    surface.blit(box_surf, (box_x, box_y))

    # NPC头像
    avatar_x = box_x + 70
    avatar_y = box_y - 30
    # 头像背景圆
    pygame.draw.circle(surface, (20, 18, 35), (avatar_x, avatar_y), 48)
    pygame.draw.circle(surface, npc.color, (avatar_x, avatar_y), 48, 3)
    npc.draw_avatar(surface, avatar_x, avatar_y, 38)

    # NPC名称
    name_t = _render_outlined(_font_sm, f"{i18n.t(npc.title)}·{i18n.t(npc.name.split('·')[-1])}", npc.color)
    surface.blit(name_t, (avatar_x + 58, avatar_y - 15))

    # 对话内容
    text_x = box_x + 30
    text_y = box_y + 25

    if not ds.showing_choices:
        # 显示当前对话行
        if ds.line_index < len(ds.lines):
            speaker_id, full_text = ds.lines[ds.line_index]
            displayed = full_text[:ds.char_reveal]

            # 分行显示 (自动换行)
            max_chars = 38
            dy = 0
            for start in range(0, len(displayed), max_chars):
                chunk = displayed[start:start + max_chars]
                lt = _render_outlined(_font_sm, chunk, (240, 240, 250))
                surface.blit(lt, (text_x, text_y + dy))
                dy += 30

            # 提示继续
            if ds.char_reveal >= len(full_text):
                blink = int(pygame.time.get_ticks() / 500) % 2
                if blink:
                    cont = _render_outlined(_font_xs, "▼ 点击继续", (180, 180, 200))
                    surface.blit(cont, (box_x + box_w - 150, box_y + box_h - 35))

        # 点击区域 (整个对话框)
        buttons['dialogue_advance'] = box_rect
    else:
        # 显示选项
        prompt = _render_outlined(_font_sm, "请选择:", (200, 200, 220))
        surface.blit(prompt, (text_x, text_y))

        if ds.choices:
            mx, my = pygame.mouse.get_pos()
            for ci, (ctext, _, _) in enumerate(ds.choices):
                cy = text_y + 40 + ci * 45
                crect = pygame.Rect(text_x, cy, box_w - 60, 38)
                hover = crect.collidepoint(mx, my)

                cs = pygame.Surface((crect.width, crect.height), pygame.SRCALPHA)
                if hover:
                    pygame.draw.rect(cs, (*npc.color, 40), (0, 0, crect.width, crect.height), border_radius=6)
                    pygame.draw.rect(cs, (*npc.color, 180), (0, 0, crect.width, crect.height), 2, border_radius=6)
                else:
                    pygame.draw.rect(cs, (255, 255, 255, 10), (0, 0, crect.width, crect.height), border_radius=6)
                    pygame.draw.rect(cs, (255, 255, 255, 60), (0, 0, crect.width, crect.height), 1, border_radius=6)
                surface.blit(cs, (crect.x, crect.y))

                # 选项序号
                num = _render_outlined(_font_xs, f"{ci+1}.", npc.color)
                surface.blit(num, (crect.x + 10, crect.y + 8))
                # 选项文本
                ct = _render_outlined(_font_sm, ctext, WHITE if hover else (200, 200, 210))
                surface.blit(ct, (crect.x + 35, crect.y + 6))

                buttons[('dialogue_choice', ci)] = crect

    # 关闭按钮
    close_rect = pygame.Rect(box_x + box_w - 40, box_y + 5, 30, 30)
    pygame.draw.line(surface, (180, 180, 200), (close_rect.x + 5, close_rect.y + 5),
                     (close_rect.x + 25, close_rect.y + 25), 2)
    pygame.draw.line(surface, (180, 180, 200), (close_rect.x + 25, close_rect.y + 5),
                     (close_rect.x + 5, close_rect.y + 25), 2)
    buttons['dialogue_close'] = close_rect

    return buttons


def draw_npc_select(surface, save_data):
    """NPC选择界面 (城镇), 返回按钮字典"""
    buttons = {}
    surface.fill((8, 8, 14))

    # 标题
    title = _render_outlined(_font_lg, i18n.t("深渊城镇"), CYAN)
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 30))

    subtitle = _render_outlined(_font_sm, i18n.t("与NPC交谈获取情报和建议"), (160, 160, 180))
    surface.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 85))

    # NPC卡片
    npc_list = list(NPCS.values())
    card_w, card_h = 240, 320
    spacing = 30
    total_w = len(npc_list) * card_w + (len(npc_list) - 1) * spacing
    start_x = WIDTH // 2 - total_w // 2
    mx, my = pygame.mouse.get_pos()

    t = pygame.time.get_ticks() / 1000.0

    for i, npc in enumerate(npc_list):
        x = start_x + i * (card_w + spacing)
        y = 140
        rect = pygame.Rect(x, y, card_w, card_h)
        hover = rect.collidepoint(mx, my)

        # 卡片背景
        cs = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        bg_alpha = 50 if hover else 20
        pygame.draw.rect(cs, (*npc.color, bg_alpha), (0, 0, card_w, card_h), border_radius=12)
        border_alpha = 200 if hover else 80
        pygame.draw.rect(cs, (*npc.color, border_alpha), (0, 0, card_w, card_h), 2, border_radius=12)

        # 悬浮动画
        float_y = int(math.sin(t * 2 + i * 1.5) * 3) if hover else 0

        surface.blit(cs, (x, y + float_y))

        # 头像
        av_x = x + card_w // 2
        av_y = y + 80 + float_y
        # 头像光环
        if hover:
            glow_surf = pygame.Surface((120, 120), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*npc.color, 30), (60, 60), 55)
            surface.blit(glow_surf, (av_x - 60, av_y - 60))
        npc.draw_avatar(surface, av_x, av_y, 42)

        # 名称
        name_parts = npc.name.split('·')
        if len(name_parts) == 2:
            prefix_t = _render_outlined(_font_xs, i18n.t(name_parts[0]), (180, 180, 200))
            surface.blit(prefix_t, (av_x - prefix_t.get_width() // 2, y + 140 + float_y))
            name_t = _render_outlined(_font_md, i18n.t(name_parts[1]), npc.color)
            surface.blit(name_t, (av_x - name_t.get_width() // 2, y + 160 + float_y))
        else:
            name_t = _render_outlined(_font_md, i18n.t(npc.name), npc.color)
            surface.blit(name_t, (av_x - name_t.get_width() // 2, y + 155 + float_y))

        # 头衔
        title_t = _render_outlined(_font_xs, i18n.t(npc.title), (200, 200, 220))
        surface.blit(title_t, (av_x - title_t.get_width() // 2, y + 195 + float_y))

        # 提示文本
        if hover:
            hint_t = _render_outlined(_font_xs, i18n.t("点击交谈"), WHITE)
            surface.blit(hint_t, (av_x - hint_t.get_width() // 2, y + 260 + float_y))

        buttons[('npc', npc.npc_id)] = rect

    # 返回按钮
    back_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 60, 200, 40)
    back_surf = pygame.Surface((200, 40), pygame.SRCALPHA)
    pygame.draw.rect(back_surf, (200, 200, 220, 20), (0, 0, 200, 40), border_radius=8)
    pygame.draw.rect(back_surf, (200, 200, 220, 120), (0, 0, 200, 40), 2, border_radius=8)
    surface.blit(back_surf, back_rect)
    bt = _render_outlined(_font_sm, "返回", (200, 200, 220))
    surface.blit(bt, (WIDTH // 2 - bt.get_width() // 2, HEIGHT - 55))
    buttons['back'] = back_rect

    return buttons
