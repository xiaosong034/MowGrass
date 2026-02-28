"""
城镇地图系统 — 可探索的俯视角城镇
========================================
玩家角色在城镇中行走，接近互动点触发功能
包含: 副本传送门、召唤祭坛、升级锻造台、灵魂商店、图鉴书架、NPC位置
========================================
"""

import pygame
import math
import random
import os
import i18n

# ---- 描边文字渲染 ----
def _render_outlined(font, text, color, outline_color=(0, 0, 0), offset=1):
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

# ---- 模块变量 ----
_screen = None
_font_lg = _font_md = _font_sm = _font_xs = None
WIDTH = HEIGHT = 0

# 颜色
WHITE  = (255, 255, 255)
CYAN   = (78, 205, 196)
PURPLE = (170, 68, 255)
GOLD   = (255, 215, 0)
GREEN  = (68, 255, 68)
ORANGE = (255, 170, 0)
PINK   = (255, 100, 200)
RED    = (255, 68, 68)
BLUE   = (68, 68, 255)

# 地图大小 (像素)
MAP_W = 2400
MAP_H = 1600


def init(screen, font_lg, font_md, font_sm, font_xs, w, h):
    global _screen, _font_lg, _font_md, _font_sm, _font_xs, WIDTH, HEIGHT
    _screen = screen
    _font_lg = font_lg
    _font_md = font_md
    _font_sm = font_sm
    _font_xs = font_xs
    WIDTH = w
    HEIGHT = h


# ========== 互动点定义 ==========
class TownLocation:
    """城镇中的互动点"""
    def __init__(self, name, x, y, w, h, action, color, icon_type, description=""):
        self.name = name
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.action = action        # 对应的 GameState 动作
        self.color = color
        self.icon_type = icon_type   # 'portal', 'altar', 'anvil', 'shop', 'book', 'npc'
        self.description = description
        self.hover_timer = 0

    @property
    def rect(self):
        return pygame.Rect(self.x - self.w // 2, self.y - self.h // 2, self.w, self.h)

    @property
    def center(self):
        return (self.x, self.y)


# 城镇互动点布局
TOWN_LOCATIONS = [
    TownLocation("副本传送门", 400, 400, 100, 100, 'dungeon',
                 CYAN, 'portal', "进入副本挑战"),
    TownLocation("召唤祭坛", 1200, 350, 100, 100, 'gacha',
                 PURPLE, 'altar', "消耗资源召唤装备"),
    TownLocation("锻造工坊", 800, 900, 100, 100, 'upgrade',
                 ORANGE, 'anvil', "升级角色和装备"),
    TownLocation("灵魂商店", 1600, 600, 90, 90, 'shop',
                 (170, 120, 255), 'shop', "消耗灵魂碎片购物"),
    TownLocation("深渊图鉴", 1800, 400, 80, 80, 'codex',
                 PINK, 'book', "查阅角色和装备图鉴"),
    TownLocation("冒险出发", 800, 350, 100, 100, 'start_run',
                 GREEN, 'gate', "选择角色开始冒险"),
    # NPC位置
    TownLocation("商人·马库斯", 1400, 900, 70, 70, 'npc_merchant',
                 GOLD, 'npc', "物资交易商人"),
    TownLocation("长老·瑟拉斯", 600, 750, 70, 70, 'npc_elder',
                 (100, 200, 180), 'npc', "深渊知识长老"),
    TownLocation("铁匠·布鲁诺", 1000, 1100, 70, 70, 'npc_blacksmith',
                 (200, 120, 60), 'npc', "武器锻造大师"),
    TownLocation("女巫·伊薇", 1700, 850, 70, 70, 'npc_witch',
                 (180, 80, 200), 'npc', "神秘魔法师"),
]

# 城镇装饰物 (x, y, type)
TOWN_DECORATIONS = [
    # 树木
    (200, 300, 'tree'), (300, 200, 'tree'), (150, 600, 'tree'),
    (500, 150, 'tree'), (1000, 200, 'tree'), (1500, 200, 'tree'),
    (1900, 300, 'tree'), (2000, 600, 'tree'), (2100, 400, 'tree'),
    (200, 1000, 'tree'), (300, 1200, 'tree'), (1800, 1100, 'tree'),
    (2000, 900, 'tree'), (100, 800, 'tree'), (2200, 700, 'tree'),
    # 灯/火把
    (550, 400, 'lamp'), (1050, 400, 'lamp'), (700, 700, 'lamp'),
    (1300, 700, 'lamp'), (1500, 450, 'lamp'), (900, 600, 'lamp'),
    # 石头
    (350, 550, 'rock'), (1100, 550, 'rock'), (1650, 350, 'rock'),
    (450, 1000, 'rock'), (1200, 1050, 'rock'),
    # 围墙段
    (100, 100, 'wall_h'), (300, 100, 'wall_h'), (500, 100, 'wall_h'),
    (700, 100, 'wall_h'), (900, 100, 'wall_h'), (1100, 100, 'wall_h'),
    (1300, 100, 'wall_h'), (1500, 100, 'wall_h'), (1700, 100, 'wall_h'),
    (1900, 100, 'wall_h'), (2100, 100, 'wall_h'),
]

# 地面路径 (连接互动点的路径, 用于装饰)
TOWN_PATHS = [
    # 中央大道 (水平)
    (300, 370, 1600, 60),
    # 中央大道 (垂直)
    (770, 300, 60, 800),
    # 右侧通道
    (1170, 320, 60, 300),
    (1170, 580, 500, 60),
    # 锻造通向NPC区
    (800, 870, 700, 60),
    # 图鉴通道
    (1770, 370, 60, 80),
]

# ========== 碰撞障碍物 ==========
TOWN_WALLS = [
    # 边界
    pygame.Rect(0, 0, MAP_W, 120),         # 顶
    pygame.Rect(0, MAP_H - 40, MAP_W, 40), # 底
    pygame.Rect(0, 0, 60, MAP_H),          # 左
    pygame.Rect(MAP_W - 60, 0, 60, MAP_H), # 右
]


# ========== 城镇玩家 ==========
class TownPlayer:
    """城镇中的可控角色"""

    def __init__(self, x, y, char_index=0):
        self.x = float(x)
        self.y = float(y)
        self.char_index = char_index
        self.speed = 280
        self.anim_timer = 0
        self.facing = 'down'
        self.moving = False
        self.nearby_location = None  # 当前靠近的互动点

    def update(self, dt, keys_pressed):
        dx, dy = 0, 0
        if keys_pressed[pygame.K_w] or keys_pressed[pygame.K_UP]:
            dy = -1
            self.facing = 'up'
        if keys_pressed[pygame.K_s] or keys_pressed[pygame.K_DOWN]:
            dy = 1
            self.facing = 'down'
        if keys_pressed[pygame.K_a] or keys_pressed[pygame.K_LEFT]:
            dx = -1
            self.facing = 'left'
        if keys_pressed[pygame.K_d] or keys_pressed[pygame.K_RIGHT]:
            dx = 1
            self.facing = 'right'

        self.moving = dx != 0 or dy != 0
        if self.moving:
            self.anim_timer += dt
            # 归一化
            length = math.hypot(dx, dy)
            if length > 0:
                dx /= length
                dy /= length
            new_x = self.x + dx * self.speed * dt
            new_y = self.y + dy * self.speed * dt

            # 碰撞检测
            player_rect = pygame.Rect(new_x - 12, new_y - 12, 24, 24)
            blocked = False
            for wall in TOWN_WALLS:
                if player_rect.colliderect(wall):
                    blocked = True
                    break
            if not blocked:
                self.x = max(80, min(MAP_W - 80, new_x))
                self.y = max(140, min(MAP_H - 60, new_y))

        # 检测附近互动点
        self.nearby_location = None
        for loc in TOWN_LOCATIONS:
            dist = math.hypot(self.x - loc.x, self.y - loc.y)
            interact_range = max(loc.w, loc.h) * 0.8 + 40
            if dist < interact_range:
                self.nearby_location = loc
                break

    def draw(self, surface, camera_x, camera_y):
        """绘制城镇角色"""
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)

        # 影子
        shadow = pygame.Surface((28, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 60), (0, 0, 28, 10))
        surface.blit(shadow, (sx - 14, sy + 10))

        # 角色身体
        bob = math.sin(self.anim_timer * 8) * 2 if self.moving else 0
        body_y = sy - 12 + int(bob)

        # 身体颜色（基于角色索引）
        char_colors = [
            (78, 205, 196),   # 剑士 cyan
            (255, 100, 200),  # 法师 pink
            (100, 220, 100),  # 弓手 green
            (170, 68, 255),   # 刺客 purple
            (255, 170, 0),    # 骑士 orange
            (100, 200, 255),  # 召唤师 ice blue
        ]
        body_color = char_colors[self.char_index % len(char_colors)]

        # 头
        pygame.draw.circle(surface, (240, 210, 180), (sx, body_y - 8), 10)
        pygame.draw.circle(surface, (60, 50, 40), (sx, body_y - 8), 10, 1)

        # 头发（朝向不同方向）
        hair_color = (40, 30, 25)
        if self.facing in ('left', 'up'):
            pygame.draw.arc(surface, hair_color, (sx - 10, body_y - 20, 20, 16), 0, math.pi, 3)
        else:
            pygame.draw.arc(surface, hair_color, (sx - 10, body_y - 20, 20, 16), 0, math.pi, 3)

        # 眼睛
        eye_dx = -3 if self.facing == 'left' else (3 if self.facing == 'right' else 0)
        eye_dy = -2 if self.facing == 'up' else (1 if self.facing == 'down' else 0)
        if self.facing != 'up':
            pygame.draw.circle(surface, (30, 30, 30), (sx - 3 + eye_dx, body_y - 8 + eye_dy), 2)
            pygame.draw.circle(surface, (30, 30, 30), (sx + 3 + eye_dx, body_y - 8 + eye_dy), 2)

        # 身体
        body_rect = pygame.Rect(sx - 8, body_y + 2, 16, 16)
        pygame.draw.rect(surface, body_color, body_rect, border_radius=3)
        pygame.draw.rect(surface, (max(0, body_color[0]-50), max(0, body_color[1]-50),
                                    max(0, body_color[2]-50)), body_rect, 1, border_radius=3)

        # 腿（走路动画）
        if self.moving:
            leg_phase = math.sin(self.anim_timer * 10)
            left_leg_y = sy + 18 + int(leg_phase * 3)
            right_leg_y = sy + 18 - int(leg_phase * 3)
        else:
            left_leg_y = sy + 18
            right_leg_y = sy + 18
        pygame.draw.line(surface, (50, 45, 55), (sx - 4, sy + 16), (sx - 4, left_leg_y), 2)
        pygame.draw.line(surface, (50, 45, 55), (sx + 4, sy + 16), (sx + 4, right_leg_y), 2)

        # 名称标签
        try:
            import characters
            char_names = ["剑士", "法师", "弓手", "刺客", "骑士", "召唤师"]
            name = i18n.t(char_names[self.char_index % len(char_names)])
        except:
            name = i18n.t("冒险者")
        name_txt = _render_outlined(_font_xs, name, body_color)
        surface.blit(name_txt, (sx - name_txt.get_width() // 2, body_y - 28))


# ========== 城镇装饰绘制 ==========
def draw_decoration(surface, x, y, dec_type, cam_x, cam_y, t):
    """绘制城镇装饰物"""
    sx = int(x - cam_x)
    sy = int(y - cam_y)
    # 不在屏幕中则跳过
    if sx < -100 or sx > WIDTH + 100 or sy < -100 or sy > HEIGHT + 100:
        return

    if dec_type == 'tree':
        # 树干
        pygame.draw.rect(surface, (80, 55, 30), (sx - 4, sy - 5, 8, 25))
        # 树冠 (微微摇动)
        sway = math.sin(t * 1.5 + x * 0.01) * 2
        points = [(sx + int(sway), sy - 30),
                  (sx - 18 + int(sway * 0.5), sy - 2),
                  (sx + 18 + int(sway * 0.5), sy - 2)]
        pygame.draw.polygon(surface, (30, 90, 40), points)
        pygame.draw.polygon(surface, (40, 110, 50), points, 1)
        # 第二层树冠
        points2 = [(sx + int(sway), sy - 42),
                   (sx - 14 + int(sway * 0.5), sy - 18),
                   (sx + 14 + int(sway * 0.5), sy - 18)]
        pygame.draw.polygon(surface, (35, 100, 45), points2)

    elif dec_type == 'lamp':
        # 灯柱
        pygame.draw.rect(surface, (70, 65, 60), (sx - 2, sy - 20, 4, 25))
        # 灯头
        pygame.draw.rect(surface, (90, 80, 50), (sx - 6, sy - 24, 12, 6))
        # 灯光
        flicker = (math.sin(t * 4 + x) + 1) * 0.5
        glow_r = int(18 + flicker * 6)
        glow_s = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        glow_a = int(40 + flicker * 30)
        pygame.draw.circle(glow_s, (255, 200, 80, glow_a), (glow_r, glow_r), glow_r)
        surface.blit(glow_s, (sx - glow_r, sy - 24 - glow_r))

    elif dec_type == 'rock':
        pygame.draw.ellipse(surface, (60, 58, 55), (sx - 12, sy - 6, 24, 12))
        pygame.draw.ellipse(surface, (75, 72, 68), (sx - 12, sy - 6, 24, 12), 1)
        # 小石头
        pygame.draw.ellipse(surface, (65, 62, 58), (sx + 8, sy - 2, 10, 6))

    elif dec_type == 'wall_h':
        pygame.draw.rect(surface, (50, 45, 55), (sx - 50, sy - 15, 100, 30))
        pygame.draw.rect(surface, (70, 65, 75), (sx - 50, sy - 15, 100, 30), 1)
        # 砖纹
        for bi in range(5):
            bx = sx - 50 + bi * 20
            pygame.draw.line(surface, (60, 55, 65), (bx, sy - 15), (bx, sy + 15), 1)
        pygame.draw.line(surface, (60, 55, 65), (sx - 50, sy), (sx + 50, sy), 1)


def draw_location_building(surface, loc, cam_x, cam_y, t):
    """绘制互动点的建筑图标"""
    sx = int(loc.x - cam_x)
    sy = int(loc.y - cam_y)
    if sx < -120 or sx > WIDTH + 120 or sy < -120 or sy > HEIGHT + 120:
        return

    hw, hh = loc.w // 2, loc.h // 2

    if loc.icon_type == 'portal':
        # 传送门 — 旋转的光环
        angle = t * 2
        r = hw - 5
        # 门框
        pygame.draw.ellipse(surface, (20, 50, 60), (sx - r, sy - r, r * 2, r * 2))
        pygame.draw.ellipse(surface, loc.color, (sx - r, sy - r, r * 2, r * 2), 2)
        # 旋转光点
        for i in range(6):
            a = angle + i * math.pi / 3
            px = sx + math.cos(a) * (r - 5)
            py = sy + math.sin(a) * (r - 5)
            ps = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*loc.color, 180), (4, 4), 4)
            surface.blit(ps, (int(px - 4), int(py - 4)))
        # 中心光晕
        pulse = (math.sin(t * 3) + 1) * 0.5
        gr = int(r * 0.5 + pulse * 10)
        gs = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*loc.color, int(30 + pulse * 30)), (gr, gr), gr)
        surface.blit(gs, (sx - gr, sy - gr))

    elif loc.icon_type == 'altar':
        # 祭坛 — 阶梯台座 + 浮空水晶
        # 台座
        points = [(sx - 35, sy + 25), (sx + 35, sy + 25),
                  (sx + 25, sy + 5), (sx - 25, sy + 5)]
        pygame.draw.polygon(surface, (45, 35, 60), points)
        pygame.draw.polygon(surface, loc.color, points, 1)
        # 水晶
        crystal_bob = math.sin(t * 2) * 4
        cy = sy - 15 + int(crystal_bob)
        # 菱形水晶
        cp = [(sx, cy - 14), (sx + 10, cy), (sx, cy + 14), (sx - 10, cy)]
        pygame.draw.polygon(surface, (80, 50, 120), cp)
        pygame.draw.polygon(surface, loc.color, cp, 2)
        # 光晕
        glow_r = int(20 + (math.sin(t * 3) + 1) * 5)
        gs = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*loc.color, 40), (glow_r, glow_r), glow_r)
        surface.blit(gs, (sx - glow_r, cy - glow_r))

    elif loc.icon_type == 'anvil':
        # 铁砧 — 锤子 + 火焰
        # 铁砧体
        pygame.draw.rect(surface, (80, 70, 65), (sx - 18, sy - 5, 36, 20), border_radius=2)
        pygame.draw.rect(surface, (100, 90, 80), (sx - 18, sy - 5, 36, 20), 1, border_radius=2)
        # 支撑
        pygame.draw.rect(surface, (70, 60, 55), (sx - 8, sy + 15, 16, 12))
        # 锤子 (上方)
        hammer_angle = math.sin(t * 4) * 0.3
        hx = sx + 12
        hy = sy - 20 + int(math.sin(t * 4) * 5)
        pygame.draw.line(surface, (90, 75, 50), (hx, hy), (hx, hy + 15), 2)
        pygame.draw.rect(surface, (120, 110, 100), (hx - 5, hy - 3, 10, 6))
        # 火花（间歇性）
        if math.sin(t * 4) > 0.5:
            for _ in range(2):
                spark_x = sx + random.randint(-10, 10)
                spark_y = sy - 8 + random.randint(-5, 0)
                ps = pygame.Surface((4, 4), pygame.SRCALPHA)
                pygame.draw.circle(ps, (255, 200, 50, 200), (2, 2), 2)
                surface.blit(ps, (spark_x, spark_y))

    elif loc.icon_type == 'shop':
        # 商店 — 帐篷样式
        # 帐篷
        points = [(sx, sy - 30), (sx - 30, sy + 15), (sx + 30, sy + 15)]
        pygame.draw.polygon(surface, (40, 30, 55), points)
        pygame.draw.polygon(surface, loc.color, points, 2)
        # 门帘
        pygame.draw.rect(surface, (55, 40, 70), (sx - 8, sy, 16, 15))
        # 旗子
        flag_wave = math.sin(t * 3) * 3
        pygame.draw.line(surface, (90, 80, 70), (sx + 20, sy - 20), (sx + 20, sy - 35), 1)
        fp = [(sx + 20, sy - 35), (sx + 32 + int(flag_wave), sy - 30),
              (sx + 20, sy - 25)]
        pygame.draw.polygon(surface, loc.color, fp)

    elif loc.icon_type == 'book':
        # 书架
        # 书架框
        pygame.draw.rect(surface, (70, 55, 40), (sx - 20, sy - 25, 40, 45), border_radius=2)
        pygame.draw.rect(surface, (90, 75, 55), (sx - 20, sy - 25, 40, 45), 1, border_radius=2)
        # 书本 (不同颜色)
        book_colors = [(200, 60, 60), (60, 120, 200), (60, 180, 80), (180, 80, 200)]
        for bi, bc in enumerate(book_colors):
            bx = sx - 16 + bi * 9
            bh = 12 + (bi % 2) * 4
            pygame.draw.rect(surface, bc, (bx, sy - 20 + (16 - bh), 7, bh), border_radius=1)
        # 光效
        pulse = (math.sin(t * 2 + 1) + 1) * 0.5
        gs = pygame.Surface((50, 50), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*loc.color, int(15 + pulse * 15)), (25, 25), 25)
        surface.blit(gs, (sx - 25, sy - 25))

    elif loc.icon_type == 'gate':
        # 出发大门
        # 门框
        pygame.draw.rect(surface, (60, 55, 50), (sx - 25, sy - 35, 50, 55), border_radius=3)
        pygame.draw.rect(surface, loc.color, (sx - 25, sy - 35, 50, 55), 2, border_radius=3)
        # 拱形顶
        pygame.draw.arc(surface, loc.color, (sx - 20, sy - 40, 40, 25), 0, math.pi, 2)
        # 门内光 (脉冲)
        pulse = (math.sin(t * 2.5) + 1) * 0.5
        inner = pygame.Surface((30, 35), pygame.SRCALPHA)
        inner.fill((*loc.color, int(20 + pulse * 30)))
        surface.blit(inner, (sx - 15, sy - 20))
        # 箭头指示
        arrow_bob = math.sin(t * 3) * 3
        ax = sx
        ay = int(sy - 45 + arrow_bob)
        pygame.draw.polygon(surface, loc.color, [(ax, ay - 6), (ax - 6, ay + 2), (ax + 6, ay + 2)])

    elif loc.icon_type == 'npc':
        # NPC — 简笔画小人
        npc_colors = {
            'npc_merchant':   GOLD,
            'npc_elder':      (100, 200, 180),
            'npc_blacksmith': (200, 120, 60),
            'npc_witch':      (180, 80, 200),
        }
        nc = npc_colors.get(loc.action, (200, 200, 200))
        bob = math.sin(t * 1.5 + hash(loc.name) % 10) * 2

        # 头
        pygame.draw.circle(surface, (230, 205, 175), (sx, int(sy - 18 + bob)), 9)
        pygame.draw.circle(surface, nc, (sx, int(sy - 18 + bob)), 9, 1)
        # 身体（品质色）
        pygame.draw.rect(surface, nc, (sx - 7, int(sy - 9 + bob), 14, 18), border_radius=3)
        # 腿
        pygame.draw.line(surface, (50, 45, 55), (sx - 3, int(sy + 9 + bob)),
                         (sx - 3, int(sy + 18 + bob)), 2)
        pygame.draw.line(surface, (50, 45, 55), (sx + 3, int(sy + 9 + bob)),
                         (sx + 3, int(sy + 18 + bob)), 2)

    # 名称标签
    name_txt = _render_outlined(_font_xs, i18n.t(loc.name), loc.color)
    surface.blit(name_txt, (sx - name_txt.get_width() // 2, sy + hh + 5))


# ========== 地面绘制 ==========
def draw_ground(surface, cam_x, cam_y, t):
    """绘制城镇地面"""
    # 基本地面
    surface.fill((18, 22, 15))

    # 地面纹理（草地格子）
    tile_size = 60
    start_tx = int(cam_x // tile_size) - 1
    start_ty = int(cam_y // tile_size) - 1
    end_tx = start_tx + WIDTH // tile_size + 3
    end_ty = start_ty + HEIGHT // tile_size + 3

    for tx in range(start_tx, end_tx):
        for ty in range(start_ty, end_ty):
            wx = tx * tile_size
            wy = ty * tile_size
            sx = wx - int(cam_x)
            sy = wy - int(cam_y)

            # 检查是否在地图内
            if wx < 0 or wx >= MAP_W or wy < 0 or wy >= MAP_H:
                # 地图外 — 暗色
                pygame.draw.rect(surface, (8, 8, 12), (sx, sy, tile_size, tile_size))
                continue

            # 棋盘格草地
            shade = 3 if (tx + ty) % 2 == 0 else 0
            grass_color = (22 + shade, 28 + shade, 18 + shade)
            pygame.draw.rect(surface, grass_color, (sx, sy, tile_size, tile_size))

    # 石板路径
    for px, py, pw, ph in TOWN_PATHS:
        psx = int(px - cam_x)
        psy = int(py - cam_y)
        if psx > WIDTH + 100 or psx + pw < -100 or psy > HEIGHT + 100 or psy + ph < -100:
            continue
        path_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(path_surf, (45, 42, 38, 200), (0, 0, pw, ph), border_radius=3)
        # 石板纹理
        stone_size = 28
        for si in range(0, pw, stone_size):
            for sj in range(0, ph, stone_size):
                offset = (sj // stone_size % 2) * stone_size // 2
                sx2 = si + offset
                if sx2 < pw and sj < ph:
                    sw = min(stone_size - 2, pw - sx2 - 1)
                    sh = min(stone_size - 2, ph - sj - 1)
                    if sw > 2 and sh > 2:
                        shade = random.Random(si * 100 + sj).randint(0, 8)
                        pygame.draw.rect(path_surf, (50 + shade, 47 + shade, 42 + shade, 180),
                                         (sx2, sj, sw, sh), border_radius=1)
        surface.blit(path_surf, (psx, psy))


# ========== 互动提示 ==========
def draw_interaction_prompt(surface, loc, cam_x, cam_y, t):
    """当玩家靠近互动点时显示提示"""
    sx = int(loc.x - cam_x)
    sy = int(loc.y - cam_y)

    # 提示框
    prompt_w = 220
    prompt_h = 60
    prompt_x = sx - prompt_w // 2
    prompt_y = sy - loc.h // 2 - prompt_h - 15

    # 浮动效果
    bob = math.sin(t * 3) * 3

    ps = pygame.Surface((prompt_w, prompt_h), pygame.SRCALPHA)
    pygame.draw.rect(ps, (10, 8, 18, 210), (0, 0, prompt_w, prompt_h), border_radius=8)
    pygame.draw.rect(ps, (*loc.color, 180), (0, 0, prompt_w, prompt_h), 2, border_radius=8)

    # 名称
    nt = _render_outlined(_font_sm, i18n.t(loc.name), loc.color)
    ps.blit(nt, (prompt_w // 2 - nt.get_width() // 2, 5))

    # 操作提示
    action_txt = _render_outlined(_font_xs, i18n.t("按 E 或 点击 互动"), (200, 200, 220))
    ps.blit(action_txt, (prompt_w // 2 - action_txt.get_width() // 2, 32))

    surface.blit(ps, (prompt_x, int(prompt_y + bob)))

    # 高亮圈
    hr = max(loc.w, loc.h) // 2 + 10
    hs = pygame.Surface((hr * 2 + 4, hr * 2 + 4), pygame.SRCALPHA)
    pulse = (math.sin(t * 4) + 1) * 0.5
    ha = int(40 + pulse * 40)
    pygame.draw.circle(hs, (*loc.color, ha), (hr + 2, hr + 2), hr, 2)
    surface.blit(hs, (sx - hr - 2, sy - hr - 2))


# ========== 小地图 ==========
def draw_minimap(surface, player, t):
    """绘制右上角小地图"""
    mm_w, mm_h = 180, 120
    mm_x, mm_y = WIDTH - mm_w - 15, 15

    mm = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
    pygame.draw.rect(mm, (10, 10, 15, 180), (0, 0, mm_w, mm_h), border_radius=5)
    pygame.draw.rect(mm, (80, 80, 100, 120), (0, 0, mm_w, mm_h), 1, border_radius=5)

    # 缩放比例
    scale_x = (mm_w - 10) / MAP_W
    scale_y = (mm_h - 10) / MAP_H

    # 路径
    for px, py, pw, ph in TOWN_PATHS:
        rx = int(5 + px * scale_x)
        ry = int(5 + py * scale_y)
        rw = max(2, int(pw * scale_x))
        rh = max(2, int(ph * scale_y))
        pygame.draw.rect(mm, (50, 48, 42, 150), (rx, ry, rw, rh))

    # 互动点
    for loc in TOWN_LOCATIONS:
        lx = int(5 + loc.x * scale_x)
        ly = int(5 + loc.y * scale_y)
        pygame.draw.circle(mm, (*loc.color, 200), (lx, ly), 3)

    # 玩家
    pp_x = int(5 + player.x * scale_x)
    pp_y = int(5 + player.y * scale_y)
    pulse = (math.sin(t * 5) + 1) * 0.5
    pygame.draw.circle(mm, (255, 255, 255, 220), (pp_x, pp_y), int(3 + pulse))

    # 视野框
    vw = int(WIDTH * scale_x)
    vh = int(HEIGHT * scale_y)
    cam_x = player.x - WIDTH // 2
    cam_y = player.y - HEIGHT // 2
    vx = int(5 + max(0, cam_x) * scale_x)
    vy = int(5 + max(0, cam_y) * scale_y)
    pygame.draw.rect(mm, (255, 255, 255, 60), (vx, vy, vw, vh), 1)

    surface.blit(mm, (mm_x, mm_y))

    # 标题
    mt = _render_outlined(_font_xs, "深渊城镇", (120, 120, 140))
    surface.blit(mt, (mm_x + mm_w // 2 - mt.get_width() // 2, mm_y + mm_h + 3))


# ========== 货币信息栏 ==========
def draw_currency_bar(surface, save_data):
    """绘制顶部左侧货币信息"""
    bar_w, bar_h = 350, 32
    bar = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
    pygame.draw.rect(bar, (10, 10, 15, 160), (0, 0, bar_w, bar_h), border_radius=6)
    pygame.draw.rect(bar, (60, 60, 80, 100), (0, 0, bar_w, bar_h), 1, border_radius=6)

    gold = save_data.get('gold', 0)
    diamond = save_data.get('diamond', 0)
    soul = save_data.get('soul_shards', 0)

    ct = _render_outlined(_font_xs, f"金: {gold}  钻: {diamond}  魂: {soul}", GOLD)
    bar.blit(ct, (bar_w // 2 - ct.get_width() // 2, bar_h // 2 - ct.get_height() // 2))
    surface.blit(bar, (15, 15))


# ========== 主绘制函数 ==========
def draw_town(surface, player, save_data, t):
    """
    绘制完整城镇画面
    返回: 'action_name' 如果玩家触发互动, 否则 None
    """
    # 相机跟随玩家
    cam_x = player.x - WIDTH // 2
    cam_y = player.y - HEIGHT // 2
    # 限制相机范围
    cam_x = max(0, min(MAP_W - WIDTH, cam_x))
    cam_y = max(0, min(MAP_H - HEIGHT, cam_y))

    # 地面
    draw_ground(surface, cam_x, cam_y, t)

    # 装饰物（先画远处的）
    for dx, dy, dt_type in TOWN_DECORATIONS:
        draw_decoration(surface, dx, dy, dt_type, cam_x, cam_y, t)

    # 互动点建筑
    for loc in TOWN_LOCATIONS:
        draw_location_building(surface, loc, cam_x, cam_y, t)

    # 玩家
    player.draw(surface, cam_x, cam_y)

    # 互动提示
    if player.nearby_location:
        draw_interaction_prompt(surface, player.nearby_location, cam_x, cam_y, t)

    # UI 层
    draw_minimap(surface, player, t)
    draw_currency_bar(surface, save_data)

    # 操作提示
    hint = _render_outlined(_font_xs, i18n.t("WASD 移动  |  E 互动  |  ESC 菜单"), (100, 100, 120))
    surface.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 25))

    return None
