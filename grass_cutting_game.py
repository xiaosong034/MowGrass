"""
割草游戏 - Grass Cutting Game (Python版)
功能：AI小伙伴、音效、酷炫特效、连击系统、Boss怪物
操作：WASD移动 | 鼠标点击射击 | 空格激活毒气 | ESC暂停
"""

import pygame
import math
import random
import sys
import os
import i18n

# ============================================================
#  初始化
# ============================================================
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("割草游戏 - Grass Cutting Game 🌿⚔️")
clock = pygame.time.Clock()

# ============================================================
#  音效生成器 (不需要外部音频文件!)
# ============================================================
import array

def generate_sound(frequency=440, duration=0.1, volume=0.3, wave_type='square'):
    """动态生成音效"""
    sample_rate = 22050
    n_samples = int(sample_rate * duration)
    buf = array.array('h', [0] * n_samples)
    max_amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        fade = 1.0 - (i / n_samples)  # 淡出
        if wave_type == 'square':
            val = max_amp if math.sin(2 * math.pi * frequency * t) > 0 else -max_amp
        elif wave_type == 'sine':
            val = int(max_amp * math.sin(2 * math.pi * frequency * t))
        elif wave_type == 'noise':
            val = random.randint(-max_amp, max_amp)
        elif wave_type == 'sawtooth':
            val = int(max_amp * (2 * (frequency * t % 1) - 1))
        else:
            val = int(max_amp * math.sin(2 * math.pi * frequency * t))
        buf[i] = int(val * fade)
    sound = pygame.mixer.Sound(buffer=buf)
    return sound

def generate_explosion_sound():
    """爆炸音效"""
    sample_rate = 22050
    duration = 0.3
    n_samples = int(sample_rate * duration)
    buf = array.array('h', [0] * n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        fade = 1.0 - (i / n_samples)
        freq = 150 * (1.0 - t * 2)
        val = int(16000 * fade * (
            math.sin(2 * math.pi * freq * t) * 0.5 +
            random.uniform(-1, 1) * 0.5
        ))
        buf[i] = max(-32767, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)

def generate_powerup_sound():
    """升级音效 - 上升音调"""
    sample_rate = 22050
    duration = 0.4
    n_samples = int(sample_rate * duration)
    buf = array.array('h', [0] * n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        fade = 1.0 - (t / duration) * 0.3
        freq = 400 + t * 1200  # 音调上升
        val = int(12000 * fade * math.sin(2 * math.pi * freq * t))
        buf[i] = max(-32767, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)

def generate_combo_sound(combo_level):
    """连击音效 - 越高连击音越高"""
    freq = 500 + combo_level * 100
    return generate_sound(min(freq, 1500), 0.08, 0.25, 'sine')

def generate_boss_roar():
    """Boss出现咆哮"""
    sample_rate = 22050
    duration = 0.6
    n_samples = int(sample_rate * duration)
    buf = array.array('h', [0] * n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        fade = 1.0 - (i / n_samples) * 0.5
        freq = 80 + math.sin(t * 20) * 30
        val = int(20000 * fade * (
            math.sin(2 * math.pi * freq * t) * 0.6 +
            math.sin(2 * math.pi * freq * 2 * t) * 0.3 +
            random.uniform(-1, 1) * 0.1
        ))
        buf[i] = max(-32767, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)

def generate_bgm_loop():
    """生成简单的背景音乐循环"""
    sample_rate = 22050
    duration = 4.0
    n_samples = int(sample_rate * duration)
    buf = array.array('h', [0] * n_samples)

    # 简单的旋律音符序列 (频率, 开始时间, 持续时间)
    melody_notes = [
        (262, 0.0, 0.4), (330, 0.5, 0.4), (392, 1.0, 0.4), (330, 1.5, 0.4),
        (294, 2.0, 0.4), (349, 2.5, 0.4), (440, 3.0, 0.4), (392, 3.5, 0.4),
    ]
    # 低音伴奏
    bass_notes = [
        (131, 0.0, 0.9), (165, 1.0, 0.9),
        (147, 2.0, 0.9), (175, 3.0, 0.9),
    ]

    for i in range(n_samples):
        t = i / sample_rate
        val = 0.0
        # 旋律
        for freq, start, dur in melody_notes:
            if start <= t < start + dur:
                local_t = t - start
                env = math.sin(math.pi * local_t / dur)  # 包络
                val += 4000 * env * math.sin(2 * math.pi * freq * t)
        # 低音
        for freq, start, dur in bass_notes:
            if start <= t < start + dur:
                local_t = t - start
                env = math.sin(math.pi * local_t / dur) * 0.5
                val += 3000 * env * math.sin(2 * math.pi * freq * t)
        # 节拍鼓点
        beat_pos = t % 0.5
        if beat_pos < 0.05:
            val += 5000 * (1 - beat_pos / 0.05) * random.uniform(-1, 1) * 0.3

        buf[i] = max(-32767, min(32767, int(val)))
    return pygame.mixer.Sound(buffer=buf)

# 预生成音效
try:
    SFX = {
        'shoot': generate_sound(800, 0.06, 0.2, 'square'),
        'hit': generate_sound(200, 0.08, 0.25, 'noise'),
        'explosion': generate_explosion_sound(),
        'powerup': generate_powerup_sound(),
        'heal': generate_sound(600, 0.15, 0.2, 'sine'),
        'boss_roar': generate_boss_roar(),
        'sword': generate_sound(1200, 0.04, 0.15, 'sawtooth'),
        'poison': generate_sound(150, 0.2, 0.15, 'sine'),
        'combo1': generate_combo_sound(1),
        'combo2': generate_combo_sound(3),
        'combo3': generate_combo_sound(5),
        'combo4': generate_combo_sound(8),
        'gameover': generate_sound(200, 0.5, 0.3, 'sawtooth'),
    }
    bgm_sound = generate_bgm_loop()
    SOUND_ENABLED = True
except Exception:
    SFX = {}
    bgm_sound = None
    SOUND_ENABLED = False

def play_sfx(name):
    if SOUND_ENABLED and name in SFX:
        SFX[name].play()

def play_combo_sfx(combo):
    if not SOUND_ENABLED:
        return
    if combo >= 30:
        SFX.get('combo4', SFX.get('combo1')).play()
    elif combo >= 15:
        SFX.get('combo3', SFX.get('combo1')).play()
    elif combo >= 5:
        SFX.get('combo2', SFX.get('combo1')).play()
    else:
        SFX.get('combo1').play()

# ============================================================
#  颜色 & 字体
# ============================================================
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 68, 68)
GREEN = (0, 255, 0)
CYAN = (78, 205, 196)
YELLOW = (255, 255, 0)
ORANGE = (255, 170, 0)
PINK = (255, 100, 200)
PURPLE = (170, 68, 255)
BLUE = (68, 68, 255)
DARK_BG = (0, 17, 34)
GRID_COLOR = (0, 51, 102)

# 尝试加载支持多语言的字体
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

font_lg = get_font(60)
font_md = get_font(32)
font_sm = get_font(20)
font_xs = get_font(16)
font_title = get_font(80)
font_combo = get_font(48)

# ============================================================
#  粒子系统
# ============================================================
class Particle:
    __slots__ = ['x', 'y', 'vx', 'vy', 'life', 'max_life', 'color', 'size', 'ptype', 'gravity']

    def __init__(self, x, y, vx, vy, life, color, size, ptype='normal', gravity=False):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.ptype = ptype
        self.gravity = gravity

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        if self.gravity:
            self.vy += 300 * dt
        self.vx *= 0.97
        self.vy *= 0.97

    def draw(self, surface, cam_shake=(0, 0)):
        if self.life <= 0:
            return
        alpha = max(0, self.life / self.max_life)
        r, g, b = self.color
        s = max(1, int(self.size * alpha))
        color = (max(0, min(255, int(r))), max(0, min(255, int(g))), max(0, min(255, int(b))))
        sx = int(self.x + cam_shake[0])
        sy = int(self.y + cam_shake[1])
        if self.ptype == 'spark':
            end_x = sx + int(self.vx * 0.02)
            end_y = sy + int(self.vy * 0.02)
            pygame.draw.line(surface, color, (sx, sy), (end_x, end_y), max(1, s))
        else:
            surf = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*color, max(0, min(255, int(255 * alpha)))), (s, s), s)
            surface.blit(surf, (sx - s, sy - s))

particles = []

PARTICLE_CONFIGS = {
    'explosion': {
        'colors': [(255, 68, 68), (255, 102, 102), (255, 170, 0), (255, 221, 0)],
        'speed': (100, 350), 'life': (0.3, 0.8), 'size': (2, 6), 'ptype': 'normal', 'gravity': True
    },
    'blood': {
        'colors': [(204, 0, 0), (170, 0, 0), (136, 0, 0), (187, 17, 17)],
        'speed': (50, 200), 'life': (0.5, 1.2), 'size': (1, 4), 'ptype': 'normal', 'gravity': True
    },
    'poison': {
        'colors': [(0, 255, 0), (68, 255, 68), (136, 255, 136), (34, 170, 34)],
        'speed': (20, 80), 'life': (0.8, 1.5), 'size': (2, 6), 'ptype': 'normal', 'gravity': False
    },
    'sword_hit': {
        'colors': [(0, 255, 255), (68, 255, 255), (136, 255, 255), (170, 255, 255)],
        'speed': (80, 280), 'life': (0.2, 0.6), 'size': (1, 3), 'ptype': 'spark', 'gravity': False
    },
    'upgrade': {
        'colors': [(255, 221, 0), (255, 170, 0), (255, 136, 0), (255, 255, 68)],
        'speed': (50, 180), 'life': (1.0, 2.0), 'size': (3, 8), 'ptype': 'normal', 'gravity': False
    },
    'heal': {
        'colors': [(0, 255, 136), (68, 255, 170), (136, 255, 204), (170, 255, 221)],
        'speed': (30, 100), 'life': (0.8, 1.5), 'size': (2, 5), 'ptype': 'normal', 'gravity': False
    },
    'muzzle': {
        'colors': [(255, 255, 0), (255, 170, 0), (255, 136, 0), (255, 221, 68)],
        'speed': (150, 450), 'life': (0.08, 0.25), 'size': (1, 3), 'ptype': 'spark', 'gravity': False
    },
    'boss_death': {
        'colors': [(255, 0, 255), (255, 100, 255), (255, 200, 0), (255, 50, 50), (0, 255, 255)],
        'speed': (100, 500), 'life': (0.5, 2.0), 'size': (3, 10), 'ptype': 'normal', 'gravity': True
    },
    'combo': {
        'colors': [(255, 255, 0), (255, 200, 0), (255, 150, 50)],
        'speed': (60, 150), 'life': (0.5, 1.0), 'size': (2, 5), 'ptype': 'normal', 'gravity': False
    },
    'ai_trail': {
        'colors': [(100, 200, 255), (50, 150, 255), (150, 220, 255)],
        'speed': (10, 40), 'life': (0.3, 0.7), 'size': (2, 4), 'ptype': 'normal', 'gravity': False
    },
}

def create_particles(x, y, count, ptype_name):
    cfg = PARTICLE_CONFIGS.get(ptype_name)
    if not cfg:
        return
    for _ in range(count):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(*cfg['speed'])
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        life = random.uniform(*cfg['life'])
        color = random.choice(cfg['colors'])
        size = random.uniform(*cfg['size'])
        particles.append(Particle(x, y, vx, vy, life, color, size, cfg['ptype'], cfg['gravity']))

# ============================================================
#  屏幕震动
# ============================================================
class ScreenShake:
    def __init__(self):
        self.intensity = 0
        self.duration = 0
        self.timer = 0
        self.offset = (0, 0)

    def trigger(self, intensity, duration):
        self.intensity = max(self.intensity, intensity)
        self.duration = max(self.duration, duration)
        self.timer = 0

    def update(self, dt):
        if self.duration > 0:
            self.timer += dt
            if self.timer >= self.duration:
                self.duration = 0
                self.intensity = 0
                self.offset = (0, 0)
            else:
                fade = 1.0 - self.timer / self.duration
                self.offset = (
                    random.uniform(-self.intensity, self.intensity) * fade,
                    random.uniform(-self.intensity, self.intensity) * fade
                )
        else:
            self.offset = (0, 0)

screen_shake = ScreenShake()

# ============================================================
#  连击系统
# ============================================================
class ComboSystem:
    def __init__(self):
        self.count = 0
        self.timer = 0
        self.max_time = 2.5  # 连击持续秒数
        self.best_combo = 0
        self.display_texts = []  # (text, x, y, timer, color)
        self.multiplier = 1.0

    def add_kill(self, x, y):
        self.count += 1
        self.timer = self.max_time
        if self.count > self.best_combo:
            self.best_combo = self.count

        # 连击倍数
        if self.count >= 50:
            self.multiplier = 5.0
        elif self.count >= 30:
            self.multiplier = 4.0
        elif self.count >= 15:
            self.multiplier = 3.0
        elif self.count >= 5:
            self.multiplier = 2.0
        else:
            self.multiplier = 1.0

        # 显示连击文字
        if self.count >= 3:
            if self.count >= 50:
                text = f"★★★ 超神连击 x{self.count}! ★★★"
                color = (255, 50, 255)
            elif self.count >= 30:
                text = f"◆◆ 无双连击 x{self.count}! ◆◆"
                color = (255, 200, 0)
            elif self.count >= 15:
                text = f"▶▶ 暴走连击 x{self.count}!"
                color = (255, 100, 0)
            elif self.count >= 5:
                text = f"☆ 连击 x{self.count}!"
                color = (0, 255, 200)
            else:
                text = f"连击 x{self.count}"
                color = WHITE
            self.display_texts.append([text, x, y, 1.5, color])
            play_combo_sfx(self.count)

    def update(self, dt):
        if self.timer > 0:
            self.timer -= dt
            if self.timer <= 0:
                self.count = 0
                self.multiplier = 1.0

        # 更新显示文字
        for t in self.display_texts:
            t[2] -= 60 * dt  # 上飘
            t[3] -= dt
        self.display_texts = [t for t in self.display_texts if t[3] > 0]

    def draw(self, surface, shake):
        # 连击条
        if self.count >= 3:
            bar_w = 300
            bar_h = 8
            bx = WIDTH // 2 - bar_w // 2 + int(shake[0])
            by = 75 + int(shake[1])
            ratio = self.timer / self.max_time

            # 背景
            pygame.draw.rect(surface, (50, 50, 50), (bx, by, bar_w, bar_h), border_radius=4)
            # 填充
            fill_color = (255, int(200 * ratio), 0)
            pygame.draw.rect(surface, fill_color, (bx, by, int(bar_w * ratio), bar_h), border_radius=4)

            # 连击数字显示 (屏幕顶部中央)
            combo_text = f"COMBO x{self.count}  (得分 x{self.multiplier:.0f})"
            ts = font_sm.render(combo_text, True, (255, 220, 50))
            surface.blit(ts, (WIDTH // 2 - ts.get_width() // 2 + int(shake[0]), 48 + int(shake[1])))

        # 飘字
        for text, x, y, timer, color in self.display_texts:
            alpha = max(0, min(255, int(255 * (timer / 1.5))))
            ts = font_md.render(text, True, color)
            ts.set_alpha(alpha)
            surface.blit(ts, (int(x - ts.get_width() // 2 + shake[0]),
                              int(y + shake[1])))

combo_system = ComboSystem()

# ============================================================
#  玩家
# ============================================================
class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.health = 100
        self.max_health = 100
        self.level = 1
        self.exp = 0
        self.exp_to_next = 10
        self.kills = 0
        self.weapons = {}
        self.trail = []  # (x, y, life)
        self.invincible_timer = 0  # 无敌时间

    def take_damage(self, amount):
        if self.invincible_timer > 0:
            return
        self.health -= amount
        self.invincible_timer = 0.15  # 短暂无敌

    def update(self, dt):
        if self.invincible_timer > 0:
            self.invincible_timer -= dt
        self.trail.append([self.x, self.y, 0.2])
        self.trail = [t for t in self.trail if t[2] > 0]
        for t in self.trail:
            t[2] -= dt * 3

    def draw(self, surface, shake):
        sx = int(self.x + shake[0])
        sy = int(self.y + shake[1])

        # 残影
        for tx, ty, tl in self.trail:
            alpha = max(0, min(255, int(tl * 200)))
            s = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(s, (*CYAN, alpha), (5, 5), 5)
            surface.blit(s, (int(tx - 5 + shake[0]), int(ty - 5 + shake[1])))

        # 无敌闪烁
        if self.invincible_timer > 0 and int(self.invincible_timer * 20) % 2 == 0:
            return

        # 身体
        pygame.draw.circle(surface, CYAN, (sx, sy), 22)
        pygame.draw.circle(surface, WHITE, (sx, sy), 22, 3)
        pygame.draw.circle(surface, WHITE, (sx, sy), 8)

player = Player()

# ============================================================
#  AI小伙伴
# ============================================================
class AICompanion:
    def __init__(self):
        self.x = player.x + 50
        self.y = player.y + 50
        self.target = None
        self.shoot_timer = 0
        self.shoot_interval = 0.6
        self.orbit_angle = 0
        self.orbit_radius = 80
        self.active = False
        self.emote_timer = 0
        self.emote_text = ""
        self.trail = []
        self.level = 1
        self.kills = 0

    def activate(self):
        self.active = True
        self.emote("来啦！", 2.0)
        play_sfx('powerup')

    def emote(self, text, duration=1.5):
        self.emote_text = text
        self.emote_timer = duration

    def find_target(self, enemies):
        """找最近的敌人"""
        nearest = None
        nearest_dist = float('inf')
        for e in enemies:
            d = math.hypot(e.x - self.x, e.y - self.y)
            if d < nearest_dist and d < 400:
                nearest = e
                nearest_dist = d
        return nearest

    def update(self, dt, enemies, bullets_list):
        if not self.active:
            return

        # 绕玩家旋转
        self.orbit_angle += dt * 1.5
        target_x = player.x + math.cos(self.orbit_angle) * self.orbit_radius
        target_y = player.y + math.sin(self.orbit_angle) * self.orbit_radius

        # 平滑移动
        self.x += (target_x - self.x) * 5 * dt
        self.y += (target_y - self.y) * 5 * dt

        # 轨迹
        self.trail.append([self.x, self.y, 0.3])
        self.trail = [t for t in self.trail if t[2] > 0]
        for t in self.trail:
            t[2] -= dt * 2

        # 偶尔产生粒子
        if random.random() < 0.1:
            create_particles(self.x, self.y, 1, 'ai_trail')

        # 自动射击
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            target = self.find_target(enemies)
            if target:
                angle = math.atan2(target.y - self.y, target.x - self.x)
                bullet_count = min(self.level, 3)
                if bullet_count == 1:
                    bullets_list.append(Bullet(self.x, self.y, angle, 400, 20, (100, 200, 255), is_ai=True))
                else:
                    spread = math.pi / 6
                    for i in range(bullet_count):
                        offset = (i - (bullet_count - 1) / 2) * (spread / max(bullet_count - 1, 1))
                        bullets_list.append(Bullet(self.x, self.y, angle + offset, 400, 20, (100, 200, 255), is_ai=True))
                self.shoot_timer = max(0.3, self.shoot_interval - self.level * 0.05)
                play_sfx('shoot')
                create_particles(self.x, self.y, 4, 'muzzle')

        # 表情更新
        if self.emote_timer > 0:
            self.emote_timer -= dt

        # 随机说话
        if random.random() < 0.001:
            phrases = ["加油！", "冲呀~", "我来帮你！", "好多怪！", "小心！", "耶！", "哇塞~"]
            self.emote(random.choice(phrases), 1.5)

    def draw(self, surface, shake):
        if not self.active:
            return

        sx = int(self.x + shake[0])
        sy = int(self.y + shake[1])

        # 轨迹
        for tx, ty, tl in self.trail:
            alpha = max(0, min(255, int(tl * 150)))
            s = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(s, (100, 200, 255, alpha), (4, 4), 4)
            surface.blit(s, (int(tx - 4 + shake[0]), int(ty - 4 + shake[1])))

        # 身体 - 蓝色小圆 + 光环
        glow_surf = pygame.Surface((50, 50), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (100, 200, 255, 40), (25, 25), 25)
        surface.blit(glow_surf, (sx - 25, sy - 25))

        pygame.draw.circle(surface, (100, 180, 255), (sx, sy), 15)
        pygame.draw.circle(surface, WHITE, (sx, sy), 15, 2)
        pygame.draw.circle(surface, WHITE, (sx, sy), 6)

        # 眼睛 (让小伙伴看起来可爱)
        eye_offset = 5
        pygame.draw.circle(surface, BLACK, (sx - 4, sy - 3), 3)
        pygame.draw.circle(surface, BLACK, (sx + 4, sy - 3), 3)
        pygame.draw.circle(surface, WHITE, (sx - 4, sy - 4), 1)
        pygame.draw.circle(surface, WHITE, (sx + 4, sy - 4), 1)

        # "AI" 标记
        label = font_xs.render("AI", True, (200, 230, 255))
        surface.blit(label, (sx - label.get_width() // 2, sy - 30))

        # 表情气泡
        if self.emote_timer > 0:
            bubble = font_sm.render(self.emote_text, True, WHITE)
            bw = bubble.get_width() + 16
            bh = bubble.get_height() + 8
            bx = sx - bw // 2
            by = sy - 55

            bubble_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(bubble_surf, (0, 0, 0, 180), (0, 0, bw, bh), border_radius=10)
            pygame.draw.rect(bubble_surf, (100, 200, 255, 200), (0, 0, bw, bh), 2, border_radius=10)
            surface.blit(bubble_surf, (bx, by))
            surface.blit(bubble, (bx + 8, by + 4))

ai_companion = AICompanion()

# ============================================================
#  子弹
# ============================================================
class Bullet:
    def __init__(self, x, y, angle, speed=500, damage=30, color=YELLOW, is_ai=False):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 2.5
        self.damage = damage
        self.hit = False
        self.color = color
        self.is_ai = is_ai

    def update(self, dt, enemies):
        if self.hit:
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

        for enemy in enemies:
            if self.hit:
                break
            dx = enemy.x - self.x
            dy = enemy.y - self.y
            dist = math.hypot(dx, dy)
            if dist < enemy.size + 8:
                enemy.health -= self.damage
                create_particles(self.x, self.y, 12, 'explosion')
                screen_shake.trigger(4, 0.1)
                play_sfx('hit')
                self.hit = True
                self.life = 0
                # 击退
                if dist > 0:
                    enemy.x += (dx / dist) * 80
                    enemy.y += (dy / dist) * 80

    def draw(self, surface, shake):
        if self.hit:
            return
        sx = int(self.x + shake[0])
        sy = int(self.y + shake[1])
        pygame.draw.circle(surface, self.color, (sx, sy), 4)
        end_x = sx - int(self.vx * 0.03)
        end_y = sy - int(self.vy * 0.03)
        trail_color = tuple(min(255, c + 50) for c in self.color[:3])
        pygame.draw.line(surface, trail_color, (sx, sy), (end_x, end_y), 3)

bullets = []

# ============================================================
#  敌人
# ============================================================
ENEMY_COLORS = [
    (255, 68, 68),    # 1级 红
    (255, 136, 68),   # 2级 橙
    (255, 170, 68),   # 3级 黄
    (255, 68, 170),   # 4级 粉
    (170, 68, 255),   # 5级 紫
    (68, 68, 255),    # 6级 蓝
]

class Enemy:
    def __init__(self, x, y, tier=1):
        self.x = x
        self.y = y
        self.tier = tier
        self.health = tier * 25
        self.max_health = self.health
        self.speed = max(40 - tier * 3, 15)
        self.size = 12 + tier * 4
        self.color = ENEMY_COLORS[min(tier - 1, len(ENEMY_COLORS) - 1)]
        self.last_hit = 0
        self.damage = tier * 8
        self.flash_timer = 0

    def update(self, dt, game_time):
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0 and dist > self.size + 25:
            self.x += (dx / dist) * self.speed * dt
            self.y += (dy / dist) * self.speed * dt

        if self.flash_timer > 0:
            self.flash_timer -= dt

        now = pygame.time.get_ticks()

        # 毒气伤害
        if 'poison' in player.weapons:
            pw = player.weapons['poison']
            poison_range = 60 + pw['level'] * 25
            if dist < poison_range:
                if now - self.last_hit > 400:
                    damage = pw['level'] * 8
                    if pw.get('activated'):
                        damage *= 2
                    if pw.get('ultimate'):
                        damage *= 2
                    self.health -= damage
                    self.last_hit = now
                    self.flash_timer = 0.1
                    create_particles(self.x, self.y, 3, 'poison')

        # 光剑伤害
        if 'sword' in player.weapons:
            for sword in swords:
                sd = math.hypot(sword[0] - self.x, sword[1] - self.y)
                if sd < 30:
                    if now - self.last_hit > 200:
                        damage = player.weapons['sword']['level'] * 20
                        if player.weapons['sword'].get('ultimate'):
                            damage *= 2
                        self.health -= damage
                        self.last_hit = now
                        self.flash_timer = 0.1
                        create_particles(self.x, self.y, 6, 'sword_hit')
                        play_sfx('sword')

    def draw(self, surface, shake):
        sx = int(self.x + shake[0])
        sy = int(self.y + shake[1])

        color = WHITE if self.flash_timer > 0 else self.color
        pygame.draw.circle(surface, color, (sx, sy), self.size)
        pygame.draw.circle(surface, WHITE, (sx, sy), self.size, 2)

        # 血条
        if self.health < self.max_health:
            bw = self.size * 2.5
            bh = 5
            bx = sx - bw / 2
            by = sy - self.size - 12
            pygame.draw.rect(surface, (50, 50, 50), (bx, by, bw, bh))
            hp_ratio = max(0, self.health / self.max_health)
            pygame.draw.rect(surface, RED, (bx, by, bw * hp_ratio, bh))

        # 等级
        t = font_xs.render(str(self.tier), True, WHITE)
        surface.blit(t, (sx - t.get_width() // 2, sy - t.get_height() // 2))

enemies = []

# ============================================================
#  Boss系统
# ============================================================
class Boss:
    def __init__(self, x, y, boss_level=1):
        self.x = x
        self.y = y
        self.boss_level = boss_level
        self.health = 500 * boss_level
        self.max_health = self.health
        self.size = 50 + boss_level * 10
        self.speed = 30 + boss_level * 5
        self.damage = 20 * boss_level
        self.last_hit = 0
        self.flash_timer = 0
        self.phase = 0
        self.attack_timer = 0
        self.attack_interval = 3.0
        self.color_cycle = 0
        self.alive = True
        self.spawn_timer = 0
        self.warning_shown = True
        self.roar_played = False
        # Boss攻击弹幕
        self.boss_bullets = []

    def get_color(self):
        """Boss颜色循环"""
        self.color_cycle += 0.02
        r = int(128 + 127 * math.sin(self.color_cycle))
        g = int(128 + 127 * math.sin(self.color_cycle + 2.1))
        b = int(128 + 127 * math.sin(self.color_cycle + 4.2))
        return (r, g, b)

    def update(self, dt, game_time):
        if not self.alive:
            return

        if not self.roar_played:
            play_sfx('boss_roar')
            self.roar_played = True

        # 追踪玩家
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0 and dist > self.size:
            self.x += (dx / dist) * self.speed * dt
            self.y += (dy / dist) * self.speed * dt

        if self.flash_timer > 0:
            self.flash_timer -= dt

        now = pygame.time.get_ticks()

        # Boss攻击 - 弹幕
        self.attack_timer -= dt
        if self.attack_timer <= 0:
            self.attack_timer = max(1.0, self.attack_interval - self.boss_level * 0.3)
            bullet_count = 8 + self.boss_level * 4
            for i in range(bullet_count):
                angle = (2 * math.pi / bullet_count) * i + self.color_cycle
                bvx = math.cos(angle) * 150
                bvy = math.sin(angle) * 150
                self.boss_bullets.append([self.x, self.y, bvx, bvy, 3.0])
            screen_shake.trigger(6, 0.2)
            play_sfx('explosion')

        # 更新弹幕
        for b in self.boss_bullets:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            b[4] -= dt
            # 检测命中玩家
            pd = math.hypot(b[0] - player.x, b[1] - player.y)
            if pd < 25:
                player.take_damage(self.damage * 0.5 * dt * 60)
                b[4] = 0
        self.boss_bullets = [b for b in self.boss_bullets if b[4] > 0]

        # 毒气伤害
        if 'poison' in player.weapons:
            pw = player.weapons['poison']
            poison_range = 60 + pw['level'] * 25
            if dist < poison_range and now - self.last_hit > 400:
                damage = pw['level'] * 8
                if pw.get('activated'):
                    damage *= 2
                if pw.get('ultimate'):
                    damage *= 2
                self.health -= damage
                self.last_hit = now
                self.flash_timer = 0.1
                create_particles(self.x, self.y, 5, 'poison')

        # 光剑伤害
        if 'sword' in player.weapons:
            for sword in swords:
                sd = math.hypot(sword[0] - self.x, sword[1] - self.y)
                if sd < self.size + 10 and now - self.last_hit > 200:
                    damage = player.weapons['sword']['level'] * 20
                    if player.weapons['sword'].get('ultimate'):
                        damage *= 2
                    self.health -= damage
                    self.last_hit = now
                    self.flash_timer = 0.1
                    create_particles(self.x, self.y, 8, 'sword_hit')

        # 碰撞伤害
        if dist < self.size + 25:
            player.take_damage(self.damage * dt)

        if self.health <= 0:
            self.alive = False

    def draw(self, surface, shake):
        if not self.alive:
            return

        sx = int(self.x + shake[0])
        sy = int(self.y + shake[1])
        color = WHITE if self.flash_timer > 0 else self.get_color()

        # 光环
        glow_surf = pygame.Surface((self.size * 4, self.size * 4), pygame.SRCALPHA)
        r_c, g_c, b_c = int(color[0]), int(color[1]), int(color[2])
        glow_color = (r_c, g_c, b_c, 30)
        pygame.draw.circle(glow_surf, glow_color, (self.size * 2, self.size * 2), self.size * 2)
        surface.blit(glow_surf, (sx - self.size * 2, sy - self.size * 2))

        # 身体
        pygame.draw.circle(surface, color, (sx, sy), self.size)
        pygame.draw.circle(surface, WHITE, (sx, sy), self.size, 3)

        # Boss眼睛 (恐怖的红色大眼睛)
        eye_r = self.size // 4
        pygame.draw.circle(surface, RED, (sx - self.size // 3, sy - self.size // 4), eye_r)
        pygame.draw.circle(surface, RED, (sx + self.size // 3, sy - self.size // 4), eye_r)
        pygame.draw.circle(surface, BLACK, (sx - self.size // 3, sy - self.size // 4), eye_r // 2)
        pygame.draw.circle(surface, BLACK, (sx + self.size // 3, sy - self.size // 4), eye_r // 2)

        # 嘴巴 (锯齿)
        mouth_y = sy + self.size // 4
        points = []
        for i in range(8):
            mx = sx - self.size // 2 + i * (self.size // 4)
            my = mouth_y + (5 if i % 2 == 0 else -5)
            points.append((mx, my))
        if len(points) >= 2:
            pygame.draw.lines(surface, WHITE, False, points, 2)

        # 血条 (Boss血条在屏幕顶部)
        bar_w = 400
        bar_h = 20
        bar_x = WIDTH // 2 - bar_w // 2 + int(shake[0])
        bar_y = 10 + int(shake[1])
        pygame.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=5)
        hp_ratio = max(0, self.health / self.max_health)
        fill_color = (
            max(0, min(255, int(255 * (1 - hp_ratio)))),
            max(0, min(255, int(255 * hp_ratio))),
            50
        )
        pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(bar_w * hp_ratio), bar_h), border_radius=5)
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_w, bar_h), 2, border_radius=5)

        # Boss名称
        boss_name = f"BOSS Lv.{self.boss_level}"
        name_surf = font_sm.render(boss_name, True, color)
        surface.blit(name_surf, (WIDTH // 2 - name_surf.get_width() // 2 + int(shake[0]),
                                  bar_y + bar_h + 2 + int(shake[1])))

        # Boss弹幕
        for b in self.boss_bullets:
            bsx = int(b[0] + shake[0])
            bsy = int(b[1] + shake[1])
            pygame.draw.circle(surface, PINK, (bsx, bsy), 5)
            pygame.draw.circle(surface, WHITE, (bsx, bsy), 5, 1)

bosses = []
next_boss_time = 60  # 第一个Boss在60秒出现
boss_level_counter = 0

# ============================================================
#  道具
# ============================================================
class Item:
    def __init__(self, x, y, item_type):
        self.x = x
        self.y = y
        self.item_type = item_type
        self.bob_offset = random.uniform(0, math.pi * 2)
        self.collected = False
        self.glow = 0

    def update(self, dt):
        self.bob_offset += dt * 4
        self.glow = math.sin(self.bob_offset * 2) * 0.5 + 0.5
        dx = player.x - self.x
        dy = player.y - self.y
        if math.hypot(dx, dy) < 35 and not self.collected:
            self.collected = True
            if self.item_type == 'health':
                player.health = min(player.max_health, player.health + 30)
                create_particles(self.x, self.y, 20, 'heal')
                play_sfx('heal')
            elif self.item_type == 'chest':
                upgrades = get_available_upgrades()
                if upgrades:
                    apply_upgrade(random.choice(upgrades))
                    create_particles(self.x, self.y, 25, 'upgrade')
                    play_sfx('powerup')

    def draw(self, surface, shake):
        if self.collected:
            return
        sx = int(self.x + shake[0])
        sy = int(self.y + math.sin(self.bob_offset) * 8 + shake[1])

        # 光环
        glow_alpha = max(0, min(255, int(80 + self.glow * 100)))
        glow_color = (255, 107, 157) if self.item_type == 'health' else (255, 215, 0)
        gs = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*glow_color, max(0, min(255, glow_alpha // 3))), (30, 30), 30)
        surface.blit(gs, (sx - 30, sy - 30))

        # 图标
        icon = "♥" if self.item_type == 'health' else "★"
        color = (255, 107, 157) if self.item_type == 'health' else (255, 215, 0)
        t = font_md.render(icon, True, color)
        surface.blit(t, (sx - t.get_width() // 2, sy - t.get_height() // 2))

items = []

# ============================================================
#  光剑
# ============================================================
swords = []  # [(x, y, angle), ...]

def update_swords(game_time):
    global swords
    if 'sword' not in player.weapons:
        swords = []
        return
    swords = []
    count = player.weapons['sword']['level']
    radius = 35
    for i in range(count):
        angle = (game_time * 3) + (i * math.pi * 2 / count)
        sx = player.x + math.cos(angle) * radius
        sy = player.y + math.sin(angle) * radius
        swords.append((sx, sy, angle))

# ============================================================
#  升级系统
# ============================================================
def get_available_upgrades():
    upgrades = []

    # 现有武器升级
    for wtype in player.weapons:
        w = player.weapons[wtype]
        if w['level'] < w['max_level']:
            names = {'gun': '枪械升级', 'poison': '毒气升级', 'sword': '光剑升级'}
            descs = {'gun': '增加子弹数量', 'poison': '增加范围和伤害', 'sword': '增加光剑数量'}
            icons = {'gun': '⊕', 'poison': '◉', 'sword': '†'}
            upgrades.append({
                'type': wtype,
                'name': names.get(wtype, wtype),
                'desc': descs.get(wtype, ''),
                'icon': icons.get(wtype, '?'),
                'level': w['level']
            })
        elif w['level'] == w['max_level'] and not w.get('ultimate'):
            names = {'gun': '枪械·究极', 'poison': '毒气·究极', 'sword': '光剑·究极'}
            icons = {'gun': '⊕', 'poison': '◉', 'sword': '†'}
            upgrades.append({
                'type': wtype + '_ultimate',
                'name': names.get(wtype, wtype + '究极'),
                'desc': '伤害翻倍！★★★★★★',
                'icon': icons.get(wtype, '?'),
                'level': 5
            })

    # 新武器
    if 'gun' not in player.weapons:
        upgrades.append({'type': 'new_gun', 'name': '获得突击枪', 'desc': '手动发射子弹', 'icon': '⊕', 'level': 0})
    if 'poison' not in player.weapons:
        upgrades.append({'type': 'new_poison', 'name': '获得毒气场', 'desc': '持续毒伤领域', 'icon': '◉', 'level': 0})
    if 'sword' not in player.weapons:
        upgrades.append({'type': 'new_sword', 'name': '获得光剑', 'desc': '旋转光剑', 'icon': '†', 'level': 0})

    # AI伙伴
    if not ai_companion.active:
        upgrades.append({'type': 'ai_companion', 'name': 'AI小伙伴', 'desc': '自动帮你打怪！', 'icon': '◈', 'level': 0})
    elif ai_companion.level < 5:
        upgrades.append({'type': 'ai_upgrade', 'name': 'AI伙伴升级', 'desc': '更强的火力！', 'icon': '◈', 'level': ai_companion.level})

    # 通用
    if 'poison' in player.weapons and not player.weapons['poison'].get('no_cooldown'):
        upgrades.append({'type': 'cooldown', 'name': '冷却缩减', 'desc': '取消毒气冷却', 'icon': '▼', 'level': 0})

    upgrades.append({'type': 'health', 'name': '生命恢复', 'desc': '恢复40点生命', 'icon': '♥', 'level': 0})

    return upgrades

def apply_upgrade(upgrade):
    utype = upgrade['type']
    if utype in ('gun', 'poison', 'sword'):
        if utype in player.weapons:
            player.weapons[utype]['level'] += 1
    elif utype == 'gun_ultimate':
        if 'gun' in player.weapons:
            player.weapons['gun']['ultimate'] = True
    elif utype == 'poison_ultimate':
        if 'poison' in player.weapons:
            player.weapons['poison']['ultimate'] = True
    elif utype == 'sword_ultimate':
        if 'sword' in player.weapons:
            player.weapons['sword']['ultimate'] = True
    elif utype == 'new_gun':
        player.weapons['gun'] = {'level': 1, 'max_level': 5, 'ultimate': False}
    elif utype == 'new_poison':
        player.weapons['poison'] = {'level': 1, 'max_level': 5, 'ultimate': False, 'activated': False, 'cooldown': 0, 'no_cooldown': False}
    elif utype == 'new_sword':
        player.weapons['sword'] = {'level': 1, 'max_level': 5, 'ultimate': False}
    elif utype == 'cooldown':
        if 'poison' in player.weapons:
            player.weapons['poison']['no_cooldown'] = True
            player.weapons['poison']['cooldown'] = 0
    elif utype == 'health':
        player.health = min(player.max_health, player.health + 40)
        create_particles(player.x, player.y, 15, 'heal')
    elif utype == 'ai_companion':
        ai_companion.activate()
    elif utype == 'ai_upgrade':
        ai_companion.level += 1
        ai_companion.emote(f"升级啦! Lv.{ai_companion.level}", 2.0)
    play_sfx('powerup')

# ============================================================
#  游戏状态管理
# ============================================================
game_state = 'start'  # start, playing, paused, upgrade, gameover
selected_weapon = 'gun'
game_time = 0.0
poison_cooldown = 0.0
background_offset = [0.0, 0.0]
upgrade_choices = []
boss_warning_timer = 0
boss_warning_text = ""

def reset_game():
    global enemies, bullets, items, particles, swords, bosses
    global game_time, poison_cooldown, background_offset
    global next_boss_time, boss_level_counter, boss_warning_timer

    player.health = 100
    player.max_health = 100
    player.level = 1
    player.exp = 0
    player.exp_to_next = 10
    player.kills = 0
    player.weapons = {}
    player.trail = []
    player.invincible_timer = 0
    player.x = WIDTH // 2
    player.y = HEIGHT // 2

    enemies = []
    bullets = []
    items = []
    particles = []
    swords = []
    bosses = []
    game_time = 0
    poison_cooldown = 0
    background_offset = [0.0, 0.0]
    next_boss_time = 60
    boss_level_counter = 0
    boss_warning_timer = 0
    combo_system.count = 0
    combo_system.timer = 0
    combo_system.best_combo = 0
    combo_system.display_texts = []

    ai_companion.active = False
    ai_companion.level = 1
    ai_companion.kills = 0
    ai_companion.trail = []
    ai_companion.boss_bullets = [] if hasattr(ai_companion, 'boss_bullets') else None

    # 初始武器
    if selected_weapon == 'gun':
        player.weapons['gun'] = {'level': 1, 'max_level': 5, 'ultimate': False}
    elif selected_weapon == 'poison':
        player.weapons['poison'] = {'level': 1, 'max_level': 5, 'ultimate': False, 'activated': False, 'cooldown': 0, 'no_cooldown': False}
    elif selected_weapon == 'sword':
        player.weapons['sword'] = {'level': 1, 'max_level': 5, 'ultimate': False}

def shoot(target_x, target_y):
    if 'gun' not in player.weapons:
        return
    gun = player.weapons['gun']
    count = min(gun['level'], 5)
    base_angle = math.atan2(target_y - player.y, target_x - player.x)
    damage = 30
    if gun.get('ultimate'):
        damage = 60

    create_particles(player.x, player.y, 6, 'muzzle')
    play_sfx('shoot')

    if count == 1:
        bullets.append(Bullet(player.x, player.y, base_angle, 500, damage))
    else:
        spread = math.pi / 4
        for i in range(count):
            offset = (i - (count - 1) / 2) * (spread / max(count - 1, 1))
            bullets.append(Bullet(player.x, player.y, base_angle + offset, 500, damage))

def activate_poison():
    if 'poison' not in player.weapons:
        return
    pw = player.weapons['poison']
    if pw.get('cooldown', 0) > 0 and not pw.get('no_cooldown'):
        return
    pw['activated'] = True
    if not pw.get('no_cooldown'):
        pw['cooldown'] = 5
    create_particles(player.x, player.y, 50, 'poison')
    screen_shake.trigger(5, 0.15)
    play_sfx('poison')

    # 3秒后关闭
    pw['_deactivate_at'] = game_time + 3.0

def show_upgrade_screen():
    global game_state, upgrade_choices
    all_upgrades = get_available_upgrades()
    random.shuffle(all_upgrades)
    upgrade_choices = all_upgrades[:3]
    game_state = 'upgrade'

# ============================================================
#  绘制各种界面
# ============================================================
def draw_background(surface, shake):
    surface.fill(DARK_BG)
    grid_size = 60
    ox = int(background_offset[0] % grid_size + shake[0])
    oy = int(background_offset[1] % grid_size + shake[1])
    for x in range(ox, WIDTH + grid_size, grid_size):
        pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, HEIGHT), 1)
    for y in range(oy, HEIGHT + grid_size, grid_size):
        pygame.draw.line(surface, GRID_COLOR, (0, y), (WIDTH, y), 1)

def draw_poison_field(surface, shake):
    if 'poison' not in player.weapons:
        return
    pw = player.weapons['poison']
    r = 60 + pw['level'] * 25
    is_active = pw.get('activated', False)
    is_ult = pw.get('ultimate', False)

    sx = int(player.x + shake[0])
    sy = int(player.y + shake[1])

    # 毒气圈
    ring_surf = pygame.Surface((r * 2 + 20, r * 2 + 20), pygame.SRCALPHA)
    center = (r + 10, r + 10)
    alpha = 120 if is_active else 50
    color = (255, 0, 255, alpha) if is_ult else ((0, 255, 0, alpha) if is_active else (0, 68, 0, alpha))
    width = 5 if is_active else 2
    pygame.draw.circle(ring_surf, color, center, r, width)
    if is_active:
        pygame.draw.circle(ring_surf, (*color[:3], 20), center, r)
    surface.blit(ring_surf, (sx - r - 10, sy - r - 10))

    # 毒气粒子
    if is_active:
        for _ in range(8):
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(0, r)
            px = sx + math.cos(angle) * dist
            py = sy + math.sin(angle) * dist
            pc = (68, 255, 68) if not is_ult else (255, 68, 255)
            s = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(s, (*pc, random.randint(40, 120)), (3, 3), 3)
            surface.blit(s, (int(px - 3), int(py - 3)))

def draw_swords(surface, shake):
    for sx, sy, angle in swords:
        is_ult = player.weapons.get('sword', {}).get('ultimate', False)
        dx = int(sx + shake[0])
        dy = int(sy + shake[1])

        color = (255, 0, 255) if is_ult else (0, 255, 255)
        inner = (255, 68, 255) if is_ult else (68, 255, 255)
        trail_color = (255, 136, 255) if is_ult else (136, 255, 255)

        # 轨迹
        trail_len = 40
        tx = dx - int(math.cos(angle) * trail_len)
        ty = dy - int(math.sin(angle) * trail_len)
        ts = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.line(ts, (*trail_color, 120), (tx, ty), (dx, dy), 3)
        surface.blit(ts, (0, 0))

        pygame.draw.circle(surface, color, (dx, dy), 18, 5)
        pygame.draw.circle(surface, inner, (dx, dy), 12)

def draw_start_screen(surface):
    # 背景粒子
    surface.fill((10, 10, 30))
    for _ in range(3):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        pygame.draw.circle(surface, (50, 50, 100), (x, y), random.randint(1, 3))

    # 标题
    title = font_title.render("割草游戏", True, CYAN)
    title_shadow = font_title.render("割草游戏", True, (0, 100, 100))
    surface.blit(title_shadow, (WIDTH // 2 - title.get_width() // 2 + 3, 80 + 3))
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))

    subtitle = font_sm.render("Grass Cutting Game - Python Edition", True, (150, 200, 200))
    surface.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 175))

    # 武器选择
    weapons_info = [
        ('gun', '⊕ 突击枪', '手动发射子弹击退敌人\n升级后变成散弹枪', (231, 76, 60)),
        ('poison', '◉ 毒气场', '持续毒伤领域\n激活时伤害翻倍', (46, 204, 113)),
        ('sword', '† 光剑', '围绕主角旋转的光剑\n可增加剑的数量', (52, 152, 219)),
    ]

    card_w = 250
    card_h = 180
    start_x = WIDTH // 2 - (card_w * 3 + 40 * 2) // 2
    y = 230

    for i, (wtype, name, desc, color) in enumerate(weapons_info):
        x = start_x + i * (card_w + 40)
        is_selected = (selected_weapon == wtype)

        # 卡片
        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        bg_alpha = 200 if is_selected else 150
        border_color = (243, 156, 18) if is_selected else color
        pygame.draw.rect(card_surf, (30, 40, 60, bg_alpha), (0, 0, card_w, card_h), border_radius=15)
        pygame.draw.rect(card_surf, (*border_color, 255), (0, 0, card_w, card_h), 3, border_radius=15)

        if is_selected:
            glow = pygame.Surface((card_w + 10, card_h + 10), pygame.SRCALPHA)
            pygame.draw.rect(glow, (243, 156, 18, 30), (0, 0, card_w + 10, card_h + 10), border_radius=18)
            surface.blit(glow, (x - 5, y - 5))

        surface.blit(card_surf, (x, y))

        # 武器名称
        n_surf = font_md.render(name, True, WHITE)
        surface.blit(n_surf, (x + card_w // 2 - n_surf.get_width() // 2, y + 20))

        # 描述
        lines = desc.split('\n')
        for li, line in enumerate(lines):
            d_surf = font_xs.render(line, True, (189, 195, 199))
            surface.blit(d_surf, (x + card_w // 2 - d_surf.get_width() // 2, y + 70 + li * 22))

        if is_selected:
            sel = font_xs.render("✓ 已选择", True, (243, 156, 18))
            surface.blit(sel, (x + card_w // 2 - sel.get_width() // 2, y + card_h - 35))

    # 操作说明
    controls = [
        "WASD - 移动  |  鼠标点击 - 射击  |  空格 - 激活毒气  |  ESC - 暂停"
    ]
    for i, c in enumerate(controls):
        cs = font_xs.render(c, True, (150, 150, 180))
        surface.blit(cs, (WIDTH // 2 - cs.get_width() // 2, 460 + i * 25))

    # 新功能说明
    features = [
        "★ 新功能：AI小伙伴自动帮你打怪！",
        "★ 新功能：连击系统，连续击杀得分翻倍！",
        "★ 新功能：Boss怪物，每60秒登场！",
        "★ 新功能：酷炫粒子特效和屏幕震动！",
        "★ 新功能：动态音效和背景音乐！",
    ]
    for i, f in enumerate(features):
        fc = (200, 200, 100) if i % 2 == 0 else (100, 200, 200)
        fs = font_xs.render(f, True, fc)
        surface.blit(fs, (WIDTH // 2 - fs.get_width() // 2, 510 + i * 24))

    # 开始按钮
    btn_w, btn_h = 250, 55
    btn_x = WIDTH // 2 - btn_w // 2
    btn_y = 660
    btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

    mx, my = pygame.mouse.get_pos()
    hover = btn_rect.collidepoint(mx, my)

    btn_color = (192, 57, 43) if hover else (231, 76, 60)
    pygame.draw.rect(surface, btn_color, btn_rect, border_radius=25)
    pygame.draw.rect(surface, WHITE, btn_rect, 2, border_radius=25)

    btn_text = font_md.render("开始游戏", True, WHITE)
    surface.blit(btn_text, (btn_x + btn_w // 2 - btn_text.get_width() // 2,
                             btn_y + btn_h // 2 - btn_text.get_height() // 2))

    return btn_rect, [(start_x + i * (card_w + 40), y, card_w, card_h) for i in range(3)]

def draw_upgrade_screen(surface):
    # 半透明背景
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 220))
    surface.blit(overlay, (0, 0))

    title = font_lg.render("选择升级", True, (243, 156, 18))
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

    card_w = 260
    card_h = 220
    gap = 30
    total_w = len(upgrade_choices) * card_w + (len(upgrade_choices) - 1) * gap
    start_x = WIDTH // 2 - total_w // 2

    rects = []
    mx, my = pygame.mouse.get_pos()

    for i, upgrade in enumerate(upgrade_choices):
        x = start_x + i * (card_w + gap)
        y = 220
        rect = pygame.Rect(x, y, card_w, card_h)
        hover = rect.collidepoint(mx, my)

        # 卡片
        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        bg = (60, 70, 90, 220) if hover else (44, 62, 80, 200)
        border = (231, 76, 60) if hover else (52, 152, 219)
        pygame.draw.rect(card_surf, bg, (0, 0, card_w, card_h), border_radius=15)
        pygame.draw.rect(card_surf, border, (0, 0, card_w, card_h), 3, border_radius=15)
        surface.blit(card_surf, (x, y))

        # 图标
        icon_text = font_lg.render(upgrade['icon'], True, WHITE)
        surface.blit(icon_text, (x + card_w // 2 - icon_text.get_width() // 2, y + 15))

        # 名称
        name_text = font_sm.render(upgrade['name'], True, WHITE)
        surface.blit(name_text, (x + card_w // 2 - name_text.get_width() // 2, y + 85))

        # 星级
        level = upgrade.get('level', 0)
        stars = ""
        for s in range(5):
            stars += "★" if s < level else "☆"
        if '_ultimate' in upgrade.get('type', ''):
            stars += "★"
        star_text = font_sm.render(stars, True, (243, 156, 18))
        surface.blit(star_text, (x + card_w // 2 - star_text.get_width() // 2, y + 115))

        # 描述
        desc_text = font_xs.render(upgrade['desc'], True, (189, 195, 199))
        surface.blit(desc_text, (x + card_w // 2 - desc_text.get_width() // 2, y + 155))

        rects.append((rect, upgrade))

    return rects

def draw_pause_screen(surface):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))

    title = font_lg.render("游戏暂停", True, (52, 152, 219))
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 150))

    # 当前信息
    info_y = 260
    minutes = int(game_time // 60)
    seconds = int(game_time % 60)
    infos = [
        f"等级: {player.level}",
        f"击杀数: {player.kills}",
        f"时间: {minutes}:{seconds:02d}",
        f"最佳连击: {combo_system.best_combo}",
    ]
    for i, info_text in enumerate(infos):
        ts = font_sm.render(info_text, True, WHITE)
        surface.blit(ts, (WIDTH // 2 - ts.get_width() // 2, info_y + i * 35))

    # 按钮
    btns = []
    btn_labels = ["继续游戏", "重新开始", "返回主菜单"]
    for i, label in enumerate(btn_labels):
        bw, bh = 220, 50
        bx = WIDTH // 2 - bw // 2
        by = 440 + i * 70
        rect = pygame.Rect(bx, by, bw, bh)
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint(mx, my)
        color = (192, 57, 43) if hover else (231, 76, 60)
        pygame.draw.rect(surface, color, rect, border_radius=20)
        pygame.draw.rect(surface, WHITE, rect, 2, border_radius=20)
        ts = font_sm.render(label, True, WHITE)
        surface.blit(ts, (bx + bw // 2 - ts.get_width() // 2, by + bh // 2 - ts.get_height() // 2))
        btns.append(rect)

    return btns  # [继续, 重新开始, 返回菜单]

def draw_gameover_screen(surface):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 230))
    surface.blit(overlay, (0, 0))

    title = font_lg.render("游戏结束", True, RED)
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

    minutes = int(game_time // 60)
    seconds = int(game_time % 60)
    score = int(player.kills * player.level * 10 * max(1, combo_system.best_combo * 0.1))

    stats = [
        (f"最终得分: {score}", (243, 156, 18), font_lg),
        (f"最终等级: {player.level}", WHITE, font_md),
        (f"总击杀数: {player.kills}", WHITE, font_md),
        (f"存活时间: {minutes}:{seconds:02d}", WHITE, font_md),
        (f"最佳连击: {combo_system.best_combo}", (255, 200, 0), font_md),
    ]

    if ai_companion.active:
        stats.append((f"AI伙伴击杀: {ai_companion.kills}", (100, 200, 255), font_md))

    y = 190
    for text, color, f in stats:
        ts = f.render(text, True, color)
        surface.blit(ts, (WIDTH // 2 - ts.get_width() // 2, y))
        y += ts.get_height() + 12

    # 按钮
    btns = []
    btn_labels = ["再玩一局", "返回主菜单"]
    for i, label in enumerate(btn_labels):
        bw, bh = 220, 50
        bx = WIDTH // 2 - bw // 2
        by = y + 30 + i * 70
        rect = pygame.Rect(bx, by, bw, bh)
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint(mx, my)
        color = (192, 57, 43) if hover else (231, 76, 60)
        pygame.draw.rect(surface, color, rect, border_radius=20)
        pygame.draw.rect(surface, WHITE, rect, 2, border_radius=20)
        ts = font_sm.render(label, True, WHITE)
        surface.blit(ts, (bx + bw // 2 - ts.get_width() // 2, by + bh // 2 - ts.get_height() // 2))
        btns.append(rect)

    return btns  # [再玩, 返回]

def draw_hud(surface, shake):
    """游戏中的HUD"""
    ox, oy = int(shake[0]), int(shake[1])

    # 生命条
    panel = pygame.Surface((250, 130), pygame.SRCALPHA)
    pygame.draw.rect(panel, (0, 0, 0, 180), (0, 0, 250, 130), border_radius=12)
    pygame.draw.rect(panel, (255, 255, 255, 60), (0, 0, 250, 130), 2, border_radius=12)
    surface.blit(panel, (15 + ox, 15 + oy))

    # 血条
    hp_text = font_xs.render("♥ 生命值:", True, (255, 100, 100))
    surface.blit(hp_text, (25 + ox, 22 + oy))
    bar_x, bar_y, bar_w, bar_h = 25 + ox, 45 + oy, 220, 18
    pygame.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=9)
    hp_ratio = max(0, player.health / player.max_health)
    hp_color = (255, 68, 68) if hp_ratio < 0.3 else ((255, 170, 0) if hp_ratio < 0.6 else (68, 255, 68))
    pygame.draw.rect(surface, hp_color, (bar_x, bar_y, int(bar_w * hp_ratio), bar_h), border_radius=9)

    # 经验条
    exp_ratio = player.exp / player.exp_to_next if player.exp_to_next > 0 else 0
    exp_y = bar_y + 22
    pygame.draw.rect(surface, (30, 30, 60), (bar_x, exp_y, bar_w, 6), border_radius=3)
    pygame.draw.rect(surface, (100, 100, 255), (bar_x, exp_y, int(bar_w * exp_ratio), 6), border_radius=3)

    # 信息
    info_y = exp_y + 14
    infos = [
        f"★ 等级: {player.level}",
        f"♠ 击杀: {player.kills}",
    ]
    minutes = int(game_time // 60)
    seconds = int(game_time % 60)
    infos.append(f"● 时间: {minutes}:{seconds:02d}")
    for i, info_text in enumerate(infos):
        ts = font_xs.render(info_text, True, WHITE)
        surface.blit(ts, (25 + ox, info_y + i * 20 + oy))

    # 毒气冷却
    if 'poison' in player.weapons:
        pw = player.weapons['poison']
        cd = pw.get('cooldown', 0)
        if cd > 0 and not pw.get('no_cooldown'):
            cd_text = font_xs.render(f"◉ 冷却: {cd:.1f}s", True, (255, 100, 100))
            surface.blit(cd_text, (25 + ox, 155 + oy))

    # Boss警告
    if boss_warning_timer > 0:
        flash = int(boss_warning_timer * 5) % 2 == 0
        if flash:
            warn_text = font_lg.render("▲▲ BOSS来了！▲▲", True, RED)
            surface.blit(warn_text, (WIDTH // 2 - warn_text.get_width() // 2 + ox,
                                      HEIGHT // 2 - 100 + oy))

# ============================================================
#  主游戏循环
# ============================================================
def main():
    global game_state, selected_weapon, game_time, poison_cooldown
    global enemies, bullets, items, particles, swords, bosses
    global upgrade_choices, next_boss_time, boss_level_counter
    global boss_warning_timer, bgm_sound

    bgm_playing = False
    running = True

    while running:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.033)  # 限制最大帧时间
        mouse_pos = pygame.mouse.get_pos()

        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game_state == 'playing':
                        game_state = 'paused'
                    elif game_state == 'paused':
                        game_state = 'playing'

                if event.key == pygame.K_SPACE and game_state == 'playing':
                    activate_poison()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game_state == 'start':
                    # 检查武器选择和开始按钮
                    pass  # 在绘制时处理
                elif game_state == 'playing':
                    shoot(mouse_pos[0], mouse_pos[1])

        # ========== 开始界面 ==========
        if game_state == 'start':
            btn_rect, weapon_rects = draw_start_screen(screen)

            if pygame.mouse.get_pressed()[0]:
                mx, my = mouse_pos
                # 武器选择
                weapon_types = ['gun', 'poison', 'sword']
                for i, (wx, wy, ww, wh) in enumerate(weapon_rects):
                    if pygame.Rect(wx, wy, ww, wh).collidepoint(mx, my):
                        selected_weapon = weapon_types[i]
                # 开始按钮
                if btn_rect.collidepoint(mx, my):
                    reset_game()
                    game_state = 'playing'
                    if SOUND_ENABLED and bgm_sound and not bgm_playing:
                        # 循环播放BGM
                        bgm_sound.play(-1)
                        bgm_sound.set_volume(0.15)
                        bgm_playing = True

        # ========== 游戏进行中 ==========
        elif game_state == 'playing':
            game_time += dt

            # 毒气冷却
            if 'poison' in player.weapons:
                pw = player.weapons['poison']
                if pw.get('cooldown', 0) > 0 and not pw.get('no_cooldown'):
                    pw['cooldown'] -= dt
                    if pw['cooldown'] < 0:
                        pw['cooldown'] = 0
                # 检查毒气是否该关闭
                if pw.get('activated') and game_time >= pw.get('_deactivate_at', 0):
                    pw['activated'] = False

            # 玩家移动（移动世界，玩家固定中心）
            keys = pygame.key.get_pressed()
            move_speed = 250
            mx_move = 0
            my_move = 0
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                my_move = move_speed
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                my_move = -move_speed
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                mx_move = move_speed
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                mx_move = -move_speed

            if mx_move != 0 and my_move != 0:
                mx_move *= 0.707
                my_move *= 0.707

            background_offset[0] += mx_move * dt
            background_offset[1] += my_move * dt

            # 移动所有对象
            for e in enemies:
                e.x += mx_move * dt
                e.y += my_move * dt
            for b in bullets:
                b.x += mx_move * dt
                b.y += my_move * dt
            for item in items:
                item.x += mx_move * dt
                item.y += my_move * dt
            for boss in bosses:
                boss.x += mx_move * dt
                boss.y += my_move * dt
                for bb in boss.boss_bullets:
                    bb[0] += mx_move * dt
                    bb[1] += my_move * dt

            # 更新
            player.update(dt)
            update_swords(game_time)
            ai_companion.update(dt, enemies + [b for b in bosses if b.alive], bullets)

            for e in enemies:
                e.update(dt, game_time)
            for b in bullets:
                b.update(dt, enemies + [boss for boss in bosses if boss.alive])
            for item in items:
                item.update(dt)
            for boss in bosses:
                boss.update(dt, game_time)

            # 粒子更新
            for p in particles:
                p.update(dt)
            particles = [p for p in particles if p.life > 0]

            # 屏幕震动
            screen_shake.update(dt)

            # 连击系统
            combo_system.update(dt)

            # Boss警告计时
            if boss_warning_timer > 0:
                boss_warning_timer -= dt

            # 移除死亡敌人
            new_enemies = []
            for e in enemies:
                if e.health <= 0:
                    player.kills += 1
                    player.exp += 1
                    combo_system.add_kill(e.x, e.y)
                    create_particles(e.x, e.y, 18, 'blood')
                    screen_shake.trigger(3, 0.08)
                    play_sfx('explosion')

                    if player.exp >= player.exp_to_next:
                        player.level += 1
                        player.exp = 0
                        player.exp_to_next = int(player.exp_to_next * 1.4)
                        show_upgrade_screen()
                        create_particles(player.x, player.y, 30, 'upgrade')
                else:
                    new_enemies.append(e)
            enemies = new_enemies

            # 移除死亡Boss
            for boss in bosses:
                if not boss.alive:
                    player.kills += 20
                    player.exp += 5
                    combo_system.add_kill(boss.x, boss.y)
                    create_particles(boss.x, boss.y, 80, 'boss_death')
                    screen_shake.trigger(20, 0.5)
                    play_sfx('explosion')
                    ai_companion.emote("Boss打倒了！！", 3.0)

                    if player.exp >= player.exp_to_next:
                        player.level += 1
                        player.exp = 0
                        player.exp_to_next = int(player.exp_to_next * 1.4)
                        show_upgrade_screen()
            bosses = [b for b in bosses if b.alive]

            # 清理子弹和道具
            bullets = [b for b in bullets if b.life > 0]
            items = [i for i in items if not i.collected]

            # 碰撞检测 - 敌人伤害玩家
            for e in enemies:
                dist = math.hypot(player.x - e.x, player.y - e.y)
                if dist < e.size + 25:
                    player.take_damage(e.damage * dt)
                    if random.random() < 0.3:
                        create_particles(player.x, player.y, 2, 'blood')

            # 生成敌人
            spawn_rate = min(0.03 + game_time * 0.001, 0.08)
            if random.random() < spawn_rate:
                side = random.randint(0, 3)
                tier = min(int(game_time // 25) + 1, 6)
                spawn_dist = 100
                if side == 0:
                    ex, ey = random.randint(0, WIDTH), -spawn_dist
                elif side == 1:
                    ex, ey = WIDTH + spawn_dist, random.randint(0, HEIGHT)
                elif side == 2:
                    ex, ey = random.randint(0, WIDTH), HEIGHT + spawn_dist
                else:
                    ex, ey = -spawn_dist, random.randint(0, HEIGHT)
                enemies.append(Enemy(ex, ey, tier))

            # 生成道具
            if random.random() < 0.003:
                ix = random.randint(50, WIDTH - 50)
                iy = random.randint(50, HEIGHT - 50)
                itype = 'chest' if random.random() < 0.4 else 'health'
                items.append(Item(ix, iy, itype))

            # Boss生成
            if game_time >= next_boss_time and not any(b.alive for b in bosses):
                boss_level_counter += 1
                boss_warning_timer = 3.0  # 3秒预警
                # 延迟生成Boss
                side = random.randint(0, 3)
                if side == 0:
                    bx, by = WIDTH // 2, -80
                elif side == 1:
                    bx, by = WIDTH + 80, HEIGHT // 2
                elif side == 2:
                    bx, by = WIDTH // 2, HEIGHT + 80
                else:
                    bx, by = -80, HEIGHT // 2
                bosses.append(Boss(bx, by, boss_level_counter))
                next_boss_time = game_time + 60  # 下一个Boss
                screen_shake.trigger(10, 0.5)
                ai_companion.emote("Boss来了！小心！", 3.0)

            # 检查游戏结束
            if player.health <= 0:
                game_state = 'gameover'
                play_sfx('gameover')
                if bgm_sound:
                    bgm_sound.stop()
                    bgm_playing = False

            # ---- 绘制 ----
            shake = screen_shake.offset
            draw_background(screen, shake)

            for item in items:
                item.draw(screen, shake)
            for e in enemies:
                e.draw(screen, shake)
            for b in bullets:
                b.draw(screen, shake)

            draw_poison_field(screen, shake)
            draw_swords(screen, shake)
            player.draw(screen, shake)
            ai_companion.draw(screen, shake)

            for boss in bosses:
                boss.draw(screen, shake)

            for p in particles:
                p.draw(screen, shake)

            # HUD
            draw_hud(screen, shake)
            combo_system.draw(screen, shake)

        # ========== 升级界面 ==========
        elif game_state == 'upgrade':
            # 先绘制游戏画面
            shake = screen_shake.offset
            draw_background(screen, shake)
            for item in items:
                item.draw(screen, shake)
            for e in enemies:
                e.draw(screen, shake)
            draw_poison_field(screen, shake)
            draw_swords(screen, shake)
            player.draw(screen, shake)
            ai_companion.draw(screen, shake)
            draw_hud(screen, shake)

            # 升级选项
            rects = draw_upgrade_screen(screen)
            if pygame.mouse.get_pressed()[0]:
                for rect, upgrade in rects:
                    if rect.collidepoint(mouse_pos):
                        apply_upgrade(upgrade)
                        game_state = 'playing'
                        create_particles(player.x, player.y, 35, 'upgrade')
                        pygame.time.delay(200)  # 防止连点
                        break

        # ========== 暂停 ==========
        elif game_state == 'paused':
            # 绘制游戏画面
            shake = screen_shake.offset
            draw_background(screen, shake)
            for item in items:
                item.draw(screen, shake)
            for e in enemies:
                e.draw(screen, shake)
            draw_poison_field(screen, shake)
            draw_swords(screen, shake)
            player.draw(screen, shake)
            ai_companion.draw(screen, shake)
            draw_hud(screen, shake)

            btns = draw_pause_screen(screen)
            if pygame.mouse.get_pressed()[0]:
                if btns[0].collidepoint(mouse_pos):  # 继续
                    game_state = 'playing'
                    pygame.time.delay(200)
                elif btns[1].collidepoint(mouse_pos):  # 重新开始
                    reset_game()
                    game_state = 'playing'
                    pygame.time.delay(200)
                elif btns[2].collidepoint(mouse_pos):  # 返回菜单
                    game_state = 'start'
                    if bgm_sound:
                        bgm_sound.stop()
                        bgm_playing = False
                    pygame.time.delay(200)

        # ========== 游戏结束 ==========
        elif game_state == 'gameover':
            # 绘制最终画面
            draw_background(screen, (0, 0))
            for e in enemies:
                e.draw(screen, (0, 0))
            player.draw(screen, (0, 0))

            btns = draw_gameover_screen(screen)
            if pygame.mouse.get_pressed()[0]:
                if btns[0].collidepoint(mouse_pos):  # 再玩
                    reset_game()
                    game_state = 'playing'
                    if SOUND_ENABLED and bgm_sound:
                        bgm_sound.play(-1)
                        bgm_sound.set_volume(0.15)
                        bgm_playing = True
                    pygame.time.delay(200)
                elif btns[1].collidepoint(mouse_pos):  # 返回菜单
                    game_state = 'start'
                    pygame.time.delay(200)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
