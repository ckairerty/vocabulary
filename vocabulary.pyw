# English:
# You may use, study, and modify this software for personal or educational purposes.
# You may not sell, redistribute commercially, or claim this work as your own without my permission.
# Creator: Nguyen Tuan Kiet
# This is a source code

name_sha512_hash = "2e202dae8d3daa37d6036dc4066ec3dfbfde03519763f621bf4661e6b38687f6344d680d72e52c5566264188f76e19bc719cc8c5ffdb836f088c94ff49d20bb1"

# Changelog:
# Version 1.0: Initial release (still basic text-based, no GUI)
# Version 1.1.0: Added click R to retry wrong answers, added randomized list
# Version 1.1.1: Fixed bug in 1.1.0 where retrying wrong answers is a "stable" sort from the original list
# Version 2.0: Added GUI, streak counter and progress bar
# Version 2.1: Added Ctrl+C => choice mode, Ctrl+I => input mode
# Version 2.2: Added strict diff panel for mistakes
# Version 3.0: Added mistake history (last 5), retry statistics, and best streak tracking
# Version 3.1: Added accuracy display, Ctrl+R full session reset (keeps saved session's stats),
#              replaced the last-5 global mistake history with per-question mistake
#              history (shows a word's own past wrong attempts when you miss it again),
#              and a Score/completion summary on the done screen

import pygame
import random
from difflib import SequenceMatcher
from collections import defaultdict
from data import vocab
pygame.init()
# --- WINDOW ---
WIDTH, HEIGHT = 1200, 750
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Vocab Quiz")
font = pygame.font.SysFont("Segoe UI", 26)
small_font = pygame.font.SysFont("Segoe UI", 20)
big_font = pygame.font.SysFont("Segoe UI", 42)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 150, 0)
RED = (200, 0, 0)
BLUE = (0, 100, 200)
GRAY = (120, 120, 120)
LIGHT_RED = (255, 205, 205)
LIGHT_GREEN = (200, 240, 200)
# --- FEEDBACK ---
messages_correct = ["Nice!", "Clean!", "W!", "Perfect!", "Good!"]
messages_wrong = ["Nah", "Try again", "Close one", "Miss", "L"]
# --- NORMALIZE ---
def normalize(text):
    return " ".join(text.lower().split())
# --- STRICT DIFF ---
def pick_closest(typed, candidates):
    """Return the candidate answer most similar to what was typed."""
    return max(
        candidates,
        key=lambda c: SequenceMatcher(None, typed, normalize(c), autojunk=False).ratio()
    )
def build_diff(typed, correct):
    """
    Character-level diff.
    Returns two segment lists of (text, kind):
      typed_segs   -> what you typed; 'bad' = extra/wrong letters (red)
      correct_segs -> the right answer; 'miss' = letters you missed (green)
    kind 'eq' = matching characters.
    """
    sm = SequenceMatcher(None, typed, correct, autojunk=False)
    typed_segs, correct_segs = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            typed_segs.append((typed[i1:i2], "eq"))
            correct_segs.append((correct[j1:j2], "eq"))
        else:
            if i2 > i1:
                typed_segs.append((typed[i1:i2], "bad"))
            if j2 > j1:
                correct_segs.append((correct[j1:j2], "miss"))
    return typed_segs, correct_segs
def make_diff(typed_raw, answers, already_given):
    typed = normalize(typed_raw)
    remaining = [a for a in answers if normalize(a) not in already_given] or answers
    target = normalize(pick_closest(typed, remaining))
    return build_diff(typed, target)
def draw_diff_line(label, segments, x, y):
    screen.blit(font.render(label, True, BLACK), (x, y))
    cx = x + 120
    for text, kind in segments:
        if not text:
            continue
        if kind == "bad":
            fg, bg = RED, LIGHT_RED
        elif kind == "miss":
            fg, bg = GREEN, LIGHT_GREEN
        else:
            fg, bg = BLACK, None
        surf = font.render(text, True, fg)
        if bg:
            pygame.draw.rect(screen, bg, (cx, y, surf.get_width(), surf.get_height()))
        screen.blit(surf, (cx, y))
        cx += surf.get_width()
# --- PER-QUESTION MISTAKE HISTORY ---
# Keyed by the word being asked (vi), so a word "remembers" your past wrong
# attempts on it specifically, instead of a flat recent-5 feed across all words.
question_mistake_log = defaultdict(list)  # vi -> list of (typed, correct) tuples
def record_mistake(vi, typed_raw, answers, already_given):
    """Log this wrong attempt under its own question and return the attempts
    that were already on file for this question BEFORE this one (for display)."""
    typed = normalize(typed_raw)
    remaining = [a for a in answers if normalize(a) not in already_given] or answers
    closest = normalize(pick_closest(typed, remaining)) if typed else normalize(remaining[0])
    prior = question_mistake_log[vi][:]
    question_mistake_log[vi].append((typed if typed else "(empty)", closest))
    return prior
def draw_question_history(vi, x, y):
    screen.blit(font.render(f'Past mistakes on "{vi}":', True, BLUE), (x, y))
    row_y = y + 35
    for typed, correct in reversed(last_question_history):
        line = f"{typed} \u2192 {correct}"
        screen.blit(small_font.render(line, True, BLACK), (x, row_y))
        row_y += 26
# --- GROUP DUPLICATES ---
grouped = defaultdict(list)
for vi, en in vocab:
    grouped[vi].append(en)
original_quiz_data = list(grouped.items())
quiz_data = list(original_quiz_data)
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
last_diff = None  # (typed_segments, correct_segments) of the last mistake
last_question_history = []  # prior wrong attempts on the word just missed
# --- SAVED / LIFETIME STATISTICS (survive Ctrl+R) ---
best_streak = 0
total_attempts = 0
total_correct = 0
# --- RETRY STATS (per round, reset on Ctrl+R) ---
is_retry_round = False
retry_total = 0
retry_stats_ready = False  # becomes True once the current round (initial or retry) is finished
def accuracy_percent():
    if total_attempts == 0:
        return 100
    return round(100 * total_correct / total_attempts)
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
def reset_session():
    """Ctrl+R: restart the entire quiz from scratch. Keeps best_streak,
    total_attempts/total_correct (accuracy) and per-question mistake history."""
    global quiz_data, index, user_answers, current_input, message, wrong
    global streak, progress, target_progress, last_diff, last_question_history
    global is_retry_round, retry_total, retry_stats_ready
    quiz_data = list(original_quiz_data)
    random.shuffle(quiz_data)
    index = 0
    user_answers = []
    current_input = ""
    message = ""
    wrong = []
    streak = 0
    progress = 0
    target_progress = 0
    last_diff = None
    last_question_history = []
    is_retry_round = False
    retry_total = 0
    retry_stats_ready = False
    load_question()
def draw():
    global message, progress, retry_stats_ready
    screen.fill(WHITE)
    if index >= len(quiz_data):
        progress = 1
        retry_stats_ready = True
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
    # --- STREAK / BEST / ACCURACY ---
    streak_text = font.render(f"Streak: {streak}", True, GREEN)
    screen.blit(streak_text, (WIDTH - 200, 50))
    best_text = small_font.render(f"Best: {best_streak}", True, GRAY)
    screen.blit(best_text, (WIDTH - 200, 80))
    acc_text = small_font.render(f"Accuracy: {accuracy_percent()}%", True, BLUE)
    screen.blit(acc_text, (WIDTH - 200, 104))
    if index < len(quiz_data):
        vi, answers = quiz_data[index]
        screen.blit(big_font.render(vi, True, BLACK), (50, 80))
        mode_text = font.render(
            "Mode: INPUT (Ctrl+I) / CHOICE (Ctrl+C) / Ctrl+R: reset quiz",
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
        # --- SCORE / COMPLETION SUMMARY ---
        round_total = len(quiz_data)
        round_correct = round_total - len(wrong)
        round_percent = round(100 * round_correct / round_total) if round_total else 0
        score_text = font.render(
            f"Score: {round_correct}/{round_total} ({round_percent}%)",
            True,
            GREEN if not wrong else BLACK
        )
        screen.blit(score_text, (250, 215))
        mistakes_text = font.render(
            f"Mistakes: {len(wrong)}",
            True,
            RED if wrong else GREEN
        )
        screen.blit(mistakes_text, (250, 250))
        # --- RETRY STATISTICS ---
        if is_retry_round and retry_stats_ready:
            retry_correct = retry_total - len(wrong)
            stats_lines = [
                f"Retry: {retry_total} questions",
                f"Correct: {retry_correct}",
                f"Still wrong: {len(wrong)}",
            ]
            sy = 285
            for line in stats_lines:
                screen.blit(small_font.render(line, True, BLACK), (250, sy))
                sy += 24
        if wrong:
            retry_text = font.render(
                "Press R to retry wrong answers",
                True,
                BLACK
            )
            screen.blit(retry_text, (180, 375))
        else:
            perfect_text = font.render(
                "Perfect!",
                True,
                GREEN
            )
            screen.blit(perfect_text, (280, 375))
        reset_text = small_font.render(
            "Ctrl+R: restart the whole quiz",
            True,
            GRAY
        )
        screen.blit(reset_text, (250, 410))
    # --- STRICT DIFF PANEL (stays until the next answer) ---
    if last_diff:
        typed_segs, correct_segs = last_diff
        panel_y = 420
        screen.blit(font.render("Last mistake:", True, BLUE), (50, panel_y))
        draw_diff_line("You:", typed_segs, 50, panel_y + 35)
        draw_diff_line("Answer:", correct_segs, 50, panel_y + 70)
        legend_y = panel_y + 110
        pygame.draw.rect(screen, LIGHT_RED, (50, legend_y + 4, 18, 18))
        screen.blit(small_font.render("extra / wrong", True, RED), (74, legend_y))
        pygame.draw.rect(screen, LIGHT_GREEN, (260, legend_y + 4, 18, 18))
        screen.blit(small_font.render("missing", True, GREEN), (284, legend_y))
    # --- PER-QUESTION MISTAKE HISTORY PANEL ---
    if last_question_history:
        vi_for_panel = quiz_data[index - 1][0] if 0 < index <= len(quiz_data) else ""
        draw_question_history(vi_for_panel, 700, 100)
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
            # --- SWITCH MODE / FULL RESET ---
            if mods & pygame.KMOD_CTRL:
                if event.key == pygame.K_c:
                    mode = "choice"
                elif event.key == pygame.K_i:
                    mode = "input"
                elif event.key == pygame.K_r:
                    reset_session()
                continue
            # --- FINISHED ---
            if index >= len(quiz_data):
                if event.key == pygame.K_r and wrong:
                    retry_total = len(wrong)
                    is_retry_round = True
                    retry_stats_ready = False
                    quiz_data = wrong[:]
                    random.shuffle(quiz_data)
                    wrong.clear()
                    index = 0
                    streak = 0
                    progress = 0
                    target_progress = 0
                    user_answers = []
                    last_diff = None
                    last_question_history = []
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
                        last_diff = make_diff(current_input, answers, user_answers)
                        last_question_history = record_mistake(vi, current_input, answers, user_answers)
                        if (vi, answers) not in wrong:
                            wrong.append((vi, answers))
                        streak = 0
                        total_attempts += 1
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
                            best_streak = max(best_streak, streak)
                            feedback = random.choice(messages_correct)
                            if streak >= 2:
                                message = f"{feedback} x{streak}"
                            else:
                                message = feedback
                            color = GREEN
                            last_diff = None
                            last_question_history = []
                            total_attempts += 1
                            total_correct += 1
                        else:
                            feedback = random.choice(messages_wrong)
                            message = f"{feedback}! {', '.join(answers)}"
                            color = RED
                            last_diff = make_diff(current_input, answers, user_answers)
                            last_question_history = record_mistake(vi, current_input, answers, user_answers)
                            if (vi, answers) not in wrong:
                                wrong.append((vi, answers))
                            streak = 0
                            total_attempts += 1
                    message_timer = pygame.time.get_ticks()
                    index += 1
                    target_progress = index / len(quiz_data)
                    user_answers = []
                    current_input = ""
                    load_question()
                elif event.key == pygame.K_BACKSPACE:
                    current_input = current_input[:-1]
                elif event.unicode and event.unicode.isprintable():
                    current_input += event.unicode
            # --- CHOICE MODE ---
            elif mode == "choice":
                if event.unicode.isdigit():
                    i = int(event.unicode) - 1
                    if 0 <= i < len(choices):
                        selected = normalize(choices[i])
                        total_attempts += 1
                        if selected in correct_set:
                            streak += 1
                            best_streak = max(best_streak, streak)
                            total_correct += 1
                            feedback = random.choice(messages_correct)
                            if streak >= 2:
                                message = f"{feedback} x{streak}"
                            else:
                                message = feedback
                            color = GREEN
                            last_diff = None
                            last_question_history = []
                        else:
                            feedback = random.choice(messages_wrong)
                            message = (
                                f"{feedback}! "
                                f"{', '.join(answers)}"
                            )
                            color = RED
                            last_diff = make_diff(choices[i], answers, [])
                            last_question_history = record_mistake(vi, choices[i], answers, [])
                            if (vi, answers) not in wrong:
                                wrong.append((vi, answers))
                            streak = 0
                        message_timer = pygame.time.get_ticks()
                        index += 1
                        target_progress = index / len(quiz_data)
                        load_question()
pygame.quit()
