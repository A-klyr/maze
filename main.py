import pygame
import sys
import time
import random
import asyncio
import os

from maze_data import generate_maze, CELL_SIZE

# ==== DETECT WEB ====
IS_WEB = sys.platform == "emscripten"

# ==== KONFIGURASI ====
MAZE_WIDTH = 31
MAZE_HEIGHT = 31

# ==== INISIALISASI PYGAME ====
pygame.init()

# Mixer init dengan error handling
try:
    pygame.mixer.init()
    MIXER_AVAILABLE = True
except:
    MIXER_AVAILABLE = False
    print("⚠️ Mixer tidak tersedia")

# ==== SCREEN SETUP ====
SCREEN_WIDTH = MAZE_WIDTH * CELL_SIZE
SCREEN_HEIGHT = MAZE_HEIGHT * CELL_SIZE + 150
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Classic Maze Game - Jumpscare Edition")

# ==== WARNA ====
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED   = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)

# ==== FONT ====
font_small = pygame.font.SysFont(None, 24)
font_large = pygame.font.SysFont(None, 48)
font_huge = pygame.font.SysFont(None, 72)

# ==== GLOBAL ASSETS ====
assets_loaded = False
jumpscare_images = []
jumpscare_sounds = []
audio_context = None  # Store audio context reference

# ==== GAME STATE VARIABLES ====
MAZE_MAP = None
player_x = player_y = 0
finish_x = finish_y = 0
jumpscare_positions = set()
triggered_jumpscares = set()
start_time = None
game_started = False
final_time = 0
best_times = []
move_delay = 150
last_move_time = 0
game_won = False
jumpscare_active = False
jumpscare_start_time = 0
current_jumpscare_img = None
current_jumpscare_sound = None
audio_unlocked = False

# ==== ASYNC ASSET LOADING (PENTING UNTUK PYGBAG) ====
async def load_assets():
    """Load assets dengan async untuk Pygbag compatibility"""
    global assets_loaded, jumpscare_images, jumpscare_sounds
    
    print("🔄 Loading assets...")
    
    # PENTING: File harus ada di ROOT FOLDER untuk Pygbag
    image_files = [
        'kucing1.jpeg',
        'kucing2.jpeg',
        'kucing3.jpeg'
    ]
    
    sound_files = [
        'fuzzy-jumpscare-80560.wav',
        'jump-scare-sound-2-82831.wav',
        'five-nights-at-freddys-full-scream-sound_2.wav'
    ]
    
    try:
        # Load images
        for img_path in image_files:
            if IS_WEB:
                await asyncio.sleep(0.1)
            
            try:
                img = pygame.image.load(img_path)
                img = pygame.transform.scale(img, (SCREEN_WIDTH, MAZE_HEIGHT * CELL_SIZE))
                jumpscare_images.append(img)
                print(f"✅ Loaded image: {img_path}")
            except Exception as e:
                print(f"❌ Failed to load {img_path}: {e}")
        
        # Load sounds (untuk desktop dan web via Pygame mixer)
        if MIXER_AVAILABLE:
            for sound_path in sound_files:
                try:
                    snd = pygame.mixer.Sound(sound_path)
                    snd.set_volume(1.0)
                    jumpscare_sounds.append(snd)
                    print(f"✅ Loaded sound: {sound_path}")
                except Exception as e:
                    print(f"❌ Failed to load {sound_path}: {e}")
        
        if len(jumpscare_images) > 0:
            assets_loaded = True
            print(f"✅ Assets loaded! Images: {len(jumpscare_images)}, Sounds: {len(jumpscare_sounds)}")
        else:
            print("⚠️ No images loaded!")
            
    except Exception as e:
        print(f"⚠️ Asset loading error: {e}")
        assets_loaded = False

# ==== UNLOCK AUDIO FUNCTION (ASYNC) ====
async def unlock_audio():
    """Unlock audio context (required for Web)"""
    global audio_unlocked, jumpscare_sounds
    
    print("🚀 unlock_audio() called!")
    
    if audio_unlocked:
        print("⚠️ Audio already unlocked!")
        return
    
    try:
        if not MIXER_AVAILABLE:
            print("❌ Mixer not available!")
            return

        # Play test sound (silent/low volume) untuk trigger unlock
        # Di Pygbag, memainkan sound event sudah cukup untuk resume context
        if jumpscare_sounds:
            print("🔊 Playing test sound to unlock audio...")
            try:
                test_sound = jumpscare_sounds[0]
                test_sound.set_volume(0.1)
                test_sound.play()
                await asyncio.sleep(0.1)
                test_sound.stop()
                test_sound.set_volume(1.0) # Restore volume
                print("   ✅ Test sound played")
            except Exception as e:
                print(f"⚠️ Test sound failed: {e}")
        else:
            print("⚠️ No sounds loaded to play test sound")
        
        # Always set to True if we reached here, assuming context is resumed or will be
        audio_unlocked = True
        print(f"🎉 Audio unlocked! Loaded {len(jumpscare_sounds)} sounds")
        
    except Exception as e:
        print(f"💥 Audio unlock FAILED: {e}")
        import traceback
        traceback.print_exc()

# ==== LOAD BEST TIMES ====
def load_best_times():
    global best_times
    if IS_WEB:
        try:
            import js, json
            data = js.localStorage.getItem("maze_best")
            if data:
                best_times = json.loads(data)
                print(f"✅ Loaded {len(best_times)} best times from localStorage")
        except:
            pass
    else:
        try:
            with open('best_times.txt', 'r') as f:
                best_times = [float(x.strip()) for x in f.readlines()]
        except:
            pass
    
    best_times = best_times[:5]

# ==== SAVE BEST TIMES ====
def save_best_times():
    if IS_WEB:
        try:
            import js, json
            js.localStorage.setItem("maze_best", json.dumps(best_times))
            print("💾 Saved to localStorage")
        except:
            pass
    else:
        try:
            with open('best_times.txt', 'w') as f:
                f.write("\n".join([str(x) for x in best_times]))
        except:
            pass

# ==== INIT GAME STATE ====
def init_game_state():
    """Initialize/reset game state"""
    global MAZE_MAP, player_x, player_y, finish_x, finish_y
    global jumpscare_positions, triggered_jumpscares
    global start_time, game_started, final_time, game_won
    global jumpscare_active, jumpscare_start_time, last_move_time
    
    # Generate maze
    MAZE_MAP = generate_maze(MAZE_WIDTH, MAZE_HEIGHT)
    
    # Find start and end
    for r, row in enumerate(MAZE_MAP):
        for c, cell in enumerate(row):
            if cell == 'S':
                player_x, player_y = c, r
            elif cell == 'E':
                finish_x, finish_y = c, r
    
    # Setup jumpscares
    path_cells = [(c, r) for r, row in enumerate(MAZE_MAP) 
                  for c, cell in enumerate(row) if cell in ['0', 'S', 'E']]
    valid_cells = [(c, r) for c, r in path_cells 
                   if (c, r) not in [(player_x, player_y), (finish_x, finish_y)]]
    
    num_jumpscares = random.randint(7, 10)
    jumpscare_positions = set(random.sample(valid_cells, min(num_jumpscares, len(valid_cells))))
    triggered_jumpscares = set()
    
    # Reset game state
    start_time = None
    game_started = False
    final_time = 0
    game_won = False
    jumpscare_active = False
    jumpscare_start_time = 0
    last_move_time = 0
    
    print(f"🎮 Game initialized with {len(jumpscare_positions)} jumpscares")

# ==== MAIN GAME LOOP ====
async def main():
    global player_x, player_y, jumpscare_active, jumpscare_start_time
    global start_time, game_started, game_won, final_time
    global last_move_time, best_times
    global current_jumpscare_img, current_jumpscare_sound
    global audio_unlocked
    
    # Load assets FIRST (async)
    await load_assets()
    
    # Load best times
    load_best_times()
    
    # Initialize game
    init_game_state()
    
    clock = pygame.time.Clock()
    running = True
    frame_count = 0
    
    while running:
        clock.tick(60)
        current_time = pygame.time.get_ticks()
        frame_count += 1
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN:
                print(f"⌨️ Key pressed: {event.key}")
                # Unlock audio on first keypress
                if not audio_unlocked:
                    print("🔄 Attempting to unlock audio via keyboard...")
                    await unlock_audio()
                    
                    # Force play after unlock
                    if audio_unlocked and len(jumpscare_sounds) > 0:
                        print("🔊 Force playing sound after keyboard unlock...")
                        try:
                            test = jumpscare_sounds[0]
                            pygame.mixer.unpause()
                            test.set_volume(0.5)
                            channel = test.play()
                            print(f"✅ Pygame keyboard test: {channel}!")
                        except Exception as e:
                            print(f"❌ Keyboard test failed: {e}")
                else:
                    print("✅ Audio already unlocked")
                
                if event.key == pygame.K_r and game_won:
                    init_game_state()
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                print(f"🖱️ Mouse clicked at: {event.pos}")
                # Unlock audio on first click
                if not audio_unlocked:
                    print("🔄 Attempting to unlock audio via mouse...")
                    await unlock_audio()
                    
                    # TEST: Force play sound setelah unlock
                    if audio_unlocked and len(jumpscare_sounds) > 0:
                        print("🔊 Testing sound after mouse unlock...")
                        try:
                            test = jumpscare_sounds[0]
                            pygame.mixer.unpause()
                            test.set_volume(0.5)
                            channel = test.play()
                            if channel:
                                print(f"✅ Pygame test on channel {channel}!")
                            else:
                                print("❌ No channel for test!")
                        except Exception as e:
                            print(f"❌ Manual test failed: {e}")
                else:
                    print("✅ Audio already unlocked")
        
        # ============ MOVEMENT ============
        if not jumpscare_active and not game_won:
            keys = pygame.key.get_pressed()
            
            if current_time - last_move_time > move_delay:
                new_x, new_y = player_x, player_y
                moved = False
                
                if keys[pygame.K_UP]:
                    new_y -= 1
                    moved = True
                elif keys[pygame.K_DOWN]:
                    new_y += 1
                    moved = True
                elif keys[pygame.K_LEFT]:
                    new_x -= 1
                    moved = True
                elif keys[pygame.K_RIGHT]:
                    new_x += 1
                    moved = True
                
                if moved:
                    if not game_started:
                        start_time = time.time()
                        game_started = True
                    
                    if 0 <= new_x < MAZE_WIDTH and 0 <= new_y < MAZE_HEIGHT:
                        if MAZE_MAP[new_y][new_x] != '1':
                            player_x, player_y = new_x, new_y
                            last_move_time = current_time
        
        # ============ CHECK JUMPSCARE ============
        if assets_loaded and len(jumpscare_images) > 0:
            if (player_x, player_y) in jumpscare_positions:
                if (player_x, player_y) not in triggered_jumpscares and not jumpscare_active:
                    jumpscare_active = True
                    jumpscare_start_time = current_time
                    triggered_jumpscares.add((player_x, player_y))
                    
                    current_jumpscare_img = random.choice(jumpscare_images)
                    print(f"👻 JUMPSCARE at ({player_x}, {player_y})!")
                    
                    # Play sound HANYA jika audio sudah unlocked
                    if audio_unlocked and len(jumpscare_sounds) > 0:
                        try:
                            current_jumpscare_sound = random.choice(jumpscare_sounds)
                            print(f"🔊 Playing jumpscare sound...")
                            
                            # Pygame Sound
                            pygame.mixer.unpause()
                            current_jumpscare_sound.set_volume(1.0)
                            channel = current_jumpscare_sound.play()
                            
                            if channel:
                                print(f"✅ Pygame jumpscare on channel: {channel}")
                            else:
                                print("❌ No channel available!")
                                pygame.mixer.stop()
                                await asyncio.sleep(0.05)
                                channel = current_jumpscare_sound.play()
                                print(f"🔄 Retry: {channel}")
                                
                        except Exception as e:
                            print(f"⚠️ Sound play failed: {e}")
                            import traceback
                            traceback.print_exc()
                    elif not audio_unlocked:
                        print("⚠️ Audio not unlocked - click screen first!")
                    else:
                        print(f"⚠️ Cannot play: sounds={len(jumpscare_sounds)}")
        
        # Handle jumpscare duration
        if jumpscare_active and current_time - jumpscare_start_time > 1500:
            jumpscare_active = False
        
        # ============ DRAW ============
        screen.fill(WHITE)
        
        if jumpscare_active and current_jumpscare_img:
            screen.blit(current_jumpscare_img, (0, 0))
        else:
            # Draw maze
            for r, row in enumerate(MAZE_MAP):
                for c, cell in enumerate(row):
                    rect = pygame.Rect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    if cell == '1':
                        pygame.draw.rect(screen, BLACK, rect)
                    elif cell == 'E':
                        pygame.draw.rect(screen, GREEN, rect)
            
            # Draw player
            player_rect = pygame.Rect(player_x * CELL_SIZE, player_y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, RED, player_rect)
            
            # UI panel
            ui_y = MAZE_HEIGHT * CELL_SIZE
            pygame.draw.rect(screen, GRAY, (0, ui_y, SCREEN_WIDTH, 150))
            
            # Timer
            if game_started and not game_won:
                elapsed = time.time() - start_time
                timer_text = font_small.render(f"Time: {elapsed:.2f}s", True, WHITE)
                screen.blit(timer_text, (10, ui_y + 10))
            
            # Best time
            if best_times:
                best_text = font_small.render(f"Best: {best_times[0]:.2f}s", True, YELLOW)
                screen.blit(best_text, (SCREEN_WIDTH - 150, ui_y + 10))
            
            # Audio warning indicator (blink) - LEBIH BESAR
            if not audio_unlocked and MIXER_AVAILABLE:
                if (current_time // 500) % 2 == 0:  # Blink every 500ms
                    # Background merah untuk lebih kelihatan
                    warn_bg = pygame.Surface((SCREEN_WIDTH - 20, 80))
                    warn_bg.fill(RED)
                    warn_bg.set_alpha(150)
                    screen.blit(warn_bg, (10, ui_y + 35))
                    
                    audio_warn = font_large.render("CLICK SCREEN TO ENABLE SOUND!", True, WHITE)
                    audio_rect = audio_warn.get_rect(center=(SCREEN_WIDTH // 2, ui_y + 75))
                    screen.blit(audio_warn, audio_rect)
            
            # Check win
            if player_x == finish_x and player_y == finish_y and not game_won:
                game_won = True
                final_time = time.time() - start_time if game_started else 0
                
                if final_time > 0:
                    best_times.append(final_time)
                    best_times.sort()
                    best_times = best_times[:5]
                    save_best_times()
                
                print(f"🎉 Win! Time: {final_time:.2f}s")
            
            # Win screen
            if game_won:
                overlay = pygame.Surface((SCREEN_WIDTH, MAZE_HEIGHT * CELL_SIZE))
                overlay.set_alpha(200)
                overlay.fill(BLACK)
                screen.blit(overlay, (0, 0))
                
                win_text = font_huge.render("YOU WIN!", True, GREEN)
                win_rect = win_text.get_rect(center=(SCREEN_WIDTH // 2, 60))
                screen.blit(win_text, win_rect)
                
                time_text = font_large.render(f"Time: {final_time:.2f}s", True, WHITE)
                time_rect = time_text.get_rect(center=(SCREEN_WIDTH // 2, 130))
                screen.blit(time_text, time_rect)
                
                restart_text = font_large.render("Press R to Restart", True, WHITE)
                restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, ui_y + 50))
                screen.blit(restart_text, restart_rect)

            # ==== DEBUG INFO ====
            debug_y = 10
            debug_infos = [
                f"Mixer: {MIXER_AVAILABLE}",
                f"Assets: {assets_loaded}",
                f"Sounds: {len(jumpscare_sounds)}",
                f"Unlocked: {audio_unlocked}",
                f"Web: {IS_WEB}"
            ]
            for info in debug_infos:
                text = font_small.render(info, True, (0, 0, 255))
                screen.blit(text, (10, debug_y))
                debug_y += 25
        
        pygame.display.flip()
        await asyncio.sleep(0)  # CRITICAL for Pygbag
    
    pygame.quit()

# ==== RUN ====
asyncio.run(main())