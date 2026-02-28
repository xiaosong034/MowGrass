"""
《暗夜割草者：深渊轮回》 — 游戏主体
Roguelite自动武器割草游戏
========================================
操作:  WASD / 方向键 = 移动
       ESC = 暂停
       ※ 所有武器全自动，无需手动攻击!
========================================
"""

import pygame
import math
import random
import sys
import os
import json
import array
import meta_systems
import dialogue_system
import gacha_animation
import town_map
import i18n

# ============================================================
#  显示配置
# ============================================================
# 支持的分辨率（宽, 高）
AVAILABLE_RESOLUTIONS = [
    (1280, 720),   # HD
    (1366, 768),   # 笔记本常用
    (1600, 900),   # HD+
    (1920, 1080),  # Full HD
    (2560, 1440),  # 2K
]
DEFAULT_RESOLUTION = (1280, 720)

# ============================================================
#  初始化
# ============================================================
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
pygame.key.stop_text_input()  # 禁用IME，防止中文输入法拦截WASD按键

WIDTH, HEIGHT = DEFAULT_RESOLUTION
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(i18n.t("暗夜割草者：深渊轮回"))
clock = pygame.time.Clock()

# ============================================================
#  颜色
# ============================================================
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
DARK_BG    = (12, 12, 20)
GRID_COLOR = (22, 22, 35)
GOLD   = (255, 215, 0)
DARK_RED   = (150, 30, 30)
DARK_GREEN = (30, 80, 30)
ICE_BLUE   = (100, 200, 255)
LIME   = (180, 255, 60)

# ============================================================
#  字体
# ============================================================
def get_font(size, lang=None):
    """加载支持多语言的字体，根据语言选择最佳系统字体"""
    if lang is None:
        lang = i18n.get_language()

    # 按语言优先选择Windows自带系统字体，无需打包额外字体
    _FONT_PRIORITY = {
        'ko': [
            ('Malgun Gothic',        'C:/Windows/Fonts/malgun.ttf'),
            ('Microsoft YaHei',      'C:/Windows/Fonts/msyh.ttc'),
            ('Arial',                'C:/Windows/Fonts/arial.ttf'),
        ],
        'ja': [
            ('Yu Gothic',            'C:/Windows/Fonts/YuGothM.ttc'),
            ('MS Gothic',            'C:/Windows/Fonts/msgothic.ttc'),
            ('Microsoft YaHei',      'C:/Windows/Fonts/msyh.ttc'),
            ('Arial',                'C:/Windows/Fonts/arial.ttf'),
        ],
        'zh': [
            ('Microsoft YaHei',      'C:/Windows/Fonts/msyh.ttc'),
            ('SimHei',               'C:/Windows/Fonts/simhei.ttf'),
            ('Arial',                'C:/Windows/Fonts/arial.ttf'),
        ],
        'ru': [
            ('Arial',                'C:/Windows/Fonts/arial.ttf'),
            ('Segoe UI',             'C:/Windows/Fonts/segoeui.ttf'),
        ],
        'en': [
            ('Arial',                'C:/Windows/Fonts/arial.ttf'),
            ('Segoe UI',             'C:/Windows/Fonts/segoeui.ttf'),
        ],
    }

    candidates = _FONT_PRIORITY.get(lang, _FONT_PRIORITY['en'])

    # 1) 先尝试 SysFont（按语言顺序）
    sys_names = ','.join(name for name, _ in candidates)
    try:
        f = pygame.font.SysFont(sys_names, size)
        if f:
            return f
    except:
        pass

    # 2) 直接按路径加载
    for _, path in candidates:
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except:
                continue

    return pygame.font.Font(None, size)

font_title = get_font(64)
font_lg    = get_font(42)
font_md    = get_font(28)
font_sm    = get_font(20)
font_xs    = get_font(14)

def reload_fonts():
    """重新加载字体（语言切换或分辨率改变时调用）"""
    global font_title, font_lg, font_md, font_sm, font_xs
    # 根据当前语言动态调整字体优先级
    lang = i18n.get_language()
    font_title = get_font(64, lang)
    font_lg    = get_font(42, lang)
    font_md    = get_font(28, lang)
    font_sm    = get_font(20, lang)
    font_xs    = get_font(14, lang)
    # 重新初始化各模块的字体
    meta_systems.init(screen, font_lg, font_md, font_sm, font_xs, WIDTH, HEIGHT)
    dialogue_system.init(screen, font_lg, font_md, font_sm, font_xs, WIDTH, HEIGHT)
    gacha_animation.init(screen, font_lg, font_md, font_sm, font_xs, WIDTH, HEIGHT)
    town_map.init(screen, font_lg, font_md, font_sm, font_xs, WIDTH, HEIGHT)

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

# ============================================================
#  音效生成
# ============================================================
SOUND_ENABLED = True
try:
    def gen_sound(freq=440, dur=0.1, vol=0.3, wave='sine'):
        sr = 22050; n = int(sr * dur)
        buf = array.array('h', [0] * n)
        amp = int(32767 * vol)
        for i in range(n):
            t = i / sr; fade = 1.0 - i / n
            if wave == 'square':
                v = amp if math.sin(2*math.pi*freq*t) > 0 else -amp
            elif wave == 'noise':
                v = random.randint(-amp, amp)
            elif wave == 'saw':
                v = int(amp * (2*(freq*t % 1) - 1))
            else:
                v = int(amp * math.sin(2*math.pi*freq*t))
            buf[i] = max(-32767, min(32767, int(v * fade)))
        return pygame.mixer.Sound(buffer=buf)

    SFX = {
        'shoot':     gen_sound(800, 0.04, 0.15),
        'hit':       gen_sound(400, 0.05, 0.2),
        'kill':      gen_sound(600, 0.06, 0.2, 'square'),
        'exp':       gen_sound(1000, 0.03, 0.1),
        'levelup':   gen_sound(500, 0.3, 0.25),
        'heal':      gen_sound(700, 0.15, 0.2),
        'boss_roar': gen_sound(80, 0.4, 0.35, 'saw'),
        'ice':       gen_sound(1200, 0.08, 0.15),
        'fire':      gen_sound(200, 0.15, 0.25, 'noise'),
        'thunder':   gen_sound(150, 0.1, 0.3, 'noise'),
        'whip':      gen_sound(300, 0.06, 0.2, 'saw'),
        'shield':    gen_sound(500, 0.05, 0.15),
        'combo':     gen_sound(900, 0.04, 0.15),
        'select':    gen_sound(600, 0.08, 0.2),
    }
    def play_sfx(name):
        s = SFX.get(name)
        if s: s.play()
except Exception:
    SOUND_ENABLED = False
    def play_sfx(name): pass

# ============================================================
#  粒子系统
# ============================================================
class Particle:
    __slots__ = ('x','y','vx','vy','color','life','max_life','size','ptype','gravity')
    def __init__(self, x, y, vx, vy, color, life=1.0, size=4, ptype='normal', gravity=False):
        self.x = x; self.y = y; self.vx = vx; self.vy = vy
        self.color = color; self.life = life; self.max_life = life
        self.size = size; self.ptype = ptype; self.gravity = gravity
    def update(self, dt):
        self.x += self.vx * dt; self.y += self.vy * dt
        if self.gravity: self.vy += 300 * dt
        self.life -= dt
    def draw(self, surface, sh):
        if self.life <= 0: return
        a = max(0, min(255, int(255 * self.life / self.max_life)))
        sx = int(self.x + sh[0]); sy = int(self.y + sh[1])
        if self.ptype == 'spark':
            ex = sx - int(self.vx * 0.02); ey = sy - int(self.vy * 0.02)
            c = (*self.color[:3], a)
            s = pygame.Surface((abs(sx-ex)+4, abs(sy-ey)+4), pygame.SRCALPHA)
            pygame.draw.line(s, c, (2, 2), (abs(sx-ex)+2, abs(sy-ey)+2), max(1, int(self.size * self.life / self.max_life)))
            surface.blit(s, (min(sx,ex)-2, min(sy,ey)-2))
        else:
            r = max(1, int(self.size * self.life / self.max_life))
            ps = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*self.color[:3], a), (r+1, r+1), r)
            surface.blit(ps, (sx-r-1, sy-r-1))

particles = []

PARTICLE_PRESETS = {
    'explosion':  {'colors': [ORANGE, YELLOW, RED],    'spd': (80,250),  'life': (0.3,0.8), 'sz': (2,5), 'g': True},
    'blood':      {'colors': [RED, DARK_RED, PINK],    'spd': (40,150),  'life': (0.3,0.7), 'sz': (2,4), 'g': True},
    'ice':        {'colors': [ICE_BLUE, WHITE, CYAN],  'spd': (30,120),  'life': (0.4,0.9), 'sz': (2,5), 'g': False},
    'fire':       {'colors': [ORANGE, YELLOW, RED],    'spd': (50,180),  'life': (0.3,0.7), 'sz': (3,6), 'g': False},
    'thunder':    {'colors': [YELLOW, WHITE, ICE_BLUE], 'spd': (100,300), 'life': (0.1,0.3), 'sz': (1,3), 'g': False, 'pt': 'spark'},
    'poison':     {'colors': [(100,200,50), GREEN, LIME], 'spd': (20,80), 'life': (0.5,1.2), 'sz': (2,4), 'g': False},
    'heal':       {'colors': [GREEN, LIME, WHITE],     'spd': (20,60),   'life': (0.5,1.0), 'sz': (2,4), 'g': False},
    'levelup':    {'colors': [GOLD, YELLOW, WHITE],    'spd': (50,200),  'life': (0.5,1.5), 'sz': (3,7), 'g': False},
    'boss_death': {'colors': [PINK, PURPLE, RED, ORANGE, YELLOW], 'spd': (80,300), 'life': (0.5,1.5), 'sz': (3,8), 'g': True},
    'dark':       {'colors': [PURPLE, (100,0,150), PINK], 'spd': (30,100), 'life': (0.3,0.8), 'sz': (2,5), 'g': False},
    'exp_pickup': {'colors': [CYAN, WHITE],            'spd': (10,40),   'life': (0.2,0.5), 'sz': (1,3), 'g': False},
}

def create_particles(x, y, count, ptype='explosion'):
    cfg = PARTICLE_PRESETS.get(ptype, PARTICLE_PRESETS['explosion'])
    pt = cfg.get('pt', 'normal')
    for _ in range(count):
        angle = random.uniform(0, math.pi*2)
        spd = random.uniform(*cfg['spd'])
        particles.append(Particle(
            x, y, math.cos(angle)*spd, math.sin(angle)*spd,
            random.choice(cfg['colors']),
            random.uniform(*cfg['life']),
            random.uniform(*cfg['sz']),
            pt, cfg.get('g', False)
        ))

# ============================================================
#  屏幕震动
# ============================================================
class ScreenShake:
    def __init__(self):
        self.intensity = 0; self.timer = 0; self.offset = [0,0]
    def trigger(self, intensity, duration):
        self.intensity = max(self.intensity, intensity)
        self.timer = max(self.timer, duration)
    def update(self, dt):
        if self.timer > 0:
            self.timer -= dt
            self.offset[0] = random.uniform(-self.intensity, self.intensity)
            self.offset[1] = random.uniform(-self.intensity, self.intensity)
            self.intensity *= 0.92
        else:
            self.offset = [0,0]; self.intensity = 0

screen_shake = ScreenShake()

# ============================================================
#  导入角色和Boss模块
# ============================================================
import characters
import boss as boss_module

# ============================================================
#  连击系统
# ============================================================
class ComboSystem:
    def __init__(self):
        self.reset()
    def reset(self):
        self.count = 0; self.timer = 0; self.best = 0
        self.texts = []  # [(text, x, y, life, color)]
    def add_kill(self, x, y):
        self.count += 1; self.timer = 2.0
        self.best = max(self.best, self.count)
        if self.count >= 10:
            play_sfx('combo')
        # 浮动文字
        if self.count % 50 == 0 and self.count >= 50:
            self.texts.append((i18n.t("超神!! x{count}", count=self.count), x, y, 2.0, GOLD))
        elif self.count % 25 == 0 and self.count >= 25:
            self.texts.append((i18n.t("无双! x{count}", count=self.count), x, y, 1.5, PINK))
        elif self.count % 10 == 0 and self.count >= 10:
            self.texts.append((i18n.t("连击 x{count}", count=self.count), x, y, 1.2, YELLOW))

    @property
    def multiplier(self):
        if self.count >= 500: return 1.3
        if self.count >= 200: return 1.15
        if self.count >= 100: return 1.1
        if self.count >= 50: return 1.05
        return 1.0

    def update(self, dt):
        if self.timer > 0:
            self.timer -= dt
            if self.timer <= 0:
                self.count = 0
        for t in self.texts:
            pass  # 这里只是标记
        self.texts = [(txt, x, y-30*dt, l-dt, c) for txt, x, y, l, c in self.texts if l > dt]

    def draw(self, surface, sh):
        if self.count >= 5:
            bar_w = min(200, self.count)
            bar_x = WIDTH // 2 - 100
            pygame.draw.rect(surface, (40, 40, 40), (bar_x, 8, 200, 14), border_radius=4)
            c = YELLOW if self.count < 100 else (GOLD if self.count < 200 else PINK)
            pygame.draw.rect(surface, c, (bar_x, 8, bar_w, 14), border_radius=4)
            ct = _render_outlined(font_xs, f"COMBO x{self.count}", c)
            surface.blit(ct, (WIDTH // 2 - ct.get_width() // 2, 24))
        for txt, x, y, l, c in self.texts:
            if l > 0:
                a = max(0, min(255, int(255 * l)))
                ts = _render_outlined(font_md, txt, c)
                ts.set_alpha(a)
                surface.blit(ts, (int(x + sh[0]) - ts.get_width()//2, int(y + sh[1])))

combo = ComboSystem()

# ============================================================
#  经验宝石
# ============================================================
class ExpGem:
    def __init__(self, x, y, value=1, gem_type='blue'):
        self.x = x; self.y = y; self.value = value
        self.gem_type = gem_type
        self.life = 60.0  # 60秒后消失
        self.flash = False
        self.bob = random.uniform(0, math.pi*2)
        self.magnet = False  # 是否被吸引中
        # 颜色
        self.color = {
            'blue': (80, 150, 255),
            'green': (80, 255, 100),
            'yellow': (255, 255, 80),
            'red': (255, 80, 80),
        }.get(gem_type, (80, 150, 255))
        self.size = {
            'blue': 4, 'green': 5, 'yellow': 6, 'red': 8,
        }.get(gem_type, 4)

    def update(self, dt, player_x, player_y, pickup_range):
        self.life -= dt
        self.bob += dt * 3
        if self.life < 15:
            self.flash = True
        # 吸取
        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.hypot(dx, dy)
        if dist < pickup_range or self.magnet:
            self.magnet = True
            speed = 600 if dist > 30 else 300
            if dist > 1:
                self.x += dx / dist * speed * dt
                self.y += dy / dist * speed * dt
            return dist < 15  # 拾取成功
        return False

    def draw(self, surface, sh):
        if self.life <= 0: return
        if self.flash and int(self.life * 6) % 2 == 0: return
        sx = int(self.x + sh[0])
        sy = int(self.y + sh[1] + math.sin(self.bob) * 3)
        # 发光
        gs = pygame.Surface((self.size*4+4, self.size*4+4), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*self.color, 60), (self.size*2+2, self.size*2+2), self.size*2)
        surface.blit(gs, (sx-self.size*2-2, sy-self.size*2-2))
        pygame.draw.circle(surface, self.color, (sx, sy), self.size)
        pygame.draw.circle(surface, WHITE, (sx, sy), max(1, self.size-2))

exp_gems = []

def spawn_exp_gem(x, y, enemy_type='normal'):
    """根据敌人类型掉落不同经验宝石"""
    if enemy_type == 'boss':
        for _ in range(8):
            ox = random.uniform(-30, 30)
            oy = random.uniform(-30, 30)
            exp_gems.append(ExpGem(x+ox, y+oy, 10, 'red'))
    elif enemy_type == 'elite':
        exp_gems.append(ExpGem(x, y, 5, 'yellow'))
    elif enemy_type == 'enhanced':
        exp_gems.append(ExpGem(x, y, 3, 'green'))
    else:
        exp_gems.append(ExpGem(x, y, 1, 'blue'))


# ============================================================
#  武器系统
# ============================================================
class WeaponBase:
    """武器基类 - 所有武器自动发射"""
    WEAPON_NAME = "武器"
    WEAPON_DESC = ""
    WEAPON_COLOR = WHITE
    WEAPON_CD = 1.0  # 基础冷却

    def __init__(self):
        self.level = 1
        self.max_level = 8
        self.cd_timer = 0
        self.projectiles = []  # 武器产生的投射物

    @property
    def display_name(self):
        """返回本地化后的武器名称"""
        return i18n.t(self.WEAPON_NAME)

    @property
    def display_desc(self):
        """返回本地化后的武器描述"""
        return i18n.t(self.WEAPON_DESC)

    def get_cooldown(self, cdr=0):
        return max(self.WEAPON_CD * 0.3, self.WEAPON_CD * (1 - cdr) * (1 - self.level * 0.05))

    def get_damage(self, dmg_bonus=0):
        base = self._base_damage()
        return base * (1 + dmg_bonus) * (1 + self.level * 0.12)

    def _base_damage(self):
        return 20

    def update(self, dt, px, py, enemies, cdr=0, dmg_bonus=0):
        """每帧更新 - 自动攻击"""
        self.cd_timer -= dt
        # 更新投射物
        alive = []
        for proj in self.projectiles:
            proj['life'] -= dt
            proj['x'] += proj.get('vx', 0) * dt
            proj['y'] += proj.get('vy', 0) * dt
            if proj.get('homing') and enemies:
                # 追踪最近敌人
                best_d = 9999; tgt = None
                for e in enemies:
                    d = math.hypot(e.x-proj['x'], e.y-proj['y'])
                    if d < best_d: best_d = d; tgt = e
                if tgt and best_d < 400:
                    dx = tgt.x - proj['x']; dy = tgt.y - proj['y']
                    dd = math.hypot(dx, dy)
                    if dd > 0:
                        turn = 5 * dt  # 转向速度
                        proj['vx'] += dx/dd * turn * 300
                        proj['vy'] += dy/dd * turn * 300
                        spd = math.hypot(proj['vx'], proj['vy'])
                        if spd > 350:
                            proj['vx'] = proj['vx']/spd * 350
                            proj['vy'] = proj['vy']/spd * 350
            if proj['life'] > 0:
                alive.append(proj)
        self.projectiles = alive

        # 冷却结束则发射
        if self.cd_timer <= 0:
            self.cd_timer = self.get_cooldown(cdr)
            self._fire(px, py, enemies, dmg_bonus)

    def _fire(self, px, py, enemies, dmg_bonus):
        """发射攻击 (子类覆盖)"""
        pass

    def check_hits(self, enemies, dmg_bonus=0):
        """检测投射物与敌人碰撞"""
        hits = []  # [(enemy, damage, proj_x, proj_y)]
        for proj in self.projectiles:
            if proj.get('hit'): continue
            damage = proj.get('damage', self.get_damage(dmg_bonus))
            radius = proj.get('radius', 8)
            pierce = proj.get('pierce', 0)
            for e in enemies:
                if not e.alive: continue
                d = math.hypot(e.x - proj['x'], e.y - proj['y'])
                if d < e.size + radius:
                    hits.append((e, damage, proj['x'], proj['y'], proj))
                    if pierce <= 0:
                        proj['hit'] = True
                        proj['life'] = 0
                    else:
                        proj['pierce'] = pierce - 1
                    break
        return hits

    def draw_projectiles(self, surface, sh):
        """绘制投射物 (子类可覆盖)"""
        for p in self.projectiles:
            if p.get('hit') or p['life'] <= 0: continue
            sx = int(p['x'] + sh[0]); sy = int(p['y'] + sh[1])
            c = p.get('color', self.WEAPON_COLOR)
            r = p.get('draw_radius', 5)
            pygame.draw.circle(surface, c, (sx, sy), r)

    def level_up_desc(self):
        return f"Lv.{self.level} → Lv.{self.level+1}"


# ---- 武器1: 魔法飞弹 ----
class MagicMissile(WeaponBase):
    WEAPON_NAME = "魔法飞弹"
    WEAPON_DESC = "自动追踪最近敌人的魔法弹"
    WEAPON_COLOR = CYAN
    WEAPON_CD = 1.2

    @property
    def display_name(self):
        return i18n.t(self.WEAPON_NAME)

    @property
    def display_desc(self):
        return i18n.t(self.WEAPON_DESC)

    def _base_damage(self): return 20

    def _fire(self, px, py, enemies, dmg_bonus):
        count = 1 + self.level // 3  # Lv1:1, Lv3:2, Lv6:3
        targets = sorted(enemies, key=lambda e: math.hypot(e.x-px, e.y-py))[:count]
        for i, tgt in enumerate(targets):
            angle = math.atan2(tgt.y - py, tgt.x - px)
            self.projectiles.append({
                'x': px, 'y': py,
                'vx': math.cos(angle) * 300,
                'vy': math.sin(angle) * 300,
                'life': 3.0,
                'damage': self.get_damage(dmg_bonus),
                'homing': True,
                'radius': 8,
                'color': CYAN,
                'draw_radius': 5,
                'hit': False, 'pierce': 0,
            })
        if targets:
            play_sfx('shoot')

    def draw_projectiles(self, surface, sh):
        for p in self.projectiles:
            if p.get('hit') or p['life'] <= 0: continue
            sx = int(p['x'] + sh[0]); sy = int(p['y'] + sh[1])
            # 尾迹
            ts = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(ts, (*CYAN, 100), (8, 8), 8)
            surface.blit(ts, (sx-8, sy-8))
            pygame.draw.circle(surface, CYAN, (sx, sy), 4)
            pygame.draw.circle(surface, WHITE, (sx, sy), 2)


# ---- 武器2: 圣光鞭 ----
class HolyWhip(WeaponBase):
    WEAPON_NAME = "圣光鞭"
    WEAPON_DESC = "近身范围扇形攻击 + 击退"
    WEAPON_COLOR = GOLD
    WEAPON_CD = 1.5

    @property
    def display_name(self):
        return i18n.t(self.WEAPON_NAME)

    @property
    def display_desc(self):
        return i18n.t(self.WEAPON_DESC)

    def __init__(self):
        super().__init__()
        self._swing_timer = 0
        self._swing_angle = 0
        self._swing_active = False

    def _base_damage(self): return 30

    def _fire(self, px, py, enemies, dmg_bonus):
        # 找最近敌人方向
        if enemies:
            nearest = min(enemies, key=lambda e: math.hypot(e.x-px, e.y-py))
            self._swing_angle = math.atan2(nearest.y - py, nearest.x - px)
        else:
            self._swing_angle = 0
        self._swing_timer = 0.3
        self._swing_active = True
        play_sfx('whip')

    def update(self, dt, px, py, enemies, cdr=0, dmg_bonus=0):
        self.cd_timer -= dt
        if self._swing_timer > 0:
            self._swing_timer -= dt
            if self._swing_timer <= 0:
                self._swing_active = False
        if self.cd_timer <= 0:
            self.cd_timer = self.get_cooldown(cdr)
            self._fire(px, py, enemies, dmg_bonus)

    def check_hits(self, enemies, dmg_bonus=0):
        hits = []
        if not self._swing_active: return hits
        if self._swing_timer < 0.15: return hits  # 只在前半段判定
        px, py = WIDTH // 2, HEIGHT // 2  # 玩家固定在中心
        reach = 100 + self.level * 15
        half_arc = math.pi / 3 + self.level * 0.05
        for e in enemies:
            d = math.hypot(e.x - px, e.y - py)
            if d > reach: continue
            angle = math.atan2(e.y - py, e.x - px)
            diff = abs((angle - self._swing_angle + math.pi) % (2*math.pi) - math.pi)
            if diff < half_arc:
                hits.append((e, self.get_damage(dmg_bonus), e.x, e.y, None))
        return hits

    def draw_projectiles(self, surface, sh):
        if not self._swing_active: return
        px = WIDTH // 2 + int(sh[0]); py = HEIGHT // 2 + int(sh[1])
        reach = 100 + self.level * 15
        half_arc = math.pi / 3 + self.level * 0.05
        prog = 1.0 - self._swing_timer / 0.3
        # 扇形
        ws = pygame.Surface((reach*2+4, reach*2+4), pygame.SRCALPHA)
        cx, cy = reach+2, reach+2
        a = max(0, min(180, int(180 * (1 - prog))))
        steps = 12
        pts = [(cx, cy)]
        for i in range(steps + 1):
            ang = self._swing_angle - half_arc + (2*half_arc) * i / steps
            pts.append((cx + int(math.cos(ang) * reach), cy + int(math.sin(ang) * reach)))
        if len(pts) > 2:
            pygame.draw.polygon(ws, (*GOLD, a), pts)
            pygame.draw.polygon(ws, (*WHITE, min(255, a+50)), pts, 2)
        surface.blit(ws, (px - reach - 2, py - reach - 2))


# ---- 武器3: 寒冰新星 ----
class IceNova(WeaponBase):
    WEAPON_NAME = "寒冰新星"
    WEAPON_DESC = "以自身为中心释放寒冰冲击波"
    WEAPON_COLOR = ICE_BLUE
    WEAPON_CD = 3.0

    def __init__(self):
        super().__init__()
        self._nova_radius = 0
        self._nova_max = 0
        self._nova_active = False
        self._nova_hit_set = set()

    def _base_damage(self): return 25

    def _fire(self, px, py, enemies, dmg_bonus):
        self._nova_radius = 0
        self._nova_max = 120 + self.level * 20
        self._nova_active = True
        self._nova_hit_set.clear()
        play_sfx('ice')
        create_particles(px, py, 15, 'ice')

    def update(self, dt, px, py, enemies, cdr=0, dmg_bonus=0):
        self.cd_timer -= dt
        if self._nova_active:
            self._nova_radius += 400 * dt
            if self._nova_radius >= self._nova_max:
                self._nova_active = False
        if self.cd_timer <= 0:
            self.cd_timer = self.get_cooldown(cdr)
            self._fire(px, py, enemies, dmg_bonus)

    def check_hits(self, enemies, dmg_bonus=0):
        hits = []
        if not self._nova_active: return hits
        px, py = WIDTH // 2, HEIGHT // 2
        for e in enemies:
            if id(e) in self._nova_hit_set: continue
            d = math.hypot(e.x - px, e.y - py)
            if d < self._nova_radius + e.size:
                hits.append((e, self.get_damage(dmg_bonus), e.x, e.y, None))
                self._nova_hit_set.add(id(e))
                e.slow_timer = 2.0 + self.level * 0.3  # 减速效果
                e.slow_factor = 0.4
        return hits

    def draw_projectiles(self, surface, sh):
        if not self._nova_active: return
        px = WIDTH // 2 + int(sh[0]); py = HEIGHT // 2 + int(sh[1])
        r = int(self._nova_radius)
        if r < 2: return
        a = max(0, min(150, int(150 * (1 - self._nova_radius / self._nova_max))))
        ns = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
        pygame.draw.circle(ns, (*ICE_BLUE, a), (r+2, r+2), r)
        pygame.draw.circle(ns, (*WHITE, min(255, a + 60)), (r+2, r+2), r, 2)
        surface.blit(ns, (px-r-2, py-r-2))


# ---- 武器4: 烈焰之球 ----
class Fireball(WeaponBase):
    WEAPON_NAME = "烈焰之球"
    WEAPON_DESC = "向随机方向发射穿透火球"
    WEAPON_COLOR = ORANGE
    WEAPON_CD = 2.5

    def _base_damage(self): return 35

    def _fire(self, px, py, enemies, dmg_bonus):
        if enemies:
            tgt = random.choice(enemies)
            angle = math.atan2(tgt.y - py, tgt.x - px)
        else:
            angle = random.uniform(0, math.pi * 2)
        count = 1 + self.level // 4
        for i in range(count):
            a = angle + (i - count//2) * 0.3
            self.projectiles.append({
                'x': px, 'y': py,
                'vx': math.cos(a) * 280,
                'vy': math.sin(a) * 280,
                'life': 3.5,
                'damage': self.get_damage(dmg_bonus),
                'homing': False,
                'radius': 12,
                'pierce': 3 + self.level,
                'color': ORANGE,
                'draw_radius': 8,
                'hit': False,
            })
        play_sfx('fire')

    def draw_projectiles(self, surface, sh):
        for p in self.projectiles:
            if p.get('hit') or p['life'] <= 0: continue
            sx = int(p['x'] + sh[0]); sy = int(p['y'] + sh[1])
            # 火焰光晕
            gs = pygame.Surface((24, 24), pygame.SRCALPHA)
            pygame.draw.circle(gs, (255, 100, 0, 80), (12, 12), 12)
            surface.blit(gs, (sx-12, sy-12))
            pygame.draw.circle(surface, ORANGE, (sx, sy), 6)
            pygame.draw.circle(surface, YELLOW, (sx, sy), 3)
            # 拖尾粒子
            if random.random() < 0.3:
                create_particles(p['x'], p['y'], 1, 'fire')


# ---- 武器5: 雷电法阵 ----
class LightningCircle(WeaponBase):
    WEAPON_NAME = "雷电法阵"
    WEAPON_DESC = "在随机位置生成持续电击区域"
    WEAPON_COLOR = YELLOW
    WEAPON_CD = 4.0

    def __init__(self):
        super().__init__()
        self._circles = []  # [{'x','y','timer','radius','hit_cd'}]

    def _base_damage(self): return 15

    def _fire(self, px, py, enemies, dmg_bonus):
        count = 1 + self.level // 3
        for _ in range(count):
            if enemies:
                tgt = random.choice(enemies)
                cx, cy = tgt.x, tgt.y
            else:
                cx = px + random.uniform(-150, 150)
                cy = py + random.uniform(-150, 150)
            self._circles.append({
                'x': cx, 'y': cy,
                'timer': 2.0 + self.level * 0.3,
                'radius': 60 + self.level * 10,
                'hit_cd': 0,
            })
        play_sfx('thunder')

    def update(self, dt, px, py, enemies, cdr=0, dmg_bonus=0):
        self.cd_timer -= dt
        alive_c = []
        for c in self._circles:
            c['timer'] -= dt
            c['hit_cd'] -= dt
            if c['timer'] > 0:
                alive_c.append(c)
        self._circles = alive_c
        if self.cd_timer <= 0:
            self.cd_timer = self.get_cooldown(cdr)
            self._fire(px, py, enemies, dmg_bonus)

    def check_hits(self, enemies, dmg_bonus=0):
        hits = []
        for c in self._circles:
            if c['hit_cd'] > 0: continue
            for e in enemies:
                d = math.hypot(e.x - c['x'], e.y - c['y'])
                if d < c['radius'] + e.size:
                    hits.append((e, self.get_damage(dmg_bonus), e.x, e.y, None))
            if hits:
                c['hit_cd'] = 0.3
                create_particles(c['x'], c['y'], 3, 'thunder')
        return hits

    def draw_projectiles(self, surface, sh):
        for c in self._circles:
            sx = int(c['x'] + sh[0]); sy = int(c['y'] + sh[1])
            r = int(c['radius'])
            a = max(0, min(100, int(100 * c['timer'] / 2.0)))
            cs = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(cs, (*YELLOW, a), (r+2, r+2), r)
            pygame.draw.circle(cs, (*WHITE, min(255, a+80)), (r+2, r+2), r, 2)
            # 闪电线
            for _ in range(3):
                ang = random.uniform(0, math.pi*2)
                lr = random.uniform(r*0.3, r*0.9)
                lx = r+2 + int(math.cos(ang)*lr)
                ly = r+2 + int(math.sin(ang)*lr)
                pygame.draw.line(cs, (*WHITE, 200), (r+2, r+2), (lx, ly), 1)
            surface.blit(cs, (sx-r-2, sy-r-2))


# ---- 武器6: 白骨之盾 ----
class BoneShield(WeaponBase):
    WEAPON_NAME = "白骨之盾"
    WEAPON_DESC = "环绕角色旋转的骨盾"
    WEAPON_COLOR = (200, 200, 180)
    WEAPON_CD = 99999  # 永久存在，无冷却

    def __init__(self):
        super().__init__()
        self._orbit_angle = 0
        self._shards = []  # 每个碎片的角度偏移
        self._rebuild()

    def _rebuild(self):
        count = 3 + self.level
        self._shards = [i * math.pi * 2 / count for i in range(count)]

    def _base_damage(self): return 12

    def _fire(self, px, py, enemies, dmg_bonus):
        pass  # 不需要发射

    def update(self, dt, px, py, enemies, cdr=0, dmg_bonus=0):
        self._orbit_angle += dt * (2.5 + self.level * 0.3)
        orbit_r = 50 + self.level * 5
        # 碰撞检测
        for off in self._shards:
            ang = self._orbit_angle + off
            sx = px + math.cos(ang) * orbit_r
            sy = py + math.sin(ang) * orbit_r
            for e in enemies:
                if not e.alive: continue
                d = math.hypot(e.x - sx, e.y - sy)
                if d < e.size + 10:
                    e.health -= self.get_damage(dmg_bonus) * dt * 3
                    e.flash_timer = 0.05
                    if random.random() < dt:
                        create_particles(sx, sy, 2, 'explosion')

    def check_hits(self, enemies, dmg_bonus=0):
        return []  # 伤害在update中直接应用

    def draw_projectiles(self, surface, sh):
        px = WIDTH // 2 + int(sh[0]); py = HEIGHT // 2 + int(sh[1])
        orbit_r = 50 + self.level * 5
        for off in self._shards:
            ang = self._orbit_angle + off
            sx = px + int(math.cos(ang) * orbit_r)
            sy = py + int(math.sin(ang) * orbit_r)
            # 骨片
            pts = [
                (sx + int(math.cos(ang)*8), sy + int(math.sin(ang)*8)),
                (sx + int(math.cos(ang+1.5)*5), sy + int(math.sin(ang+1.5)*5)),
                (sx + int(math.cos(ang-1.5)*5), sy + int(math.sin(ang-1.5)*5)),
            ]
            pygame.draw.polygon(surface, (200, 200, 180), pts)
            pygame.draw.polygon(surface, WHITE, pts, 1)


# ---- 武器7: 回旋镖 ----
class Boomerang(WeaponBase):
    WEAPON_NAME = "回旋镖"
    WEAPON_DESC = "飞出再返回，穿透所有敌人"
    WEAPON_COLOR = LIME
    WEAPON_CD = 1.8

    def _base_damage(self): return 22

    def _fire(self, px, py, enemies, dmg_bonus):
        if enemies:
            tgt = min(enemies, key=lambda e: math.hypot(e.x-px, e.y-py))
            angle = math.atan2(tgt.y - py, tgt.x - px)
        else:
            angle = random.uniform(0, math.pi*2)
        count = 1 + self.level // 4
        for i in range(count):
            a = angle + i * math.pi * 2 / max(count, 1)
            self.projectiles.append({
                'x': px, 'y': py,
                'vx': math.cos(a) * 400,
                'vy': math.sin(a) * 400,
                'life': 2.5,
                'damage': self.get_damage(dmg_bonus),
                'pierce': 999,  # 无限穿透
                'radius': 12,
                'phase': 'out',  # 'out' → 'back'
                'start_x': px, 'start_y': py,
                'color': LIME,
                'draw_radius': 7,
                'hit': False,
                'spin': 0,
                '_hit_ids': set(),
            })
        play_sfx('shoot')

    def update(self, dt, px, py, enemies, cdr=0, dmg_bonus=0):
        self.cd_timer -= dt
        alive = []
        for p in self.projectiles:
            p['life'] -= dt
            p['spin'] += dt * 15
            if p['phase'] == 'out':
                p['x'] += p['vx'] * dt
                p['y'] += p['vy'] * dt
                p['vx'] *= 0.97; p['vy'] *= 0.97
                if math.hypot(p['vx'], p['vy']) < 50:
                    p['phase'] = 'back'
            else:
                dx = px - p['x']; dy = py - p['y']
                d = math.hypot(dx, dy)
                if d < 20:
                    p['life'] = 0; continue
                spd = 500
                p['vx'] = dx/d * spd; p['vy'] = dy/d * spd
                p['x'] += p['vx'] * dt; p['y'] += p['vy'] * dt
                p['_hit_ids'].clear()  # 返回时可以再次命中
            if p['life'] > 0:
                alive.append(p)
        self.projectiles = alive
        if self.cd_timer <= 0:
            self.cd_timer = self.get_cooldown(cdr)
            self._fire(px, py, enemies, dmg_bonus)

    def check_hits(self, enemies, dmg_bonus=0):
        hits = []
        for p in self.projectiles:
            if p.get('hit') or p['life'] <= 0: continue
            for e in enemies:
                if not e.alive: continue
                if id(e) in p.get('_hit_ids', set()): continue
                d = math.hypot(e.x - p['x'], e.y - p['y'])
                if d < e.size + p['radius']:
                    hits.append((e, self.get_damage(dmg_bonus), p['x'], p['y'], p))
                    p['_hit_ids'].add(id(e))
        return hits

    def draw_projectiles(self, surface, sh):
        for p in self.projectiles:
            if p.get('hit') or p['life'] <= 0: continue
            sx = int(p['x'] + sh[0]); sy = int(p['y'] + sh[1])
            # 旋转十字
            r = 8
            spin = p['spin']
            for i in range(4):
                a = spin + i * math.pi / 2
                ex = sx + int(math.cos(a) * r)
                ey = sy + int(math.sin(a) * r)
                pygame.draw.line(surface, LIME, (sx, sy), (ex, ey), 3)
            pygame.draw.circle(surface, WHITE, (sx, sy), 3)


# ---- 武器8: 地刺术 ----
class EarthSpikes(WeaponBase):
    WEAPON_NAME = "地刺术"
    WEAPON_DESC = "在敌人密集处召唤地刺"
    WEAPON_COLOR = (180, 130, 80)
    WEAPON_CD = 3.5

    def __init__(self):
        super().__init__()
        self._spikes = []  # [{'x','y','timer','phase'}]

    def _base_damage(self): return 28

    def _fire(self, px, py, enemies, dmg_bonus):
        count = 3 + self.level
        # 选择敌人密集区域
        spots = []
        if enemies:
            for _ in range(count):
                e = random.choice(enemies)
                spots.append((e.x + random.uniform(-20, 20), e.y + random.uniform(-20, 20)))
        else:
            for _ in range(count):
                spots.append((px + random.uniform(-100, 100), py + random.uniform(-100, 100)))
        for x, y in spots:
            self._spikes.append({'x': x, 'y': y, 'timer': 1.0, 'phase': 'warn', 'hit': False})
        play_sfx('thunder')

    def update(self, dt, px, py, enemies, cdr=0, dmg_bonus=0):
        self.cd_timer -= dt
        alive = []
        for s in self._spikes:
            s['timer'] -= dt
            if s['phase'] == 'warn' and s['timer'] < 0.5:
                s['phase'] = 'spike'
                s['timer'] = 0.5
            elif s['phase'] == 'spike' and s['timer'] <= 0:
                continue
            alive.append(s)
        self._spikes = alive
        if self.cd_timer <= 0:
            self.cd_timer = self.get_cooldown(cdr)
            self._fire(px, py, enemies, dmg_bonus)

    def check_hits(self, enemies, dmg_bonus=0):
        hits = []
        for s in self._spikes:
            if s['phase'] != 'spike' or s.get('hit'): continue
            s['hit'] = True
            for e in enemies:
                d = math.hypot(e.x - s['x'], e.y - s['y'])
                if d < 40 + self.level * 5:
                    hits.append((e, self.get_damage(dmg_bonus), s['x'], s['y'], None))
            create_particles(s['x'], s['y'], 6, 'explosion')
        return hits

    def draw_projectiles(self, surface, sh):
        for s in self._spikes:
            sx = int(s['x'] + sh[0]); sy = int(s['y'] + sh[1])
            if s['phase'] == 'warn':
                # 预警圈
                a = max(0, min(150, int(150 * (1 - s['timer']))))
                ws = pygame.Surface((60, 60), pygame.SRCALPHA)
                pygame.draw.circle(ws, (255, 100, 50, a), (30, 30), 25, 2)
                surface.blit(ws, (sx-30, sy-30))
            else:
                # 地刺
                prog = 1.0 - s['timer'] / 0.5
                h = int(30 * prog)
                pts = [(sx-6, sy), (sx+6, sy), (sx+2, sy-h), (sx-2, sy-h)]
                if len(pts) >= 3:
                    pygame.draw.polygon(surface, (180, 130, 80), pts)
                    pygame.draw.polygon(surface, (220, 180, 120), pts, 2)


# 武器总表
WEAPON_CLASSES = [
    MagicMissile, HolyWhip, IceNova, Fireball,
    LightningCircle, BoneShield, Boomerang, EarthSpikes,
]

WEAPON_CLASS_MAP = {cls.WEAPON_NAME: cls for cls in WEAPON_CLASSES}


# ============================================================
#  敌人系统
# ============================================================
ENEMY_TYPES = [
    # (name, base_hp, base_speed, base_dmg, base_size, color, spawn_after_min, special)
    ("骷髅杂兵",  20,  60, 5,  12, (200, 200, 180), 0,   None),
    ("蝙蝠群",    10, 120, 3,  10, (100, 80, 120),   0,   None),
    ("泥沼史莱姆", 30,  30, 8,  16, (80, 200, 80),    2,   'split'),
    ("幽灵",      25,  70, 7,  14, (150, 150, 220),   5,   None),
    ("自爆蜘蛛",   15, 100, 0,  11, (180, 60, 60),     7,   'explode'),
    ("骷髅弓箭手", 25,  50, 10, 13, (220, 200, 160),   8,   'ranged'),
    ("暗影法师",   35,  40, 12, 15, (120, 50, 180),   10,   'ranged'),
    ("精英骑士",  120,  55, 20, 22, (200, 180, 50),   15,   'charge'),
]


class Enemy:
    def __init__(self, x, y, etype_idx=0, difficulty_mult=1.0):
        info = ENEMY_TYPES[min(etype_idx, len(ENEMY_TYPES)-1)]
        self.name = info[0]
        self.x = x; self.y = y
        self.health = info[1] * difficulty_mult
        self.max_health = self.health
        self.speed = info[2]
        self.damage = info[3] * difficulty_mult
        self.size = info[4]
        self.color = info[5]
        self.special = info[7]
        self.alive = True
        self.flash_timer = 0
        self.slow_timer = 0
        self.slow_factor = 1.0
        self.anim_timer = random.uniform(0, 5)
        self.is_elite = False
        self.etype_idx = etype_idx
        # 远程攻击
        self._shoot_cd = 2.0
        self._shoot_timer = random.uniform(0, 2)
        self._charge_timer = 0
        self._charge_dir = [0, 0]
        # 分裂/爆炸产出
        self.children = []
        self.explosion_dmg = 25

    def update(self, dt, px, py, game_time):
        if not self.alive: return
        self.anim_timer += dt
        if self.flash_timer > 0:
            self.flash_timer -= dt
        if self.slow_timer > 0:
            self.slow_timer -= dt

        # 移动向玩家
        dx = px - self.x; dy = py - self.y
        dist = math.hypot(dx, dy)
        spd = self.speed
        if self.slow_timer > 0:
            spd *= self.slow_factor

        # 特殊行为
        if self.special == 'charge' and self._charge_timer > 0:
            self._charge_timer -= dt
            self.x += self._charge_dir[0] * spd * 4 * dt
            self.y += self._charge_dir[1] * spd * 4 * dt
        elif self.special == 'ranged' and dist < 250:
            # 远程保持距离
            if dist > 0 and dist < 200:
                self.x -= dx / dist * spd * 0.5 * dt
                self.y -= dy / dist * spd * 0.5 * dt
        else:
            if dist > 0:
                self.x += dx / dist * spd * dt
                self.y += dy / dist * spd * dt

        # 冲锋
        if self.special == 'charge':
            self._shoot_timer -= dt
            if self._shoot_timer <= 0 and dist < 300:
                self._charge_timer = 0.5
                if dist > 0:
                    self._charge_dir = [dx / dist, dy / dist]
                self._shoot_timer = 4.0

        # 死亡判定
        if self.health <= 0:
            self.alive = False
            # 分裂
            if self.special == 'split':
                for _ in range(2):
                    child = Enemy(
                        self.x + random.uniform(-15, 15),
                        self.y + random.uniform(-15, 15),
                        self.etype_idx, 0.5)
                    child.special = None  # 子体不再分裂
                    child.size = self.size * 0.7
                    self.children.append(child)

    def get_ranged_bullet(self, px, py, dt):
        """远程敌人射击"""
        if self.special != 'ranged': return None
        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = 2.0 + random.uniform(0, 1)
            angle = math.atan2(py - self.y, px - self.x)
            return {'x': self.x, 'y': self.y,
                    'vx': math.cos(angle) * 200,
                    'vy': math.sin(angle) * 200,
                    'life': 4.0, 'damage': self.damage}
        return None

    def draw(self, surface, sh):
        if not self.alive: return
        sx = int(self.x + sh[0]); sy = int(self.y + sh[1])
        # 屏幕外不画
        if sx < -50 or sx > WIDTH+50 or sy < -50 or sy > HEIGHT+50:
            return
        c = WHITE if self.flash_timer > 0 else self.color
        # 减速标记
        if self.slow_timer > 0:
            c = ICE_BLUE
        r = int(self.size)
        # 精英标记
        if self.is_elite:
            es = pygame.Surface((r*2+10, r*2+10), pygame.SRCALPHA)
            ea = max(0, min(120, int(80 + 40 * math.sin(self.anim_timer * 4))))
            pygame.draw.circle(es, (255, 50, 50, ea), (r+5, r+5), r+4, 2)
            surface.blit(es, (sx-r-5, sy-r-5))
        # 身体
        pygame.draw.circle(surface, c, (sx, sy), r)
        # 眼睛
        eye_r = max(1, r // 4)
        pygame.draw.circle(surface, (255, 50, 50), (sx - eye_r, sy - eye_r), eye_r)
        pygame.draw.circle(surface, (255, 50, 50), (sx + eye_r, sy - eye_r), eye_r)
        # 血条 (受伤时)
        if self.health < self.max_health:
            bar_w = r * 2
            ratio = max(0, self.health / self.max_health)
            pygame.draw.rect(surface, (60,60,60), (sx-r, sy-r-6, bar_w, 3))
            pygame.draw.rect(surface, RED, (sx-r, sy-r-6, int(bar_w*ratio), 3))


# 敌人子弹
enemy_bullets = []


# ============================================================
#  被动物品系统
# ============================================================
PASSIVE_ITEMS = [
    # (name, desc, stat_changes)
    ("弹射宝石",   "所有投射物 +1 弹射",       {'bounce': 1}),
    ("冰封之心",   "接触敌人时自动减速",         {'contact_slow': True}),
    ("燃烧之魂",   "10%击杀几率留下火焰地面",    {'burn_chance': 0.1}),
    ("疾风护符",   "移速+15%  闪避+5%",         {'speed_mult': 0.15, 'dodge': 0.05}),
    ("大地之心",   "护甲+5  击退+30%",          {'armor': 5, 'knockback': 0.3}),
    ("血色宝石",   "暴击+8%  暴击伤害+30%",     {'crit': 0.08, 'crit_dmg': 0.3}),
    ("吞噬之牙",   "5%生命偷取",               {'lifesteal': 0.05}),
    ("幸运骰子",   "升级选项+1 (3→4)",          {'extra_choice': 1}),
    ("幽冥灯笼",   "拾取范围+40%  经验+10%",    {'pickup_mult': 0.4, 'exp_mult': 0.1}),
    ("战争号角",   "伤害+12%  受伤+8%",         {'dmg_bonus': 0.12, 'dmg_taken': 0.08}),
    ("生命树苗",   "每秒回血+1  每10击杀+5血",   {'regen': 1.0, 'kill_heal': True}),
    ("时空碎片",   "全局冷却-10%",              {'cdr': 0.10}),
]


# ============================================================
#  材料系统
# ============================================================
MATERIALS = {
    'iron':    ('铁矿石',   (180, 180, 200), 4),
    'shadow':  ('暗影精华', (160, 60, 200),  5),
    'crystal': ('魔力水晶', (80, 180, 255),  5),
    'dragon':  ('龙鳞碎片', (230, 170, 50),  6),
    'abyss':   ('深渊之心', (220, 40, 80),   7),
}

def get_levelup_material_cost(level):
    """获取升级到下一级所需材料"""
    if level < 20:  return {'iron': 1}
    elif level < 50:  return {'iron': 2}
    elif level < 80:  return {'iron': 1, 'shadow': 1}
    elif level < 110: return {'shadow': 1, 'crystal': 1}
    elif level < 140: return {'shadow': 1, 'dragon': 1}
    else:             return {'dragon': 1, 'abyss': 1}


class MaterialDrop:
    """掉落的材料物品"""
    def __init__(self, x, y, mat_type='iron'):
        self.x = x; self.y = y; self.mat_type = mat_type
        info = MATERIALS.get(mat_type, MATERIALS['iron'])
        self.name = info[0]; self.color = info[1]; self.size = info[2]
        self.life = 45.0; self.bob = random.uniform(0, math.pi*2)
        self.magnet = False

    def update(self, dt, player_x, player_y, pickup_range):
        self.life -= dt; self.bob += dt * 2.5
        dx = player_x - self.x; dy = player_y - self.y
        dist = math.hypot(dx, dy)
        if dist < pickup_range * 0.8 or self.magnet:
            self.magnet = True
            speed = 500 if dist > 30 else 250
            if dist > 1:
                self.x += dx/dist * speed * dt
                self.y += dy/dist * speed * dt
            return dist < 18
        return False

    def draw(self, surface, sh):
        if self.life <= 0: return
        if self.life < 10 and int(self.life*5)%2 == 0: return
        sx = int(self.x + sh[0])
        sy = int(self.y + sh[1] + math.sin(self.bob)*2)
        r = self.size
        pts = [(sx, sy-r), (sx+r, sy), (sx, sy+r), (sx-r, sy)]
        pygame.draw.polygon(surface, self.color, pts)
        pygame.draw.polygon(surface, WHITE, pts, 1)
        gs = pygame.Surface((r*3, r*3), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*self.color, 40), (r*3//2, r*3//2), r*3//2)
        surface.blit(gs, (sx-r*3//2, sy-r*3//2))

material_drops = []

def spawn_materials(x, y, enemy_type='normal'):
    """根据敌人类型掉落材料"""
    if enemy_type == 'boss':
        for mt in MATERIALS:
            for _ in range(random.randint(3, 5)):
                ox = random.uniform(-40, 40); oy = random.uniform(-40, 40)
                material_drops.append(MaterialDrop(x+ox, y+oy, mt))
    elif enemy_type == 'elite':
        for _ in range(random.randint(1, 2)):
            material_drops.append(MaterialDrop(
                x+random.uniform(-15,15), y+random.uniform(-15,15),
                random.choice(['shadow','crystal','dragon'])))
        material_drops.append(MaterialDrop(x, y, 'iron'))
    elif enemy_type == 'enhanced':
        if random.random() < 0.6:
            material_drops.append(MaterialDrop(x, y, 'iron'))
        if random.random() < 0.25:
            material_drops.append(MaterialDrop(x+random.uniform(-10,10), y+random.uniform(-10,10), 'shadow'))
    else:
        if random.random() < 0.4:
            material_drops.append(MaterialDrop(x, y, 'iron'))
        if random.random() < 0.08:
            material_drops.append(MaterialDrop(x, y, 'shadow'))


# ============================================================
#  装备系统
# ============================================================
EQUIP_SLOTS = ['weapon', 'armor', 'accessory', 'rune']
EQUIP_SLOT_NAMES = {'weapon': '武器', 'armor': '护甲', 'accessory': '饰品', 'rune': '符文'}
RARITY_ORDER = ['common', 'uncommon', 'rare', 'epic', 'legendary']
RARITY_NAMES = {
    'common':    ('普通', (200,200,200)),
    'uncommon':  ('优秀', (100,220,100)),
    'rare':      ('稀有', (80,150,255)),
    'epic':      ('史诗', (180,80,255)),
    'legendary': ('传说', (255,200,50)),
}

EQUIPMENT_DB = [
    # 武器
    ("铁短剑",     'weapon', 'common',    {'dmg_bonus': 0.05}),
    ("暗影匕首",   'weapon', 'uncommon',  {'dmg_bonus': 0.08, 'crit': 0.03}),
    ("碧焰长剑",   'weapon', 'rare',      {'dmg_bonus': 0.12, 'crit': 0.05}),
    ("深渊大剑",   'weapon', 'epic',      {'dmg_bonus': 0.18, 'crit': 0.08, 'crit_dmg': 0.2}),
    ("毁灭之刃",   'weapon', 'legendary', {'dmg_bonus': 0.25, 'crit': 0.10, 'crit_dmg': 0.4}),
    # 护甲
    ("皮甲",       'armor', 'common',     {'max_health': 15}),
    ("锁子甲",     'armor', 'uncommon',   {'max_health': 25, 'armor': 2}),
    ("暗影铠甲",   'armor', 'rare',       {'max_health': 40, 'armor': 4}),
    ("龙鳞战甲",   'armor', 'epic',       {'max_health': 60, 'armor': 6, 'regen': 0.3}),
    ("深渊圣甲",   'armor', 'legendary',  {'max_health': 80, 'armor': 10, 'regen': 0.5}),
    # 饰品
    ("旅人之靴",   'accessory', 'common',    {'speed_mult': 0.05}),
    ("疾风之翼",   'accessory', 'uncommon',  {'speed_mult': 0.08, 'dodge': 0.03}),
    ("闪光护符",   'accessory', 'rare',      {'speed_mult': 0.10, 'dodge': 0.05, 'pickup': 15}),
    ("传送之戒",   'accessory', 'epic',      {'speed_mult': 0.15, 'dodge': 0.08, 'pickup': 25}),
    ("时间之冠",   'accessory', 'legendary', {'speed_mult': 0.20, 'dodge': 0.12, 'pickup': 40}),
    # 符文
    ("初级符文",   'rune', 'common',    {'cdr': 0.03}),
    ("聚能符文",   'rune', 'uncommon',  {'cdr': 0.05, 'exp_mult': 0.05}),
    ("掠夺符文",   'rune', 'rare',      {'cdr': 0.08, 'exp_mult': 0.10, 'lifesteal': 0.02}),
    ("深渊符文",   'rune', 'epic',      {'cdr': 0.10, 'exp_mult': 0.15, 'lifesteal': 0.04}),
    ("创世符文",   'rune', 'legendary', {'cdr': 0.15, 'exp_mult': 0.20, 'lifesteal': 0.06}),
]

def get_equip_upgrade_cost(enhance_level):
    """装备强化所需材料"""
    if enhance_level < 3:   return {'iron': 3}
    elif enhance_level < 6: return {'iron': 2, 'shadow': 2}
    elif enhance_level < 8: return {'shadow': 3, 'crystal': 2}
    elif enhance_level == 8: return {'crystal': 2, 'dragon': 2}
    else:                   return {'dragon': 3, 'abyss': 1}


class Equipment:
    def __init__(self, template_idx):
        tpl = EQUIPMENT_DB[template_idx]
        self.name = tpl[0]; self.slot = tpl[1]; self.rarity = tpl[2]
        self.base_stats = dict(tpl[3]); self.enhance = 0; self.template_idx = template_idx

    @property
    def display_name(self):
        base_name = i18n.t(self.name)
        return f"{base_name} +{self.enhance}" if self.enhance > 0 else base_name

    @property
    def enhance_level(self):
        return self.enhance

    @property
    def rarity_color(self):
        return RARITY_NAMES[self.rarity][1]

    @property
    def rarity_name(self):
        return i18n.rarity_name(self.rarity)

    def get_stats(self):
        mult = 1.0 + self.enhance * 0.12
        stats = {}
        for k, v in self.base_stats.items():
            stats[k] = round(v * mult, 3) if isinstance(v, float) else int(v * mult)
        return stats

    def can_enhance(self, materials):
        if self.enhance >= 10: return False
        cost = get_equip_upgrade_cost(self.enhance)
        return all(materials.get(m, 0) >= c for m, c in cost.items())

    def do_enhance(self, materials):
        if not self.can_enhance(materials): return False
        cost = get_equip_upgrade_cost(self.enhance)
        for m, c in cost.items(): materials[m] -= c
        self.enhance += 1; return True


def roll_equipment_drop(enemy_type='normal'):
    """根据敌人类型随机生成装备"""
    drop_chance = {'normal': 0.008, 'enhanced': 0.025, 'elite': 0.15, 'boss': 1.0}.get(enemy_type, 0.008)
    if random.random() > drop_chance: return None
    weights = {
        'normal':   [70, 25, 5, 0, 0],
        'enhanced': [40, 40, 15, 5, 0],
        'elite':    [10, 30, 35, 20, 5],
        'boss':     [0, 5, 25, 45, 25],
    }.get(enemy_type, [70, 25, 5, 0, 0])
    rarity = random.choices(RARITY_ORDER, weights=weights)[0]
    candidates = [i for i, tpl in enumerate(EQUIPMENT_DB) if tpl[2] == rarity]
    if not candidates: return None
    return Equipment(random.choice(candidates))


# ============================================================
#  升级选项
# ============================================================
def generate_upgrade_options(player_weapons, player_passives, count=3):
    """生成升级选项"""
    options = []
    pool = []

    # 新武器 (如果 < 6 个)
    if len(player_weapons) < 6:
        available = [cls for cls in WEAPON_CLASSES if cls.WEAPON_NAME not in
                     [w.WEAPON_NAME for w in player_weapons]]
        for cls in available:
            pool.append({
                'type': 'new_weapon',
                'name': i18n.t(cls.WEAPON_NAME),
                'desc': i18n.t(cls.WEAPON_DESC),
                'color': cls.WEAPON_COLOR,
                'icon': '★',
                'cls': cls,
            })

    # 武器升级
    for w in player_weapons:
        if w.level < w.max_level:
            pool.append({
                'type': 'weapon_upgrade',
                'name': f"{i18n.t(w.WEAPON_NAME)} {i18n.t('升级')}",
                'desc': i18n.t("Lv.{from_level} -> Lv.{to_level}  伤害/效果提升",
                               from_level=w.level, to_level=w.level + 1),
                'color': w.WEAPON_COLOR,
                'icon': '▲',
                'weapon': w,
            })

    # 被动物品 (如果 < 6 个)
    if len(player_passives) < 6:
        owned_names = {p[0] for p in player_passives}
        for item in PASSIVE_ITEMS:
            if item[0] not in owned_names:
                pool.append({
                    'type': 'new_passive',
                    'name': i18n.t(item[0]),
                    'desc': i18n.t(item[1]),
                    'color': PURPLE,
                    'icon': '◆',
                    'item': item,
                })

    # 属性提升
    stat_boosts = [
        (i18n.t("生命 +20"),    {'max_health': 20},   GREEN),
        (i18n.t("移速 +8%"),    {'speed_mult': 0.08}, CYAN),
        (i18n.t("护甲 +3"),     {'armor': 3},         (180,180,200)),
        (i18n.t("暴击 +3%"),    {'crit': 0.03},       ORANGE),
        (i18n.t("回血 +0.3/s"), {'regen': 0.3},       GREEN),
        (i18n.t("拾取 +20"),    {'pickup': 20},        YELLOW),
        (i18n.t("伤害 +8%"),    {'dmg_bonus': 0.08},   RED),
        (i18n.t("冷却 -5%"),    {'cdr': 0.05},         ICE_BLUE),
    ]
    for name, stats, color in stat_boosts:
        pool.append({
            'type': 'stat_boost',
            'name': name,
            'desc': i18n.t("基础属性提升"),
            'color': color,
            'icon': '●',
            'stats': stats,
        })

    random.shuffle(pool)
    return pool[:count]


# ============================================================
#  存档系统 (Roguelite 灵魂碎片)
# ============================================================
# 处理PyInstaller打包后的存档路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的exe，保存到exe所在目录
    SAVE_PATH = os.path.join(os.path.dirname(sys.executable), 'save_data.json')
else:
    # 开发环境，保存到脚本所在目录
    SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'save_data.json')

def load_save():
    default = {
        'soul_shards': 0,
        'total_runs': 0,
        'best_time': 0,
        'best_kills': 0,
        'language': 'en',
        'resolution': list(DEFAULT_RESOLUTION),
        'fullscreen': False,
        'unlocked_chars': [0],  # 索引列表
        'upgrades': {  # 永久升级
            'survival': 0,  # 0-5级
            'combat': 0,
            'exploration': 0,
            'fate': 0,
        },
        'achievements': [],
    }
    try:
        with open(SAVE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            # 合并局外系统数据
            data = meta_systems.merge_meta_save(data)
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        default = meta_systems.merge_meta_save(default)
        return default

def save_game(data):
    try:
        with open(SAVE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(i18n.t("保存失败: {err}", err=e))

def apply_display_settings(resolution, fullscreen):
    """应用显示设置"""
    global screen, WIDTH, HEIGHT
    WIDTH, HEIGHT = resolution
    flags = pygame.FULLSCREEN if fullscreen else 0
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    pygame.display.set_caption(i18n.t("暗夜割草者：深渊轮回"))
    # 重新初始化模块以适应新分辨率
    reload_fonts()

save_data = load_save()
i18n.set_language(save_data.get('language', 'en'))

# 根据保存的语言重新加载字体
reload_fonts()

# 应用保存的显示设置
saved_resolution = tuple(save_data.get('resolution', list(DEFAULT_RESOLUTION)))
saved_fullscreen = save_data.get('fullscreen', False)
if saved_resolution in AVAILABLE_RESOLUTIONS:
    apply_display_settings(saved_resolution, saved_fullscreen)
else:
    # 如果保存的分辨率无效，使用默认值
    save_data['resolution'] = list(DEFAULT_RESOLUTION)
    save_data['fullscreen'] = False
    save_game(save_data)

pygame.display.set_caption(i18n.t("暗夜割草者：深渊轮回"))


def set_game_language(lang):
    i18n.set_language(lang)
    save_data['language'] = lang
    save_game(save_data)
    pygame.display.set_caption(i18n.t("暗夜割草者：深渊轮回"))
    reload_fonts()  # 重新加载字体


# ============================================================
#  永久升级加成
# ============================================================
def get_permanent_bonuses():
    """从存档计算永久加成"""
    u = save_data.get('upgrades', {})
    bonuses = {
        'bonus_hp': 0, 'bonus_armor': 0, 'bonus_regen': 0,
        'bonus_dmg': 0, 'bonus_crit': 0, 'bonus_cdr': 0,
        'bonus_speed': 0, 'bonus_pickup': 0, 'bonus_exp': 0,
        'extra_choices': 0, 'start_level': 1,
    }
    # 生存之路
    sl = u.get('survival', 0)
    if sl >= 1: bonuses['bonus_hp'] += 10
    if sl >= 2: bonuses['bonus_hp'] += 20
    if sl >= 3: bonuses['bonus_hp'] += 30
    if sl >= 4: bonuses['bonus_armor'] += 2
    if sl >= 5: bonuses['bonus_regen'] += 0.5
    # 战斗之路
    cl = u.get('combat', 0)
    if cl >= 1: bonuses['bonus_dmg'] += 0.05
    if cl >= 2: bonuses['bonus_crit'] += 0.03
    if cl >= 3: bonuses['bonus_cdr'] += 0.05
    # 探索之路
    el = u.get('exploration', 0)
    if el >= 1: bonuses['bonus_speed'] += 0.05
    if el >= 2: bonuses['bonus_pickup'] += 20
    if el >= 3: bonuses['bonus_exp'] += 0.1
    if el >= 4: bonuses['extra_choices'] += 1
    if el >= 5: bonuses['start_level'] = 3
    return bonuses


# ============================================================
#  游戏状态
# ============================================================
class GameState:
    START = 'start'
    SETTINGS = 'settings'
    LANG_SELECT = 'lang_select'
    CHAR_SELECT = 'char_select'
    PLAYING = 'playing'
    PAUSED = 'paused'
    UPGRADE = 'upgrade'
    BOSS_WARNING = 'boss_warning'
    GAME_OVER = 'game_over'
    VICTORY = 'victory'
    SOUL_SHOP = 'soul_shop'
    INVENTORY = 'inventory'
    CODEX = 'codex'
    DUNGEON_SELECT = 'dungeon_select'
    CHAR_UPGRADE = 'char_upgrade'
    GACHA = 'gacha'
    SETTLEMENT = 'settlement'
    NPC_SELECT = 'npc_select'
    DIALOGUE = 'dialogue'
    TOWN = 'town'
    GACHA_ANIM = 'gacha_anim'


# ============================================================
#  游戏运行时数据
# ============================================================
class RunData:
    """单局游戏数据"""
    def __init__(self):
        # 角色
        self.char_index = 0
        self.character = None  # characters.CharacterBase实例
        # 玩家位置 (固定在屏幕中心, Boss模块需要)
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        # 属性 (基础 + 永久加成 + 本局加成)
        self.max_health = 100
        self.health = 100
        self.move_speed = 300
        self.pickup_range = 80
        self.armor = 0
        self.dodge_rate = 0.0
        self.regen = 0.0
        self.crit_rate = 0.05
        self.crit_damage = 1.5
        self.dmg_bonus = 0.0
        self.cdr = 0.0
        self.exp_bonus = 0.0
        self.lifesteal = 0.0
        self.dmg_taken_mult = 1.0
        # 等级 (满级150)
        self.level = 1
        self.MAX_LEVEL = 150
        self.exp = 0
        self.exp_to_next = 50
        self.level_up_pending = False  # 经验够但材料不足
        self.mat_shortage_msg = ''     # 材料不足提示
        self.mat_shortage_timer = 0
        # 材料背包
        self.materials = {m: 0 for m in MATERIALS}
        # 装备系统
        self.equipped = {s: None for s in EQUIP_SLOTS}   # 穿戴中
        self.equipment_bag = []  # 待选装备(最多8)
        self.equip_notify = []   # [(text, timer, color)]
        # 武器与被动
        self.weapons = []     # [WeaponBase实例]
        self.passives = []    # [(name, desc, stats)]
        # 统计
        self.kills = 0
        self.kill_heal_counter = 0
        self.game_time = 0.0
        self.total_damage = 0
        # Boss
        self.boss_spawned_count = 0
        self.boss_active = False
        # 死亡/胜利
        self.alive = True
        self.invincible_timer = 0
        # 场景数据
        self.bg_offset = [0.0, 0.0]
        # 升级选项
        self.upgrade_options = []

    def apply_character(self, char_index):
        """根据选择的角色应用基础属性"""
        self.char_index = char_index
        self.character = characters.create_character(char_index, WIDTH // 2, HEIGHT // 2)
        ch = self.character
        self.max_health = ch.max_health
        self.health = self.max_health
        self.move_speed = ch.move_speed
        self.pickup_range = ch.pickup_range
        self.armor = ch.armor
        self.dodge_rate = ch.dodge_rate
        self.regen = ch.regen
        self.crit_rate = ch.crit_rate
        self.crit_damage = ch.crit_damage
        self.dmg_bonus = ch.damage_bonus

    def apply_permanent_bonuses(self):
        b = get_permanent_bonuses()
        self.max_health += b['bonus_hp']
        self.health = self.max_health
        self.armor += b['bonus_armor']
        self.regen += b['bonus_regen']
        self.dmg_bonus += b['bonus_dmg']
        self.crit_rate += b['bonus_crit']
        self.cdr += b['bonus_cdr']
        self.move_speed *= (1 + b['bonus_speed'])
        self.pickup_range += b['bonus_pickup']
        self.exp_bonus += b['bonus_exp']
        self.level = b.get('start_level', 1)

    def apply_stat(self, stat_key, value):
        """应用单个属性变化"""
        if stat_key == 'max_health':
            self.max_health += value; self.health += value
        elif stat_key == 'speed_mult':
            self.move_speed *= (1 + value)
        elif stat_key == 'armor':
            self.armor += value
        elif stat_key == 'crit':
            self.crit_rate += value
        elif stat_key == 'crit_dmg':
            self.crit_damage += value
        elif stat_key == 'regen':
            self.regen += value
        elif stat_key == 'pickup':
            self.pickup_range += value
        elif stat_key == 'pickup_mult':
            self.pickup_range *= (1 + value)
        elif stat_key == 'dmg_bonus':
            self.dmg_bonus += value
        elif stat_key == 'cdr':
            self.cdr = min(0.5, self.cdr + value)
        elif stat_key == 'dodge':
            self.dodge_rate = min(0.6, self.dodge_rate + value)
        elif stat_key == 'lifesteal':
            self.lifesteal += value
        elif stat_key == 'exp_mult':
            self.exp_bonus += value
        elif stat_key == 'dmg_taken':
            self.dmg_taken_mult += value
        elif stat_key == 'extra_choice':
            pass  # 升级时处理

    def add_exp(self, amount):
        if self.level >= self.MAX_LEVEL:
            return False
        actual = int(amount * (1 + self.exp_bonus))
        self.exp += actual
        if self.exp >= self.exp_to_next:
            return self.can_level_up()
        return False

    def can_level_up(self):
        """检查是否满足升级条件(经验+材料)"""
        if self.level >= self.MAX_LEVEL: return False
        if self.exp < self.exp_to_next: return False
        cost = get_levelup_material_cost(self.level)
        for m, c in cost.items():
            if self.materials.get(m, 0) < c:
                names = [f"{i18n.material_name(k)}x{v}" for k, v in cost.items()]
                self.mat_shortage_msg = i18n.t("材料不足: ") + ' '.join(names)
                self.mat_shortage_timer = 2.0
                self.level_up_pending = True
                return False
        return True

    def do_level_up(self):
        # 扣除材料
        cost = get_levelup_material_cost(self.level)
        for m, c in cost.items():
            self.materials[m] -= c
        self.exp -= self.exp_to_next
        self.level += 1
        self.level_up_pending = False
        # 经验需求曲线 (150级)
        lv = self.level
        if lv <= 20:    self.exp_to_next = 50 + lv * 8
        elif lv <= 50:  self.exp_to_next = 210 + (lv - 20) * 15
        elif lv <= 80:  self.exp_to_next = 660 + (lv - 50) * 22
        elif lv <= 110: self.exp_to_next = 1320 + (lv - 80) * 30
        elif lv <= 140: self.exp_to_next = 2220 + (lv - 110) * 40
        else:           self.exp_to_next = 3420 + (lv - 140) * 60
        # 每级自动属性微提升
        self.max_health += 2
        self.health = min(self.health + 2, self.max_health)
        if lv % 5 == 0: self.dmg_bonus += 0.01
        if lv % 10 == 0: self.armor += 1
        if lv % 15 == 0: self.crit_rate = min(0.5, self.crit_rate + 0.005)

    def take_damage(self, amount):
        # 闪避
        if random.random() < self.dodge_rate:
            return False
        actual = max(1, amount * self.dmg_taken_mult - self.armor)
        self.health -= actual
        screen_shake.trigger(5, 0.1)
        if self.health <= 0:
            self.alive = False
        return True

    def equip_item(self, equip):
        """装备一件装备，旧装备回到背包"""
        slot = equip.slot
        old = self.equipped[slot]
        # 移除旧装备属性
        if old:
            for sk, sv in old.get_stats().items():
                if isinstance(sv, (int, float)):
                    self.apply_stat(sk, -sv)
            if len(self.equipment_bag) < 8:
                self.equipment_bag.append(old)
        # 穿上新装备
        self.equipped[slot] = equip
        for sk, sv in equip.get_stats().items():
            if isinstance(sv, (int, float)):
                self.apply_stat(sk, sv)
        # 从背包移除
        if equip in self.equipment_bag:
            self.equipment_bag.remove(equip)
        # 提示
        rc = equip.rarity_color
        self.equip_notify.append((
            i18n.t("装备: {name} [{rarity}]", name=equip.display_name, rarity=equip.rarity_name),
            3.0,
            rc,
        ))

    def try_auto_equip(self, equip):
        """自动装备: 空槽直接装，否则放背包"""
        slot = equip.slot
        # 图鉴解锁装备
        tidx = getattr(equip, 'template_idx', -1)
        if tidx >= 0 and tidx not in save_data.get('codex_equips', []):
            save_data['codex_equips'].append(tidx)
        if self.equipped[slot] is None:
            self.equip_item(equip)
        else:
            if len(self.equipment_bag) < 8:
                self.equipment_bag.append(equip)
                rc = equip.rarity_color
                self.equip_notify.append((
                    i18n.t("获得: {name} [{rarity}]", name=equip.display_name, rarity=equip.rarity_name),
                    3.0,
                    rc,
                ))
            # 背包满了就丢弃

run = RunData()

# ============================================================
#  全局列表
# ============================================================
enemies = []
bosses = []
items = []  # 场景物品 (宝箱等)


# ============================================================
#  绘制函数
# ============================================================
def draw_background(surface, sh, bg_off):
    surface.fill(DARK_BG)
    grid = 60
    ox = int(bg_off[0] % grid + sh[0])
    oy = int(bg_off[1] % grid + sh[1])
    for x in range(ox - grid, WIDTH + grid, grid):
        pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, HEIGHT), 1)
    for y in range(oy - grid, HEIGHT + grid, grid):
        pygame.draw.line(surface, GRID_COLOR, (0, y), (WIDTH, y), 1)


def draw_hud(surface):
    """绘制游戏内HUD"""
    # ---- 左上: 角色 + 血条 + 经验 ----
    panel = pygame.Surface((260, 90), pygame.SRCALPHA)
    pygame.draw.rect(panel, (0, 0, 0, 160), (0, 0, 260, 90), border_radius=8)
    surface.blit(panel, (8, 8))

    # 角色名
    ch_info = characters.get_character_info(run.char_index)
    nt = _render_outlined(font_xs, f"{ch_info['title']}·{ch_info['name']}  Lv.{run.level}", ch_info['color'])
    surface.blit(nt, (16, 12))

    # 血条
    hp_w = 200; hp_h = 14
    hp_ratio = max(0, run.health / run.max_health)
    pygame.draw.rect(surface, (40, 40, 40), (16, 30, hp_w, hp_h), border_radius=3)
    if hp_ratio > 0:
        hc = GREEN if hp_ratio > 0.5 else (YELLOW if hp_ratio > 0.25 else RED)
        pygame.draw.rect(surface, hc, (16, 30, int(hp_w * hp_ratio), hp_h), border_radius=3)
    ht = _render_outlined(font_xs, f"{int(run.health)}/{run.max_health}", WHITE)
    surface.blit(ht, (16 + hp_w//2 - ht.get_width()//2, 31))

    # 经验条
    exp_ratio = min(1.0, run.exp / max(1, run.exp_to_next))
    pygame.draw.rect(surface, (20, 20, 40), (16, 48, hp_w, 8), border_radius=2)
    if exp_ratio > 0:
        pygame.draw.rect(surface, CYAN, (16, 48, int(hp_w * exp_ratio), 8), border_radius=2)
    et = _render_outlined(font_xs, f"{i18n.t('经验')} {run.exp}/{run.exp_to_next}", (150, 200, 255))
    surface.blit(et, (16, 58))

    # 击杀 + 时间
    minutes = int(run.game_time) // 60
    seconds = int(run.game_time) % 60
    st = _render_outlined(
        font_xs,
        i18n.t("击杀:{kills}  {time}", kills=run.kills, time=f"{minutes:02d}:{seconds:02d}"),
        (180, 180, 180),
    )
    surface.blit(st, (16, 74))

    # ---- 右上: 武器列表 ----
    if run.weapons:
        wp = pygame.Surface((180, 20 * len(run.weapons) + 10), pygame.SRCALPHA)
        pygame.draw.rect(wp, (0, 0, 0, 120), (0, 0, wp.get_width(), wp.get_height()), border_radius=6)
        surface.blit(wp, (WIDTH - 188, 8))
        for i, w in enumerate(run.weapons):
            wt = _render_outlined(font_xs, f"{i18n.t(w.WEAPON_NAME)} Lv.{w.level}", w.WEAPON_COLOR)
            surface.blit(wt, (WIDTH - 180, 14 + i * 20))

    # ---- 30分钟倒计时 ----
    remain = max(0, 1800 - run.game_time)
    rm = int(remain) // 60; rs = int(remain) % 60
    if remain < 60:
        tc = RED if int(run.game_time * 3) % 2 == 0 else YELLOW
    elif remain < 180:
        tc = ORANGE
    else:
        tc = (150, 150, 150)
    tt = _render_outlined(font_sm, f"{rm:02d}:{rs:02d}", tc)
    surface.blit(tt, (WIDTH // 2 - tt.get_width() // 2, 50))

    # 被动物品图标 (底部)
    if run.passives:
        pi_y = HEIGHT - 50
        pi_x = 10
        for i, (pn, pd, ps) in enumerate(run.passives):
            pt = _render_outlined(font_xs, f"[{i18n.t(pn)}]", PURPLE)
            surface.blit(pt, (pi_x + i * 80, pi_y))

    # TAB提示
    tab_t = _render_outlined(font_xs, i18n.t("[TAB] 装备/材料"), (100, 100, 130))
    surface.blit(tab_t, (WIDTH - 130, HEIGHT - 18))

    # 装备拾取通知 (淡出)
    if run.equip_notify:
        shown = 0
        for entry in reversed(run.equip_notify[-5:]):
            txt, _, color = entry
            nt = _render_outlined(font_xs, txt, color)
            surface.blit(nt, (WIDTH//2 - nt.get_width()//2, 120 + shown * 18))
            shown += 1
        # 超过5条时清除旧的
        if len(run.equip_notify) > 10:
            run.equip_notify = run.equip_notify[-5:]

    # 材料不足提示
    if run.mat_shortage_timer > 0:
        alpha = min(255, int(run.mat_shortage_timer * 255 / 2.0))
        ms = _render_outlined(font_xs, run.mat_shortage_msg, ORANGE)
        ms.set_alpha(alpha)
        surface.blit(ms, (WIDTH//2 - ms.get_width()//2, HEIGHT//2 + 40))

    # 材料简要显示 (左下)
    mat_y = HEIGHT - 30
    mx = 10
    for mk, (mname, mcolor, _) in MATERIALS.items():
        cnt = run.materials.get(mk, 0)
        if cnt > 0:
            mt = _render_outlined(font_xs, f"{i18n.material_short(mk)}:{cnt}", mcolor)
            surface.blit(mt, (mx, mat_y))
            mx += 55


def draw_inventory(surface):
    """绘制背包/装备界面，返回按钮字典"""
    buttons = {}
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))

    # 标题
    title = _render_outlined(font_lg, i18n.t("装备 & 材料"), CYAN)
    surface.blit(title, (WIDTH//2 - title.get_width()//2, 20))

    # ---- 左侧: 装备栏 (4 slots) ----
    slot_names = {s: i18n.slot_name(s) for s in EQUIP_SLOTS}
    left_x = 40
    for i, slot in enumerate(EQUIP_SLOTS):
        sy = 80 + i * 100
        # 槽位背景
        slot_rect = pygame.Rect(left_x, sy, 300, 85)
        pygame.draw.rect(surface, (30, 30, 50, 200), slot_rect, border_radius=6)
        pygame.draw.rect(surface, (80, 80, 120), slot_rect, 2, border_radius=6)
        # 槽位名
        sn = _render_outlined(font_sm, slot_names[slot], (200, 200, 220))
        surface.blit(sn, (left_x + 8, sy + 4))
        # 已装备
        eq = run.equipped[slot]
        if eq:
            tmpl = EQUIPMENT_DB[eq.template_idx]
            dn = eq.display_name
            rarity_color = eq.rarity_color
            et = _render_outlined(font_xs, dn, rarity_color)
            surface.blit(et, (left_x + 8, sy + 28))
            # 属性
            stats = eq.get_stats()
            stat_str = "  ".join(
                f"{i18n.stat_name(k)}+{v:.1f}" if isinstance(v, float) else f"{i18n.stat_name(k)}+{v}"
                for k, v in stats.items()
            )
            st = _render_outlined(font_xs, stat_str, (180, 180, 200))
            surface.blit(st, (left_x + 8, sy + 46))
            # 强化按钮
            if eq.enhance_level < 10:
                cost = get_equip_upgrade_cost(eq.enhance_level)
                can = all(run.materials.get(m, 0) >= c for m, c in cost.items())
                btn_color = (0, 180, 80) if can else (80, 80, 80)
                btn_rect = pygame.Rect(left_x + 200, sy + 60, 90, 22)
                pygame.draw.rect(surface, btn_color, btn_rect, border_radius=4)
                cost_str = " ".join(f"{i18n.material_short(m)}{c}" for m, c in cost.items())
                bt = _render_outlined(font_xs, i18n.t("强化 {cost}", cost=cost_str), WHITE)
                surface.blit(bt, (btn_rect.x + 4, btn_rect.y + 3))
                buttons[('enhance', slot)] = btn_rect
        else:
            et = _render_outlined(font_xs, i18n.t("-- 空 --"), (100, 100, 120))
            surface.blit(et, (left_x + 8, sy + 35))

    # ---- 右侧: 背包装备 ----
    right_x = 380
    bag_title = _render_outlined(font_sm, i18n.t("背包 ({count}/8)", count=len(run.equipment_bag)), YELLOW)
    surface.blit(bag_title, (right_x, 80))
    for i, eq in enumerate(run.equipment_bag):
        by = 110 + i * 50
        tmpl = EQUIPMENT_DB[eq.template_idx]
        rc = eq.rarity_color
        brect = pygame.Rect(right_x, by, 280, 44)
        pygame.draw.rect(surface, (25, 25, 40, 200), brect, border_radius=4)
        pygame.draw.rect(surface, rc, brect, 1, border_radius=4)
        # 名字
        nt = _render_outlined(font_xs, eq.display_name, rc)
        surface.blit(nt, (right_x + 6, by + 4))
        # 属性
        stats = eq.get_stats()
        stat_str = "  ".join(
            f"{i18n.stat_name(k)}+{v:.1f}" if isinstance(v, float) else f"{i18n.stat_name(k)}+{v}"
            for k, v in stats.items()
        )
        st = _render_outlined(font_xs, stat_str, (160, 160, 180))
        surface.blit(st, (right_x + 6, by + 20))
        # 装备按钮
        eq_btn = pygame.Rect(right_x + 210, by + 8, 60, 24)
        pygame.draw.rect(surface, (80, 120, 200), eq_btn, border_radius=4)
        ebt = _render_outlined(font_xs, i18n.t("装备"), WHITE)
        surface.blit(ebt, (eq_btn.x + 14, eq_btn.y + 4))
        buttons[('equip_bag', i)] = eq_btn

    # ---- 底部: 材料 ----
    mat_y = HEIGHT - 120
    mat_title = _render_outlined(font_sm, i18n.t("材料"), ORANGE)
    surface.blit(mat_title, (40, mat_y))
    for i, (mk, (mname, mcolor, _)) in enumerate(MATERIALS.items()):
        mx = 40 + i * 140
        my = mat_y + 30
        cnt = run.materials.get(mk, 0)
        mt = _render_outlined(font_xs, f"{i18n.material_name(mk)}: {cnt}", mcolor)
        surface.blit(mt, (mx, my))

    # ---- 当前等级 + 升级所需材料 ----
    lv_info = _render_outlined(font_sm, i18n.t("等级 {level}/{max_level}", level=run.level, max_level=run.MAX_LEVEL), CYAN)
    surface.blit(lv_info, (40, mat_y + 55))
    if run.level < run.MAX_LEVEL:
        cost = get_levelup_material_cost(run.level)
        if cost:
            cost_parts = []
            for m, c in cost.items():
                has = run.materials.get(m, 0)
                color_tag = "✓" if has >= c else "✗"
                cost_parts.append(f"{i18n.material_name(m)}×{c}({has}){color_tag}")
            ct = _render_outlined(font_xs, i18n.t("升级需: {cost}", cost=" ".join(cost_parts)), (200, 200, 180))
            surface.blit(ct, (200, mat_y + 60))

    # 关闭提示
    close_t = _render_outlined(font_xs, i18n.t("按 TAB 或 I 关闭"), (150, 150, 170))
    surface.blit(close_t, (WIDTH//2 - close_t.get_width()//2, HEIGHT - 30))

    return buttons


def draw_start_screen(surface):
    """主菜单 — 简化版（开始游戏 → 进入城镇, 退出游戏）"""
    surface.fill((8, 8, 15))
    # 背景粒子
    for _ in range(5):
        px = random.randint(0, WIDTH)
        py = random.randint(0, HEIGHT)
        ps = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(ps, (PURPLE[0], PURPLE[1], PURPLE[2], random.randint(20, 80)), (3, 3), 3)
        surface.blit(ps, (px, py))

    # 标题
    title = _render_outlined(font_title, i18n.t("暗夜割草者"), CYAN)
    surface.blit(title, (WIDTH//2 - title.get_width()//2, max(80, HEIGHT//6)))
    subtitle = _render_outlined(font_md, i18n.t("深 渊 轮 回"), (PURPLE))
    surface.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, max(170, HEIGHT//6 + 90)))

    # 装饰光环
    t = pygame.time.get_ticks() / 1000.0
    pulse = (math.sin(t * 2) + 1) * 0.5
    glow_r = int(120 + pulse * 20)
    glow_s = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
    pygame.draw.circle(glow_s, (PURPLE[0], PURPLE[1], PURPLE[2], int(10 + pulse * 15)),
                       (glow_r, glow_r), glow_r)
    surface.blit(glow_s, (WIDTH // 2 - glow_r, max(120, HEIGHT//6 + 40) - glow_r + 40))

    # 按钮
    buttons = {}
    start_y = max(280, HEIGHT//2 - 60)
    btn_data = [
        ('start',    i18n.t("开始游戏"),   CYAN,    start_y),
        ('settings', i18n.t("设置"),       PURPLE,  start_y + 80),
        ('lang',     i18n.t("语言"),       ORANGE,  start_y + 160),
        ('quit',     i18n.t("退出游戏"),   RED,     start_y + 240),
    ]
    for key, text, color, y in btn_data:
        btn_w, btn_h = 300, 58
        bx = WIDTH // 2 - btn_w // 2
        rect = pygame.Rect(bx, y, btn_w, btn_h)
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint(mx, my)
        bc = color if hover else tuple(max(0, c-60) for c in color)
        bs = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        pygame.draw.rect(bs, (*bc, 40 if not hover else 80), (0, 0, btn_w, btn_h), border_radius=10)
        pygame.draw.rect(bs, (*bc, 200), (0, 0, btn_w, btn_h), 2, border_radius=10)
        surface.blit(bs, (bx, y))
        bt = _render_outlined(font_lg, text, color)
        surface.blit(bt, (WIDTH//2 - bt.get_width()//2, y + btn_h//2 - bt.get_height()//2))
        buttons[key] = rect

    # 底部信息
    info = _render_outlined(
        font_xs,
        i18n.t("总局数: {runs}  最佳击杀: {best}", runs=save_data['total_runs'], best=save_data['best_kills']),
        (80, 80, 100),
    )
    surface.blit(info, (WIDTH//2 - info.get_width()//2, HEIGHT - 40))
    return buttons


def draw_settings_screen(surface):
    """显示设置界面"""
    surface.fill((8, 8, 15))
    
    title = _render_outlined(font_lg, i18n.t("显示设置"), CYAN)
    surface.blit(title, (WIDTH//2 - title.get_width()//2, 60))
    
    buttons = {}
    
    # 当前设置
    current_res = save_data.get('resolution', DEFAULT_RESOLUTION)
    current_fullscreen = save_data.get('fullscreen', False)
    
    # 分辨率选择
    res_label = _render_outlined(font_md, i18n.t("分辨率"), WHITE)
    surface.blit(res_label, (WIDTH//2 - 250, 150))
    
    y = 200
    for i, res in enumerate(AVAILABLE_RESOLUTIONS):
        w, h = res
        res_text = f"{w} x {h}"
        is_current = (w, h) == current_res
        
        btn_w, btn_h = 200, 45
        bx = WIDTH//2 - 250 + (i % 2) * 220
        by = y + (i // 2) * 60
        rect = pygame.Rect(bx, by, btn_w, btn_h)
        
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint(mx, my)
        
        color = GREEN if is_current else (CYAN if hover else (60, 60, 80))
        pygame.draw.rect(surface, color, rect, 0 if is_current else 2, border_radius=8)
        if is_current:
            pygame.draw.rect(surface, (*color, 60), rect.inflate(-4, -4), 0, border_radius=6)
        
        text = _render_outlined(font_sm, res_text, WHITE if is_current else CYAN)
        surface.blit(text, (bx + btn_w//2 - text.get_width()//2, by + btn_h//2 - text.get_height()//2))
        
        buttons[f'res_{i}'] = (rect, res)
    
    # 全屏选项
    fs_label = _render_outlined(font_md, i18n.t("显示模式"), WHITE)
    surface.blit(fs_label, (WIDTH//2 - 250, y + 180))
    
    fs_y = y + 230
    for i, (mode_key, mode_text) in enumerate([('window', '窗口模式'), ('fullscreen', '全屏模式')]):
        is_fullscreen = (mode_key == 'fullscreen')
        is_current = is_fullscreen == current_fullscreen
        
        btn_w, btn_h = 200, 45
        bx = WIDTH//2 - 250 + i * 220
        rect = pygame.Rect(bx, fs_y, btn_w, btn_h)
        
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint(mx, my)
        
        color = GREEN if is_current else (CYAN if hover else (60, 60, 80))
        pygame.draw.rect(surface, color, rect, 0 if is_current else 2, border_radius=8)
        if is_current:
            pygame.draw.rect(surface, (*color, 60), rect.inflate(-4, -4), 0, border_radius=6)
        
        text = _render_outlined(font_sm, i18n.t(mode_text), WHITE if is_current else CYAN)
        surface.blit(text, (bx + btn_w//2 - text.get_width()//2, fs_y + btn_h//2 - text.get_height()//2))
        
        buttons[f'fs_{mode_key}'] = (rect, is_fullscreen)
    
    # 应用按钮
    apply_y = fs_y + 80
    apply_w, apply_h = 180, 50
    apply_rect = pygame.Rect(WIDTH//2 - apply_w//2, apply_y, apply_w, apply_h)
    mx, my = pygame.mouse.get_pos()
    hover = apply_rect.collidepoint(mx, my)
    
    color = GOLD if hover else ORANGE
    pygame.draw.rect(surface, (*color, 80), apply_rect, 0, border_radius=10)
    pygame.draw.rect(surface, color, apply_rect, 2, border_radius=10)
    
    apply_text = _render_outlined(font_md, i18n.t("应用"), color)
    surface.blit(apply_text, (WIDTH//2 - apply_text.get_width()//2, apply_y + apply_h//2 - apply_text.get_height()//2))
    buttons['apply'] = (apply_rect, None)
    
    # 返回提示
    back_hint = _render_outlined(font_sm, i18n.t("ESC 返回"), (100, 100, 120))
    surface.blit(back_hint, (WIDTH//2 - back_hint.get_width()//2, HEIGHT - 50))
    
    return buttons

def draw_language_screen(surface):
    """语言选择界面"""
    surface.fill((8, 8, 15))
    title = _render_outlined(font_lg, i18n.t("选择语言"), CYAN)
    surface.blit(title, (WIDTH//2 - title.get_width()//2, 120))

    buttons = {}
    langs = i18n.available_languages()
    start_y = 220
    btn_w, btn_h = 280, 48
    for i, code in enumerate(langs):
        y = start_y + i * 70
        rect = pygame.Rect(WIDTH//2 - btn_w//2, y, btn_w, btn_h)
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint(mx, my)
        bc = CYAN if hover else (100, 120, 140)
        bs = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        pygame.draw.rect(bs, (*bc, 40 if not hover else 80), (0, 0, btn_w, btn_h), border_radius=8)
        pygame.draw.rect(bs, (*bc, 200), (0, 0, btn_w, btn_h), 2, border_radius=8)
        surface.blit(bs, (rect.x, rect.y))
        label = i18n.lang_name(code)
        # 用对应语言的字体渲染，确保韩文等非拉丁文字首次就能正确显示
        lang_font = get_font(28, code)
        bt = _render_outlined(lang_font, label, bc)
        surface.blit(bt, (WIDTH//2 - bt.get_width()//2, y + btn_h//2 - bt.get_height()//2))
        buttons[('lang', code)] = rect

    back_rect = pygame.Rect(WIDTH//2 - 120, HEIGHT - 80, 240, 40)
    mx, my = pygame.mouse.get_pos()
    hover = back_rect.collidepoint(mx, my)
    bc = (200, 200, 200) if hover else (120, 120, 140)
    bs = pygame.Surface((back_rect.w, back_rect.h), pygame.SRCALPHA)
    pygame.draw.rect(bs, (*bc, 60 if hover else 30), (0, 0, back_rect.w, back_rect.h), border_radius=6)
    pygame.draw.rect(bs, (*bc, 180), (0, 0, back_rect.w, back_rect.h), 2, border_radius=6)
    surface.blit(bs, back_rect.topleft)
    bt = _render_outlined(font_sm, i18n.t("返回"), bc)
    surface.blit(bt, (back_rect.centerx - bt.get_width()//2, back_rect.centery - bt.get_height()//2))
    buttons['back'] = back_rect
    return buttons


def draw_char_select(surface):
    """角色选择界面"""
    surface.fill((10, 8, 18))
    title = _render_outlined(font_lg, i18n.t("选择角色"), WHITE)
    surface.blit(title, (WIDTH//2 - title.get_width()//2, 30))

    n = characters.get_character_count()
    card_w, card_h = 160, 280
    spacing = 15
    total_w = n * card_w + (n-1) * spacing
    start_x = WIDTH // 2 - total_w // 2

    cards = {}
    mx, my = pygame.mouse.get_pos()

    for i in range(n):
        info = characters.get_character_info(i)
        x = start_x + i * (card_w + spacing)
        y = 100
        rect = pygame.Rect(x, y, card_w, card_h)
        hover = rect.collidepoint(mx, my)

        # 卡片背景
        cs = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        bg_a = 60 if hover else 30
        pygame.draw.rect(cs, (*info['color'], bg_a), (0, 0, card_w, card_h), border_radius=10)
        border_a = 200 if hover else 80
        pygame.draw.rect(cs, (*info['color'], border_a), (0, 0, card_w, card_h), 2, border_radius=10)
        surface.blit(cs, (x, y))

        # 角色预览 (创建临时角色画)
        temp_char = characters.create_character(i, x + card_w // 2, y + 80)
        temp_char.anim_timer = pygame.time.get_ticks() / 1000.0
        temp_char.draw(surface, (0, 0))

        # 名称
        nt = _render_outlined(font_sm, info['name'], WHITE)
        surface.blit(nt, (x + card_w//2 - nt.get_width()//2, y + 120))
        tt = _render_outlined(font_xs, info['title'], info['color'])
        surface.blit(tt, (x + card_w//2 - tt.get_width()//2, y + 145))

        # 描述 (换行)
        desc = info['desc']
        desc_parts = [desc[j:j+10] for j in range(0, len(desc), 10)]
        for j, part in enumerate(desc_parts[:4]):
            dt = _render_outlined(font_xs, part, (160, 160, 170))
            surface.blit(dt, (x + 10, y + 170 + j * 16))

        # 锁定检查
        if i not in save_data.get('unlocked_chars', [0]) and i > 0:
            lock = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            pygame.draw.rect(lock, (0, 0, 0, 150), (0, 0, card_w, card_h), border_radius=10)
            lt = _render_outlined(font_md, i18n.t("未解锁"), (100, 100, 100))
            surface.blit(lock, (x, y))
            surface.blit(lt, (x + card_w//2 - lt.get_width()//2, y + card_h//2 - lt.get_height()//2 - 15))
            # 显示解锁条件
            cond = meta_systems.CHAR_UNLOCK_CONDITIONS.get(i, {})
            cond_desc = cond.get('desc', '')
            if cond_desc:
                cd = _render_outlined(font_xs, cond_desc, (150, 130, 80))
                surface.blit(cd, (x + card_w//2 - cd.get_width()//2, y + card_h//2 + 12))
        else:
            cards[i] = rect

    # 提示
    hint = _render_outlined(font_sm, i18n.t("点击角色开始游戏"), (120, 120, 140))
    surface.blit(hint, (WIDTH//2 - hint.get_width()//2, 420))
    back = _render_outlined(font_xs, i18n.t("ESC 返回主菜单"), (80, 80, 100))
    surface.blit(back, (WIDTH//2 - back.get_width()//2, 460))
    return cards


def draw_upgrade_screen(surface):
    """升级选择界面"""
    # 暗化背景
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surface.blit(overlay, (0, 0))

    title = _render_outlined(font_lg, i18n.t("等级提升! Lv.{level}", level=run.level), GOLD)
    surface.blit(title, (WIDTH//2 - title.get_width()//2, 80))

    cards = {}
    n = len(run.upgrade_options)
    card_w, card_h = 200, 250
    spacing = 20
    total_w = n * card_w + (n-1) * spacing
    start_x = WIDTH // 2 - total_w // 2

    mx, my = pygame.mouse.get_pos()

    for i, opt in enumerate(run.upgrade_options):
        x = start_x + i * (card_w + spacing)
        y = 180
        rect = pygame.Rect(x, y, card_w, card_h)
        hover = rect.collidepoint(mx, my)

        color = opt.get('color', WHITE)
        cs = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        bg_a = 80 if hover else 40
        pygame.draw.rect(cs, (*color, bg_a), (0, 0, card_w, card_h), border_radius=10)
        border_a = 255 if hover else 120
        pygame.draw.rect(cs, (*color, border_a), (0, 0, card_w, card_h), 2, border_radius=10)
        surface.blit(cs, (x, y))

        # 图标
        icon = opt.get('icon', '?')
        it = _render_outlined(font_lg, icon, color)
        surface.blit(it, (x + card_w//2 - it.get_width()//2, y + 20))

        # 类型标签
        type_labels = {
            'new_weapon': i18n.t('新武器'),
            'weapon_upgrade': i18n.t('武器强化'),
            'new_passive': i18n.t('被动物品'),
            'stat_boost': i18n.t('属性提升'),
        }
        tl = _render_outlined(font_xs, type_labels.get(opt['type'], ''), (150, 150, 160))
        surface.blit(tl, (x + card_w//2 - tl.get_width()//2, y + 80))

        # 名称
        nt = _render_outlined(font_sm, i18n.t(opt['name']), WHITE)
        surface.blit(nt, (x + card_w//2 - nt.get_width()//2, y + 105))

        # 描述
        desc = i18n.t(opt.get('desc', ''))
        desc_parts = [desc[j:j+12] for j in range(0, len(desc), 12)]
        for j, part in enumerate(desc_parts[:4]):
            dt = _render_outlined(font_xs, part, (170, 170, 180))
            surface.blit(dt, (x + 12, y + 140 + j * 18))

        cards[i] = rect

    return cards


def draw_pause_screen(surface):
    """暂停界面"""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surface.blit(overlay, (0, 0))

    title = _render_outlined(font_lg, i18n.t("已暂停"), WHITE)
    surface.blit(title, (WIDTH//2 - title.get_width()//2, 200))

    # 统计
    stats = [
        i18n.t("存活时间: {time}", time=f"{int(run.game_time//60):02d}:{int(run.game_time%60):02d}"),
        f"{i18n.t('等级')} : {run.level}  {i18n.t('击杀数')} : {run.kills}",
        f"{i18n.t('武器')} : {len(run.weapons)}/6  {i18n.t('被动物品')} : {len(run.passives)}/6",
    ]
    for i, s in enumerate(stats):
        st = _render_outlined(font_sm, s, (180, 180, 180))
        surface.blit(st, (WIDTH//2 - st.get_width()//2, 280 + i * 30))

    buttons = {}
    btn_data = [
        ('resume', i18n.t("继续游戏"),  CYAN,  400),
        ('restart', i18n.t("重新开始"), ORANGE, 460),
        ('menu',   i18n.t("返回主菜单"), RED,    520),
    ]
    for key, text, color, y in btn_data:
        btn_w, btn_h = 220, 44
        bx = WIDTH//2 - btn_w//2
        rect = pygame.Rect(bx, y, btn_w, btn_h)
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint(mx, my)
        bs = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        bc = color if hover else tuple(max(0, c-60) for c in color)
        pygame.draw.rect(bs, (*bc, 60 if hover else 30), (0, 0, btn_w, btn_h), border_radius=6)
        pygame.draw.rect(bs, (*bc, 180), (0, 0, btn_w, btn_h), 2, border_radius=6)
        surface.blit(bs, (bx, y))
        bt = _render_outlined(font_md, text, color)
        surface.blit(bt, (WIDTH//2 - bt.get_width()//2, y + btn_h//2 - bt.get_height()//2))
        buttons[key] = rect
    return buttons


def draw_gameover_screen(surface):
    """游戏结束界面"""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))

    title = _render_outlined(font_lg, i18n.t("深渊吞噬了你..."), RED)
    surface.blit(title, (WIDTH//2 - title.get_width()//2, 120))

    # 计算灵魂碎片
    souls = int(run.kills * 0.1 + run.game_time / 60 * 5 + run.boss_spawned_count * 30)

    stats = [
        i18n.t("存活时间: {time}", time=f"{int(run.game_time//60):02d}:{int(run.game_time%60):02d}"),
        i18n.t("击杀数: {kills}", kills=run.kills),
        i18n.t("最终等级: Lv.{level}", level=run.level),
        i18n.t("最高连击: {combo}", combo=combo.best),
        i18n.t("获得灵魂碎片: +{souls}", souls=souls),
    ]
    for i, s in enumerate(stats):
        c = GOLD if '灵魂碎片' in s else (180, 180, 180)
        st = _render_outlined(font_sm, s, c)
        surface.blit(st, (WIDTH//2 - st.get_width()//2, 220 + i * 35))

    buttons = {}
    btn_data = [
        ('retry', i18n.t("再来一局"), CYAN, 500),
        ('menu',  i18n.t("返回主菜单"), (150, 150, 150), 560),
    ]
    for key, text, color, y in btn_data:
        btn_w, btn_h = 220, 44
        bx = WIDTH//2 - btn_w//2
        rect = pygame.Rect(bx, y, btn_w, btn_h)
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint(mx, my)
        bs = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        bc = color if hover else tuple(max(0, c-60) for c in color)
        pygame.draw.rect(bs, (*bc, 60 if hover else 30), (0, 0, btn_w, btn_h), border_radius=6)
        pygame.draw.rect(bs, (*bc, 180), (0, 0, btn_w, btn_h), 2, border_radius=6)
        surface.blit(bs, (bx, y))
        bt = _render_outlined(font_md, text, color)
        surface.blit(bt, (WIDTH//2 - bt.get_width()//2, y + btn_h//2 - bt.get_height()//2))
        buttons[key] = rect
    return buttons, souls


def draw_victory_screen(surface):
    """胜利界面"""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))

    title = _render_outlined(font_lg, i18n.t("你击败了深渊之主!"), GOLD)
    surface.blit(title, (WIDTH//2 - title.get_width()//2, 120))

    souls = int(run.kills * 0.1 + 30 * 5 + run.boss_spawned_count * 30 + 100)  # 胜利额外100

    stats = [
        i18n.t("通关时间: {time}", time=f"{int(run.game_time//60):02d}:{int(run.game_time%60):02d}"),
        i18n.t("击杀数: {kills}", kills=run.kills),
        i18n.t("最终等级: Lv.{level}", level=run.level),
        i18n.t("获得灵魂碎片: +{souls}", souls=souls),
    ]
    for i, s in enumerate(stats):
        c = GOLD if '灵魂碎片' in s else WHITE
        st = _render_outlined(font_sm, s, c)
        surface.blit(st, (WIDTH//2 - st.get_width()//2, 220 + i * 35))

    buttons = {}
    btn_data = [
        ('menu', i18n.t("返回主菜单"), GOLD, 530),
    ]
    for key, text, color, y in btn_data:
        btn_w, btn_h = 220, 44
        bx = WIDTH//2 - btn_w//2
        rect = pygame.Rect(bx, y, btn_w, btn_h)
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint(mx, my)
        bs = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        bc = color if hover else tuple(max(0, c-60) for c in color)
        pygame.draw.rect(bs, (*bc, 60 if hover else 30), (0, 0, btn_w, btn_h), border_radius=6)
        pygame.draw.rect(bs, (*bc, 180), (0, 0, btn_w, btn_h), 2, border_radius=6)
        surface.blit(bs, (bx, y))
        bt = _render_outlined(font_md, text, color)
        surface.blit(bt, (WIDTH//2 - bt.get_width()//2, y + btn_h//2 - bt.get_height()//2))
        buttons[key] = rect
    return buttons, souls


def draw_soul_shop(surface):
    """灵魂商店"""
    surface.fill((10, 5, 20))
    title = _render_outlined(font_lg, i18n.t("灵魂商店"), GOLD)
    surface.blit(title, (WIDTH//2 - title.get_width()//2, 30))

    soul_t = _render_outlined(
        font_md,
        i18n.t("灵魂碎片: {value}", value=save_data['soul_shards']),
        GOLD,
    )
    surface.blit(soul_t, (WIDTH//2 - soul_t.get_width()//2, 85))

    paths = [
        (i18n.t("生存之路"), [(i18n.t("+10 HP"), 50), (i18n.t("+20 HP"), 120), (i18n.t("+30 HP"), 250), (i18n.t("+2 护甲"), 400), (i18n.t("+0.5 回血"), 600)], GREEN),
        (i18n.t("战斗之路"), [(i18n.t("+5% 伤害"), 50), (i18n.t("+3% 暴击"), 120), (i18n.t("+5% 冷缩"), 250), (i18n.t("+5% 攻速"), 400), (i18n.t("+1 初始武器"), 800)], RED),
        (i18n.t("探索之路"), [(i18n.t("+5% 移速"), 50), (i18n.t("+20 拾取"), 120), (i18n.t("+10% 经验"), 250), (i18n.t("+1 升级选项"), 500), (i18n.t("初始Lv3"), 800)], CYAN),
        (i18n.t("命运之路"), [(i18n.t("+1 武器栏"), 500), (i18n.t("+1 被动栏"), 500), (i18n.t("+1 武器栏"), 1200), (i18n.t("+1 被动栏"), 1200), (i18n.t("开局选诅咒"), 2000)], PURPLE),
    ]

    path_keys = ['survival', 'combat', 'exploration', 'fate']
    buttons = {}
    mx, my = pygame.mouse.get_pos()

    for row, (path_name, upgrades, color) in enumerate(paths):
        py_start = 130 + row * 140
        pnt = _render_outlined(font_sm, path_name, color)
        surface.blit(pnt, (30, py_start))

        current = save_data['upgrades'].get(path_keys[row], 0)
        for col, (desc, cost) in enumerate(upgrades):
            x = 40 + col * 220
            y = py_start + 30
            w, h = 200, 80
            rect = pygame.Rect(x, y, w, h)
            unlocked = col < current
            available = col == current and save_data['soul_shards'] >= cost
            hover = rect.collidepoint(mx, my) and available

            cs = pygame.Surface((w, h), pygame.SRCALPHA)
            if unlocked:
                pygame.draw.rect(cs, (*color, 40), (0, 0, w, h), border_radius=6)
                pygame.draw.rect(cs, (*color, 120), (0, 0, w, h), 2, border_radius=6)
            elif available:
                ba = 80 if hover else 30
                pygame.draw.rect(cs, (*color, ba), (0, 0, w, h), border_radius=6)
                pygame.draw.rect(cs, (*color, 200 if hover else 100), (0, 0, w, h), 2, border_radius=6)
            else:
                pygame.draw.rect(cs, (40, 40, 50, 80), (0, 0, w, h), border_radius=6)
                pygame.draw.rect(cs, (60, 60, 70, 100), (0, 0, w, h), 2, border_radius=6)
            surface.blit(cs, (x, y))

            dt = _render_outlined(font_xs, desc, color if (unlocked or available) else (80, 80, 90))
            surface.blit(dt, (x + w//2 - dt.get_width()//2, y + 15))

            if unlocked:
                st = _render_outlined(font_xs, i18n.t("已解锁"), (100, 200, 100))
            elif available:
                st = _render_outlined(font_xs, i18n.t("花费 {cost}", cost=cost), GOLD)
            else:
                st = _render_outlined(font_xs, i18n.t("需要 {cost}", cost=cost), (80, 80, 90))
            surface.blit(st, (x + w//2 - st.get_width()//2, y + 45))

            if available:
                buttons[(path_keys[row], col)] = rect

    # 返回按钮
    back_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT - 60, 200, 40)
    hover = back_rect.collidepoint(mx, my)
    bs = pygame.Surface((200, 40), pygame.SRCALPHA)
    pygame.draw.rect(bs, (200, 200, 200, 40 if not hover else 80), (0, 0, 200, 40), border_radius=6)
    pygame.draw.rect(bs, (200, 200, 200, 150), (0, 0, 200, 40), 2, border_radius=6)
    surface.blit(bs, back_rect.topleft)
    bt = _render_outlined(font_sm, i18n.t("返回"), WHITE)
    surface.blit(bt, (WIDTH//2 - bt.get_width()//2, HEIGHT - 55))
    buttons['back'] = back_rect

    return buttons


# ============================================================
#  游戏初始化/重置
# ============================================================
def init_run(char_index=0):
    """初始化一局游戏"""
    global run, enemies, bosses, exp_gems, particles, enemy_bullets
    run = RunData()
    run.apply_character(char_index)
    run.apply_permanent_bonuses()

    # 初始武器 (根据角色给不同初始武器)
    starter_weapons = {
        0: MagicMissile,    # 阿什
        1: Boomerang,       # 莉拉
        2: BoneShield,      # 加隆
        3: Fireball,        # 菲奥
        4: IceNova,         # 虚无 (原型用寒冰代替虚空之眼)
        5: HolyWhip,        # 死神 (原型用圣光鞭代替镰刀)
    }
    weapon_cls = starter_weapons.get(char_index, MagicMissile)
    run.weapons.append(weapon_cls())

    # 清空
    enemies.clear()
    bosses.clear()
    exp_gems.clear()
    particles.clear()
    enemy_bullets.clear()
    combo.reset()

    # Boss模块初始化
    boss_module.init(
        run,  # player-like object
        lambda: [],  # swords_ref (不使用旧系统)
        screen_shake,
        create_particles,
        play_sfx,
        font_sm, font_xs,
        WIDTH, HEIGHT
    )


# ============================================================
#  主循环
# ============================================================
def main():
    global run, enemies, bosses, exp_gems, particles, enemy_bullets, save_data, material_drops

    game_state = GameState.START
    start_buttons = {}
    settings_buttons = {}
    lang_buttons = {}
    char_cards = {}
    pause_buttons = {}
    upgrade_cards = {}
    over_buttons = {}
    victory_buttons = {}
    shop_buttons = {}
    inventory_buttons = {}
    codex_buttons = {}
    dungeon_buttons = {}
    char_upgrade_buttons = {}
    gacha_buttons = {}
    settlement_buttons = {}
    boss_warning_timer = 0
    spawn_timer = 0

    # 新界面状态变量
    codex_tab = 'characters'
    selected_upgrade_char = 0
    equip_scroll = 0
    gacha_results = None
    settlement_rewards = None
    current_dungeon = None    # 当前副本信息
    bosses_killed_this_run = 0

    # 初始化局外模块
    meta_systems.init(screen, font_lg, font_md, font_sm, font_xs, WIDTH, HEIGHT)
    dialogue_system.init(screen, font_lg, font_md, font_sm, font_xs, WIDTH, HEIGHT)
    gacha_animation.init(screen, font_lg, font_md, font_sm, font_xs, WIDTH, HEIGHT)
    town_map.init(screen, font_lg, font_md, font_sm, font_xs, WIDTH, HEIGHT)
    npc_buttons = {}
    dialogue_buttons = {}

    # 城镇玩家
    town_player = town_map.TownPlayer(800, 500, 0)
    # 抽卡动画控制器
    gacha_anim = None

    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.033)
        mouse_pos = pygame.mouse.get_pos()

        # ==== 事件 ====
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game_state == GameState.PLAYING:
                        game_state = GameState.PAUSED
                    elif game_state == GameState.PAUSED:
                        game_state = GameState.PLAYING
                    elif game_state == GameState.CHAR_SELECT:
                        game_state = GameState.TOWN
                    elif game_state == GameState.LANG_SELECT:
                        game_state = GameState.START
                    elif game_state == GameState.SOUL_SHOP:
                        game_state = GameState.TOWN
                    elif game_state == GameState.INVENTORY:
                        game_state = GameState.PLAYING
                    elif game_state == GameState.CODEX:
                        game_state = GameState.TOWN
                    elif game_state == GameState.DUNGEON_SELECT:
                        game_state = GameState.TOWN
                    elif game_state == GameState.CHAR_UPGRADE:
                        game_state = GameState.TOWN
                    elif game_state == GameState.GACHA:
                        gacha_results = None
                        game_state = GameState.TOWN
                    elif game_state == GameState.NPC_SELECT:
                        game_state = GameState.TOWN
                    elif game_state == GameState.DIALOGUE:
                        dialogue_system.dialogue_state.active = False
                        game_state = GameState.TOWN
                    elif game_state == GameState.TOWN:
                        game_state = GameState.START
                    elif game_state == GameState.GACHA_ANIM:
                        if gacha_anim:
                            gacha_anim.skip()
                if event.key == pygame.K_e:
                    if game_state == GameState.TOWN and town_player.nearby_location:
                        loc = town_player.nearby_location
                        action = loc.action
                        if action == 'dungeon':
                            game_state = GameState.DUNGEON_SELECT
                        elif action == 'gacha':
                            gacha_results = None
                            game_state = GameState.GACHA
                        elif action == 'upgrade':
                            game_state = GameState.CHAR_UPGRADE
                        elif action == 'shop':
                            game_state = GameState.SOUL_SHOP
                        elif action == 'codex':
                            codex_tab = 'characters'
                            game_state = GameState.CODEX
                        elif action == 'start_run':
                            current_dungeon = None
                            game_state = GameState.CHAR_SELECT
                        elif action.startswith('npc_'):
                            npc_id = action.replace('npc_', '')
                            dialogue_system.dialogue_state.start(npc_id, save_data)
                            game_state = GameState.DIALOGUE
                        play_sfx('select')
                if event.key in (pygame.K_TAB, pygame.K_i):
                    if game_state == GameState.PLAYING:
                        game_state = GameState.INVENTORY
                    elif game_state == GameState.INVENTORY:
                        game_state = GameState.PLAYING

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # ---- 主菜单 ----
                if game_state == GameState.START:
                    if start_buttons.get('start') and start_buttons['start'].collidepoint(mouse_pos):
                        game_state = GameState.TOWN
                        play_sfx('select')
                    elif start_buttons.get('settings') and start_buttons['settings'].collidepoint(mouse_pos):
                        game_state = GameState.SETTINGS
                        play_sfx('select')
                    elif start_buttons.get('lang') and start_buttons['lang'].collidepoint(mouse_pos):
                        game_state = GameState.LANG_SELECT
                        play_sfx('select')
                    elif start_buttons.get('quit') and start_buttons['quit'].collidepoint(mouse_pos):
                        running = False

                # ---- 语言选择 ----
                elif game_state == GameState.LANG_SELECT:
                    if lang_buttons.get('back') and lang_buttons['back'].collidepoint(mouse_pos):
                        game_state = GameState.START
                        play_sfx('select')
                    else:
                        for key, rect in lang_buttons.items():
                            if isinstance(key, tuple) and key[0] == 'lang':
                                if rect.collidepoint(mouse_pos):
                                    set_game_language(key[1])
                                    game_state = GameState.START
                                    play_sfx('select')
                                    break

                # ---- 显示设置 ----
                elif game_state == GameState.SETTINGS:
                    handled = False
                    # 检查应用按钮
                    if settings_buttons.get('apply'):
                        rect, _ = settings_buttons['apply']
                        if rect.collidepoint(mouse_pos):
                            res = tuple(save_data.get('resolution', list(DEFAULT_RESOLUTION)))
                            fs = save_data.get('fullscreen', False)
                            apply_display_settings(res, fs)
                            game_state = GameState.START
                            play_sfx('select')
                            handled = True
                    
                    # 检查分辨率和显示模式选项
                    if not handled:
                        for key, value in settings_buttons.items():
                            if key.startswith('res_'):
                                rect, res = value
                                if rect.collidepoint(mouse_pos):
                                    save_data['resolution'] = list(res)
                                    save_game(save_data)
                                    play_sfx('select')
                                    break
                            elif key.startswith('fs_'):
                                rect, is_fullscreen = value
                                if rect.collidepoint(mouse_pos):
                                    save_data['fullscreen'] = is_fullscreen
                                    save_game(save_data)
                                    play_sfx('select')
                                    break

                # ---- 角色选择 ----
                elif game_state == GameState.CHAR_SELECT:
                    for idx, rect in char_cards.items():
                        if rect.collidepoint(mouse_pos):
                            init_run(idx)
                            bosses_killed_this_run = 0
                            game_state = GameState.PLAYING
                            play_sfx('levelup')
                            save_data['total_runs'] += 1
                            # 图鉴解锁角色
                            if idx not in save_data.get('codex_chars', []):
                                save_data['codex_chars'].append(idx)
                            # 图鉴解锁初始武器
                            starter_names = ['魔法飞弹', '回旋镖', '骨盾环绕', '火球术', '寒冰新星', '圣光鞭']
                            if idx < len(starter_names):
                                wn = starter_names[idx]
                                if wn not in save_data.get('codex_weapons', []):
                                    save_data['codex_weapons'].append(wn)
                            # 局外角色等级加成
                            char_lv = int(save_data.get('char_levels', {}).get(str(idx), 1))
                            if char_lv > 1:
                                bonus = meta_systems.get_char_stat_bonus(char_lv)
                                for sk, sv in bonus.items():
                                    run.apply_stat(sk, sv)
                            # 局外装备加成
                            equip_stats = meta_systems.get_meta_equip_stats(save_data, idx, EQUIPMENT_DB)
                            for sk, sv in equip_stats.items():
                                run.apply_stat(sk, sv)
                            break

                # ---- 暂停 ----
                elif game_state == GameState.PAUSED:
                    if pause_buttons.get('resume') and pause_buttons['resume'].collidepoint(mouse_pos):
                        game_state = GameState.PLAYING
                    elif pause_buttons.get('restart') and pause_buttons['restart'].collidepoint(mouse_pos):
                        game_state = GameState.CHAR_SELECT
                    elif pause_buttons.get('menu') and pause_buttons['menu'].collidepoint(mouse_pos):
                        game_state = GameState.START

                # ---- 升级 ----
                elif game_state == GameState.UPGRADE:
                    for idx, rect in upgrade_cards.items():
                        if rect.collidepoint(mouse_pos):
                            opt = run.upgrade_options[idx]
                            # 应用选择
                            if opt['type'] == 'new_weapon':
                                new_w = opt['cls']()
                                run.weapons.append(new_w)
                                # 图鉴解锁武器
                                wn = getattr(new_w, 'WEAPON_NAME', '')
                                if wn and wn not in save_data.get('codex_weapons', []):
                                    save_data['codex_weapons'].append(wn)
                            elif opt['type'] == 'weapon_upgrade':
                                opt['weapon'].level += 1
                                if isinstance(opt['weapon'], BoneShield):
                                    opt['weapon']._rebuild()
                            elif opt['type'] == 'new_passive':
                                item = opt['item']
                                run.passives.append(item)
                                for sk, sv in item[2].items():
                                    if isinstance(sv, (int, float)):
                                        run.apply_stat(sk, sv)
                            elif opt['type'] == 'stat_boost':
                                for sk, sv in opt['stats'].items():
                                    run.apply_stat(sk, sv)
                            play_sfx('levelup')
                            create_particles(WIDTH//2, HEIGHT//2, 30, 'levelup')
                            game_state = GameState.PLAYING
                            break

                # ---- 游戏结束 ----
                elif game_state == GameState.GAME_OVER:
                    if over_buttons.get('retry') and over_buttons['retry'].collidepoint(mouse_pos):
                        game_state = GameState.CHAR_SELECT
                    elif over_buttons.get('menu') and over_buttons['menu'].collidepoint(mouse_pos):
                        game_state = GameState.START

                # ---- 胜利 ----
                elif game_state == GameState.VICTORY:
                    if victory_buttons.get('menu') and victory_buttons['menu'].collidepoint(mouse_pos):
                        game_state = GameState.START

                # ---- 灵魂商店 ----
                elif game_state == GameState.SOUL_SHOP:
                    if shop_buttons.get('back') and shop_buttons['back'].collidepoint(mouse_pos):
                        game_state = GameState.TOWN
                        play_sfx('select')
                    else:
                        for key, rect in shop_buttons.items():
                            if key == 'back': continue
                            if rect.collidepoint(mouse_pos):
                                path_key, level = key
                                # 购买升级
                                paths_costs = {
                                    'survival': [50, 120, 250, 400, 600],
                                    'combat': [50, 120, 250, 400, 800],
                                    'exploration': [50, 120, 250, 500, 800],
                                    'fate': [500, 500, 1200, 1200, 2000],
                                }
                                cost = paths_costs[path_key][level]
                                if save_data['soul_shards'] >= cost:
                                    save_data['soul_shards'] -= cost
                                    save_data['upgrades'][path_key] = level + 1
                                    save_game(save_data)
                                    play_sfx('levelup')
                                    create_particles(mouse_pos[0], mouse_pos[1], 20, 'levelup')
                                break

                # ---- 背包/装备 ----
                elif game_state == GameState.INVENTORY:
                    for key, rect in inventory_buttons.items():
                        if rect.collidepoint(mouse_pos):
                            if key[0] == 'enhance':
                                slot = key[1]
                                eq = run.equipped[slot]
                                if eq and eq.enhance_level < 10:
                                    cost = get_equip_upgrade_cost(eq.enhance_level)
                                    can = all(run.materials.get(m, 0) >= c for m, c in cost.items())
                                    if can:
                                        eq.do_enhance(run.materials)
                                        play_sfx('levelup')
                                        create_particles(WIDTH//2, HEIGHT//2, 15, 'levelup')
                            elif key[0] == 'equip_bag':
                                idx = key[1]
                                if 0 <= idx < len(run.equipment_bag):
                                    bag_eq = run.equipment_bag[idx]
                                    run.equip_item(bag_eq)
                                    play_sfx('select')
                            break

                # ---- 图鉴 ----
                elif game_state == GameState.CODEX:
                    for key, rect in codex_buttons.items():
                        if isinstance(key, tuple) and key[0] == 'codex_tab':
                            if rect.collidepoint(mouse_pos):
                                codex_tab = key[1]
                                play_sfx('select')
                                break
                    if codex_buttons.get('back') and codex_buttons['back'].collidepoint(mouse_pos):
                        game_state = GameState.TOWN
                        play_sfx('select')

                # ---- 副本选择 ----
                elif game_state == GameState.DUNGEON_SELECT:
                    if dungeon_buttons.get('back') and dungeon_buttons['back'].collidepoint(mouse_pos):
                        game_state = GameState.TOWN
                        play_sfx('select')
                    else:
                        for key, rect in dungeon_buttons.items():
                            if isinstance(key, tuple) and key[0] == 'dungeon':
                                if rect.collidepoint(mouse_pos):
                                    current_dungeon = meta_systems.DUNGEON_LIST[key[1]]
                                    game_state = GameState.CHAR_SELECT
                                    play_sfx('select')
                                    break

                # ---- 角色升级 ----
                elif game_state == GameState.CHAR_UPGRADE:
                    # 解锁检查 - 未解锁角色不能升级 / 装备
                    char_real_idx = meta_systems.CHARACTER_CODEX[selected_upgrade_char][0]
                    is_char_unlocked = char_real_idx in save_data.get('unlocked_chars', [0])

                    if char_upgrade_buttons.get('back') and char_upgrade_buttons['back'].collidepoint(mouse_pos):
                        game_state = GameState.TOWN
                        play_sfx('select')
                    elif is_char_unlocked and char_upgrade_buttons.get('char_levelup') and char_upgrade_buttons['char_levelup'].collidepoint(mouse_pos):
                        cidx = selected_upgrade_char
                        clv = int(save_data.get('char_levels', {}).get(str(cidx), 1))
                        cost = meta_systems.get_char_level_cost(clv)
                        if save_data.get('gold', 0) >= cost and clv < 150:
                            save_data['gold'] -= cost
                            save_data['char_levels'][str(cidx)] = clv + 1
                            save_game(save_data)
                            play_sfx('levelup')
                    elif is_char_unlocked and char_upgrade_buttons.get('char_levelup10') and char_upgrade_buttons['char_levelup10'].collidepoint(mouse_pos):
                        cidx = selected_upgrade_char
                        clv = int(save_data.get('char_levels', {}).get(str(cidx), 1))
                        casc = int(save_data.get('char_ascend', {}).get(str(cidx), 0))
                        for _ in range(10):
                            if clv >= 150:
                                break
                            if clv % 10 == 0 and casc < clv // 10:
                                break  # 需要进阶
                            c = meta_systems.get_char_level_cost(clv)
                            if save_data.get('gold', 0) < c:
                                break
                            save_data['gold'] -= c
                            clv += 1
                        save_data['char_levels'][str(cidx)] = clv
                        save_game(save_data)
                        play_sfx('levelup')
                    elif is_char_unlocked and char_upgrade_buttons.get('char_ascend') and char_upgrade_buttons['char_ascend'].collidepoint(mouse_pos):
                        cidx = selected_upgrade_char
                        casc = int(save_data.get('char_ascend', {}).get(str(cidx), 0))
                        gold_c, dia_c, mat_c = meta_systems.get_char_ascend_cost(casc)
                        can = (save_data.get('gold', 0) >= gold_c and
                               save_data.get('diamond', 0) >= dia_c and
                               all(save_data.get('meta_materials', {}).get(m, 0) >= c for m, c in mat_c.items()))
                        if can:
                            save_data['gold'] -= gold_c
                            save_data['diamond'] -= dia_c
                            for m, c in mat_c.items():
                                save_data['meta_materials'][m] -= c
                            save_data['char_ascend'][str(cidx)] = casc + 1
                            save_game(save_data)
                            play_sfx('levelup')
                    elif char_upgrade_buttons.get('equip_prev') and char_upgrade_buttons['equip_prev'].collidepoint(mouse_pos):
                        equip_scroll = max(0, equip_scroll - 14)
                        play_sfx('select')
                    elif char_upgrade_buttons.get('equip_next') and char_upgrade_buttons['equip_next'].collidepoint(mouse_pos):
                        equip_scroll += 14
                        play_sfx('select')
                    else:
                        for key, rect in char_upgrade_buttons.items():
                            if isinstance(key, tuple) and key[0] == 'char_tab':
                                if rect.collidepoint(mouse_pos):
                                    selected_upgrade_char = key[1]
                                    equip_scroll = 0
                                    play_sfx('select')
                                    break
                            elif isinstance(key, tuple) and key[0] == 'equip_up':
                                if rect.collidepoint(mouse_pos):
                                    eq_idx = key[1]
                                    meqs = save_data.get('meta_equipment', [])
                                    if eq_idx < len(meqs):
                                        meq = meqs[eq_idx]
                                        tidx = meq.get('template_idx', 0)
                                        if tidx < len(EQUIPMENT_DB):
                                            tpl = EQUIPMENT_DB[tidx]
                                            eq_lv = meq.get('level', 1)
                                            cost = meta_systems.get_meta_equip_level_cost(eq_lv, tpl[2])
                                            if save_data.get('gold', 0) >= cost and eq_lv < 150:
                                                save_data['gold'] -= cost
                                                meq['level'] = eq_lv + 1
                                                if meq['level'] % 10 == 0:
                                                    meq['ascend'] = meq.get('ascend', 0) + 1
                                                save_game(save_data)
                                                play_sfx('levelup')
                                    break
                            elif isinstance(key, tuple) and key[0] == 'meta_equip' and is_char_unlocked:
                                if rect.collidepoint(mouse_pos):
                                    meta_systems.equip_meta_item(save_data, selected_upgrade_char, key[1], EQUIPMENT_DB)
                                    save_game(save_data)
                                    play_sfx('select')
                                    break
                            elif isinstance(key, tuple) and key[0] == 'unequip' and is_char_unlocked:
                                if rect.collidepoint(mouse_pos):
                                    meta_systems.unequip_meta_item(save_data, selected_upgrade_char, key[1])
                                    save_game(save_data)
                                    play_sfx('select')
                                    break
                            elif isinstance(key, tuple) and key[0] == 'batch_sell':
                                if rect.collidepoint(mouse_pos):
                                    sell_key = key[1]
                                    keep_map = {
                                        'sell_keep_leg':  ['legendary'],
                                        'sell_keep_ep':   ['epic', 'legendary'],
                                        'sell_keep_rare': ['rare', 'epic', 'legendary'],
                                    }
                                    keep = keep_map.get(sell_key, ['legendary'])
                                    sold, gold = meta_systems.batch_sell_equipment(
                                        save_data, EQUIPMENT_DB, keep)
                                    if sold > 0:
                                        equip_scroll = 0
                                        save_game(save_data)
                                        play_sfx('levelup')
                                    break

                # ---- 抽卡 ----
                elif game_state == GameState.GACHA:
                    if gacha_buttons.get('back') and gacha_buttons['back'].collidepoint(mouse_pos):
                        gacha_results = None
                        game_state = GameState.TOWN
                        play_sfx('select')
                    else:
                        for key, rect in gacha_buttons.items():
                            if not isinstance(key, tuple): continue
                            if not rect.collidepoint(mouse_pos): continue
                            pool, action = key
                            count = 1 if action == 'pull1' else 10
                            # 检查费用
                            if pool == 'normal':
                                cost = meta_systems.NORMAL_GACHA_COST if count == 1 else meta_systems.NORMAL_GACHA_10_COST
                                if save_data.get('gold', 0) < cost:
                                    break
                                save_data['gold'] -= cost
                            else:
                                cost = meta_systems.SUPER_GACHA_COST if count == 1 else meta_systems.SUPER_GACHA_10_COST
                                if save_data.get('diamond', 0) < cost:
                                    break
                                save_data['diamond'] -= cost
                            # 执行抽卡
                            gacha_results = []
                            for _ in range(count):
                                result = meta_systems.do_gacha_pull(pool, save_data, EQUIPMENT_DB)
                                if result:
                                    gacha_results.append(result)
                                    tidx, rarity = result
                                    save_data['meta_equipment'].append({
                                        'template_idx': tidx, 'level': 1, 'ascend': 0
                                    })
                                    if tidx not in save_data.get('codex_equips', []):
                                        save_data['codex_equips'].append(tidx)
                            save_data['gacha_total_pulls'] = save_data.get('gacha_total_pulls', 0) + count
                            save_game(save_data)
                            # 触发抽卡动画
                            if gacha_results:
                                gacha_anim = gacha_animation.GachaAnimation(gacha_results, EQUIPMENT_DB)
                                game_state = GameState.GACHA_ANIM
                            play_sfx('levelup')
                            break

                # ---- 结算界面 ----
                elif game_state == GameState.SETTLEMENT:
                    if settlement_buttons.get('confirm') and settlement_buttons['confirm'].collidepoint(mouse_pos):
                        game_state = GameState.TOWN
                        play_sfx('select')

                # ---- 城镇地图 ----
                elif game_state == GameState.TOWN:
                    # 点击互动
                    if town_player.nearby_location:
                        loc = town_player.nearby_location
                        action = loc.action
                        if action == 'dungeon':
                            game_state = GameState.DUNGEON_SELECT
                            play_sfx('select')
                        elif action == 'gacha':
                            gacha_results = None
                            game_state = GameState.GACHA
                            play_sfx('select')
                        elif action == 'upgrade':
                            game_state = GameState.CHAR_UPGRADE
                            play_sfx('select')
                        elif action == 'shop':
                            game_state = GameState.SOUL_SHOP
                            play_sfx('select')
                        elif action == 'codex':
                            codex_tab = 'characters'
                            game_state = GameState.CODEX
                            play_sfx('select')
                        elif action == 'start_run':
                            current_dungeon = None
                            game_state = GameState.CHAR_SELECT
                            play_sfx('select')
                        elif action.startswith('npc_'):
                            npc_id = action.replace('npc_', '')
                            dialogue_system.dialogue_state.start(npc_id, save_data)
                            game_state = GameState.DIALOGUE
                            play_sfx('select')

                # ---- 抽卡动画 ----
                elif game_state == GameState.GACHA_ANIM:
                    if gacha_anim:
                        done = gacha_anim.handle_click(mouse_pos)
                        if done:
                            game_state = GameState.GACHA
                            gacha_anim = None
                            play_sfx('select')

                # ---- NPC选择 ----
                elif game_state == GameState.NPC_SELECT:
                    if npc_buttons.get('back') and npc_buttons['back'].collidepoint(mouse_pos):
                        game_state = GameState.TOWN
                        play_sfx('select')
                    else:
                        for key, rect in npc_buttons.items():
                            if isinstance(key, tuple) and key[0] == 'npc':
                                if rect.collidepoint(mouse_pos):
                                    dialogue_system.dialogue_state.start(key[1], save_data)
                                    game_state = GameState.DIALOGUE
                                    play_sfx('select')
                                    break

                # ---- 对话 ----
                elif game_state == GameState.DIALOGUE:
                    ds = dialogue_system.dialogue_state
                    if dialogue_buttons.get('dialogue_close') and dialogue_buttons['dialogue_close'].collidepoint(mouse_pos):
                        ds.active = False
                        game_state = GameState.TOWN
                        play_sfx('select')
                    elif dialogue_buttons.get('dialogue_advance') and dialogue_buttons['dialogue_advance'].collidepoint(mouse_pos):
                        ds.advance()
                        if not ds.active:
                            game_state = GameState.TOWN
                        play_sfx('select')
                    else:
                        for key, rect in dialogue_buttons.items():
                            if isinstance(key, tuple) and key[0] == 'dialogue_choice':
                                if rect.collidepoint(mouse_pos):
                                    ds.select_choice(key[1])
                                    if not ds.active:
                                        game_state = GameState.TOWN
                                    play_sfx('select')
                                    break

        # ==== 状态处理 ====

        # ---- 主菜单 ----
        if game_state == GameState.START:
            start_buttons = draw_start_screen(screen)
            pygame.display.flip()
            continue

        # ---- 显示设置 ----
        if game_state == GameState.SETTINGS:
            settings_buttons = draw_settings_screen(screen)
            pygame.display.flip()
            continue

        # ---- 语言选择 ----
        if game_state == GameState.LANG_SELECT:
            lang_buttons = draw_language_screen(screen)
            pygame.display.flip()
            continue

        # ---- 城镇地图 ----
        if game_state == GameState.TOWN:
            keys = pygame.key.get_pressed()
            town_player.update(dt, keys)
            t = pygame.time.get_ticks() / 1000.0
            town_map.draw_town(screen, town_player, save_data, t)
            pygame.display.flip()
            continue

        # ---- 抽卡动画 ----
        if game_state == GameState.GACHA_ANIM:
            if gacha_anim:
                gacha_anim.update(dt)
                gacha_anim.draw(screen)
                if gacha_anim.finished:
                    game_state = GameState.GACHA
                    gacha_anim = None
            else:
                game_state = GameState.GACHA
            pygame.display.flip()
            continue

        # ---- NPC城镇 ----
        if game_state == GameState.NPC_SELECT:
            npc_buttons = dialogue_system.draw_npc_select(screen, save_data)
            pygame.display.flip()
            continue

        # ---- 对话 ----
        if game_state == GameState.DIALOGUE:
            dialogue_system.dialogue_state.update(dt)
            # 绘制暗色背景
            screen.fill((8, 8, 14))
            dialogue_buttons = dialogue_system.draw_dialogue_box(screen, save_data)
            if not dialogue_system.dialogue_state.active:
                game_state = GameState.TOWN
            pygame.display.flip()
            continue

        # ---- 角色选择 ----
        if game_state == GameState.CHAR_SELECT:
            char_cards = draw_char_select(screen)
            pygame.display.flip()
            continue

        # ---- 灵魂商店 ----
        if game_state == GameState.SOUL_SHOP:
            shop_buttons = draw_soul_shop(screen)
            # 粒子
            for p in particles:
                p.update(dt)
            particles = [p for p in particles if p.life > 0]
            for p in particles:
                p.draw(screen, [0, 0])
            pygame.display.flip()
            continue

        # ---- 图鉴 ----
        if game_state == GameState.CODEX:
            codex_buttons = meta_systems.draw_codex_screen(screen, save_data, codex_tab)
            pygame.display.flip()
            continue

        # ---- 副本选择 ----
        if game_state == GameState.DUNGEON_SELECT:
            dungeon_buttons = meta_systems.draw_dungeon_select(screen, save_data)
            pygame.display.flip()
            continue

        # ---- 角色升级 ----
        if game_state == GameState.CHAR_UPGRADE:
            char_upgrade_buttons = meta_systems.draw_char_upgrade_screen(screen, save_data, selected_upgrade_char, EQUIPMENT_DB, equip_scroll)
            pygame.display.flip()
            continue

        # ---- 抽卡 ----
        if game_state == GameState.GACHA:
            gacha_buttons = meta_systems.draw_gacha_screen(screen, save_data, gacha_results)
            pygame.display.flip()
            continue

        # ---- 结算 ----
        if game_state == GameState.SETTLEMENT:
            draw_background(screen, screen_shake.offset, run.bg_offset)
            if settlement_rewards:
                settlement_buttons = meta_systems.draw_settlement_screen(screen, settlement_rewards, True)
            else:
                settlement_buttons = meta_systems.draw_settlement_screen(screen, {'gold': 0, 'diamond': 0, 'materials': {}, 'equipment': []}, False)
            pygame.display.flip()
            continue

        # ---- 背包/装备 ----
        if game_state == GameState.INVENTORY:
            draw_background(screen, screen_shake.offset, run.bg_offset)
            for g in exp_gems:
                g.draw(screen, screen_shake.offset)
            for md in material_drops:
                md.draw(screen, screen_shake.offset)
            for e in enemies:
                e.draw(screen, screen_shake.offset)
            if run.character:
                run.character.x = WIDTH // 2
                run.character.y = HEIGHT // 2
                run.character.draw(screen, screen_shake.offset)
            draw_hud(screen)
            inventory_buttons = draw_inventory(screen)
            pygame.display.flip()
            continue

        # ---- 暂停 ----
        if game_state == GameState.PAUSED:
            draw_background(screen, screen_shake.offset, run.bg_offset)
            # 静态实体绘制
            for g in exp_gems:
                g.draw(screen, screen_shake.offset)
            for e in enemies:
                e.draw(screen, screen_shake.offset)
            for b in bosses:
                b.draw(screen, screen_shake.offset)
            if run.character:
                run.character.x = WIDTH // 2
                run.character.y = HEIGHT // 2
                run.character.draw(screen, screen_shake.offset)
            draw_hud(screen)
            pause_buttons = draw_pause_screen(screen)
            pygame.display.flip()
            continue

        # ---- 升级选择 ----
        if game_state == GameState.UPGRADE:
            draw_background(screen, screen_shake.offset, run.bg_offset)
            for g in exp_gems:
                g.draw(screen, screen_shake.offset)
            for e in enemies:
                e.draw(screen, screen_shake.offset)
            if run.character:
                run.character.x = WIDTH // 2
                run.character.y = HEIGHT // 2
                run.character.draw(screen, screen_shake.offset)
            draw_hud(screen)
            upgrade_cards = draw_upgrade_screen(screen)
            pygame.display.flip()
            continue

        # ---- Boss警告 ----
        if game_state == GameState.BOSS_WARNING:
            boss_warning_timer -= dt
            draw_background(screen, screen_shake.offset, run.bg_offset)
            for g in exp_gems:
                g.draw(screen, screen_shake.offset)
            for e in enemies:
                e.draw(screen, screen_shake.offset)
            if run.character:
                run.character.x = WIDTH // 2
                run.character.y = HEIGHT // 2
                run.character.draw(screen, screen_shake.offset)
            draw_hud(screen)
            # 警告文字
            warn_a = max(0, min(255, int(255 * abs(math.sin(boss_warning_timer * 4)))))
            wt = _render_outlined(font_lg, i18n.t("!! BOSS来了 !!"), RED)
            wt.set_alpha(warn_a)
            screen.blit(wt, (WIDTH//2 - wt.get_width()//2, HEIGHT//2 - 40))
            screen_shake.trigger(3, 0.1)
            screen_shake.update(dt)
            if boss_warning_timer <= 0:
                # 生成Boss
                run.boss_spawned_count += 1
                boss_level = run.boss_spawned_count
                new_boss = boss_module.create_boss(WIDTH // 2, -80, boss_level)
                bosses.append(new_boss)
                run.boss_active = True
                game_state = GameState.PLAYING
                play_sfx('boss_roar')
            pygame.display.flip()
            continue

        # ---- 游戏结束 ----
        if game_state == GameState.GAME_OVER:
            draw_background(screen, [0,0], run.bg_offset)
            result = draw_gameover_screen(screen)
            over_buttons = result[0]
            # 显示结算奖励
            if settlement_rewards:
                ry = 470
                info_items = [
                    (i18n.t("金币: +{gold}", gold=settlement_rewards['gold']), GOLD),
                    (i18n.t("钻石: +{diamond}", diamond=settlement_rewards['diamond']), CYAN),
                ]
                for t, c in info_items:
                    rt = _render_outlined(font_xs, t, c)
                    screen.blit(rt, (WIDTH//2 - rt.get_width()//2, ry))
                    ry += 22
            pygame.display.flip()
            continue

        # ---- 胜利 ----
        if game_state == GameState.VICTORY:
            draw_background(screen, [0,0], run.bg_offset)
            result = draw_victory_screen(screen)
            victory_buttons = result[0]
            # 显示结算奖励
            if settlement_rewards:
                ry = 470
                info_items = [
                    (i18n.t("金币: +{gold}", gold=settlement_rewards['gold']), GOLD),
                    (i18n.t("钻石: +{diamond}", diamond=settlement_rewards['diamond']), CYAN),
                ]
                for t, c in info_items:
                    rt = _render_outlined(font_xs, t, c)
                    screen.blit(rt, (WIDTH//2 - rt.get_width()//2, ry))
                    ry += 22
            pygame.display.flip()
            continue

        # ============================================
        #  PLAYING 状态 - 核心游戏逻辑
        # ============================================
        run.game_time += dt
        screen_shake.update(dt)
        sh = screen_shake.offset

        # ---- 玩家移动 (世界滚动) ----
        keys = pygame.key.get_pressed()
        mx_move, my_move = 0, 0
        spd = run.move_speed
        if keys[pygame.K_w] or keys[pygame.K_UP]:    my_move = spd
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:   my_move = -spd
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:   mx_move = spd
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:  mx_move = -spd
        if mx_move and my_move:
            mx_move *= 0.707; my_move *= 0.707
        run.bg_offset[0] += mx_move * dt
        run.bg_offset[1] += my_move * dt

        # 移动所有实体 (世界滚动)
        for e in enemies:
            e.x += mx_move * dt; e.y += my_move * dt
        for b in bosses:
            b.x += mx_move * dt; b.y += my_move * dt
            for bb in b.boss_bullets:
                bb[0] += mx_move * dt; bb[1] += my_move * dt
        for g in exp_gems:
            g.x += mx_move * dt; g.y += my_move * dt
        for eb in enemy_bullets:
            eb['x'] += mx_move * dt; eb['y'] += my_move * dt
        # 武器投射物/效果也随世界滚动
        for w in run.weapons:
            for proj in w.projectiles:
                proj['x'] += mx_move * dt; proj['y'] += my_move * dt
            if isinstance(w, LightningCircle):
                for c in w._circles:
                    c['x'] += mx_move * dt; c['y'] += my_move * dt
            elif isinstance(w, EarthSpikes):
                for s in w._spikes:
                    s['x'] += mx_move * dt; s['y'] += my_move * dt
        # 材料掉落也随世界滚动
        for md in material_drops:
            md.x += mx_move * dt; md.y += my_move * dt
        # 粒子也随世界滚动
        for p in particles:
            p.x += mx_move * dt; p.y += my_move * dt

        # ---- 无敌计时 (已移除) ----

        # ---- 材料不足提示计时 ----
        if run.mat_shortage_timer > 0:
            run.mat_shortage_timer -= dt

        # ---- 回血 ----
        if run.regen > 0:
            run.health = min(run.max_health, run.health + run.regen * dt)

        # ---- 武器自动攻击 ----
        px, py = WIDTH // 2, HEIGHT // 2
        for w in run.weapons:
            w.update(dt, px, py, enemies, run.cdr, run.dmg_bonus)
            hits = w.check_hits(enemies, run.dmg_bonus)
            for e, dmg, hx, hy, proj in hits:
                # 暴击
                is_crit = random.random() < run.crit_rate
                final_dmg = dmg * (run.crit_damage if is_crit else 1.0) * combo.multiplier
                e.health -= final_dmg
                e.flash_timer = 0.08
                run.total_damage += final_dmg
                # 击退
                dist = math.hypot(e.x - px, e.y - py)
                if dist > 0:
                    kb = 50
                    e.x += (e.x - px) / dist * kb * dt * 60
                    e.y += (e.y - py) / dist * kb * dt * 60
                # 生命偷取
                if run.lifesteal > 0:
                    run.health = min(run.max_health, run.health + final_dmg * run.lifesteal)
                # 粒子
                ptype = 'ice' if isinstance(w, IceNova) else ('fire' if isinstance(w, Fireball) else 'explosion')
                create_particles(hx, hy, 4 if not is_crit else 8, ptype)
                if is_crit:
                    create_particles(hx, hy, 5, 'levelup')
                play_sfx('hit')

        # ---- 敌人更新 ----
        new_enemies = []
        alive_enemies = []
        for e in enemies:
            e.update(dt, px, py, run.game_time)
            # 远程敌人射击
            bullet = e.get_ranged_bullet(px, py, dt)
            if bullet:
                enemy_bullets.append(bullet)
            if e.alive:
                alive_enemies.append(e)
                # 接触伤害
                dist = math.hypot(e.x - px, e.y - py)
                if dist < e.size + 20:
                    if run.take_damage(e.damage * dt * 2):
                        create_particles(px, py, 3, 'blood')
            else:
                # 死亡处理
                run.kills += 1
                combo.add_kill(e.x, e.y)
                # 图鉴解锁敌人
                eidx = getattr(e, 'etype_idx', 0)
                if eidx not in save_data.get('codex_enemies', []):
                    save_data['codex_enemies'].append(eidx)
                # 爆炸特殊
                if e.special == 'explode':
                    create_particles(e.x, e.y, 15, 'fire')
                    screen_shake.trigger(6, 0.15)
                    # 爆炸范围伤害
                    dist_p = math.hypot(e.x - px, e.y - py)
                    if dist_p < 80:
                        run.take_damage(e.explosion_dmg)
                else:
                    create_particles(e.x, e.y, 6, 'blood')
                # 掉落经验
                etype = 'elite' if e.is_elite else ('enhanced' if e.max_health > 40 else 'normal')
                spawn_exp_gem(e.x, e.y, etype)
                # 掉落材料
                spawn_materials(e.x, e.y, etype)
                # 掉落装备
                eq_drop = roll_equipment_drop(etype)
                if eq_drop:
                    run.try_auto_equip(eq_drop)
                # 角色被动: 击杀效果
                if run.character:
                    run.character.health = run.health  # 同步给角色
                    run.character.max_health = run.max_health
                    run.character._on_kill()
                    run.health = run.character.health  # 回读
                # 子代
                new_enemies.extend(e.children)
                # 击杀回血被动
                if run.kill_heal_counter > 0:
                    run.kill_heal_counter -= 1
                    if run.kill_heal_counter <= 0:
                        run.kill_heal_counter = 10
                        run.health = min(run.max_health, run.health + 5)
        enemies = alive_enemies + new_enemies

        # ---- 敌人子弹 ----
        alive_eb = []
        for eb in enemy_bullets:
            eb['x'] += eb['vx'] * dt
            eb['y'] += eb['vy'] * dt
            eb['life'] -= dt
            if eb['life'] > 0:
                dist = math.hypot(eb['x'] - px, eb['y'] - py)
                if dist < 20:
                    run.take_damage(eb['damage'])
                    create_particles(px, py, 5, 'blood')
                    continue
                alive_eb.append(eb)
        enemy_bullets = alive_eb

        # ---- Boss更新 ----
        alive_bosses = []
        for b in bosses:
            b.update(dt, run.game_time)
            if b.alive:
                alive_bosses.append(b)
                # Boss子弹伤害
                for bb in b.boss_bullets:
                    d = math.hypot(bb[0] - px, bb[1] - py)
                    if d < 15:
                        run.take_damage(b.damage * 0.3)
                        bb[4] = 0  # 命中后消失
            else:
                # Boss死亡
                create_particles(b.x, b.y, 80, 'boss_death')
                screen_shake.trigger(20, 0.5)
                spawn_exp_gem(b.x, b.y, 'boss')
                spawn_materials(b.x, b.y, 'boss')
                eq_drop = roll_equipment_drop('boss')
                if eq_drop:
                    run.try_auto_equip(eq_drop)
                run.boss_active = False
                bosses_killed_this_run += 1
                save_data['total_boss_kills'] = save_data.get('total_boss_kills', 0) + 1
                # 图鉴解锁Boss (通过boss_type属性)
                btype = getattr(b, 'boss_type', -1)
                if btype >= 0 and btype not in save_data.get('codex_bosses', []):
                    save_data['codex_bosses'].append(btype)
        bosses = alive_bosses

        # ---- 武器投射物对Boss的伤害 ----
        for w in run.weapons:
            for proj in w.projectiles:
                if proj.get('hit') or proj['life'] <= 0: continue
                for b in bosses:
                    if not b.alive: continue
                    d = math.hypot(b.x - proj['x'], b.y - proj['y'])
                    r = proj.get('radius', 8)
                    if d < b.size + r:
                        dmg = proj.get('damage', 20)
                        is_crit = random.random() < run.crit_rate
                        final_dmg = dmg * (run.crit_damage if is_crit else 1.0)
                        b.health -= final_dmg
                        b.flash_timer = 0.08
                        create_particles(proj['x'], proj['y'], 5, 'explosion')
                        screen_shake.trigger(3, 0.05)
                        if proj.get('pierce', 0) <= 0:
                            proj['hit'] = True
                            proj['life'] = 0
                        else:
                            proj['pierce'] -= 1

        # ---- 经验宝石 ----
        alive_gems = []
        for g in exp_gems:
            picked = g.update(dt, px, py, run.pickup_range)
            if picked:
                leveled = run.add_exp(g.value)
                play_sfx('exp')
                create_particles(g.x, g.y, 3, 'exp_pickup')
                if leveled:
                    run.do_level_up()
                    extra = sum(1 for p in run.passives if p[2].get('extra_choice'))
                    bonuses = get_permanent_bonuses()
                    choices = 3 + extra + bonuses.get('extra_choices', 0)
                    run.upgrade_options = generate_upgrade_options(
                        run.weapons, run.passives, min(choices, 5))
                    if run.upgrade_options:
                        game_state = GameState.UPGRADE
                        play_sfx('levelup')
                        create_particles(px, py, 40, 'levelup')
            elif g.life > 0:
                alive_gems.append(g)
        exp_gems = alive_gems

        # ---- 材料掉落拾取 ----
        alive_mats = []
        for md in material_drops:
            picked = md.update(dt, px, py, run.pickup_range * 0.8)
            if picked:
                run.materials[md.mat_type] += 1
                create_particles(md.x, md.y, 3, 'levelup')
                play_sfx('exp')
                # 如果之前缺材料升级失败，现在可能够了
                if run.level_up_pending and run.can_level_up():
                    run.do_level_up()
                    extra = sum(1 for p in run.passives if p[2].get('extra_choice'))
                    bonuses = get_permanent_bonuses()
                    choices = 3 + extra + bonuses.get('extra_choices', 0)
                    run.upgrade_options = generate_upgrade_options(
                        run.weapons, run.passives, min(choices, 5))
                    if run.upgrade_options:
                        game_state = GameState.UPGRADE
                        play_sfx('levelup')
                        create_particles(px, py, 40, 'levelup')
            elif md.life > 0:
                alive_mats.append(md)
        material_drops = alive_mats

        # ---- 连击 ----
        combo.update(dt)

        # ---- 粒子 ----
        for p in particles:
            p.update(dt)
        particles = [p for p in particles if p.life > 0]

        # ---- 角色动画更新 ----
        if run.character:
            run.character.x = px; run.character.y = py
            run.character.update(dt)
            run.character.health = run.health  # 同步血量

        # ---- 敌人生成 ----
        spawn_timer -= dt
        if spawn_timer <= 0 and not run.boss_active:
            # 生成频率随时间增加
            rate = min(0.5, 0.8 + run.game_time * 0.001)
            spawn_timer = max(0.05, 1.0 / (1 + run.game_time * 0.02))

            # 根据时间决定敌人类型
            t = run.game_time / 60  # 分钟
            available = [i for i, info in enumerate(ENEMY_TYPES) if info[6] <= t]
            if not available:
                available = [0]
            # 更高级的敌人更少
            weights = [max(1, 10 - i * 2) for i in available]
            etype = random.choices(available, weights=weights)[0]

            # 难度倍率
            diff_mult = 1.0 + run.game_time / 300  # 每5分钟+1倍

            # 生成位置 (屏幕外)
            side = random.randint(0, 3)
            if side == 0:   ex, ey = random.uniform(0, WIDTH), -30
            elif side == 1: ex, ey = random.uniform(0, WIDTH), HEIGHT + 30
            elif side == 2: ex, ey = -30, random.uniform(0, HEIGHT)
            else:           ex, ey = WIDTH + 30, random.uniform(0, HEIGHT)

            new_enemy = Enemy(ex, ey, etype, diff_mult)
            # 精英几率
            if run.game_time > 900 and random.random() < 0.15:  # 15分钟后
                new_enemy.is_elite = True
                new_enemy.health *= 3
                new_enemy.max_health = new_enemy.health
                new_enemy.damage *= 1.5
                new_enemy.size *= 1.3
            enemies.append(new_enemy)

        # ---- Boss生成检查 (每10分钟) ----
        boss_minute = int(run.game_time / 60)
        if boss_minute >= 10 and not run.boss_active and run.boss_spawned_count < boss_minute // 10:
            boss_warning_timer = 3.0
            game_state = GameState.BOSS_WARNING
            play_sfx('boss_roar')

        # ---- 30分钟胜利 & 最终Boss ----
        if run.game_time >= 1800 and not run.boss_active and run.boss_spawned_count >= 3:
            # 胜利! 计算结算奖励
            souls = int(run.kills * 0.1 + 30 * 5 + run.boss_spawned_count * 30 + 100)
            save_data['soul_shards'] += souls
            save_data['best_kills'] = max(save_data['best_kills'], run.kills)
            save_data['best_time'] = max(save_data['best_time'], int(run.game_time))
            # 局外结算
            settlement_rewards = meta_systems.calculate_settlement(run, current_dungeon, bosses_killed_this_run)
            meta_systems.apply_settlement(save_data, settlement_rewards, EQUIPMENT_DB)
            meta_systems.check_char_unlocks(save_data)
            if current_dungeon:
                did = current_dungeon['id']
                save_data['dungeon_clears'][did] = save_data.get('dungeon_clears', {}).get(did, 0) + 1
            save_game(save_data)
            game_state = GameState.SETTLEMENT

        # ---- 死亡检查 ----
        if not run.alive:
            souls = int(run.kills * 0.1 + run.game_time / 60 * 5 + run.boss_spawned_count * 30)
            save_data['soul_shards'] += souls
            save_data['best_kills'] = max(save_data['best_kills'], run.kills)
            save_data['best_time'] = max(save_data['best_time'], int(run.game_time))
            # 局外结算
            settlement_rewards = meta_systems.calculate_settlement(run, current_dungeon, bosses_killed_this_run)
            meta_systems.apply_settlement(save_data, settlement_rewards, EQUIPMENT_DB)
            meta_systems.check_char_unlocks(save_data)
            save_game(save_data)
            game_state = GameState.GAME_OVER
            create_particles(px, py, 50, 'boss_death')
            screen_shake.trigger(15, 0.4)

        # ==== 绘制 ====
        draw_background(screen, sh, run.bg_offset)

        # 经验宝石
        for g in exp_gems:
            g.draw(screen, sh)

        # 材料掉落
        for md in material_drops:
            md.draw(screen, sh)

        # 敌人子弹
        for eb in enemy_bullets:
            ebx = int(eb['x'] + sh[0]); eby = int(eb['y'] + sh[1])
            pygame.draw.circle(screen, RED, (ebx, eby), 4)
            pygame.draw.circle(screen, (255, 150, 150), (ebx, eby), 2)

        # 敌人
        for e in enemies:
            e.draw(screen, sh)

        # 武器效果
        for w in run.weapons:
            w.draw_projectiles(screen, sh)

        # 玩家角色
        if run.character:
            run.character.x = px; run.character.y = py
            run.character.draw(screen, sh)

        # Boss
        for b in bosses:
            b.draw(screen, sh)

        # 粒子 (最上层)
        for p in particles:
            p.draw(screen, sh)

        # HUD
        draw_hud(screen)
        combo.draw(screen, sh)

        # FPS
        fps = clock.get_fps()
        ft = _render_outlined(font_xs, f"FPS:{fps:.0f} E:{len(enemies)}", (60, 60, 80))
        screen.blit(ft, (WIDTH - ft.get_width() - 5, HEIGHT - 18))

        pygame.display.flip()

    # 退出前保存
    save_game(save_data)
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
