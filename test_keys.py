"""快速测试Q/E按键和角色切换"""
import pygame
import sys
sys.path.insert(0, r"c:\N-20W1PF404RCA-Data\hencui\Desktop\割草")
import characters

pygame.init()
screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("按键测试 - 按Q/E切换")
clock = pygame.time.Clock()
font = pygame.font.Font('C:/Windows/Fonts/msyh.ttc', 24)

char_index = 0
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_q:
                char_index = (char_index - 1) % characters.get_character_count()
                print(f"Q pressed -> char_index = {char_index}")
            elif event.key == pygame.K_e:
                char_index = (char_index + 1) % characters.get_character_count()
                print(f"E pressed -> char_index = {char_index}")
    
    screen.fill((20, 20, 30))
    info = characters.get_character_info(char_index)
    text = font.render(f"{info['title']} · {info['name']}", True, info['color'])
    screen.blit(text, (200 - text.get_width()//2, 130))
    hint = font.render("按 Q / E 切换角色", True, (150, 150, 150))
    screen.blit(hint, (200 - hint.get_width()//2, 200))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
