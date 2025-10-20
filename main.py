import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import pyautogui
import time
import sys
import pyttsx3
import os
from dotenv import load_dotenv
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel


# ===================== CONFIGURATION =====================
load_dotenv()
API_KEY = os.getenv("GENAI_API_KEY")

genai.configure(api_key=API_KEY)

# Increased grid resolution (finer precision)
GRID_ROWS, GRID_COLS = 27, 48
SCREENSHOT_PATH = "screen.png"

# Creating the GUI for user input

def gui():
    app = QApplication([])

    window = QWidget()
    window.setWindowTitle("LLM Controller")
    window.setGeometry(100, 100, 400, 100)

    layout = QVBoxLayout()
    label = QLabel("Enter the task you wish to perform (Ex: Open Chrome and search for cats):")
    layout.addWidget(label)

    text_box = QLineEdit()
    layout.addWidget(text_box)

    result = {"text": None}  # store entered text

    def handle_enter():
        result["text"] = text_box.text()
        window.close()

    text_box.returnPressed.connect(handle_enter)

    window.setLayout(layout)
    window.show()
    app.exec()
    
    return result["text"]


# ===================== SCREEN CAPTURE =====================
def take_screenshot(filename=SCREENSHOT_PATH):
    """Capture the screen and overlay a coordinate grid."""
    screenshot = pyautogui.screenshot()
    draw = ImageDraw.Draw(screenshot)
    w, h = screenshot.size
    cell_w, cell_h = w / GRID_COLS, h / GRID_ROWS

    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except:
        font = None

    for i in range(GRID_COLS):
        for j in range(GRID_ROWS):
            x, y = i * cell_w, j * cell_h
            draw.rectangle([x, y, x + cell_w, y + cell_h], outline="red", width=1)
            draw.text((x + 3, y + 3), f"{j+1},{i+1}", fill="red", font=font)

    screenshot.save(filename)
    return filename


def grid_to_pixel(grid_pos):
    """Convert grid coordinates (row, col) → pixel center (no jitter)."""
    row, col = grid_pos
    w, h = pyautogui.size()
    cell_w, cell_h = w / GRID_COLS, h / GRID_ROWS
    x = (col - 0.5) * cell_w
    y = (row - 0.5) * cell_h
    return int(x), int(y)


# ===================== INPUT CONTROL =====================
def release_modifiers():
    """Release any potentially stuck modifier keys."""
    for mod in ['shift', 'ctrl', 'alt', 'win']:
        try:
            pyautogui.keyUp(mod)
        except:
            pass
    time.sleep(0.05)


def safe_hotkey(*keys):
    """Safely press key combinations without sticky issues."""
    release_modifiers()
    pyautogui.hotkey(*keys)
    time.sleep(0.1)
    release_modifiers()


def execute_instruction(line):
    """Execute one structured instruction from the LLM."""
    line = line.strip()
    if not line:
        return

    try:
        release_modifiers()

        if line.startswith("Press:"):
            keys = [k.strip().lower() for k in line.split(":", 1)[1].split("+")]
            safe_hotkey(*keys)

        elif line.startswith("Type:"):
            text = line.split(":", 1)[1].strip()
            pyautogui.typewrite(text, interval=0.05)

        elif line.startswith("Click: Grid("):
            coords = line[line.find("(")+1:line.find(")")].split(',')
            row, col = int(coords[0]), int(coords[1])
            x, y = grid_to_pixel((row, col))
            # for attempt in range(3):
            pyautogui.click(x, y)
                # time.sleep(0.2)

        elif line.startswith("Click:"):
            coords = line.split(":", 1)[1].strip("() ").split(',')
            x, y = map(int, coords)
            # for attempt in range(3):
            pyautogui.click(x, y)
                # time.sleep(0.2)

        elif line.startswith("Wait:"):
            seconds = float(line.split(":", 1)[1].strip())
            time.sleep(seconds)

        time.sleep(0.1)

    except Exception as e:
        print(f"[WARN] Failed to execute line: '{line}' → {e}")
        release_modifiers()


# ===================== SYSTEM PROMPT =====================
system_prompt = (
    "You are an AI computer vision assistant that remotely controls a Windows computer by analyzing screenshots.\n"
    "You act only based on what you see in the screenshot. Never assume any window or app is open unless visible.\n\n"

    "=== RULES ===\n"
    "1. Observe the screenshot and decide what to do next. Do not assume any prior state.\n"
    "2. If you need to open an app (e.g., Chrome, Word, Settings):\n"
    "   Press: Win\n"
    "   Type: <App Name>\n"
    "   Press: Enter\n"
    "   Wait: 3\n"
    "   Please provide a screenshot of your screen.\n"
    "3. Prefer keyboard shortcuts (Ctrl + L, Ctrl + T) over clicking since the clicking isn't always accurate. THIS IS IMPORTANT.\n"
    "4. Always ensure the correct input field is focused before typing.\n"
    "5. Click using Grid(row, col) coordinates for precision.\n"
    "6. Format strictly:\n"
    "   Press: <keys>\n"
    "   Type: <text>\n"
    "   Click: Grid(row,col)\n"
    "   Wait: <seconds>\n"
    "7. Begin each response with:\n"
    "   Thought: <short explanation>\n"
    "8. After major steps (opening app, loading site, etc.), stop and say:\n"
    "   Please provide a screenshot of your screen.\n"
    "9. Say 'Task completed.' only when the task is visibly achieved.\n"
    "10. Never end a task immediately after performing a search (e.g., typing in Google or YouTube and pressing Enter).\n"
    "    Always wait for search results, analyze them, and take the next logical action.\n"
    "11. You must visually verify that the requested content or page is clearly open and visible before saying 'Task completed.'\n"
    "12. If the result is unclear or not visible, ask for another screenshot instead of finishing.\n"
    "13. If an action (like a click or keypress) does not change the visible screen, adjust your approach.\n"
    "    For example: try clicking slightly elsewhere, refocusing an input field, or using a different method.\n"
    "14. Assume that clicks may not be pixel-perfect; compensate by trying nearby spots or alternative steps. The click will be at the exact centre of the grid that you ask for.\n"
    "15. Never repeat identical clicks indefinitely — adapt after failed attempts.\n\n"

    "=== EXAMPLES (for format reference only) ===\n"
    "User: 'Open Google Chrome'\n"
    "Thought: Chrome is closed, opening it.\n"
    "Press: Win\n"
    "Type: Google Chrome\n"
    "Press: Enter\n"
    "Wait: 3\n"
    "Please provide a screenshot of your screen.\n\n"

    "User: 'Play Never Gonna Give You Up on YouTube'\n"
    "Thought: Chrome is closed, opening it first.\n"
    "Press: Win\n"
    "Type: Google Chrome\n"
    "Press: Enter\n"
    "Wait: 3\n"
    "Please provide a screenshot of your screen.\n"
    "Thought: Chrome opened, going to YouTube.\n"
    "Press: Ctrl + L\n"
    "Type: youtube.com\n"
    "Press: Enter\n"
    "Wait: 4\n"
    "Please provide a screenshot of your screen.\n"
    "Thought: YouTube loaded, searching video.\n"
    "Click: Grid(10,18)\n"
    "Type: Never Gonna Give You Up Rick Astley\n"
    "Press: Enter\n"
    "Wait: 4\n"
    "Please provide a screenshot of your screen.\n"
    "Thought: Clicking first video.\n"
    "Click: Grid(10,20)\n"
    "Wait: 5\n"
    "Please provide a screenshot of your screen.\n"
    "Thought: The video is playing.\n"
    "Task completed.\n\n"

    "Important: These examples are illustrative only. Always adapt steps to the actual visible screenshot."
)


# ===================== GEMINI REQUEST =====================
def ask_llm(task, screenshot_path, history):
    """Send task, screenshot, and conversation history to Gemini multimodal model."""
    model = genai.GenerativeModel(
        model_name="models/gemini-2.0-flash",
        system_instruction=system_prompt
    )

    with open(screenshot_path, "rb") as img_file:
        image_data = img_file.read()

    messages = history + [
        {"role": "user", "parts": [
            {"text": f"Task: {task}"},
            {"inline_data": {"mime_type": "image/png", "data": image_data}}
        ]}
    ]

    response = model.generate_content(messages)
    pyttsx3.speak(response.text)
    return response.text


# ===================== MAIN LOOP =====================
def main():
    task = gui()
    history = []
    attempt_log = {}  # ✅ tracks how many times each instruction was executed

    try:
        while True:
            screenshot_path = take_screenshot()
            
            # If any instruction has been repeated 2+ times, tell Gemini to adapt
            feedback = ""
            for cmd, count in attempt_log.items():
                if count >= 2:
                    feedback += f"The previous action '{cmd}' didn't change the screen. Try a different approach.\n"

            # Add adaptive feedback to next prompt
            task_with_feedback = task + ("\n" + feedback if feedback else "")

            response_text = ask_llm(task_with_feedback, screenshot_path, history)

            print("\n=== LLM Response ===\n")
            print(response_text)
            print("====================\n")

            history.append({"role": "user", "parts": [{"text": f"Task: {task_with_feedback}"}]})
            history.append({"role": "model", "parts": [{"text": response_text}]})

            for line in response_text.split("\n"):
                if line.startswith(("Press:", "Type:", "Click:", "Wait:")):
                    attempt_log[line] = attempt_log.get(line, 0) + 1  # ✅ track attempts
                    execute_instruction(line)

            if "Task completed" in response_text:
                print("✅ Task completed.")
                break

            elif "Please provide a screenshot" in response_text:
                time.sleep(2)
            else:
                time.sleep(2)

    except KeyboardInterrupt:
        print("\n⚠️ KeyboardInterrupt detected — stopping gracefully.")
    finally:
        release_modifiers()
        print("Exiting program safely.")
        sys.exit(0)


# ===================== RUN =====================
if __name__ == "__main__":
    main()
