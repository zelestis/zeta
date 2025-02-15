import random
import unittest
import shutil
import os
import sys
import time
import csv
import signal
import tty
import termios
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List


@dataclass(frozen=False)
class Config:
    """Configuration for game parameters."""

    ADD_SUB_RANGE: list = field(
        default_factory=lambda: list(range(2, 101))
    )  # 2 to 100 inclusive
    MULT_SMALL_RANGE: list = field(
        default_factory=lambda: list(range(2, 13))
    )  # 2 to 12 inclusive
    MULT_BIG_RANGE: list = field(
        default_factory=lambda: list(range(2, 101))
    )  # 2 to 100 inclusive
    TIMER_DURATION: int = 120  # 2 minutes in seconds
    SCREEN_WIDTH: int = 80  # Default terminal width if not detected
    DETAILED_LOG_FILE: str = str(Path.home() / ".zeta" / "zeta_log_summary.csv")
    SUMMARY_LOG_FILE: str = str(Path.home() / ".zeta" / "zeta_log.csv")


# Global configuration instance
config = Config()


def clear_screen():
    """Clears the terminal for a clean display."""
    os.system("clear" if os.name == "posix" else "cls")


def center_text(text):
    """Centers text based on the terminal width.
    This version pads both left and right."""
    terminal_width = shutil.get_terminal_size((Config.SCREEN_WIDTH, 20)).columns
    return text.center(terminal_width)


def center_text_left(text):
    """Centers text horizontally by prepending left spaces only.
    This avoids padding on the right so that the cursor remains immediately after the text."""
    terminal_width = shutil.get_terminal_size((Config.SCREEN_WIDTH, 20)).columns
    left_padding = (terminal_width - len(text)) // 2
    return " " * left_padding + text


def print_header():
    """Prints the game header."""
    clear_screen()
    print("\n" + center_text("=" * 50))
    print(center_text("Welcome to the Zelestis Arithmetic!"))
    print(center_text("Solve each problem correctly to proceed."))
    print(center_text("Type 'exit' to quit at any time."))
    print(center_text("=" * 50) + "\n")


def generate_problem():
    """Generate a random arithmetic problem."""
    operation = random.choice(["+", "-", "*", "/"])

    if operation == "+":  # Addition
        num1 = random.choice(config.ADD_SUB_RANGE)
        num2 = random.choice(config.ADD_SUB_RANGE)
        answer = num1 + num2

    elif operation == "-":  # Subtraction
        num1 = random.choice(config.ADD_SUB_RANGE)
        num2 = random.choice(config.ADD_SUB_RANGE)
        num1, num2 = max(num1, num2), min(num1, num2)
        answer = num1 - num2

    elif operation == "*":  # Multiplication
        num1 = random.choice(config.MULT_SMALL_RANGE)
        num2 = random.choice(config.MULT_BIG_RANGE)
        answer = num1 * num2

    else:  # Division
        num2 = random.choice(config.MULT_SMALL_RANGE)
        num1 = num2 * random.choice(config.MULT_BIG_RANGE)
        answer = num1 // num2

    return f"{num1} {operation} {num2}", answer


def log_detailed(timestamp, question, correct_answer, user_answer, time_taken, status):
    """Logs each question attempt in a detailed CSV file."""
    os.makedirs(os.path.dirname(Config.DETAILED_LOG_FILE), exist_ok=True)
    file_exists = os.path.isfile(Config.DETAILED_LOG_FILE)

    with open(Config.DETAILED_LOG_FILE, "a", newline="") as csv_file:
        writer = csv.writer(csv_file)
        if not file_exists:
            writer.writerow(["datetime", "time_taken", "question", "answer", "correct"])
        writer.writerow(
            [timestamp, time_taken, question, user_answer, status == "Correct"]
        )


def log_summary(session_data):
    """Logs the full game session to the summary CSV file."""
    os.makedirs(os.path.dirname(Config.SUMMARY_LOG_FILE), exist_ok=True)
    file_exists = os.path.isfile(Config.SUMMARY_LOG_FILE)

    with open(Config.SUMMARY_LOG_FILE, "a", newline="") as csv_file:
        writer = csv.writer(csv_file)
        if not file_exists:
            writer.writerow(
                ["Timestamp", "Duration (s)", "Final Score", "Questions & Answers"]
            )
        writer.writerow(session_data)


def format_session_data(start_time, score):
    """Formats session data into a single CSV row for summary logging."""
    duration = round(time.time() - start_time, 2)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return [timestamp, duration, score]


def time_up_message(score, start_time, question_log: List[str]):
    """Displays time-up message and logs session data."""
    session_data = format_session_data(start_time, score)
    log_summary(session_data)
    clear_screen()
    print("\n" + center_text("=" * 50))
    print(center_text("Time's up!"))
    print(center_text(f"Game over! Your final score is: {score}"))
    print(center_text("=" * 50) + "\n")
    for question in question_log:
        if "Correct" in question:
            question = "✅" + question
        else:
            question = "❌" + question
        print(center_text(question))


def get_user_input(correct_answer):
    """
    Captures user input in raw mode, displaying each character as typed.
    Auto-submits (returns the answer) if:
      - The typed input (if numeric) equals the correct answer, or
      - The user presses Enter, or
      - The user types 'exit' (case insensitive).
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    user_input = ""
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch == "\x03":  # Ctrl+C
                raise KeyboardInterrupt
            if ch in ("\x7f", "\b"):  # Handle backspace
                if user_input:
                    user_input = user_input[:-1]
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif ch in ("\r", "\n"):
                sys.stdout.write("\n")
                sys.stdout.flush()
                return user_input
            else:
                user_input += ch
                sys.stdout.write(ch)
                sys.stdout.flush()
                # Check if the user wants to exit.
                if user_input.lower() == "exit":
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return user_input
                # If the input is numeric and matches the correct answer, auto-submit.
                if user_input.lstrip("-").isdigit():
                    try:
                        if int(user_input) == correct_answer:
                            sys.stdout.write("\n")
                            sys.stdout.flush()
                            return user_input
                    except ValueError:
                        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def play_game():
    start_time = time.time()
    print_header()
    print(center_text(f"Playing for {Config.TIMER_DURATION // 60} minutes...\n"))
    score = 0
    question_log = []  # Stores questions and answers

    def exit_gracefully(sig, frame):
        """Handles Ctrl+C to ensure data is saved before exiting."""
        time_up_message(score, start_time, question_log)
        sys.exit(0)

    signal.signal(signal.SIGINT, exit_gracefully)

    while True:
        if time.time() - start_time >= Config.TIMER_DURATION:
            time_up_message(score, start_time, question_log)
            return

        problem, answer = generate_problem()
        question_start_time = time.time()

        # Print prompt using center_text_left so the cursor stays right after the '=' sign.
        print(center_text_left(f"{problem} = "), end="", flush=True)
        user_answer = get_user_input(answer)
        question_end_time = time.time()
        time_taken = round(question_end_time - question_start_time, 2)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if user_answer.lower() == "exit":
            time_up_message(score, start_time, question_log)
            return

        try:
            if int(user_answer) == answer:
                question_log.append(
                    f"{problem} = {user_answer} (Correct, {time_taken}s)"
                )
                log_detailed(
                    timestamp, problem, answer, user_answer, time_taken, "Correct"
                )
                print_header()
                score += 1
            else:
                question_log.append(f"{problem} = {user_answer} (Wrong, {time_taken}s)")
                log_detailed(
                    timestamp, problem, answer, user_answer, time_taken, "Wrong"
                )
                print(center_text("❌ Wrong! Try again."), end="")
        except ValueError:
            print(center_text("❌ Invalid input. Please enter a number."), end="")


if __name__ == "__main__":
    play_game()
