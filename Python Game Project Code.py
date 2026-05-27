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

# ── OSC CONFIGURATION ─────────────────────────────────────────────────────────
GMA3_LAPTOP_IP   = "192.168.254.18" 
GMA3_PORT        = 8000             
GMA3_ADDRESS     = "/gma3/cmd"      

REAPER_LAPTOP_IP = "192.168.254.238" 
REAPER_PORT      = 8000             
# ──────────────────────────────────────────────────────────────────────────────

MA3_MATCH_COMMAND  = "Go+ Sequence 1"
MA3_RESET_COMMANDS = ["Off Sequence 1", "Off Sequence 2"]
MA3_BONUS_COMMANDS = ["Go+ Sequence 2 Cue 1", "Go+ Sequence 2 Cue 2", "Go+ Sequence 2 Cue 3"]

REAPER_ON_TRACK_PATHS = [f"/track/{i}/mute" for i in range(1, 25)]

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=4, model_complexity=1, min_detection_confidence=0.55, min_tracking_confidence=0.5)

def create_osc_client(ip, port, system_name): 
    try: 
        client = udp_client.SimpleUDPClient(ip, port)
        print(f"[+] OSC ready -> {system_name} on {ip}:{port}")
        return client 
    except Exception as e:
        print(f"[!] Network Pipeline Failed for {system_name}: {e}")
        return None

def send_osc_signal(client, address, message):
    if client is None: return
    try: client.send_message(address, message)
    except Exception: pass 

def trigger_reaper_action(client, action_id):
    """Sends a value of 1 then 0 to simulate a button press/release"""
    if client is None: return
    send_osc_signal(client, f"/action/{action_id}", float(1))
    time.sleep(0.01) 
    send_osc_signal(client, f"/action/{action_id}", float(0))

def extract_feature_vector(landmarks_21):
    lm = landmarks_21.copy() 
    lm = lm - lm[0] 
    scale = np.max(np.linalg.norm(lm, axis=1)) 
    if scale > 0: lm /= scale 
    feat = [] 
    for hub_idx in [0, 5, 17]: 
        feat.extend(np.linalg.norm(lm - lm[hub_idx], axis=1)) 
    return np.array(feat)

def load_gesture_definitions(csv_file):
    raw_captures = defaultdict(lambda: np.zeros((21, 3))) 
    try:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                
        with open(csv_file, newline="", encoding="utf-8-sig") as f: 
            reader = csv.DictReader(f) 
            for row in reader:
                key = (row["gesture_name"].strip().lower(), row["hand"].strip().lower(), int(float(row["capture_id"].strip()))) 
                raw_captures[key][int(row["landmark_id"])] = [float(row["x"]), float(row["y"]), float(row["z"])] 
    except FileNotFoundError:
        print(f"[-] Error: {csv_file} not found.")
        exit()

    templates = defaultdict(list) 
    for (gesture, hand, _), lm_array in raw_captures.items(): 
        templates[(gesture, hand)].append({"feature_vector": extract_feature_vector(lm_array), "raw_landmarks": lm_array}) 
    return templates                    

PRELOADED_IMAGES = {} 
def cache_target_images(templates_keys, box_size):
    folder = "Hand_Images"
    if not os.path.exists(folder): return
    for g_name in set([k[0] for k in templates_keys]): 
        for ext in [".png", ".jpg", ".jpeg"]:
            img_path = os.path.join(folder,f"{g_name}{ext}") 
            if os.path.exists(img_path):
                img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
                if img is not None:
                    PRELOADED_IMAGES[g_name] = cv2.resize(img, (box_size, box_size))
                    break 
 
def match_gesture(landmarks_21_raw, hand_label, templates, threshold=0.55):
    live_feat = extract_feature_vector(landmarks_21_raw) 
    best_gesture, best_distance, search_hand = None, float("inf"), hand_label.strip().lower() 

    for (gesture, hand), variants in templates.items():  
        if hand != search_hand: continue 
        for v in variants:
            dist = np.linalg.norm(live_feat - v["feature_vector"]) 
            if dist < best_distance: best_distance, best_gesture = dist, gesture 

    if best_distance > threshold:  
        fallback_hand = "right" if search_hand == "left" else "left" 
        for (gesture, hand), variants in templates.items():
            if hand != fallback_hand: continue
            for v in variants:
                dist = np.linalg.norm(live_feat - v["feature_vector"])
                if dist < best_distance: best_distance, best_gesture = dist, gesture

    return (best_gesture, best_distance) if best_distance <= threshold else (None, best_distance)

def draw_sleek_text(frame, text, pos, font_scale=0.6, thickness=1, color=(255, 255, 255)):
    font = cv2.FONT_HERSHEY_SIMPLEX
    x, y = pos 
    cv2.putText(frame, text, (x + 1, y + 1), font, font_scale, (10, 10, 10), thickness + 1, cv2.LINE_AA) 
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)

def draw_cyber_hand(frame, landmarks, color):
    h, w, _ = frame.shape  
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks.landmark] 
    for start_idx, end_idx in mp_hands.HAND_CONNECTIONS: 
        if start_idx < len(pts) and end_idx < len(pts): 
            cv2.line(frame, pts[start_idx], pts[end_idx], color, 2, cv2.LINE_AA) 
    for pt in pts: 
        cv2.circle(frame, pt, 3, (255, 255, 255), -1, cv2.LINE_AA) 
    cv2.circle(frame, pts[0], 9, color, 1, cv2.LINE_AA) 

def overlay_preloaded_picture(frame, img, x_min, y_min, box_size): 
    roi = frame[y_min:y_min+box_size, x_min:x_min+box_size] 
    if img.shape[2] == 4: 
        alpha = img[:, :, 3] / 255.0 
        alpha = np.expand_dims(alpha, axis=2) 
        blended = (img[:, :, :3] * alpha + roi * (1 - alpha)).astype(np.uint8) 
        frame[y_min:y_min+box_size, x_min:x_min+box_size] = blended 
    else:
        frame[y_min:y_min+box_size, x_min:x_min+box_size] = img[:, :, :3] 
    return True 

# ── INITIALIZATION ────────────────────────────────────────────────────────────
box_size = 150       
templates = load_gesture_definitions(CSV_FILE) 
all_keys = list(templates.keys()) 
cache_target_images(all_keys, box_size) 

gma3_client   = create_osc_client(GMA3_LAPTOP_IP, GMA3_PORT, "grandMA3")
reaper_client = create_osc_client(REAPER_LAPTOP_IP, REAPER_PORT, "REAPER")

left_gestures  = [k for k in all_keys if k[1] == "left" and k[0].startswith("left_")] or [k for k in all_keys if k[1] == "left"]
right_gestures = [k for k in all_keys if k[1] == "right" and k[0].startswith("right_")] or [k for k in all_keys if k[1] == "right"]

def get_new_targets():
    return [
        (random.choice(left_gestures)[0], "Left"),
        (random.choice(right_gestures)[0], "Right"),
        (random.choice(left_gestures)[0], "Left"),
        (random.choice(right_gestures)[0], "Right")
    ]

target_keys = get_new_targets()
cap = cv2.VideoCapture(0) 
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 

if not cap.isOpened(): exit() 

cv2.namedWindow("Gesture Recognition", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Gesture Recognition", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

MATCH_MIN_THRESHOLD = 0.15    
MATCH_THRESHOLD     = 0.58    
BASE_DURATION, MAX_LEVELS = 10.0, 6                

current_level, current_cycle = 1, 0
player_lives = 3 
round_duration = BASE_DURATION
matched_targets = [False] * 4 
HOLD_REQUIRED_DURATION = 2.0  
match_hold_start_time = None  

COUNTDOWN_DURATION = 3.0
countdown_start_time = 0.0

BONUS_ALERT_DURATION, bonus_cycle, bonus_gesture_count = 5.0, 0, 4
round_start_time = time.time()
game_status = "START_SCREEN"
status_display_time = 0.0
failed_from_bonus = False

while True:
    ret, frame = cap.read() 
    if not ret: break
    frame = cv2.flip(frame, 1) 
    h, w, _ = frame.shape
    
    result = None
    if game_status not in ["START_SCREEN", "COUNTDOWN", "GAME_CLEAR", "WIN", "LOSE", "BONUS_ALERT", "GAMEOVER"]: 
        small_rgb = cv2.resize(frame, (640, 360)) 
        small_rgb = cv2.cvtColor(small_rgb, cv2.COLOR_BGR2RGB) 
        result = hands.process(small_rgb) 
    
    hud_lines, current_time = [], time.time() 
    
    if game_status == "START_SCREEN":
        player_lives = 3 
        round_duration = max(2.0, BASE_DURATION - (current_level - 1))
        time_left = round_duration
        draw_sleek_text(frame, "THE ENCHANTMENT ROOM", (w // 2 - 280, h // 2 - 40), font_scale=1.3, thickness=2, color=(0, 255, 255))
        draw_sleek_text(frame, "Press [ S ] to initialize cooperative calibration sequences", (w // 2 - 280, h // 2 + 30), font_scale=0.6, thickness=1, color=(180, 180, 180))

    elif game_status == "COUNTDOWN":
        time_elapsed = current_time - countdown_start_time
        time_remaining = max(0.0, COUNTDOWN_DURATION - time_elapsed)
        
        if time_remaining <= 0:
            # Countdown complete -> Fire triggers and begin play
            for cmd in MA3_RESET_COMMANDS: send_osc_signal(gma3_client, GMA3_ADDRESS, cmd)
            for track_path in REAPER_ON_TRACK_PATHS: send_osc_signal(reaper_client, track_path, 0)
            trigger_reaper_action(reaper_client, 40161) # Marker 1
            send_osc_signal(reaper_client, "/play", 1)
            
            round_start_time = time.time()
            game_status = "PLAYING"
        else:
            # Visualise big numbers in center of screen
            secs_num = int(np.ceil(time_remaining))
            draw_sleek_text(frame, str(secs_num), (w // 2 - 25, h // 2 + 20), font_scale=3.5, thickness=4, color=(0, 255, 255))
            draw_sleek_text(frame, "PREPARING PIPELINE...", (w // 2 - 130, h // 2 - 60), font_scale=0.7, thickness=2, color=(255, 255, 255))

    elif game_status == "PLAYING":
        time_left = max(0.0, round_duration - (current_time - round_start_time))
        if time_left <= 0:
            player_lives -= 1 
            send_osc_signal(reaper_client, "/stop", 1)
            trigger_reaper_action(reaper_client, 41251) # Marker 11
            send_osc_signal(reaper_client, "/play", 1)

            for cmd in MA3_RESET_COMMANDS: send_osc_signal(gma3_client, GMA3_ADDRESS, cmd)
            for track_path in REAPER_ON_TRACK_PATHS: send_osc_signal(reaper_client, track_path, 1)
            
            if player_lives <= 0:
                game_status, status_display_time = "GAMEOVER", current_time
            else:
                game_status, status_display_time = "LOSE", current_time
                failed_from_bonus = False

    elif game_status == "BONUS_PLAYING":
        time_left = max(0.0, round_duration - (current_time - round_start_time))
        if time_left <= 0:
            player_lives -= 1
            for cmd in MA3_RESET_COMMANDS: send_osc_signal(gma3_client, GMA3_ADDRESS, cmd)
            if player_lives <= 0:
                game_status, status_display_time = "GAMEOVER", current_time
            else:
                game_status, status_display_time = "LOSE", current_time
                failed_from_bonus = True
            send_osc_signal(reaper_client, "/stop", 1)
            trigger_reaper_action(reaper_client, 41251) # Marker 11
            send_osc_signal(reaper_client, "/play", 1)

    elif game_status == "BONUS_ALERT":
        time_left = 0
        if current_time - status_display_time > BONUS_ALERT_DURATION:
            target_keys, matched_targets, bonus_cycle, round_duration = get_new_targets(), [False]*bonus_gesture_count, 0, 15.0
            round_start_time, game_status = time.time(), "BONUS_PLAYING"
           
    elif game_status in ["WIN", "LOSE", "GAME_CLEAR", "GAMEOVER"]:
        time_left = 0 
        display_timeout = 6.0 if game_status == "GAMEOVER" else 3.0

        if current_time - status_display_time > display_timeout: 
            if game_status == "WIN":
                target_keys, matched_targets, round_duration = get_new_targets(), [False]*4, max(2.0, BASE_DURATION - (current_level - 1)) 
                round_start_time, game_status = time.time(), "PLAYING"
                marker_cmd = 40160 + current_level
                trigger_reaper_action(reaper_client, marker_cmd) 
                send_osc_signal(reaper_client, "/play", 1)

            elif game_status == "LOSE":
                if failed_from_bonus:
                    current_level = 1
                else:
                    if current_level in [1, 2]: current_level = 1
                    elif current_level in [3, 4]: current_level = 3
                    elif current_level in [5, 6]: current_level = 5
                
                current_cycle, bonus_cycle = 0, 0  
                target_keys, matched_targets = get_new_targets(), [False] * 4 
                round_duration = max(2.0, BASE_DURATION - (current_level - 1)) 
                marker_cmd = 40160 + current_level
                trigger_reaper_action(reaper_client, marker_cmd)
                send_osc_signal(reaper_client, "/play", 1)
                time.sleep(1) 
                for track_path in REAPER_ON_TRACK_PATHS: send_osc_signal(reaper_client, track_path, 0)
                for cmd in MA3_RESET_COMMANDS: send_osc_signal(gma3_client, GMA3_ADDRESS, cmd)
                round_start_time, game_status = time.time(), "PLAYING"

            elif game_status in ["GAME_CLEAR", "GAMEOVER"]:
                current_level, current_cycle, bonus_cycle, game_status = 1, 0, 0, "START_SCREEN"

    # ── RENDER OVERLAYS ───────────────────────────────────────────────────────
    margin_x, margin_y, spacing = 80, 120, 290
    colors = [(0, 255, 255), (255, 0, 255), (0, 255, 100), (255, 150, 0)]

    if game_status in ["PLAYING", "BONUS_PLAYING"]:
        title = f"BONUS ROUND ({bonus_cycle + 1}/3)" if game_status == "BONUS_PLAYING" else f"LEVEL {current_level}  STAGE {current_cycle + 1}/4"
        draw_sleek_text(frame, title, (35, 45), font_scale=0.55, thickness=1, color=(255, 255, 255))
        timer_color = (0, 255, 0) if time_left > 10 else (0, 64, 255)
        draw_sleek_text(frame, f"TIME REMAINING: {time_left:.1f}s", (35, 68), font_scale=0.5, thickness=1, color=timer_color)
        lives_color = (0, 255, 0) if player_lives >= 2 else (0, 0, 255)
        draw_sleek_text(frame, f"LIVES: {player_lives} / 3", (35, 91), font_scale=0.5, thickness=1, color=lives_color)

    if game_status not in ["START_SCREEN", "COUNTDOWN", "GAME_CLEAR", "WIN", "LOSE", "BONUS_ALERT", "GAMEOVER"]:
        for i, key in enumerate(target_keys): 
            gesture_name, hand_label = key 
            lookup_key = (gesture_name.lower().strip(), hand_label.lower().strip()) 
            target_landmarks = templates[lookup_key][0]["raw_landmarks"] if lookup_key in templates else (templates.get((lookup_key[0], "right" if lookup_key[1] == "left" else "left"), [{"raw_landmarks": np.zeros((21,3))}])[0]["raw_landmarks"]) 
            center_x = margin_x + i * spacing + (box_size // 2)
            center_y = margin_y + (box_size // 2)
            x_min, y_min = center_x - (box_size // 2), center_y - (box_size // 2)
            x_max, y_max = center_x + (box_size // 2), center_y + (box_size // 2)
            color = colors[i]
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, 1, cv2.LINE_AA)

            if gesture_name in PRELOADED_IMAGES:
                overlay_preloaded_picture(frame, PRELOADED_IMAGES[gesture_name], x_min, y_min, box_size)
            elif np.any(target_landmarks):
                lm = target_landmarks.copy()
                lm -= np.mean(lm[:, :2], axis=0)
                max_val = np.max(np.abs(lm[:, :2]))
                if max_val > 0: lm[:, :2] = (lm[:, :2] / max_val) * (box_size // 2 * 0.7)
                lm[:, 0] += center_x
                lm[:, 1] += center_y
                for start_idx, end_idx in mp_hands.HAND_CONNECTIONS:
                    cv2.line(frame, (int(lm[start_idx, 0]), int(lm[start_idx, 1])), (int(lm[end_idx, 0]), int(lm[end_idx, 1])), color, 1, cv2.LINE_AA)
                for point in lm: cv2.circle(frame, (int(point[0]), int(point[1])), 2, (255, 255, 255), -1, cv2.LINE_AA)
                
            player_id = "P1" if i < 2 else "P2"
            draw_sleek_text(frame, f"{player_id} {hand_label.upper()}", (x_min + 5, y_min - 10), font_scale=0.5, thickness=1, color=color)
            draw_sleek_text(frame, gesture_name.upper(), (x_min + 5, y_max + 22), font_scale=0.5, thickness=1, color=(255, 255, 255))
    
    if game_status in ["PLAYING", "BONUS_PLAYING"]: matched_targets = [False] * len(target_keys) 

    if result and result.multi_hand_landmarks and result.multi_handedness and game_status not in ["START_SCREEN", "COUNTDOWN", "GAME_CLEAR", "WIN", "LOSE", "BONUS_ALERT", "GAMEOVER"]: 
        hand_colors = [(0,165, 255), (255, 0, 150), (0, 255, 100), (255, 150, 0)]
        for idx, (hand_landmarks, handedness) in enumerate(zip(result.multi_hand_landmarks, result.multi_handedness)): 
            if idx >= 4: break
            detected_label = handedness.classification[0].label 
            color = hand_colors[idx % len(hand_colors)] 
            draw_cyber_hand(frame, hand_landmarks, color)
            lm_array = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark]) 
            detected_gesture, best_dist = match_gesture(lm_array, detected_label, templates, threshold=MATCH_THRESHOLD) 
            for t_idx, target_key in enumerate(target_keys):
                if not matched_targets[t_idx] and detected_label == target_key[1] and detected_gesture == target_key[0]: 
                    if MATCH_MIN_THRESHOLD <= best_dist <= MATCH_THRESHOLD: 
                        matched_targets[t_idx] = True 
                    break
            wx, wy = int(hand_landmarks.landmark[0].x * w), int(hand_landmarks.landmark[0].y * h)
            draw_sleek_text(frame, detected_label.upper(), (wx - 25, wy + 25), font_scale=0.45, thickness=1, color=color) 
            g_name = detected_gesture if detected_gesture else "Scanning..."
            text_color = (0, 255, 0) if MATCH_MIN_THRESHOLD <= best_dist <= MATCH_THRESHOLD else (170, 170, 170)
            hud_lines.append((f"H{idx+1}({detected_label[0]}):{g_name.upper()}", text_color)) 

    # ── GAME ENGINE ───────────────────────────────────────────────────────────
    if game_status == "PLAYING" and result and result.multi_hand_landmarks and all(matched_targets):
        if match_hold_start_time is None: match_hold_start_time = current_time
        if current_time - match_hold_start_time >= HOLD_REQUIRED_DURATION:
            match_hold_start_time = None 
            send_osc_signal(gma3_client, GMA3_ADDRESS, MA3_MATCH_COMMAND)
            global_fixture_idx = ((current_level - 1) * 4) + current_cycle
            if global_fixture_idx < len(REAPER_ON_TRACK_PATHS): 
                send_osc_signal(reaper_client, REAPER_ON_TRACK_PATHS[global_fixture_idx], 0)
            
            current_cycle += 1
            
            if current_cycle >= 4:
                current_level += 1
                current_cycle = 0 
                
                if current_level > MAX_LEVELS:
                    game_status, status_display_time = "BONUS_ALERT", current_time
                    for cmd in MA3_RESET_COMMANDS: send_osc_signal(gma3_client, GMA3_ADDRESS, cmd)
                    for track_path in REAPER_ON_TRACK_PATHS: send_osc_signal(reaper_client, track_path, 1)
                else:
                    game_status, status_display_time = "WIN", current_time
                    send_osc_signal(reaper_client, "/stop", 1)
                    trigger_reaper_action(reaper_client, 41252) # Marker 12
                    send_osc_signal(reaper_client, "/play", 1)
            else:
                target_keys, matched_targets = get_new_targets(), [False] * 4
                round_duration, round_start_time, status_display_time = max(2.0, BASE_DURATION - (current_level - 1)), time.time(), current_time
            
    elif game_status == "BONUS_PLAYING" and result and result.multi_hand_landmarks and all(matched_targets):
        if match_hold_start_time is None: match_hold_start_time = current_time
        if current_time - match_hold_start_time >= HOLD_REQUIRED_DURATION:
            match_hold_start_time = None
            if bonus_cycle < len(MA3_BONUS_COMMANDS): send_osc_signal(gma3_client, GMA3_ADDRESS, MA3_BONUS_COMMANDS[bonus_cycle])
            trigger_reaper_action(reaper_client, 4000 + bonus_cycle) 
            bonus_cycle += 1
            if bonus_cycle >= 3:
                game_status = "GAME_CLEAR"
                send_osc_signal(reaper_client, "/stop", 1)
            else:
                target_keys, matched_targets, round_start_time = get_new_targets(), [False] * bonus_gesture_count, time.time()
            status_display_time= current_time
    else:
        match_hold_start_time = None

    # ── UI HUD ────────────────────────────────────────────────────────────────
    if game_status not in ["START_SCREEN", "COUNTDOWN", "GAME_CLEAR", "WIN", "LOSE", "BONUS_ALERT", "GAMEOVER"]:
        if hud_lines:
            x_offset = 40
            for text, txt_color in hud_lines:
                 draw_sleek_text(frame, text, (x_offset, h - 33), font_scale=0.45, thickness=1, color=txt_color)
                 x_offset += cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0][0] + 30
        else:
            draw_sleek_text(frame, "COOP LINK ACTIVE — AWAITING ALL 4 SIGNALS TO MATCH", (40, h - 33), font_scale=0.45, thickness=1, color=(120, 120, 120))

    if game_status in ["PLAYING", "BONUS_PLAYING"] and match_hold_start_time is not None:
        bar_width, bar_height, bar_x, bar_y = 400, 6, (w - 400) // 2, h - 90
        progress = min(1.0, (current_time - match_hold_start_time) / HOLD_REQUIRED_DURATION)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (30, 30, 30), -1)
        if progress > 0:
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_width * progress), bar_y + bar_height), (255, 255, 0), -1, cv2.LINE_AA)
        draw_sleek_text(frame, "LOCKING ALL COOP WAVEFORMS...", (bar_x + 90, bar_y - 12), font_scale=0.45, thickness=1, color=(0, 255, 255))

    if game_status in ["WIN", "LOSE", "GAME_CLEAR", "BONUS_ALERT", "GAMEOVER"]:
        if game_status == "GAMEOVER":
            draw_sleek_text(frame, "You Have Failed To Craft The Legendary Weapon", (w // 2 - 350, h // 2 + 8), font_scale=0.72, thickness=2, color=(0, 0, 255))
        else:
            if game_status == "WIN": draw_sleek_text(frame, "LEVEL DISCHARGE COMPLETE", (w // 2 - 230, h // 2), font_scale=1.0, thickness=2, color=(0, 255, 0))
            elif game_status == "LOSE": draw_sleek_text(frame, "ENCHANTMENT FAILED", (w // 2 - 240, h // 2), font_scale=1.0, thickness=2, color=(0, 0, 255))
            elif game_status == "GAME_CLEAR": draw_sleek_text(frame, "ENCHANTMENT UPGRADED!", (w // 2 - 250, h // 2), font_scale=1.0, thickness=2, color=(0, 255, 255))
            elif game_status == "BONUS_ALERT":
                draw_sleek_text(frame, "BONUS ENCHANTMENT RUNNING", (w // 2 - 270, h // 2 - 15), font_scale=0.9, thickness=2, color=(0, 165, 255))

    cv2.imshow("Gesture Recognition", frame)
    key = cv2.waitKey(1) & 0xFF 
    if key == ord('q'): break
    if key == ord('s') and game_status == "START_SCREEN":
        # Enter intermediate countdown phase instead of triggering media instantly
        target_keys, matched_targets = get_new_targets(), [False]*4
        countdown_start_time = time.time()
        game_status = "COUNTDOWN"

cap.release() 
cv2.destroyAllWindows()

