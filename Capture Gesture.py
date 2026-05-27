"""
This code here helps to capture your desired gesture and save it to a CSV file
You can add gestures & delete gestures

Instructions: 

Press G to type the intended gesture name
Press Enter to save the name
Postition your hand according to your intended gesture
Use your mouse and right click on the screen to save the gesture


Repeat the above process to save other gestures also. There is no need for you to re-run the whole script to save other gestures
"""
import cv2
import mediapipe as mp
import csv
import os
from datetime import datetime

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

LANDMARK_NAMES = [
    "WRIST",
    "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
    "INDEX_MCP", "INDEX_PIP", "INDEX_DIP", "INDEX_TIP",
    "MIDDLE_MCP", "MIDDLE_PIP", "MIDDLE_DIP", "MIDDLE_TIP",
    "RING_MCP", "RING_PIP", "RING_DIP", "RING_TIP",
    "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP",
]

CSV_FILE = "new_gesture_definitions.csv"            """ Please Change the CSV file if neccesary"""
CSV_HEADERS = ["gesture_name", "hand", "capture_id", "timestamp",
               "landmark_id", "landmark_name", "x", "y", "z"]

# Global trigger flag for the mouse callback function
right_click_triggered = False

def mouse_callback(event, x, y, flags, param):
    """Listens for mouse events in the OpenCV window."""
    global right_click_triggered
    if event == cv2.EVENT_RBUTTONDOWN:  # Check for Right Mouse Button Click
        right_click_triggered = True

def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as f:
            csv.writer(f).writerow(CSV_HEADERS)
        print(f"[+] Created new file: {CSV_FILE}")
    else:
        print(f"[+] Appending to existing file: {CSV_FILE}")

def get_total_unique_captures():
    """Scans the CSV file to find the highest capture_id present."""
    if not os.path.exists(CSV_FILE):
        return 0
    try:
        with open(CSV_FILE, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            max_id = 0
            for row in reader:
                try:
                    c_id = int(row["capture_id"])
                    if c_id > max_id:
                        max_id = c_id
                except (ValueError, KeyError):
                    continue
            return max_id
    except Exception:
        return 0

def save_to_csv(gesture_name, hand_label, capture_id, landmarks):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        for i, lm in enumerate(landmarks):
            writer.writerow([
                gesture_name, hand_label, capture_id, timestamp,
                i, LANDMARK_NAMES[i],
                round(lm.x, 4), round(lm.y, 4), round(lm.z, 4),
            ])

def remove_gesture_from_csv(target_gesture_name):
    """
    Reads the CSV, filters out rows matching the target gesture name,
    and overwrites the file with remaining gestures. Returns number of entries removed.
    """
    if not os.path.exists(CSV_FILE):
        return 0

    target_clean = target_gesture_name.strip().lower().replace(" ", "_")
    rows_to_keep = []
    removed_count = 0

    try:
        with open(CSV_FILE, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            
            for row in reader:
                if row and len(row) > 0:
                    if row[0].strip().lower() == target_clean:
                        removed_count += 1
                    else:
                        rows_to_keep.append(row)
        
        if removed_count > 0:
            with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                if headers:
                    writer.writerow(headers)
                writer.writerows(rows_to_keep)
                
        return removed_count
    except Exception as e:
        print(f"[-] Error processing CSV deletion: {e}")
        return 0

def draw_text_with_bg(frame, text, pos, font_scale=0.65, thickness=1,
                    text_color=(255, 255, 255), bg_color=(0, 0, 0)):
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = pos
    cv2.rectangle(frame, (x - 4, y - th - 6), (x + tw + 4, y + baseline), bg_color, -1)
    cv2.putText(frame, text, (x, y), font, font_scale, text_color, thickness, cv2.LINE_AA)

def draw_input_box(frame, typing_buffer, frame_w, is_delete_mode=False):
    """Draw the on-screen typing prompt at the bottom of the frame."""
    h = frame.shape[0]
    box_y1, box_y2 = h - 60, h - 10

    overlay = frame.copy()
    cv2.rectangle(overlay, (10, box_y1), (frame_w - 10, box_y2), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # Set UI Theme color depending on selection vs removal mechanics
    theme_color = (100, 100, 255) if is_delete_mode else (100, 255, 100)
    prompt = "DELETE GESTURE: " if is_delete_mode else "Gesture name: "

    cv2.rectangle(frame, (10, box_y1), (frame_w - 10, box_y2), theme_color, 2)

    cursor = "_" if (datetime.now().microsecond // 300000) % 2 == 0 else " "
    display = prompt + typing_buffer + cursor

    cv2.putText(frame, display, (20, box_y2 - 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, theme_color, 2, cv2.LINE_AA)
    cv2.putText(frame, "ENTER=confirm   ESC=cancel", (20, box_y1 + 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1, cv2.LINE_AA)

def draw_flash(frame, message, color=(100, 255, 100)):
    """Briefly overlay a centred confirmation message."""
    h, w = frame.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale, thickness = 0.8, 2
    (tw, th), _ = cv2.getTextSize(message, font, scale, thickness)
    x = (w - tw) // 2
    y = h // 2
    cv2.rectangle(frame, (x - 12, y - th - 12), (x + tw + 12, y + 12), (0, 0, 0), -1)
    cv2.putText(frame, message, (x, y), font, scale, color, thickness, cv2.LINE_AA)

# ── Window Setup & Initialization ─────────────────────────────────────────────
WINDOW_NAME = "Gesture Calibration"
cv2.namedWindow(WINDOW_NAME)
cv2.setMouseCallback(WINDOW_NAME, mouse_callback) # Connect mouse actions to our script

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Webcam not detected")
    exit()

init_csv()

capture_count   = get_total_unique_captures() # Pull exact tracking ID matrix state
pending_gesture = None   # confirmed gesture name
typing_mode     = False   # True while user is typing a name
delete_mode     = False   # True while user is typing a name to delete
typing_buffer   = ""      # characters typed so far
flash_msg       = ""      # brief on-screen confirmation text
flash_timer     = 0       # frames remaining to show flash
flash_color     = (100, 255, 100)

print("\n[+] Window controls:")
print("    G           = start typing gesture name to capture")
print("    D           = start typing gesture name to PURGE/DELETE completely")
print("    ENTER       = confirm action input text processing loop")
print("    ESC         = cancel operational modes safely")
print("    RIGHT CLICK = capture current landmarks")
print("    Q           = quit\n")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    h, w = frame.shape[:2]
    num_hands = 0

    # ── Draw hand skeletons ───────────────────────────────────────────────────
    if result.multi_hand_landmarks and result.multi_handedness:
        num_hands = len(result.multi_hand_landmarks)
        for hand_landmarks, handedness in zip(result.multi_hand_landmarks,
                                              result.multi_handedness):
            label = handedness.classification[0].label
            color = (255, 180, 60) if label == "Left" else (60, 200, 255)

            mp_drawing.draw_landmarks(
                frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                mp_drawing.DrawingSpec(color=color, thickness=2, circle_radius=4),
                mp_drawing.DrawingSpec(color=color, thickness=2)
            )

            wx = int(hand_landmarks.landmark[0].x * w)
            wy = int(hand_landmarks.landmark[0].y * h)
            draw_text_with_bg(frame, label, (wx - 20, wy + 30),
                              text_color=color, bg_color=(0, 0, 0))

    # ── Top HUD ───────────────────────────────────────────────────────────────
    if pending_gesture:
        gesture_display = f"Gesture: [{pending_gesture}]"
        g_color = (100, 255, 100)
    else:
        gesture_display = "Gesture: [none  —  press G to set]"
        g_color = (160, 160, 160)

    draw_text_with_bg(frame, gesture_display, (10, 30),
                      font_scale=0.7, thickness=2,
                      text_color=g_color, bg_color=(0, 0, 0))

    mode_label = ""
    if typing_mode:
        mode_label = "[TYPING SET] "
    elif delete_mode:
        mode_label = "[PURGE MODE] "

    status = (f"Hands: {num_hands}   Captures: {capture_count}   "
              f"{mode_label}G=name  D=delete  R-CLICK=save  Q=quit")
    draw_text_with_bg(frame, status, (10, 62),
                      font_scale=0.48, thickness=1,
                      text_color=(200, 200, 200), bg_color=(0, 0, 0))

    # ── Typing overlay ────────────────────────────────────────────────────────
    if typing_mode:
        draw_input_box(frame, typing_buffer, w, is_delete_mode=False)
    elif delete_mode:
        draw_input_box(frame, typing_buffer, w, is_delete_mode=True)

    # ── Core Capture Processing Engine (Triggered via Mouse Click) ──────────
    if right_click_triggered and not (typing_mode or delete_mode):
        right_click_triggered = False # Immediately reset the trap trigger flag
        
        if not pending_gesture:
            flash_msg   = "Set a gesture name first  (press G)"
            flash_color = (100, 100, 255)
            flash_timer = 50
        elif not result.multi_hand_landmarks:
            flash_msg   = "No hands detected!"
            flash_color = (100, 100, 255)
            flash_timer = 50
        else:
            capture_count += 1
            ts = datetime.now().strftime("%H:%M:%S")
            saved_hands = []
            for hand_landmarks, handedness in zip(result.multi_hand_landmarks,
                                                   result.multi_handedness):
                label = handedness.classification[0].label
                conf  = handedness.classification[0].score
                save_to_csv(pending_gesture, label, capture_count,
                            hand_landmarks.landmark)
                saved_hands.append(f"{label}({conf:.0%})")
                print(f"  [{ts}] #{capture_count}  {pending_gesture}  |  "
                      f"{label} hand  {conf:.1%}")

            flash_msg   = f"Saved #{capture_count}  {pending_gesture}  [{', '.join(saved_hands)}]"
            flash_color = (100, 255, 100)
            flash_timer = 55
            
    elif right_click_triggered and (typing_mode or delete_mode):
        right_click_triggered = False

    # ── Flash message ─────────────────────────────────────────────────────────
    if flash_timer > 0:
        draw_flash(frame, flash_msg, color=flash_color)
        flash_timer -= 1

    cv2.imshow(WINDOW_NAME, frame)

    # ── Key handling ──────────────────────────────────────────────────────────
    key = cv2.waitKey(1) & 0xFF

    if typing_mode or delete_mode:
        if key == 13:   # Enter — confirm
            processed_name = typing_buffer.strip().lower().replace(" ", "_")
            
            if typing_mode:
                if processed_name:
                    pending_gesture = processed_name
                    flash_msg   = f"Gesture set: {pending_gesture}"
                    flash_color = (100, 255, 100)
                    flash_timer = 45
                    print(f"  [>] Gesture name set to '{pending_gesture}'")
                typing_mode = False
                
            elif delete_mode:
                if processed_name:
                    removed = remove_gesture_from_csv(processed_name)
                    if removed > 0:
                        flash_msg = f"Purged '{processed_name}' ({removed} rows removed)"
                        flash_color = (100, 100, 255)
                        # Re-calculate total distinct capture counts present within remaining dataset
                        capture_count = get_total_unique_captures()
                        if pending_gesture == processed_name:
                            pending_gesture = None
                        print(f"  [-] Completely removed '{processed_name}' from definitions database map entries.")
                    else:
                        flash_msg = f"Gesture '{processed_name}' not found inside file."
                        flash_color = (100, 255, 255)
                    flash_timer = 65
                delete_mode = False
                
            typing_buffer = ""

        elif key == 27:   # Escape — cancel
            typing_mode   = False
            delete_mode   = False
            typing_buffer = ""

        elif key == 8:    # Backspace
            typing_buffer = typing_buffer[:-1]

        elif 32 <= key <= 126:   # Printable ASCII
            typing_buffer += chr(key)

    else:
        if key == ord('q'):
            break
        elif key == ord('g'):
            typing_mode   = True
            delete_mode   = False
            typing_buffer = ""
        elif key == ord('d'):
            delete_mode   = True
            typing_mode   = False
            typing_buffer = ""

print(f"\n[+] Done. Final session reference count track: {capture_count}  →  {CSV_FILE}\n")
cap.release()
cv2.destroyAllWindows()
