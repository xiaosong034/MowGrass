"""
综合测试平台 - Boss + 角色 联合测试
支持切换角色、切换Boss、实时查看属性、测试战斗

操作说明:
  WASD / 方向键  : 移动角色
  鼠标左键       : 散弹射击
  1-4            : 切换Boss类型(骷髅王/毒液巨兽/烈焰魔将/虚空之眼)
  Q / E          : 切换角色 (←/→)
  N              : 下一级Boss
  R              : 重置当前Boss
  H              : 恢复满血
  P              : 暂停/继续
  TAB            : 切换信息面板
  ESC            : 退出
"""

import pygame
import math
import random
import sys
import array

pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

WIDTH, HEIGHT = 1200, 800
DARK_BG = (15, 15, 25)
GRID_COLOR = (30, 30, 45)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 68, 68)
PINK = (255, 100, 200)
CYAN = (78, 205, 196)
YELLOW = (255, 255, 0)
ORANGE = (255, 170, 0)
PURPLE = (170, 68, 255)
GREEN = (68, 255, 68)
DARK_CYAN = (40, 130, 120)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("割草游戏 - 综合测试平台")
clock = pygame.time.Clock()

# 字体
font_path = 'C:/Windows/Fonts/msyh.ttc'
font_lg = pygame.font.Font(font_path, 36)
font_md = pygame.font.Font(font_path, 24)
font_sm = pygame.font.Font(font_path, 18)
font_xs = pygame.font.Font(font_path, 14)


# ============================================================
#  简易音效系统
# ============================================================
sfx_cache = {}
def make_beep(freq=440, duration=0.1, volume=0.3):
    sr = 22050
    n = int(sr * duration)
    buf = array.array('h', [0] * n)
    for i in range(n):
        t = i / sr
        v = math.sin(2 * math.pi * freq * t) * volume * 32767
        env = min(1.0, (n - i) / (n * 0.3))
        buf[i] = max(-32767, min(32767, int(v * env)))
    return pygame.mixer.Sound(buffer=buf)

sfx_cache['hit'] = make_beep(600, 0.05, 0.2)
sfx_cache['shoot'] = make_beep(800, 0.04, 0.15)
sfx_cache['boss_roar'] = make_beep(120, 0.3, 0.4)
sfx_cache['explosion'] = make_beep(200, 0.15, 0.3)

def play_sfx(name):
    snd = sfx_cache.get(name)
    if snd:
        snd.play()


# ============================================================
#  屏幕震动
# ============================================================
class ScreenShake:
    def __init__(self):
        self.intensity = 0
        self.timer = 0
        self.offset = [0, 0]
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
            self.offset = [0, 0]
            self.intensity = 0

shake = ScreenShake()


# ============================================================
#  粒子系统
# ============================================================
class Particle:
    def __init__(self, x, y, vx, vy, color, life=1.0, size=4):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 200 * dt
        self.life -= dt
    def draw(self, surface, sh):
        if self.life <= 0:
            return
        a = max(0, min(255, int(255 * self.life / self.max_life)))
        r = max(1, int(self.size * self.life / self.max_life))
        sx = int(self.x + sh[0])
        sy = int(self.y + sh[1])
        ps = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        c = (*self.color[:3], a)
        pygame.draw.circle(ps, c, (r + 1, r + 1), r)
        surface.blit(ps, (sx - r - 1, sy - r - 1))

particles = []
def create_particles(x, y, count, effect_type='default'):
    colors = {
        'default': [WHITE, CYAN, YELLOW],
        'explosion': [ORANGE, YELLOW, RED],
        'boss_death': [PINK, PURPLE, RED, ORANGE, YELLOW],
        'heal': [GREEN, (100, 255, 150), WHITE],
    }
    palette = colors.get(effect_type, colors['default'])
    for _ in range(count):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(50, 250)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        c = random.choice(palette)
        life = random.uniform(0.4, 1.2)
        size = random.uniform(2, 6)
        particles.append(Particle(x, y, vx, vy, c, life, size))


# ============================================================
#  导入Boss和角色模块
# ============================================================
import boss
import characters


# ============================================================
#  子弹类
# ============================================================
class Bullet:
    def __init__(self, x, y, angle, speed=500, damage=30):
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 2.5
        self.damage = damage
        self.hit = False

    def update(self, dt, bosses):
        if self.hit:
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        for b in bosses:
            if self.hit or not b.alive:
                continue
            d = math.hypot(b.x - self.x, b.y - self.y)
            if d < b.size + 8:
                b.health -= self.damage
                b.flash_timer = 0.1
                create_particles(self.x, self.y, 10, 'explosion')
                shake.trigger(4, 0.1)
                play_sfx('hit')
                self.hit = True
                self.life = 0
                if d > 0:
                    b.x += (b.x - self.x) / d * 30
                    b.y += (b.y - self.y) / d * 30

    def draw(self, surface, sh):
        if self.hit:
            return
        sx = int(self.x + sh[0])
        sy = int(self.y + sh[1])
        pygame.draw.circle(surface, YELLOW, (sx, sy), 4)
        ex = sx - int(self.vx * 0.03)
        ey = sy - int(self.vy * 0.03)
        pygame.draw.line(surface, ORANGE, (sx, sy), (ex, ey), 3)


# ============================================================
#  测试场模拟玩家 (连接角色和Boss系统)
# ============================================================
class TestPlayer:
    """测试用玩家包装类 - 包装角色类给Boss系统使用"""
    def __init__(self, char_index=0):
        self.char_index = char_index
        self.character = characters.create_character(char_index, WIDTH // 2, HEIGHT // 2)
        # Boss系统需要的属性
        self.x = self.character.x
        self.y = self.character.y
        self.health = self.character.health
        self.max_health = self.character.max_health
        self.weapons = self.character.weapons
        self.invincible_timer = 0

    def switch_character(self, index):
        """切换角色"""
        self.char_index = index % characters.get_character_count()
        self.character = characters.create_character(self.char_index, self.x, self.y)
        self.health = self.character.health
        self.max_health = self.character.max_health
        self.weapons = self.character.weapons

    def take_damage(self, amount):
        result = self.character.take_damage(amount)
        self.health = self.character.health
        self.invincible_timer = self.character.invincible_timer
        return result

    def heal_full(self):
        self.character.health = self.character.max_health
        self.health = self.character.max_health
        create_particles(self.x, self.y, 20, 'heal')

    def update(self, dt):
        self.character.x = self.x
        self.character.y = self.y
        self.character.update(dt)
        self.health = self.character.health
        self.invincible_timer = self.character.invincible_timer

    def draw(self, surface, sh):
        self.character.x = self.x
        self.character.y = self.y
        self.character.draw(surface, sh)


# ============================================================
#  初始化
# ============================================================
player = TestPlayer(0)

# 注入boss模块
test_swords = []
def get_swords():
    return test_swords

boss.init(player, get_swords, shake, create_particles, play_sfx, font_sm, font_xs, WIDTH, HEIGHT)

# ============================================================
#  状态
# ============================================================
current_boss_level = 1
bosses_list = [boss.create_boss(WIDTH // 2, 150, current_boss_level)]
game_time = 0.0
bg_offset = [0.0, 0.0]
auto_shoot_timer = 0
paused = False
show_info_panel = True
bullets = []
mode = 'battle'  # 'battle' / 'gallery'
gallery_boss_index = 0
gallery_char_index = 0

# Floor decoration
floor_decorations = []
for _ in range(40):
    floor_decorations.append([
        random.uniform(0, WIDTH), random.uniform(0, HEIGHT),
        random.choice(['stone', 'grass', 'mark']),
        random.uniform(3, 8)])


def reset_boss():
    global bosses_list, bullets
    bosses_list = [boss.create_boss(WIDTH // 2, 150, current_boss_level)]
    bullets.clear()
    particles.clear()
    player.heal_full()


def next_boss_level():
    global current_boss_level
    current_boss_level += 1
    reset_boss()


# ============================================================
#  主循环
# ============================================================
running = True
while running:
    dt = min(clock.tick(60) / 1000.0, 0.033)
    mouse_pos = pygame.mouse.get_pos()

    # ---- 事件处理 ----
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            # 1-4: 切换Boss类型
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                current_boss_level = event.key - pygame.K_0
                reset_boss()

            # N: 下一级Boss
            elif event.key == pygame.K_n:
                next_boss_level()

            # R: 重置
            elif event.key == pygame.K_r:
                reset_boss()

            # P: 暂停
            elif event.key == pygame.K_p:
                paused = not paused

            # H: 满血
            elif event.key == pygame.K_h:
                player.heal_full()

            # Q/E: 切换角色
            elif event.key == pygame.K_q:
                old_char = player.char_index
                player.switch_character(player.char_index - 1)
                create_particles(player.x, player.y, 25, 'default')
                play_sfx('shoot')
                print(f"切换角色: {old_char} -> {player.char_index}")

            elif event.key == pygame.K_e:
                old_char = player.char_index
                player.switch_character(player.char_index + 1)
                create_particles(player.x, player.y, 25, 'default')
                play_sfx('shoot')
                print(f"切换角色: {old_char} -> {player.char_index}")

            # TAB: 信息面板
            elif event.key == pygame.K_TAB:
                show_info_panel = not show_info_panel

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            angle = math.atan2(mouse_pos[1] - player.y, mouse_pos[0] - player.x)
            spread = math.pi / 6
            gun_level = player.weapons.get('gun', {}).get('level', 1)
            num = min(gun_level + 1, 5)
            for i in range(num):
                offset = (i - num / 2 + 0.5) * spread / num
                bullets.append(Bullet(player.x, player.y, angle + offset, 500, 50))
            play_sfx('shoot')
            create_particles(player.x, player.y, 5, 'explosion')

    # ---- 暂停 ----
    if paused:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        pt = font_lg.render("已暂停", True, WHITE)
        screen.blit(pt, (WIDTH // 2 - pt.get_width() // 2, HEIGHT // 2 - 50))
        tips = font_sm.render("P 继续  |  ESC 退出", True, (180, 180, 180))
        screen.blit(tips, (WIDTH // 2 - tips.get_width() // 2, HEIGHT // 2 + 10))
        pygame.display.flip()
        continue

    game_time += dt

    # ---- 玩家移动 (世界移动模式) ----
    keys = pygame.key.get_pressed()
    move_speed = player.character.move_speed
    mx_move, my_move = 0, 0
    if keys[pygame.K_w] or keys[pygame.K_UP]:    my_move = move_speed
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:   my_move = -move_speed
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:   mx_move = move_speed
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:  mx_move = -move_speed
    if mx_move and my_move:
        mx_move *= 0.707; my_move *= 0.707
    bg_offset[0] += mx_move * dt
    bg_offset[1] += my_move * dt
    for b in bosses_list:
        b.x += mx_move * dt
        b.y += my_move * dt
        for bb in b.boss_bullets:
            bb[0] += mx_move * dt
            bb[1] += my_move * dt
    for b in bullets:
        b.x += mx_move * dt
        b.y += my_move * dt
    for dec in floor_decorations:
        dec[0] += mx_move * dt
        dec[1] += my_move * dt

    # ---- 光剑 ----
    test_swords.clear()
    sword_count = player.weapons.get('sword', {}).get('level', 0)
    for i in range(sword_count):
        angle = game_time * 3 + i * math.pi * 2 / sword_count
        test_swords.append((
            player.x + math.cos(angle) * 40,
            player.y + math.sin(angle) * 40,
            angle
        ))

    # ---- 自动射击 ----
    auto_shoot_timer -= dt
    if auto_shoot_timer <= 0 and bosses_list and bosses_list[0].alive:
        target = bosses_list[0]
        if not target.entrance_active:
            angle = math.atan2(target.y - player.y, target.x - player.x)
            bullets.append(Bullet(player.x, player.y, angle, 500, 30))
            auto_shoot_timer = 0.3

    # ---- 更新 ----
    player.update(dt)
    shake.update(dt)
    for b in bosses_list:
        b.update(dt, game_time)
    for b in bullets:
        b.update(dt, bosses_list)
    bullets = [b for b in bullets if b.life > 0]
    for p in particles:
        p.update(dt)
    particles = [p for p in particles if p.life > 0]

    # Boss死亡 → 自动下一个
    for b in bosses_list:
        if not b.alive:
            create_particles(b.x, b.y, 80, 'boss_death')
            shake.trigger(20, 0.5)
    bosses_list = [b for b in bosses_list if b.alive]
    if not bosses_list:
        current_boss_level += 1
        bosses_list = [boss.create_boss(WIDTH // 2, 150, current_boss_level)]
        player.heal_full()

    # ====================================================
    #  绘制
    # ====================================================
    sh = shake.offset
    screen.fill(DARK_BG)

    # ---- 网格背景 ----
    grid = 60
    ox = int(bg_offset[0] % grid + sh[0])
    oy = int(bg_offset[1] % grid + sh[1])
    for x in range(ox, WIDTH + grid, grid):
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, HEIGHT), 1)
    for y in range(oy, HEIGHT + grid, grid):
        pygame.draw.line(screen, GRID_COLOR, (0, y), (WIDTH, y), 1)

    # ---- 地面装饰 ----
    for dec in floor_decorations:
        dx = int(dec[0] + sh[0]) % WIDTH
        dy = int(dec[1] + sh[1]) % HEIGHT
        sz = int(dec[3])
        if dec[2] == 'stone':
            pygame.draw.circle(screen, (35, 35, 50), (dx, dy), sz)
        elif dec[2] == 'grass':
            for i in range(3):
                gx = dx + random.randint(-3, 3)
                pygame.draw.line(screen, (30, 50, 30), (gx, dy), (gx, dy - sz), 1)
        else:
            pygame.draw.circle(screen, (25, 25, 40), (dx, dy), sz, 1)

    # ---- 光剑 ----
    for sx, sy, sa in test_swords:
        dx, dy = int(sx + sh[0]), int(sy + sh[1])
        ss = pygame.Surface((40, 40), pygame.SRCALPHA)
        pa = max(0, min(180, int(120 + 60 * math.sin(game_time * 6))))
        pygame.draw.circle(ss, (*CYAN, pa), (20, 20), 18, 5)
        pygame.draw.circle(ss, (68, 255, 255, max(0, pa + 40)), (20, 20), 10)
        screen.blit(ss, (dx - 20, dy - 20))

    # ---- 子弹 ----
    for b in bullets:
        b.draw(screen, sh)

    # ---- 玩家 ----
    player.draw(screen, sh)

    # ---- Boss ----
    for b in bosses_list:
        b.draw(screen, sh)

    # ---- 粒子 ----
    for p in particles:
        p.draw(screen, sh)

    # ====================================================
    #  HUD
    # ====================================================
    # 顶部状态栏
    top_bar = pygame.Surface((WIDTH, 50), pygame.SRCALPHA)
    pygame.draw.rect(top_bar, (0, 0, 0, 160), (0, 0, WIDTH, 50))
    screen.blit(top_bar, (0, 0))

    # 角色信息 (左上)
    char_info = characters.get_character_info(player.char_index)
    char_label = f"[Q/E] {char_info['title']} · {char_info['name']}"
    ct = font_sm.render(char_label, True, char_info['color'])
    screen.blit(ct, (10, 5))

    # 血条
    hp_w = 200
    hp_h = 16
    hp_x = 10
    hp_y = 28
    hp_ratio = max(0, player.health / player.max_health)
    pygame.draw.rect(screen, (60, 60, 60), (hp_x, hp_y, hp_w, hp_h), border_radius=3)
    if hp_ratio > 0:
        bar_color = GREEN if hp_ratio > 0.5 else (YELLOW if hp_ratio > 0.25 else RED)
        pygame.draw.rect(screen, bar_color, (hp_x, hp_y, int(hp_w * hp_ratio), hp_h), border_radius=3)
    hpt = font_xs.render(f"{int(player.health)}/{player.max_health}", True, WHITE)
    screen.blit(hpt, (hp_x + hp_w // 2 - hpt.get_width() // 2, hp_y))

    # Boss信息 (中上)
    if bosses_list:
        cur_boss = bosses_list[0]
        boss_label = f"Lv.{cur_boss.boss_level} {cur_boss.BOSS_TITLE} {cur_boss.BOSS_NAME}"
        bt = font_sm.render(boss_label, True, PINK)
        screen.blit(bt, (WIDTH // 2 - bt.get_width() // 2, 3))
        # Boss血条
        boss_hp_w = 300
        boss_hp_x = WIDTH // 2 - boss_hp_w // 2
        boss_hp_y = 28
        boss_ratio = max(0, cur_boss.health / cur_boss.max_health)
        pygame.draw.rect(screen, (60, 60, 60), (boss_hp_x, boss_hp_y, boss_hp_w, hp_h), border_radius=3)
        if boss_ratio > 0:
            bc = PINK if boss_ratio > 0.3 else RED
            pygame.draw.rect(screen, bc, (boss_hp_x, boss_hp_y, int(boss_hp_w * boss_ratio), hp_h), border_radius=3)
        bht = font_xs.render(f"{int(cur_boss.health)}/{cur_boss.max_health}", True, WHITE)
        screen.blit(bht, (boss_hp_x + boss_hp_w // 2 - bht.get_width() // 2, boss_hp_y))

    # FPS
    fps = clock.get_fps()
    fps_t = font_xs.render(f"FPS: {fps:.0f}", True, (100, 100, 100))
    screen.blit(fps_t, (WIDTH - fps_t.get_width() - 10, 5))

    # ---- 信息面板 (右侧) ----
    if show_info_panel:
        panel_w = 260
        panel_h = 340
        panel_x = WIDTH - panel_w - 10
        panel_y = 60
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 180), (0, 0, panel_w, panel_h), border_radius=8)
        pygame.draw.rect(panel, (80, 80, 100, 100), (0, 0, panel_w, panel_h), 2, border_radius=8)
        screen.blit(panel, (panel_x, panel_y))

        py_off = 8
        # 标题
        pt = font_sm.render("── 测试场控制台 ──", True, YELLOW)
        screen.blit(pt, (panel_x + panel_w // 2 - pt.get_width() // 2, panel_y + py_off))
        py_off += 28

        # 角色属性
        stats = player.character.get_stats_dict()
        st_title = font_xs.render(f"[{char_info['title']}·{char_info['name']}] 属性:", True, char_info['color'])
        screen.blit(st_title, (panel_x + 10, panel_y + py_off))
        py_off += 20
        for k, v in stats.items():
            st = font_xs.render(f"  {k}: {v}", True, (180, 180, 190))
            screen.blit(st, (panel_x + 10, panel_y + py_off))
            py_off += 16
        py_off += 6

        # 操作说明
        divider = font_xs.render("─── 操作说明 ───", True, (100, 100, 120))
        screen.blit(divider, (panel_x + panel_w // 2 - divider.get_width() // 2, panel_y + py_off))
        py_off += 18

        helps = [
            ("WASD / 方向键", "移动"),
            ("鼠标左键", "散弹射击"),
            ("1-4", "切换Boss"),
            ("Q / E", "切换角色"),
            ("N", "下一级Boss"),
            ("R", "重置"),
            ("H", "恢复满血"),
            ("P", "暂停"),
            ("TAB", "toggle面板"),
        ]
        for key, desc in helps:
            kt = font_xs.render(key, True, CYAN)
            dt_txt = font_xs.render(f"  {desc}", True, (160, 160, 170))
            screen.blit(kt, (panel_x + 10, panel_y + py_off))
            screen.blit(dt_txt, (panel_x + 10 + kt.get_width(), panel_y + py_off))
            py_off += 15

    # ---- 角色选择提示 (底部) ----
    bottom_bar = pygame.Surface((WIDTH, 40), pygame.SRCALPHA)
    pygame.draw.rect(bottom_bar, (0, 0, 0, 120), (0, 0, WIDTH, 40))
    screen.blit(bottom_bar, (0, HEIGHT - 40))

    # 角色小图标
    n_chars = characters.get_character_count()
    icon_spacing = 80
    icons_start_x = WIDTH // 2 - (n_chars * icon_spacing) // 2

    for i in range(n_chars):
        ci = characters.get_character_info(i)
        ix = icons_start_x + i * icon_spacing + icon_spacing // 2
        iy = HEIGHT - 20
        # 选中高亮
        if i == player.char_index:
            hs = pygame.Surface((60, 30), pygame.SRCALPHA)
            pygame.draw.rect(hs, (*ci['color'], 40), (0, 0, 60, 30), border_radius=5)
            pygame.draw.rect(hs, (*ci['color'], 180), (0, 0, 60, 30), 2, border_radius=5)
            screen.blit(hs, (ix - 30, iy - 15))
        # 小圆点
        pygame.draw.circle(screen, ci['color'], (ix - 15, iy), 6)
        # 名称
        nt = font_xs.render(ci['name'], True, WHITE if i == player.char_index else (120, 120, 130))
        screen.blit(nt, (ix - 8, iy - 8))

    pygame.display.flip()

pygame.quit()
sys.exit()
