# Pygame 6010 — Práctica 4 (Survival/Dodger + Dibujo)
# Mecánica central: EVITAR CHOCAR. Sobrevive 60 s. Una colisión con enemigo = Game Over.
# Añadido: CAPA DE DIBUJO con primitivas (línea, rect, circle, polygon, arc) y paletas.
# Teclas: [ENTER] empezar · [R] reiniciar · [G] grid · [H] mostrar/ocultar dibujo · [K] cambiar paleta · [ESC] salir

import pygame, sys, random, math

pygame.init()
WIDTH, HEIGHT = 960, 540
WINDOW = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("P4 — Survival Dodger + Dibujo")
CLOCK = pygame.time.Clock()
FPS = 60

def clamp(v, a, b): return max(a, min(v, b))
def make_text(txt, size=26, color=(235,235,245)):
    return pygame.font.SysFont(None, size).render(txt, True, color)

# ---------- Paletas para capa de dibujo ----------
PALETTES = [
    # (fondo_grid, lineas, acento1, acento2, acento3)
    ((22,24,34), (60, 80,120), (255,220,80), (140,200,255), (180,255,190)),
    ((26,22,34), (120, 70,120), (255,160,70), (255,100,140), (190,255,120)),
    ((20,26,24), (70,120,90), (180,220,255), (255,200,120), (255,120,160)),
]
palette_idx = 0

# ---------- Config por triplas ----------
COIN_TYPES = [(22,(255,220,80),10),(26,(170,240,170),20),(16,(180,220,255),5)]
ENEMY_TYPES = [(18,(240,120,90),140),(22,(220,80,120),110),(14,(255,160,70),170)]
SURVIVE_TIME = 60.0

class Particle(pygame.sprite.Sprite):
    def __init__(self, pos, vel, life, size, color):
        super().__init__()
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (size//2, size//2), size//2)
        self.rect = self.image.get_rect(center=pos)
        self.vel = pygame.Vector2(vel); self.life = life; self.max_life = life
    def update(self, dt):
        self.rect.x += self.vel.x * dt; self.rect.y += self.vel.y * dt
        self.life -= dt
        self.image.set_alpha(clamp(int(255*(self.life/self.max_life)),0,255))
        if self.life <= 0: self.kill()

class ScreenFlash:
    def __init__(self): self.alpha=0; self.color=(255,50,50)
    def trigger(self, s=160): self.alpha = clamp(self.alpha + s, 0, 255)
    def draw(self, surf):
        if self.alpha<=0: return
        o=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); o.fill((*self.color,int(self.alpha)))
        surf.blit(o,(0,0)); self.alpha=max(0,self.alpha-10)

class ScreenShake:
    def __init__(self): self.timer=0.0; self.intensity=0.0
    def shake(self,i=8,d=0.25): self.intensity=max(self.intensity,i); self.timer=max(self.timer,d)
    def get_offset(self,dt):
        if self.timer<=0: return 0,0
        self.timer=max(0,self.timer-dt)
        return (int(random.uniform(-1,1)*self.intensity*self.timer),
                int(random.uniform(-1,1)*self.intensity*self.timer))

class Player(pygame.sprite.Sprite):
    def __init__(self,pos):
        super().__init__()
        self.base_image=pygame.Surface((38,38),pygame.SRCALPHA)
        pygame.draw.rect(self.base_image,(80,200,255),(0,0,38,38),border_radius=6)
        pygame.draw.rect(self.base_image,(255,255,255),(8,8,22,6),border_radius=3)
        self.image=self.base_image.copy(); self.rect=self.image.get_rect(center=pos)
        self.vel=pygame.Vector2(0,0); self.accel=900; self.friction=0.85; self.max_speed=340
        self.grace_time=1.5
    def handle_input(self,dt):
        keys=pygame.key.get_pressed()
        ax=(keys[pygame.K_d]-keys[pygame.K_a])*self.accel
        ay=(keys[pygame.K_s]-keys[pygame.K_w])*self.accel
        self.vel.x += ax*dt; self.vel.y += ay*dt
        if self.vel.length()>self.max_speed: self.vel.scale_to_length(self.max_speed)
        self.vel *= self.friction
    def update(self,dt):
        self.handle_input(dt)
        self.rect.x += int(self.vel.x*dt); self.rect.y += int(self.vel.y*dt)
        self.rect.clamp_ip(pygame.Rect(0,0,WIDTH,HEIGHT))
        if self.grace_time>0: self.grace_time -= dt

class Enemy(pygame.sprite.Sprite):
    def __init__(self,pos,speed_scale=1.0):
        super().__init__()
        r,color,v=random.choice(ENEMY_TYPES)
        self.image=pygame.Surface((r*2,r*2),pygame.SRCALPHA)
        pygame.draw.circle(self.image,color,(r,r),r)
        pygame.draw.circle(self.image,(20,20,20),(r-4,r-6),3)
        pygame.draw.circle(self.image,(20,20,20),(r+4,r-6),3)
        self.rect=self.image.get_rect(center=pos)
        self.speed=int(v*speed_scale)
        d=pygame.Vector2(random.choice([-1,1]),random.choice([-1,1])); self.dir=d.normalize()
    def update(self,dt):
        self.rect.x += int(self.dir.x*self.speed*dt); self.rect.y += int(self.dir.y*self.speed*dt)
        if self.rect.left<=0 or self.rect.right>=WIDTH: self.dir.x*=-1
        if self.rect.top<=0 or self.rect.bottom>=HEIGHT: self.dir.y*=-1

class Coin(pygame.sprite.Sprite):
    def __init__(self,pos):
        super().__init__()
        d,color,pts=random.choice(COIN_TYPES); self.pts=pts
        self.base=pygame.Surface((d,d),pygame.SRCALPHA)
        pygame.draw.circle(self.base,color,(d//2,d//2),d//2)
        pygame.draw.circle(self.base,(255,255,180),(d//2,d//2),max(2,d//3))
        self.image=self.base.copy(); self.rect=self.image.get_rect(center=pos); self.t=0.0; self.d=d
    def update(self,dt):
        self.t += dt; scale = 1.0 + 0.1*math.sin(self.t*6.0)
        size=int(self.d*scale); self.image=pygame.transform.smoothscale(self.base,(size,size))
        self.rect=self.image.get_rect(center=self.rect.center)

MENU, PLAYING, GAMEOVER, WIN = range(4)

class Game:
    def __init__(self):
        self.state=MENU; self.flash=ScreenFlash(); self.shake=ScreenShake()
        self.show_grid=True; self.show_art=True; self.reset()
    def reset(self):
        self.player=Player((WIDTH//2,HEIGHT//2))
        self.enemies=pygame.sprite.Group(); self.coins=pygame.sprite.Group()
        self.all_sprites=pygame.sprite.Group(self.player); self.particles=pygame.sprite.Group()
        self.time_left=SURVIVE_TIME; self.wave_timer=0.0; self.score=0; self.difficulty=1
        for _ in range(5): self.spawn_enemy()
        for _ in range(5): self.spawn_coin()
    def spawn_enemy(self):
        margin=40; pos=(random.randint(margin,WIDTH-margin),random.randint(margin,HEIGHT-margin))
        e=Enemy(pos, speed_scale=1.0+(self.difficulty-1)*0.12); self.enemies.add(e); self.all_sprites.add(e)
    def spawn_coin(self):
        margin=20; pos=(random.randint(margin,WIDTH-margin),random.randint(margin,HEIGHT-margin))
        c=Coin(pos); self.coins.add(c); self.all_sprites.add(c)
    def burst(self,pos,color):
        for _ in range(18):
            ang=random.uniform(0,math.tau); spd=random.uniform(60,220)
            vel=(math.cos(ang)*spd, math.sin(ang)*spd); life=random.uniform(0.3,0.9); size=random.randint(3,6)
            self.particles.add(Particle(pos,vel,life,size,color))
    def update_playing(self,dt):
        self.time_left=max(0.0,self.time_left-dt); self.wave_timer+=dt
        if self.wave_timer>=7.0:
            self.wave_timer=0.0; self.difficulty+=1
            for _ in range(2): self.spawn_enemy()
            for _ in range(2): self.spawn_coin()
        self.all_sprites.update(dt); self.particles.update(dt)
        for coin in pygame.sprite.spritecollide(self.player,self.coins,True):
            self.score += coin.pts; self.burst(self.player.rect.center,(255,220,80))
        if self.player.grace_time<=0 and pygame.sprite.spritecollide(self.player,self.enemies,False):
            self.state=GAMEOVER; self.flash.trigger(220); self.shake.shake(10,0.35)
            self.burst(self.player.rect.center,(255,60,60))
        if self.time_left<=0: self.state=WIN
    # ---------- CAPA DE DIBUJO ----------
    # RETO DIBUJO: añade aquí más figuras (rects, lines, circles, polygons, arcs) usando pygame.draw.*
    def draw_art_layer(self, surf):
        grid, line, a1, a2, a3 = PALETTES[palette_idx]
        # líneas cruzadas
        pygame.draw.line(surf, line, (0,0), (WIDTH,HEIGHT), 2)
        pygame.draw.line(surf, line, (WIDTH,0), (0,HEIGHT), 2)
        # rectángulo marco
        pygame.draw.rect(surf, a2, (40,30, WIDTH-80, HEIGHT-60), 2, border_radius=12)
        # círculos decorativos
        pygame.draw.circle(surf, a1, (120,100), 18, 2)
        pygame.draw.circle(surf, a3, (WIDTH-120,HEIGHT-100), 22, 2)
        # polígono (flecha)
        pts=[(WIDTH//2-30, 90), (WIDTH//2+30, 90), (WIDTH//2, 130)]
        pygame.draw.polygon(surf, a1, pts, 0); pygame.draw.polygon(surf, line, pts, 2)
        # arco superior
        rect=(WIDTH//2-60, 60, 120, 60)
        pygame.draw.arc(surf, a3, rect, math.pi, 2*math.pi, 2)
    # ---------- Fondo + HUD ----------
    def draw_background(self, surf, ox, oy):
        grid_col, *_ = PALETTES[palette_idx]
        surf.fill((14,16,24))
        if self.show_grid:
            for i in range(0, WIDTH, 32):
                pygame.draw.line(surf, grid_col, (i+ox,0), (i+ox,HEIGHT))
            for j in range(0, HEIGHT, 32):
                pygame.draw.line(surf, grid_col, (0,j+oy), (WIDTH,j+oy))
        if self.show_art:
            self.draw_art_layer(surf)
    def draw_hud(self, surf):
        surf.blit(make_text(f"Tiempo: {int(self.time_left)}s", 24), (10, 10))
        surf.blit(make_text(f"Puntos: {self.score}", 24), (10, 40))
        surf.blit(make_text("[H] Dibujo ON/OFF  [K] Cambiar paleta  [G] Grid", 18), (10, 70))
        if self.player.grace_time>0: surf.blit(make_text("Invulnerable...", 18,(180,220,255)), (10, 95))
    def run(self):
        global palette_idx
        state=MENU; running=True
        while running:
            dt=CLOCK.tick(FPS)/1000.0
            for e in pygame.event.get():
                if e.type==pygame.QUIT: running=False
                if e.type==pygame.KEYDOWN:
                    if e.key==pygame.K_ESCAPE: running=False
                    elif e.key==pygame.K_g: self.show_grid = not self.show_grid
                    elif e.key==pygame.K_h: self.show_art = not self.show_art
                    elif e.key==pygame.K_k: palette_idx = (palette_idx+1) % len(PALETTES)
                    elif state==MENU and e.key==pygame.K_RETURN: state=PLAYING; self.reset()
                    elif state in (GAMEOVER,WIN) and e.key==pygame.K_r: state=PLAYING; self.reset()
            if state==PLAYING: self.update_playing(dt)
            ox,oy = self.shake.get_offset(dt)
            self.draw_background(WINDOW, ox, oy)
            if state==MENU:
                t=make_text("SURVIVAL DODGER + DIBUJO", 48); WINDOW.blit(t,(WIDTH//2-t.get_width()//2,120))
                WINDOW.blit(make_text("Evita chocar 60 s. Monedas = bonus.", 26),(WIDTH//2-250, 210))
                WINDOW.blit(make_text("Primitivas: line/rect/circle/polygon/arc (revisa el código).", 22),(WIDTH//2-320, 245))
                WINDOW.blit(make_text("[ENTER] Comenzar   [H] Dibujo   [K] Paleta   [G] Grid   [ESC] Salir", 20),(WIDTH//2-320, 290))
            elif state==PLAYING:
                for spr in self.all_sprites: WINDOW.blit(spr.image, spr.rect.move(ox,oy))
                self.particles.draw(WINDOW); self.draw_hud(WINDOW)
            elif state==GAMEOVER:
                for spr in self.all_sprites: WINDOW.blit(spr.image, spr.rect.move(ox,oy))
                self.particles.draw(WINDOW); self.flash.draw(WINDOW)
                msg=make_text("GAME OVER — chocaste con un enemigo", 32)
                WINDOW.blit(msg,(WIDTH//2-msg.get_width()//2, HEIGHT//2-40))
                WINDOW.blit(make_text("[R] Reiniciar   [ESC] Salir", 24),(WIDTH//2-140, HEIGHT//2+10))
            elif state==WIN:
                WINDOW.blit(make_text("¡GANASTE! Sobreviviste 60 s", 38),(WIDTH//2-260, HEIGHT//2-30))
                WINDOW.blit(make_text(f"Puntuación final: {self.score}", 26),(WIDTH//2-150, HEIGHT//2+15))
                WINDOW.blit(make_text("[R] Reiniciar   [ESC] Salir", 24),(WIDTH//2-140, HEIGHT//2+50))
            self.flash.draw(WINDOW); pygame.display.flip()
        pygame.quit(); sys.exit()

if __name__ == "__main__":
    Game().run()