"""
Here We begin the coding of the game

How to play?
Grab 2 player and stand infront of the webcam
Press 'S' to start the game
The 2 players must match the gesture shown in the screen
For each correct gesture, the light in GrandMa3 will light up
There are a total of 6 level and for each level, you must match the 4 gestures 4 times
You have 3 lives in the game
"""

import cv2
import mediapipe as mp
import csv
import numpy as np
import random
import time
import os
from collections import defaultdict
from pythonosc import udp_client

CSV_FILE = "new_gesture_definitions.csv"

# ── OSC CONFIGURATION — SEPARATE TARGET LAPTOPS ───────────────────────────────
GMA3_LAPTOP_IP   = "192.168.254.18" # IP address of the grandMA3 laptop
GMA3_PORT        = 8000             # grandMA3 network inbound gateway
GMA3_ADDRESS     = "/gma3/cmd"      # Target path for grandMA3 commands

REAPER_LAPTOP_IP = "192.168.254.19" # IP address of the REAPER laptop
REAPER_PORT      = 9000             # REAPER network inbound gateway
# ──────────────────────────────────────────────────────────────────────────────

# ── SHOW ENGINE COMMAND DATA MAPS ─────────────────────────────────────────────
MA3_ON_COMMANDS = [
    "Fixture 1 At 100",  "Fixture 2 At 100",  "Fixture 3 At 100",  "Fixture 4 At 100",
    "Fixture 5 At 100",  "Fixture 6 At 100",  "Fixture 7 At 100",  "Fixture 8 At 100",
    "Fixture 9 At 100",  "Fixture 10 At 100", "Fixture 11 At 100", "Fixture 12 At 100",
    "Fixture 13 At 100", "Fixture 14 At 100", "Fixture 15 At 100", "Fixture 16 At 100",
    "Fixture 17 At 100", "Fixture 18 At 100", "Fixture 19 At 100", "Fixture 20 At 100",
    "Fixture 21 At 100", "Fixture 22 At 100", "Fixture 23 At 100", "Fixture 24 At 100"
]

MA3_OFF_COMMANDS = [
    "Fixture 1 At 0",    "Fixture 2 At 0",    "Fixture 3 At 0",    "Fixture 4 At 0",
    "Fixture 5 At 0",    "Fixture 6 At 0",    "Fixture 7 At 0",    "Fixture 8 At 0",
    "Fixture 9 At 0",    "Fixture 10 At 0",   "Fixture 11 At 0",   "Fixture 12 At 0",
    "Fixture 13 At 0",   "Fixture 14 At 0",   "Fixture 15 At 0",   "Fixture 16 At 0",
    "Fixture 17 At 0",   "Fixture 18 At 0",   "Fixture 19 At 0",   "Fixture 20 At 0",
    "Fixture 21 At 0",   "Fixture 22 At 0",   "Fixture 23 At 0",   "Fixture 24 At 0"
]

MA3_BONUS_COMMANDS = [
    "Go+ Sequence 1 Cue 1",
    "Go+ Sequence 1 Cue 2",
    "Go+ Sequence 1 Cue 3"
]

REAPER_ON_TRACK_PATHS = [
    "/track/1/mute",  "/track/2/mute",  "/track/3/mute",  "/track/4/mute",
    "/track/5/mute"
]
# ──────────────────────────────────────────────────────────────────────────────

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=4,
     model_complexity=1,             # High precision tracking model
    min_detection_confidence=0.55,
    min_tracking_confidence=0.5
)

def create_osc_client(ip, port, system_name):
    try:
        client = udp_client.SimpleUDPClient(ip, port)
        print(f"[+] OSC network pipeline ready -> Connected to {system_name} on {ip}:{port}")
        return client
    except Exception as e:
        print(f"[!] Network Pipeline Build Failed for {system_name}: {e}")
        return None

def send_osc_signal(client, address, message):
    if client is None:
        return
    try:
        client.send_message(address, message)
    except Exception:
        pass # Suppress logging overhead during runtime to maximize loop frequency

def extract_feature_vector(landmarks_21):
    lm = landmarks_21.copy()
    lm = lm - lm[0]
    scale = np.max(np.linalg.norm(lm, axis=1))
    if scale > 0:
        lm /= scale
    feat = []
    for hub_idx in [0, 5, 17]:
        hub = lm[hub_idx]
        distances = np.linalg.norm(lm - hub, axis=1)
        feat.extend(distances)
    return np.array(feat)

def load_gesture_definitions(csv_file):
    raw_captures = defaultdict(lambda: np.zeros((21, 3)))
    try:
        with open(csv_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row["gesture_name"].strip().lower(), row["hand"].strip().lower(), int(float(row["capture_id"].strip())))
                lm_id = int(row["landmark_id"])
                raw_captures[key][lm_id] = [float(row["x"]), float(row["y"]), float(row["z"])]
    except FileNotFoundError:
        print(f"[-] Error: {csv_file} not found.")
        exit()

    templates = defaultdict(list)
    for (gesture, hand, _cap_id), lm_array in raw_captures.items():
        feat = extract_feature_vector(lm_array)
        templates[(gesture, hand)].append({
            "feature_vector": feat,
            "raw_landmarks": lm_array
        })
    return templates

# ── OPTIMIZATION 1: PRE-LOAD ALL TARGET IMAGES INTO RAM CACHE ─────────────────
PRELOADED_IMAGES = {}
def cache_target_images(templates_keys, box_size):
    folder = "Hand_Images"
    if not os.path.exists(folder):
        return
    
    distinct_gestures = set([key[0] for key in templates_keys])
    extensions = [".png", ".jpg", ".jpeg"]
    
    for g_name in distinct_gestures:
        found = False
        for ext in extensions:
            img_path = os.path.join(folder, f"{g_name}{ext}")
            if os.path.exists(img_path):
                img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
                if img is not None:
                    # Pre-resize them to match our exactly UI spec
                    img_resized = cv2.resize(img, (box_size, box_size))
                    PRELOADED_IMAGES[g_name] = img_resized
                    found = True
                    break
    print(f"[+] Cached {len(PRELOADED_IMAGES)} target graphical asset configurations into hardware memory layers.")

def match_gesture(landmarks_21_raw, hand_label, templates, threshold=0.55):
    live_feat = extract_feature_vector(landmarks_21_raw)
    best_gesture = None
    best_distance = float("inf")
    search_hand = hand_label.strip().lower()

    for (gesture, hand), variants in templates.items():
        if hand != search_hand:
            continue
        for v in variants:
            dist = np.linalg.norm(live_feat - v["feature_vector"])
            if dist < best_distance:
                best_distance = dist
                best_gesture = gesture

    if best_distance > threshold:
        fallback_hand = "right" if search_hand == "left" else "left"
        for (gesture, hand), variants in templates.items():
            if hand != fallback_hand:
                continue
            for v in variants:
                dist = np.linalg.norm(live_feat - v["feature_vector"])
                if dist < best_distance:
                    best_distance = dist
                    best_gesture = gesture

    if best_distance > threshold:
        return None, best_distance
    return best_gesture, best_distance

def draw_text_with_bg(frame, text, pos, font_scale=0.7, thickness=2,
                    text_color=(255, 255, 255), bg_color=(0, 0, 0)):
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = pos
    cv2.rectangle(frame, (x - 4, y - th - 6), (x + tw + 4, y + baseline), bg_color, -1)
    cv2.putText(frame, text, (x, y), font, font_scale, text_color, thickness, cv2.LINE_AA)

def overlay_preloaded_picture(frame, img, x_min, y_min, box_size):
    roi = frame[y_min:y_min+box_size, x_min:x_min+box_size]
    if img.shape[2] == 4: # PNG blending
        alpha = img[:, :, 3] / 255.0
        alpha = np.expand_dims(alpha, axis=2)
        blended = (img[:, :, :3] * alpha + roi * (1 - alpha)).astype(np.uint8)
        frame[y_min:y_min+box_size, x_min:x_min+box_size] = blended
    else: # JPG blending
        frame[y_min:y_min+box_size, x_min:x_min+box_size] = img[:, :, :3]
    return True

box_size = 180       
templates = load_gesture_definitions(CSV_FILE)
all_keys = [(g, h) for (g, h) in templates.keys()]

# Run cache engine
cache_target_images(all_keys, box_size)

gma3_client   = create_osc_client(GMA3_LAPTOP_IP, GMA3_PORT, "grandMA3")
reaper_client = create_osc_client(REAPER_LAPTOP_IP, REAPER_PORT, "REAPER")

left_gestures  = [k for k in all_keys if k[1].strip().lower() == "left" and k[0].startswith("left_")]
right_gestures = [k for k in all_keys if k[1].strip().lower() == "right" and k[0].startswith("right_")]

if not left_gestures: 
    left_gestures = [k for k in all_keys if k[1].strip().lower() == "left"]
if not right_gestures: 
    right_gestures = [k for k in all_keys if k[1].strip().lower() == "right"]

def get_new_targets():
    p1_l = random.choice(left_gestures)
    p1_r = random.choice(right_gestures)
    p2_l = random.choice(left_gestures)
    p2_r = random.choice(right_gestures)
    return [(p1_l[0], "Left"), (p1_r[0], "Right"), (p2_l[0], "Left"), (p2_r[0], "Right")]

target_keys = get_new_targets()

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
# ── OPTIMIZATION 2: RECTIFY CAMERA BUFFER DELAYS ──────────────────────────────
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 

if not cap.isOpened():
    print("Webcam not detected")
    exit()

cv2.namedWindow("Gesture Recognition", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Gesture Recognition", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

print("[+] Initializing Audio Timeline...")
send_osc_signal(reaper_client, "/action/40044", float(1))

for track_path in REAPER_ON_TRACK_PATHS:
    send_osc_signal(reaper_client, track_path, 0)

BASE_DURATION = 100.0           
MATCH_THRESHOLD = 0.52         
MAX_LEVELS = 6                 

current_level = 1       
current_cycle = 0              
round_duration = BASE_DURATION
matched_targets = [False] * 4  

HOLD_REQUIRED_DURATION = 2.0   
match_hold_start_time = None   

BONUS_ALERT_DURATION = 5.0     
bonus_cycle = 0                
bonus_gesture_count = 4        

round_start_time = time.time()
game_status = "START_SCREEN" 
status_display_time = 0.0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1) 
    h, w, _ = frame.shape
    
    # ── OPTIMIZATION 3: SCALE DOWN DATALAYER INPUT FOR MEDIAPIPE ONLY ─────────
    # We trace on a lighter downscaled map but display full 720p HD coordinates
    small_rgb = cv2.resize(frame, (640, 360))
    small_rgb = cv2.cvtColor(small_rgb, cv2.COLOR_BGR2RGB)
    result = hands.process(small_rgb)
    
    hud_lines = []
    current_time = time.time()
    
    if game_status == "START_SCREEN":
        round_duration = max(2.0, BASE_DURATION - (current_level - 1))
        time_left = round_duration
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (15, 15, 15), -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
        draw_text_with_bg(frame, " Welcome To The Enchantment Room ", (w // 2 - 340, h // 2 - 80), font_scale=1.1, thickness=3, text_color=(0, 255, 255), bg_color=(20, 20, 20))
        draw_text_with_bg(frame, f" PRESS [ S ] TO START THE ENCHANTMENT", (w // 2 - 240, h // 2 + 50), font_scale=0.8, thickness=2, text_color=(0, 255, 0), bg_color=(0, 40, 0))

    elif game_status == "PLAYING":
        time_left = round_duration - (current_time - round_start_time)
        if time_left <= 0:
            time_left = 0
            game_status = "LOSE"
            status_display_time = current_time
            send_osc_signal(reaper_client, "/stop", 1)  
            level_offset = (current_level - 1) * 4
            for t_idx in range(4):
                global_fixture_idx = level_offset + t_idx
                send_osc_signal(gma3_client, GMA3_ADDRESS, MA3_OFF_COMMANDS[global_fixture_idx])
                send_osc_signal(reaper_client, REAPER_ON_TRACK_PATHS[global_fixture_idx], 1)

    elif game_status == "BONUS_PLAYING":
        time_left = round_duration - (current_time - round_start_time)
        if time_left <= 0:
            time_left = 0
            game_status = "LOSE"
            status_display_time = current_time
            send_osc_signal(reaper_client, "/stop", 1)

    elif game_status == "BONUS_ALERT":
        time_left = 0
        if current_time - status_display_time > BONUS_ALERT_DURATION:
            target_keys = get_new_targets()  
            matched_targets = [False] * bonus_gesture_count
            bonus_cycle = 0
            round_duration = 15.0  
            round_start_time = time.time()
            game_status = "BONUS_PLAYING"
            
    elif game_status in ["WIN", "LOSE", "GAME_CLEAR"]:
        time_left = 0
        if current_time - status_display_time > 3.0:
            if game_status == "WIN":
                target_keys = get_new_targets()
                matched_targets = [False] * 4
                round_duration = max(2.0, BASE_DURATION - (current_level - 1))
                round_start_time = time.time()
                game_status = "PLAYING"
            elif game_status == "LOSE":
                current_cycle = 0 
                bonus_cycle = 0
                current_level = max(1, ((current_level - 1) // 2) * 2 + 1)
                game_status = "START_SCREEN"  
            elif game_status == "GAME_CLEAR":
                current_level, current_cycle, bonus_cycle = 1, 0, 0
                game_status = "START_SCREEN"  

    margin_x, margin_y, spacing = 150, 100, 250
    colors = [(0, 255, 255), (0, 255, 255), (255, 0, 255), (255, 0, 255)]

    if game_status not in ["START_SCREEN", "GAME_CLEAR", "WIN", "LOSE", "BONUS_ALERT"]:
        for i, key in enumerate(target_keys):
            gesture_name, hand_label = key
            player_label = "P1" if i < 2 else "P2"
            lookup_key = (gesture_name.lower().strip(), hand_label.lower().strip())
            
            if lookup_key in templates:
                target_landmarks = templates[lookup_key][0]["raw_landmarks"]
            else:
                alt_hand = "right" if lookup_key[1] == "left" else "left"
                alt_key = (lookup_key[0], alt_hand)
                target_landmarks = templates[alt_key][0]["raw_landmarks"] if alt_key in templates else np.zeros((21,3))

            center_x = margin_x + i * spacing + (box_size // 2)
            center_y = margin_y + (box_size // 2)
            x_min, x_max = center_x - (box_size // 2), center_x + (box_size // 2)
            y_min, y_max = center_y - (box_size // 2), center_y + (box_size // 2)
            
            overlay = frame.copy()
            cv2.rectangle(overlay, (x_min, y_min), (x_max, y_max), (30, 30, 30), -1)
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

            color = colors[i]
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, 2)

            # Pull cleanly from memory cache array instantly
            picture_drawn = False
            if gesture_name in PRELOADED_IMAGES:
                picture_drawn = overlay_preloaded_picture(frame, PRELOADED_IMAGES[gesture_name], x_min, y_min, box_size)

            if not picture_drawn and np.any(target_landmarks):
                lm = target_landmarks.copy()
                lm_center = np.mean(lm[:, :2], axis=0)
                lm[:, 0] -= lm_center[0]
                lm[:, 1] -= lm_center[1]
                max_val = np.max(np.abs(lm[:, :2]))
                if max_val > 0:
                    lm[:, :2] = (lm[:, :2] / max_val) * (box_size // 2 * 0.75) 
                lm[:, 0] += center_x
                lm[:, 1] += center_y

                for start_idx, end_idx in mp_hands.HAND_CONNECTIONS:
                    cv2.line(frame, (int(lm[start_idx, 0]), int(lm[start_idx, 1])), (int(lm[end_idx, 0]), int(lm[end_idx, 1])), color, 2, cv2.LINE_AA)
                for point in lm:
                     cv2.circle(frame, (int(point[0]), int(point[1])), 3, (255, 255, 255), -1, cv2.LINE_AA)
                
            draw_text_with_bg(frame, f"[ {player_label} {hand_label.upper()} ]", (x_min + 2, y_min - 12), font_scale=0.45, thickness=1, text_color=color)
            draw_text_with_bg(frame, f" {gesture_name.upper()} ", (x_min + 5, y_max + 28), font_scale=0.7, thickness=2, text_color=(255, 255, 255), bg_color=(20, 20, 20))
    
    if game_status == "BONUS_ROUND":
        draw_text_with_bg(frame, f"BONUS ROUND  (ROUND {bonus_cycle + 1}/3)", (w // 2 - 110, 15), font_scale=0.5, thickness=1, text_color=(0, 165, 255), bg_color=(0,0,0))
    elif game_status == "PLAYING":
        draw_text_with_bg(frame, f"LVL {current_level}  (ROUND {current_cycle + 1}/4)", (w // 2 - 95, 15), font_scale=0.5, thickness=1, text_color=(255, 255, 255), bg_color=(0,0,0))

    any_hand_detected = False
    if game_status in ["PLAYING", "BONUS_PLAYING"]:
         matched_targets = [False] * len(target_keys)

    if result.multi_hand_landmarks and result.multi_handedness and game_status not in ["START_SCREEN", "GAME_CLEAR", "WIN", "LOSE", "BONUS_ALERT"]:
        any_hand_detected = True  
        
        hand_positions = [(hl.landmark[0].x, idx) for idx, hl in enumerate(result.multi_hand_landmarks)]
        hand_positions.sort(key=lambda x: x[0])

        player_hands = {}
        num_hands = len(hand_positions)
        for i, (_, idx) in enumerate(hand_positions):
            player_hands[idx] = "P1" if i < (num_hands + 1) // 2 else "P2"

        hand_colors = [(255, 150, 0), (0, 150, 255), (0, 255, 150), (200, 100, 250)]
        
        for idx, (hand_landmarks, handedness) in enumerate(zip(result.multi_hand_landmarks, result.multi_handedness)):
            player_label = player_hands.get(idx, "Unknown")
            raw_label = handedness.classification[0].label
            detected_label = raw_label
            conf = handedness.classification[0].score

            color = hand_colors[idx % len(hand_colors)]
            bg = tuple(int(c * 0.2) for c in color)

            # Map the downscaled coordinates smoothly back into display scale bounds
            mp_drawing.draw_landmarks(
                frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                mp_drawing.DrawingSpec(color=color, thickness=2, circle_radius=3),
                mp_drawing.DrawingSpec(color=color, thickness=1)
            )

            lm_array = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark])
            detected_gesture, best_dist = match_gesture(lm_array, detected_label, templates)

            for t_idx, target_key in enumerate(target_keys):
                if not matched_targets[t_idx]: 
                    expected_player = "P1" if t_idx < 2 else "P2"
                    if player_label == expected_player and detected_gesture == target_key[0]:
                        if best_dist <= MATCH_THRESHOLD:
                            matched_targets[t_idx] = True
                            break 

            wx = int(hand_landmarks.landmark[0].x * w)
            wy = int(hand_landmarks.landmark[0].y * h)
            draw_text_with_bg(frame, f"{player_label} {detected_label} ({conf:.0%})", (wx - 30, wy + 25), font_scale=0.4, thickness=1, text_color=color, bg_color=bg)

            g_name = detected_gesture if detected_gesture else "unknown"
            hud_lines.append((f"{player_label}: {g_name} ({best_dist:.2f})", color, bg))

    if game_status == "PLAYING":
        if any_hand_detected and all(matched_targets):
            if match_hold_start_time is None:
                match_hold_start_time = current_time
            time_held = current_time - match_hold_start_time
            
            if time_held >= HOLD_REQUIRED_DURATION:
                match_hold_start_time = None  
                level_offset = (current_level - 1) * 4
                global_fixture_idx = level_offset + current_cycle
                
                send_osc_signal(gma3_client, GMA3_ADDRESS, MA3_ON_COMMANDS[global_fixture_idx])
                send_osc_signal(reaper_client, REAPER_ON_TRACK_PATHS[global_fixture_idx], 0)
                current_cycle += 1  
                
                if current_cycle >= 4:
                    current_cycle = 0  
                    if current_level >= MAX_LEVELS:
                        game_status = "BONUS_ALERT"
                        status_display_time = current_time
                        for off_cmd in MA3_OFF_COMMANDS:
                            send_osc_signal(gma3_client, GMA3_ADDRESS, off_cmd)
                        for track_path in REAPER_ON_TRACK_PATHS:
                            send_osc_signal(reaper_client, track_path, 1)
                    else:
                        game_status = "WIN"
                        send_osc_signal(gma3_client, GMA3_ADDRESS, f"LEVEL_{current_level}_CLEARED")
                        current_level += 1
                else:
                    target_keys = get_new_targets()
                    matched_targets = [False] * 4
             
                round_duration = max(2.0, BASE_DURATION - (current_level - 1))
                round_start_time = time.time()
                status_display_time = current_time
        else:
             match_hold_start_time = None

    elif game_status == "BONUS_PLAYING":
        if any_hand_detected and all(matched_targets):
            if match_hold_start_time is None:
                match_hold_start_time = current_time
            time_held = current_time - match_hold_start_time
            
            if time_held >= HOLD_REQUIRED_DURATION:
                match_hold_start_time = None
                send_osc_signal(gma3_client, GMA3_ADDRESS, MA3_BONUS_COMMANDS[bonus_cycle])
                send_osc_signal(reaper_client, f"/action/4000{bonus_cycle}", 1) 
                bonus_cycle += 1
                
                if bonus_cycle >= 3:
                    game_status = "GAME_CLEAR"
                    send_osc_signal(gma3_client, GMA3_ADDRESS, "CAMPAIGN_ULTIMATE_VICTORY")
                    send_osc_signal(reaper_client, "/stop", 1)
                else:
                    target_keys = get_new_targets()
                    matched_targets = [False] * bonus_gesture_count
                    round_start_time = time.time()  
                status_display_time = current_time
        else:
             match_hold_start_time = None

    if game_status not in ["START_SCREEN", "GAME_CLEAR", "WIN", "LOSE", "BONUS_ALERT"]:
        if hud_lines:
            x_offset = 20
            y_offset = h - 30
            for text, color, bg in hud_lines:
                 draw_text_with_bg(frame, text, (x_offset, y_offset), font_scale=0.45, thickness=1, text_color=color, bg_color=bg)
                 (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                 x_offset += tw + 25
        else:
            draw_text_with_bg(frame, "No Hands Detected", (20, h - 30), font_scale=0.5, text_color=(150, 150, 150), bg_color=(30, 30, 30))

        timer_color = (0, 255, 0) if time_left > 3 else (0, 0, 255)
        draw_text_with_bg(frame, f"TIME: {time_left:.1f}s", (w // 2 - 60, 50), font_scale=0.8, thickness=2, text_color=timer_color, bg_color=(0,0,0))

    if game_status in ["PLAYING", "BONUS_PLAYING"]:
        bar_width, bar_height, bar_x, bar_y = 400, 20, (w - 400) // 2, h - 80
        progress_ratio = min(1.0, (current_time - match_hold_start_time) / HOLD_REQUIRED_DURATION) if match_hold_start_time is not None else 0.0

        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (40, 40, 40), -1)
        fill_width = int(bar_width * progress_ratio)
        if fill_width > 0:
            color_progress = (0, int(150 + (105 * progress_ratio)), int(255 - (255 * progress_ratio)))
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), color_progress, -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (255, 255, 255), 1)
         
        if match_hold_start_time is not None:
            remaining_hold = max(0.0, HOLD_REQUIRED_DURATION - (current_time - match_hold_start_time))
            draw_text_with_bg(frame, f"HOLD POSITION: {remaining_hold:.1f}s", (bar_x + 90, bar_y - 12), font_scale=0.5, thickness=1, text_color=(0, 255, 0), bg_color=(0, 0, 0))

    if game_status == "WIN":
        cv2.putText(frame, "LEVEL CLEARED!", (w // 2 - 250, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 5, cv2.LINE_AA)
    elif game_status == "LOSE":
         cv2.putText(frame, "ROUND FAILED", (w // 2 - 220, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 5, cv2.LINE_AA)
    elif game_status == "GAME_CLEAR":
         cv2.putText(frame, "YOU BEAT THE GAME!", (w // 2 - 320, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 5, cv2.LINE_AA)
    elif game_status == "BONUS_ALERT":
         cv2.putText(frame, "BONUS ROUND", (w // 2 - 230, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 165, 255), 6, cv2.LINE_AA)
         cv2.putText(frame, "Prepare Your Hands...", (w // 2 - 170, h // 2 + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

    cv2.imshow("Gesture Recognition", frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
        
    if key == ord('s') and game_status == "START_SCREEN":
        target_keys = get_new_targets()  
        matched_targets = [False] * 4    
        for off_cmd in MA3_OFF_COMMANDS:
            send_osc_signal(gma3_client, GMA3_ADDRESS, off_cmd)
        for track_path in REAPER_ON_TRACK_PATHS:
            send_osc_signal(reaper_client, track_path, 0)
            
        round_start_time = time.time()   
        game_status = "PLAYING"

cap.release()
cv2.destroyAllWindows()

