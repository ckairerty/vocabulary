# English:
# You may use, study, and modify this software for personal or educational purposes.
# You may not sell, redistribute commercially, or claim this work as your own without my permission.
# Creator: Nguyen Tuan Kiet
# This is a source code
# Vietnamese: 
# Bạn có thể sử dụng, nghiên cứu và chỉnh sửa phần mềm này cho mục đích cá nhân hoặc giáo dục.
# Bạn không được bán, phân phối thương mại hoặc tuyên bố tác phẩm này là của riêng bạn mà không có sự cho phép của tôi.
# Tác giả: Nguyễn Tuấn Kiệt
# Đây là mã nguồn

name_sha512_hash = "2e202dae8d3daa37d6036dc4066ec3dfbfde03519763f621bf4661e6b38687f6344d680d72e52c5566264188f76e19bc719cc8c5ffdb836f088c94ff49d20bb1"

import pygame
import random
from collections import defaultdict
from data import vocab
pygame.init()
# --- WINDOW ---
WIDTH, HEIGHT = 1200, 750
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Vocab Quiz")
font = pygame.font.SysFont("Segoe UI", 26)
big_font = pygame.font.SysFont("Segoe UI", 42)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 150, 0)
RED = (200, 0, 0)
BLUE = (0, 100, 200)
# --- FEEDBACK ---
messages_correct = ["Nice!", "Clean!", "W!", "Perfect!", "Good!"]
messages_wrong = ["Nah", "Try again", "Close one", "Miss", "L"]
# --- NORMALIZE ---
def normalize(text):
    return " ".join(text.lower().split())
# --- GROUP DUPLICATES ---
grouped = defaultdict(list)
for vi, en in vocab:
    grouped[vi].append(en)
quiz_data = list(grouped.items())
random.shuffle(quiz_data)
# --- STATE ---
index = 0
user_answers = []
current_input = ""
message = ""
color = BLACK
wrong = []
mode = "input"
choices = []
message_timer = 0
MESSAGE_DURATION = 1500
message_y = 420
streak = 0
progress = 0
target_progress = 0
def generate_choices(correct_answers):
    all_answers = [en for _, answers in quiz_data for en in answers]
    pool = [a for a in all_answers if a not in correct_answers]
    needed = max(0, 4 - len(correct_answers))
    wrong_choices = random.sample(pool, min(needed, len(pool)))
    options = wrong_choices + correct_answers
    random.shuffle(options)
    return options
def load_question():
    global choices
    if index < len(quiz_data):
        _, answers = quiz_data[index]
        choices = generate_choices(answers)
load_question()
def draw():
    global message, progress
    screen.fill(WHITE)
    if index >= len(quiz_data):
        progress = 1
    # --- PROGRESS BAR ---
    bar_x, bar_y = 50, 20
    bar_width, bar_height = 650, 15
    pygame.draw.rect(
        screen,
        (220, 220, 220),
        (bar_x, bar_y, bar_width, bar_height)
    )
    fill_width = int(bar_width * progress)
    pygame.draw.rect(
        screen,
        GREEN,
        (bar_x, bar_y, fill_width, bar_height)
    )
    pygame.draw.rect(
        screen,
        BLACK,
        (bar_x, bar_y, bar_width, bar_height),
        2
    )
    percent = int(progress * 100)
    percent_text = font.render(f"{percent}%", True, BLACK)
    screen.blit(percent_text, (bar_x + bar_width + 10, bar_y - 5))
    # --- STREAK ---
    streak_text = font.render(f"Streak: {streak}", True, GREEN)
    screen.blit(streak_text, (WIDTH - 150, 50))
    if index < len(quiz_data):
        vi, answers = quiz_data[index]
        screen.blit(big_font.render(vi, True, BLACK), (50, 80))
        mode_text = font.render(
            "Mode: INPUT (Ctrl+I) / CHOICE (Ctrl+C)",
            True,
            BLUE
        )
        screen.blit(mode_text, (50, 140))
        if mode == "input":
            screen.blit(
                font.render("Your answer:", True, BLACK),
                (50, 190)
            )
            screen.blit(
                font.render(current_input, True, BLACK),
                (50, 220)
            )
            progress_text = font.render(
                f"{len(user_answers)}/{len(answers)} answers",
                True,
                BLACK
            )
            screen.blit(progress_text, (50, 260))
        else:
            for i, choice in enumerate(choices):
                txt = font.render(
                    f"{i+1}. {choice}",
                    True,
                    BLACK
                )
                screen.blit(txt, (50, 190 + i * 40))
    else:
        done_text = big_font.render(
            "Quiz Done!",
            True,
            GREEN
        )
        screen.blit(done_text, (250, 150))
        mistakes_text = font.render(
            f"Mistakes: {len(wrong)}",
            True,
            RED if wrong else GREEN
        )
        screen.blit(mistakes_text, (250, 220))
        if wrong:
            retry_text = font.render(
                "Press R to retry wrong answers",
                True,
                BLACK
            )
            screen.blit(retry_text, (180, 280))
        else:
            perfect_text = font.render(
                "Perfect!",
                True,
                GREEN
            )
            screen.blit(perfect_text, (280, 280))
    # --- MESSAGE ---
    if message:
        elapsed = pygame.time.get_ticks() - message_timer
        if elapsed < MESSAGE_DURATION:
            t = elapsed / MESSAGE_DURATION
            alpha = int(255 * (1 - t))
            y_offset = int(30 * t)
            y = message_y - y_offset
            msg_surface = font.render(message, True, color)
            msg_surface.set_alpha(alpha)
            screen.blit(msg_surface, (50, y))
        else:
            message = ""
    pygame.display.update()
clock = pygame.time.Clock()
running = True
while running:
    clock.tick(60)
    progress += (target_progress - progress) * 0.1
    if abs(progress - target_progress) < 0.001:
        progress = target_progress
    draw()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            # --- SWITCH MODE ---
            if mods & pygame.KMOD_CTRL:
                if event.key == pygame.K_c:
                    mode = "choice"
                elif event.key == pygame.K_i:
                    mode = "input"
                continue
            # --- FINISHED ---
            if index >= len(quiz_data):
                if event.key == pygame.K_r and wrong:
                    quiz_data = wrong[:]
                    random.shuffle(quiz_data)
                    wrong.clear()
                    index = 0
                    streak = 0
                    progress = 0
                    target_progress = 0
                    user_answers = []
                    load_question()
                continue
            vi, answers = quiz_data[index]
            correct_set = {
                normalize(a)
                for a in answers
            }
            # --- INPUT MODE ---
            if mode == "input":
                if event.key == pygame.K_RETURN:
                    ans = normalize(current_input)
                    if not ans:
                        feedback = random.choice(messages_wrong)
                        message = f"{feedback}! {', '.join(answers)}"
                        color = RED
                        if (vi, answers) not in wrong:
                            wrong.append((vi, answers))
                        streak = 0
                    else:
                        if ans in correct_set and ans not in user_answers:
                            user_answers.append(ans)
                            # still more answers needed
                            if len(user_answers) < len(correct_set):
                                feedback = random.choice(messages_correct)

                                message = (
                                    f"{feedback} "
                                    f"({len(user_answers)}/{len(correct_set)})"
                                )
                                color = GREEN
                                current_input = ""
                                message_timer = pygame.time.get_ticks()
                                continue
                            # finished all answers
                            streak += 1
                            feedback = random.choice(messages_correct)
                            if streak >= 2:
                                message = f"{feedback} x{streak}"
                            else:
                                message = feedback
                            color = GREEN
                        else:
                            feedback = random.choice(messages_wrong)
                            message = f"{feedback}! {', '.join(answers)}"
                            color = RED
                            if (vi, answers) not in wrong:
                                wrong.append((vi, answers))
                            streak = 0
                    message_timer = pygame.time.get_ticks()
                    index += 1
                    target_progress = index / len(quiz_data)
                    user_answers = []
                    current_input = ""
                    load_question()
                elif event.key == pygame.K_BACKSPACE:
                    current_input = current_input[:-1]
                else:
                    current_input += event.unicode
            # --- CHOICE MODE ---
            elif mode == "choice":
                if event.unicode.isdigit():
                    i = int(event.unicode) - 1
                    if 0 <= i < len(choices):
                        selected = normalize(choices[i])
                        if selected in correct_set:
                            streak += 1
                            feedback = random.choice(messages_correct)
                            if streak >= 2:
                                message = f"{feedback} x{streak}"
                            else:
                                message = feedback
                            color = GREEN
                        else:
                            feedback = random.choice(messages_wrong)
                            message = (
                                f"{feedback}! "
                                f"{', '.join(answers)}"
                            )
                            color = RED
                            if (vi, answers) not in wrong:
                                wrong.append((vi, answers))
                            streak = 0
                        message_timer = pygame.time.get_ticks()
                        index += 1
                        target_progress = index / len(quiz_data)
                        load_question()
pygame.quit()
