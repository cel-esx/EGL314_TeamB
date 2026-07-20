import cv2
import mediapipe as mp
import csv  
import numpy as np
import random
import time
import os
from collections import defaultdict
from pythonosc import udp_client
import threading
import torch
import torchvision.transforms as transforms
import PIL.Image as Image

# Thread-safe result holder
_mp_result = None
_mp_lock = threading.Lock()

def _run_mediapipe(frame_rgb):
    global _mp_result
   
    result = hands.process(frame_rgb)
    with _mp_lock:
        _mp_result = result

CSV_FILE = "MVP_gesture_definitions.csv"

# ── PICTURE SLIDESHOW CONFIGURATION ───────────────────────────────────────────
TRANSITION_INTERVAL = 1.0  

PIC1 = cv2.imread("MVP Pictures/Pack Recharge Start Page.jpg") 
PIC2 = cv2.imread("MVP Pictures/3.jpg") 
PIC3 = cv2.imread("MVP Pictures/2.jpg") 
PIC4 = cv2.imread("MVP Pictures/1.jpg") 
PIC5 = cv2.imread("MVP Pictures/Begin.jpg") 
PIC6 = cv2.imread("MVP Pictures/Level 4.png") 

TRANSITION_SLIDES = [PIC2, PIC3, PIC4, PIC5]
TRANSITION_SLIDES = [img for img in TRANSITION_SLIDES if img is not None]
# ──────────────────────────────────────────────────────────────────────────────

# ── OSC CONFIGURATION ─────────────────────────────────────────────────────────
GMA3_LAPTOP_IP   = "192.168.254.252s" 
GMA3_PORT        = 8000           
GMA3_ADDRESS     = "/gma3/cmd"      

MULTIPLAY_LAPTOP_IP = "192.168.254.238" 
MULTIPLAY_PORT      = 8000      
# ──────────────────────────────────────────────────────────────────────────────

MA3_MATCH_COMMAND  = "Go+ Sequence 1"
MA3_RESET_COMMANDS = ["Off Sequence 2", "Off Sequence 3"]

MA3_PASS_LEVEL_CMD = "Go+ Sequence 2 Cue 1"
MA3_GAMEOVER_CMD   = "Go+ Sequence 2 Cue 2"

GAME_SHOW_MAP = {
    1: { 
        1: {"fixture": 1, "cue_cmd": "Go+ Sequence 3 Cue 1"}, 
        2: {"fixture": 2, "cue_cmd": "Go+ Sequence 3 Cue 2"}, 
    },
    2: { 
        1: {"fixture": 5, "cue_cmd": "Go+ Sequence 3 Cue 5"},
        2: {"fixture": 6, "cue_cmd": "Go+ Sequence 3 Cue 6"},
    },
    3: { 
        1: {"fixture": 9, "cue_cmd": "Go+ Sequence 3 Cue 9"},
        2: {"fixture": 10, "cue_cmd": "Go+ Sequence 3 Cue 10"},
    },
    4: { 
        1: {"fixture": 13, "cue_cmd": "Go+ Sequence 3 Cue 13"},
        2: {"fixture": 14, "cue_cmd": "Go+ Sequence 3 Cue 14"},
    }
}

# ── LEVEL 4 PYTORCH MODEL INITIALIZATION ─────────────────────────────────────
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
try:
    model = torch.load('best_model.pth', map_location=device, weights_only=False)
    model = model.to(device)
    model.eval()
    print("[+] PyTorch Level 4 Model Successfully Loaded!")
except Exception as e:
    print(f"[!] Failed to load Level 4 model: {e}")
    model = None

ai_classes = ["Background", "Bird", "Palm", "Spider", "Wolf"]
mean = [0.4363, 0.4328, 0.3291]
std = [0.2129, 0.2075, 0.2037]
CONFIDENCE_THRESHOLD = 0.75

image_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(torch.Tensor(mean), torch.Tensor(std))
])

MANUAL_LEVEL_4_TARGETS = {
    0: "bird",    
    1: "wolf",    
    2: "spider",
}

MANUAL_LEVEL_1_GESTURES = {
    0: ("left_3", "right_2", "left_oath", "right_oath"), # Stage 1 Gestures
    1: ("left_oath", "right_2", "left_3", "right_3")  # Stage 2 Gestures
}
# ──────────────────────────────────────────────────────────────────────────────

mp_hands = mp.solutions.hands 
hands = mp_hands.Hands(max_num_hands=4, model_complexity=1, min_detection_confidence=0.50, min_tracking_confidence=0.50) 

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
    folder = "MVP Pictures"
    if not os.path.exists(folder): return
    for g_name in set([k[0] for k in templates_keys]):
        for ext in [".png", ".jpg", ".jpeg"]:
            img_path = os.path.join(folder, f"{g_name}{ext}")
            if os.path.exists(img_path):
                img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
                if img is None: continue
                img = cv2.resize(img, (box_size, box_size), interpolation=cv2.INTER_AREA)
            
                if img.ndim == 3 and img.shape[2] == 4:
                    alpha_mask = (img[:, :, 3:4].astype(np.float32) / 255.0)
                    rgb = img[:, :, :3].astype(np.float32)
                    PRELOADED_IMAGES[g_name] = {
                        "has_alpha": True,
                        "rgb_f32": rgb,
                        "alpha": alpha_mask,
                        "inv_alpha": 1.0 - alpha_mask,
                    }
                else:
                    PRELOADED_IMAGES[g_name] = {
                        "has_alpha": False,
                        "bgr": img[:, :, :3],
                    }
                break
 
def match_gesture(landmarks_21_raw, hand_label, templates, threshold=0.65):
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

def draw_hearts(frame, lives, max_lives=3, x_start=35, y=35, size=40, gap=10):
    for i in range(max_lives):
        x = x_start + i * (size + gap)
        if HEART_DATA is None:
            cv2.circle(frame, (x + size//2, y + size//2), size//2,
                       (0, 0, 255) if i < lives else (60, 60, 60), -1, cv2.LINE_AA)
        else:
            roi = frame[y:y+size, x:x+size]
            if roi.shape[:2] != (size, size): continue
            if i < lives:  
                if HEART_DATA["has_alpha"]:
                    blended = HEART_DATA["rgb_f32"] * HEART_DATA["alpha"] + roi.astype(np.float32) * HEART_DATA["inv_alpha"]
                    frame[y:y+size, x:x+size] = blended.astype(np.uint8)
                else:
                    frame[y:y+size, x:x+size] = HEART_DATA["bgr"]
            else:           
                if HEART_DATA["has_alpha"]:
                    dark = HEART_DATA["rgb_f32"] * 0.2  
                    blended = dark * HEART_DATA["alpha"] + roi.astype(np.float32) * HEART_DATA["inv_alpha"]
                    frame[y:y+size, x:x+size] = blended.astype(np.uint8)
                else:
                    frame[y:y+size, x:x+size] = (HEART_DATA["bgr"] * 0.2).astype(np.uint8)

def overlay_preloaded_picture(frame, img_data, x_min, y_min, box_size):
    roi = frame[y_min:y_min + box_size, x_min:x_min + box_size]
    if img_data["has_alpha"]:
        blended = img_data["rgb_f32"] * img_data["alpha"] + roi.astype(np.float32) * img_data["inv_alpha"]
        frame[y_min:y_min + box_size, x_min:x_min + box_size] = blended.astype(np.uint8)
    else:
        frame[y_min:y_min + box_size, x_min:x_min + box_size] = img_data["bgr"]
    return True

def draw_fullscreen_image(frame, image):
    if image is None: return
    h, w, _ = frame.shape
    resized = cv2.resize(image, (w, h), interpolation=cv2.INTER_AREA)
    np.copyto(frame, resized)

# ── INITIALIZATION ────────────────────────────────────────────────────────────
box_size = 200
     
templates = load_gesture_definitions(CSV_FILE)
all_keys = list(templates.keys()) 
cache_target_images(all_keys, box_size) 

gma3_client   = create_osc_client(GMA3_LAPTOP_IP, GMA3_PORT, "grandMA3")
multiplay_client = create_osc_client(MULTIPLAY_LAPTOP_IP, MULTIPLAY_PORT, "MultiPlay")

HEART_SIZE = 60 
heart_img = cv2.imread("MVP Pictures/Heart.png", cv2.IMREAD_UNCHANGED)
if heart_img is not None:
    heart_img = cv2.resize(heart_img, (HEART_SIZE, HEART_SIZE), interpolation=cv2.INTER_AREA)
    if heart_img.ndim == 3 and heart_img.shape[2] == 4:
        heart_alpha = heart_img[:, :, 3:4].astype(np.float32) / 255.0
        heart_rgb   = heart_img[:, :, :3].astype(np.float32)
        heart_inv   = 1.0 - heart_alpha
        HEART_DATA  = {"has_alpha": True, "rgb_f32": heart_rgb, "alpha": heart_alpha, "inv_alpha": heart_inv}
    else:
        HEART_DATA  = {"has_alpha": False, "bgr": heart_img[:, :, :3]}
else:
    HEART_DATA = None

print("Script started! Initializing system and grandMA3 connection...")
send_osc_signal(gma3_client, GMA3_ADDRESS, "ClearAll") 
send_osc_signal(gma3_client, GMA3_ADDRESS, "Off Sequence 1")
send_osc_signal(gma3_client, GMA3_ADDRESS, "Off Sequence 2")
send_osc_signal(gma3_client, GMA3_ADDRESS, "Off Sequence 3")
send_osc_signal(gma3_client, GMA3_ADDRESS, "On Sequence 1")

EXCLUDED_GESTURES = ["game_start"]

left_gestures = [k for k in all_keys if k[1] == "left" and k[0].startswith("left_") and k[0] not in EXCLUDED_GESTURES] or [k for k in all_keys if k[1] == "left" and k[0] not in EXCLUDED_GESTURES]
right_gestures = [k for k in all_keys if k[1] == "right" and k[0].startswith("right_") and k[0] not in EXCLUDED_GESTURES] or [k for k in all_keys if k[1] == "right" and k[0] not in EXCLUDED_GESTURES]
joint_gestures = list(set([k[0] for k in all_keys if not k[0].startswith("left_") and not k[0].startswith("right_") and k[0] not in EXCLUDED_GESTURES])) or list(set([k[0] for k in all_keys if k[0] not in EXCLUDED_GESTURES]))

MANUAL_LEVEL_2_GESTURES = {
    # Format: (Player 1 Left, Player 1 Right [Hidden], Player 2 Left, Player 2 Right [Hidden])
    0: ("stage2_level1", "stage2_level1", "level2_stage1", "level2_stage1"), 
    1: ("level2_stage2_1", "level2_stage2_1", "level2_stage2_2", "level2_stage2_2")  
}
MANUAL_LEVEL_3_GESTURES = {
    # Format: (Visible Main Joint Target, Hidden Guard 1, Hidden Guard 2, Hidden Guard 3)
    0: ("game_start_right", "game_start_left", "game_start_right", "game_start_left"), 
    1: ("palm", "palm", "palm", "palm")
}

def get_new_targets(lvl=1):
    global current_cycle
    stage = current_cycle if 'current_cycle' in globals() else 0

    if lvl == 4:
        target_name = MANUAL_LEVEL_4_TARGETS.get(stage, "palm")
        return [(target_name, "AICameraClass")]
    if lvl == 3:
        if stage in MANUAL_LEVEL_3_GESTURES:
            g1, g2, g3, g4 = MANUAL_LEVEL_3_GESTURES[stage]
        else:
            g1 = random.choice(joint_gestures)
            g2 = random.choice(joint_gestures)
            g3 = random.choice(joint_gestures)
            g4 = random.choice(joint_gestures)
        return [
            (g1, "JointShape"),
            (g2, "JointShape"),
            (g3, "JointShape"),
            (g4, "JointShape")
        ]
    elif lvl == 2:
        if stage in MANUAL_LEVEL_2_GESTURES:
            g1, g2, g3, g4 = MANUAL_LEVEL_2_GESTURES[stage]
        else:
            g1 = random.choice(left_gestures)[0]
            g2 = random.choice(right_gestures)[0]
            g3 = random.choice(left_gestures)[0]
            g4 = random.choice(right_gestures)[0]
            
        return [
            (g1, "Left"),
            (g2, "Right"),
            (g3, "Left"),
            (g4, "Right")
        ]
    
    # ── LEVEL 1 LOGIC ──────────────────────────────────────────────────────────
    if stage in MANUAL_LEVEL_1_GESTURES:
        g1, g2, g3, g4 = MANUAL_LEVEL_1_GESTURES[stage]
    else:
        g1 = random.choice(left_gestures)[0]
        g2 = random.choice(right_gestures)[0]
        g3 = random.choice(left_gestures)[0]
        g4 = random.choice(right_gestures)[0]
        
    return [
        (g1, "Left"),
        (g2, "Right"),
        (g3, "Left"),
        (g4, "Right")
    ]

target_keys = get_new_targets(lvl=1)
cap = cv2.VideoCapture(1 + cv2.CAP_DSHOW)  # Starts with laptop camera (0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 

if not cap.isOpened(): exit()  

# ── DYNAMIC STAGE VIDEO MATRIX CONFIGURATION ─────────────────────────────────
# Maps (Level, Stage_Index) to their specific background video paths.
# Stage 1 corresponds to current_cycle 0, Stage 2 to 1, and Stage 3 to 2.
VIDEO_STAGE_MAP = {
    (3, 0): "MVP Pictures/level_bg.mp4",
    (3, 1): "MVP Pictures/level_bg.mp4",
    (4, 0): "MVP Pictures/level_bg.mp4",
    (4, 1): "MVP Pictures/level_bg.mp4",
    (4, 2): "MVP Pictures/level_bg.mp4"
}

# Keep fallback stream reference for fallback scenarios
default_bg_path = "MVP Pictures/level_bg.mp4"
bg_video = cv2.VideoCapture(default_bg_path)
last_loaded_video_path = default_bg_path

cv2.namedWindow("Gesture Recognition", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Gesture Recognition", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

MATCH_MIN_THRESHOLD = 0.15    
MATCH_THRESHOLD     = 0.48 
BASE_DURATION, MAX_LEVELS = 30.0, 4  

current_level, current_cycle = 1, 0
player_lives = 3
round_duration = BASE_DURATION
matched_targets = [False] * 4 
HOLD_REQUIRED_DURATION = 2.0 
match_hold_start_time = None  

transition_start_time = None
round_start_time = time.time()
game_status = "START_SCREEN"
status_display_time = 0.0
last_active_cue_cmd = None
level4_unlocked = False  # Track if Level 4 initial palm unlock is completed

# ── DEFINITION OF THE START GAME SEQUENCE FUNCTION ────────────────────────────
def start_game_sequence():
    global game_status, round_start_time, transition_start_time, current_level, current_cycle, player_lives, target_keys, matched_targets, round_duration, last_active_cue_cmd, level4_unlocked
    print("[+] Starting game sequence...")
    player_lives = 3
    current_level = 1
    current_cycle = 0
    level4_unlocked = False
    round_duration = BASE_DURATION
    last_active_cue_cmd = None
    target_keys = get_new_targets(lvl=1)
    matched_targets = [False] * len(target_keys)
    send_osc_signal(multiplay_client, f"/cue/{current_level}/go", 1)
    transition_start_time = time.time()
    game_status = "TRANSITION_SCENE"

while True:
    ret, frame = cap.read() 
    if not ret: continue  # FIXED: Changed break to continue to prevent crash on camera device initialization frames
    frame = cv2.flip(frame, 1) 
    raw_camera_feed = frame.copy()
    h, w, _ = frame.shape
    
    # ── DYNAMIC STAGE VIDEO LOADING ENGINE ──
    # Determine which video should be playing based on current game level and stage cycles
    target_video_path = VIDEO_STAGE_MAP.get((current_level, current_cycle), default_bg_path)
    
    if target_video_path != last_loaded_video_path:
        bg_video.release()
        bg_video = cv2.VideoCapture(target_video_path)
        last_loaded_video_path = target_video_path

    # Read background video frame
    v_frame = None
    if bg_video.isOpened():
        v_ret, v_frame = bg_video.read()
        if not v_ret:
            bg_video.set(cv2.CAP_PROP_POS_FRAMES, 0)
            v_ret, v_frame = bg_video.read()

    result = None
    if game_status == "START_SCREEN" or (game_status not in ["TRANSITION_SCENE", "GAME_CLEAR", "WIN", "LOSE", "GAMEOVER"] and current_level != 4): 
        small_rgb = cv2.resize(raw_camera_feed, (640, 360)) 
        small_rgb = cv2.cvtColor(small_rgb, cv2.COLOR_BGR2RGB) 
        result = hands.process(small_rgb)  
    
    hud_lines, current_time = [], time.time() 

 
    if game_status == "START_SCREEN":
        player_lives = player_lives
        round_duration = BASE_DURATION
        time_left = round_duration
        
        # ── TRACK AND DRAW LANDMARKS ON MAIN FEED BEFORE COPYING TO PIP ────────
        total_hands_detected = 0
        if result and result.multi_hand_landmarks:
            hand_colors = [(0, 165, 255), (255, 0, 150), (0, 255, 100), (255, 150, 0)]
            for idx, hand_landmarks in enumerate(result.multi_hand_landmarks):
                if idx >= 4: break
                total_hands_detected += 1
                draw_cyber_hand(frame, hand_landmarks, hand_colors[idx % len(hand_colors)])
        
        if PIC1 is not None:
            # Refresh live view tracking onto the scaled PiP thumbnail area
            pip_feed_with_landmarks = frame.copy()
            draw_fullscreen_image(frame, PIC1)
            pip_w, pip_h = 400, 225
            pip_x, pip_y = w - pip_w - 30, 30
            pip_thumb = cv2.resize(pip_feed_with_landmarks, (pip_w, pip_h), interpolation=cv2.INTER_AREA)
            frame[pip_y:pip_y+pip_h, pip_x:pip_x+pip_w] = pip_thumb
            cv2.rectangle(frame, (pip_x, pip_y), (pip_x + pip_w, pip_y + pip_h), (0, 255, 255), 1, cv2.LINE_AA)
            draw_sleek_text(frame, "LIVE FEED", (pip_x + 6, pip_y + 15), font_scale=0.35, thickness=1, color=(0, 255, 255))
            
            # Display tracking label directly under the live feed component bounding box
            draw_sleek_text(frame, f"Total Hands Detected : {total_hands_detected}/4", (pip_x - 40, pip_y + pip_h + 20), font_scale=0.45, thickness=1, color=(0, 255, 255))
        else:
            draw_sleek_text(frame, "WEAPON UPGRADE ARENA", (w // 2 - 280, h // 2 - 40), font_scale=1.3, thickness=2, color=(0, 255, 255))

        # ── MODIFIED 4-HAND (TWO PAIRS) START GESTURE DETECTION ────────────────
        start_gesture_detected = False
        
        if result and result.multi_hand_landmarks and result.multi_handedness:
            start_left_count = 0
            start_right_count = 0
            
            for idx, (hand_landmarks, bandwidth) in enumerate(zip(result.multi_hand_landmarks, result.multi_handedness)):
                if idx >= 4: break  
                
                detected_label = bandwidth.classification[0].label  
                lm_array = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark])
                
                hand_span = np.max(lm_array[:, :2], axis=0) - np.min(lm_array[:, :2], axis=0)
                if hand_span[0] < 0.05 or hand_span[1] < 0.05: continue
                
                matched_gest, _ = match_gesture(lm_array, detected_label, templates, threshold=MATCH_THRESHOLD)
                
                if matched_gest and "palm" in matched_gest.lower():
                    if detected_label.lower().strip() == "left":
                        start_left_count += 1
                    elif detected_label.lower().strip() == "right":
                        start_right_count += 1
            
            if start_left_count >= 2 and start_right_count >= 2:
                start_gesture_detected = True

        if start_gesture_detected:
            if match_hold_start_time is None: match_hold_start_time = current_time
            elif current_time - match_hold_start_time >= HOLD_REQUIRED_DURATION:
                match_hold_start_time = None
                start_game_sequence()
        else:
            if match_hold_start_time is not None: match_hold_start_time = None
          
    elif game_status == "TRANSITION_SCENE":
        elapsed_transition = current_time - transition_start_time
        slide_idx = int(elapsed_transition // TRANSITION_INTERVAL)
        if slide_idx < len(TRANSITION_SLIDES): draw_fullscreen_image(frame, TRANSITION_SLIDES[slide_idx])
        else:
            game_status = "PLAYING"
            round_start_time = time.time()

    elif game_status == "PLAYING":
        # Only run standard game level timers if we aren't waiting for the level 4 shadow screen unlock
        if current_level == 4 and not level4_unlocked:
            time_left = round_duration
        else:
            time_left = max(0.0, round_duration - (current_time - round_start_time))
            if time_left <= 0:
                player_lives -= 1
                send_osc_signal(gma3_client, GMA3_ADDRESS, "Off Sequence 3")
                
                if player_lives <= 0:
                    game_status, status_display_time = "GAMEOVER", current_time 
                    send_osc_signal(multiplay_client, "/cue/15/go", 1)
                    send_osc_signal(multiplay_client, f"/cue/{current_level}/stop", 1)
                    send_osc_signal(gma3_client, GMA3_ADDRESS, MA3_GAMEOVER_CMD)
                else:
                    game_status, status_display_time = "LOSE", current_time
                    send_osc_signal(multiplay_client, "/cue/12/go", 1)
                    send_osc_signal(gma3_client, GMA3_ADDRESS, MA3_GAMEOVER_CMD)

    elif game_status in ["WIN", "LOSE", "GAME_CLEAR", "GAMEOVER"]:
        time_left = 0
        display_timeout = 6.0 if (game_status == "GAMEOVER") else 3.0 

        if current_time - status_display_time > display_timeout:  
            if game_status == "WIN":
                send_osc_signal(gma3_client, GMA3_ADDRESS, "Off Sequence 2")
                target_keys = get_new_targets(lvl=current_level)
                matched_targets = [False] * len(target_keys)
                round_duration = BASE_DURATION
                round_start_time, game_status = time.time(), "PLAYING"  
                last_active_cue_cmd = None
        
            elif game_status == "LOSE":
                send_osc_signal(gma3_client, GMA3_ADDRESS, "Off Sequence 2")
                target_keys = get_new_targets(lvl=current_level)
                matched_targets = [False] * len(target_keys)
                round_duration = BASE_DURATION
                round_start_time, game_status = time.time(), "PLAYING"
                last_active_cue_cmd = None
         
            elif game_status == "GAMEOVER":
                cap.release()
                cap = cv2.VideoCapture(1 + cv2.CAP_DSHOW) # FIXED: Re-initialize camera cleanly back to the configured start-index stream to prevent shutdown loop crashes
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                current_level, current_cycle, game_status = 1, 0, "START_SCREEN"
                level4_unlocked = False
                send_osc_signal(multiplay_client, f"/cue/{current_level}/stop", 1)
                send_osc_signal(gma3_client, GMA3_ADDRESS, "Off Sequence 2; Off Sequence 3")
                last_active_cue_cmd = None
              
            elif game_status == "GAME_CLEAR":
                cap.release()
                cap = cv2.VideoCapture(1 + cv2.CAP_DSHOW)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                current_level, current_cycle, game_status = 1, 0, "START_SCREEN"
                level4_unlocked = False
                target_keys, matched_targets = get_new_targets(lvl=1), [False] * 4
                round_duration = BASE_DURATION
                send_osc_signal(multiplay_client, f"/cue/{current_level}/stop", 1)
                send_osc_signal(gma3_client, GMA3_ADDRESS, "Off Sequence 2; Off Sequence 3")
                last_active_cue_cmd = None

    # ── RENDER OVERLAYS ───────────────────────────────────────────────────────
    margin_x, margin_y, spacing = 120, 190, 290
    colors = [(0, 255, 255), (0, 0, 255), (0, 255, 0), (255, 0, 0)]

    if game_status == "PLAYING" and not (current_level == 4 and not level4_unlocked):
        title = f"LEVEL {current_level} STAGE {current_cycle + 1}/3" if current_level == 4 else f"LEVEL {current_level} STAGE {current_cycle + 1}/2"
        draw_sleek_text(frame, title, (42, 45), font_scale=0.55, thickness=1, color=(255, 255, 255))
        
        # ── COUNTDOWN BAR ──────────────────────────────────────────────────────
        bar_x, bar_y, bar_w, bar_h = 320, 67, 600, 40
        time_ratio = max(0.0, time_left / round_duration)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (40, 40, 40), -1, cv2.LINE_AA)

        if time_ratio > 0.7: bar_color = (0, 255, 0)        
        elif time_ratio > 0.25: bar_color = (0, 165, 255)      
        else: bar_color = (0, 0, 255)        

        fill_w = int(bar_w * time_ratio)
        if fill_w > 0: cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), bar_color, -1, cv2.LINE_AA)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (150, 150, 150), 1, cv2.LINE_AA)
        draw_sleek_text(frame, f"{time_left:.1f}s", (bar_x + (bar_w // 2) - 20, bar_y + 26), font_scale=0.6, thickness=2, color=(255, 255, 255))
        draw_hearts(frame, player_lives, max_lives=3, x_start=35, y=60, size=60, gap=8)

    # ── HOLD SYNC PROGRESS BAR RENDERING ─────────────────────────────────────
    if match_hold_start_time is not None:
        elapsed_hold = current_time - match_hold_start_time
        hold_ratio = min(1.0, elapsed_hold / HOLD_REQUIRED_DURATION)
        bar_x, bar_y, bar_w, bar_h = 480, 520, 320, 20
        fill_w = int(bar_w * hold_ratio)
        
        overlay = frame.copy()
        cv2.rectangle(overlay, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (80, 40, 0), -1, cv2.LINE_AA)
        if fill_w > 0: cv2.rectangle(overlay, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), (255, 255, 0), -1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)
        
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (0, 255, 255), 1, cv2.LINE_AA)
        for marker in range(bar_x + 20, bar_x + bar_w, 20):
            cv2.line(frame, (marker, bar_y), (marker, bar_y + bar_h), (0, 255, 255), 1)
        draw_sleek_text(frame, f"SYSTEM SYNC: {int(hold_ratio * 100)}%", (bar_x, bar_y - 8), font_scale=0.45, thickness=1, color=(0, 255, 255))

    if game_status not in ["START_SCREEN", "TRANSITION_SCENE", "GAME_CLEAR", "WIN", "LOSE", "GAMEOVER"]:
        # ── CONFIGURING BOX SIZES DYNAMICALLY FOR LEVEL 3 AND 4 ──
        current_box_size = 300 if current_level in [3, 4] else box_size
        
        if current_level == 4 or current_level == 3:
            render_spacing = 0
            render_margin = (w // 2) - (current_box_size // 2)
        else:
            render_spacing = spacing
            render_margin = margin_x

        for i, key in enumerate(target_keys):
            # If we are in Level 4 but haven't unlocked it yet, override layout to display the shadow screen
            if current_level == 4 and not level4_unlocked:
                break

            # VISUAL CULLING FOR LEVEL 2: Hides tracking configurations 1 and 3 from the frame layout entirely
            if current_level == 2 and i in [1, 3]:
                continue
                
            # VISUAL CULLING FOR LEVEL 3: Hides tracking configurations 1, 2, and 3 from layout (only index 0 shows in center)
            if current_level == 3 and i in [1, 2, 3]:
                continue

            gesture_name, hand_label = key
            center_x = render_margin + i * render_spacing + (current_box_size // 2)
            center_y = margin_y + (current_box_size // 2)
            x_min, y_min = center_x - (current_box_size // 2), center_y - (current_box_size // 2)
            x_max, y_max = center_x + (current_box_size // 2), center_y + (current_box_size // 2)
            color = colors[i % len(colors)]
            
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, 1, cv2.LINE_AA)
            
            if current_level == 4:
                draw_sleek_text(frame, f"AI TARGET: {gesture_name.upper()}", (x_min - 20, y_min - 10), font_scale=0.5, thickness=1, color=color)
            elif current_level == 3:
                draw_sleek_text(frame, "ULTIMATE 4-HAND GESTURE", (x_min - 20, y_min - 10), font_scale=0.5, thickness=1, color=color)
            elif current_level == 2:
                player_lbl = "PLAYER 1" if i == 0 else "PLAYER 2"
                draw_sleek_text(frame, player_lbl, (x_min - 10, y_min - 10), font_scale=0.45, thickness=1, color=color)
            elif current_level == 1:
                player_lbl = "PLAYER 1" if i in [0, 1] else "PLAYER 2"
                draw_sleek_text(frame, player_lbl, (x_min + 5, y_min - 10), font_scale=0.5, thickness=1, color=color)
            else:
                draw_sleek_text(frame, f"TARGET {i+1}", (x_min + 5, y_min - 10), font_scale=0.5, thickness=1, color=color)

            # ── EMBED VIDEO LOOP ONLY INSIDE BOX IN LEVEL 3 & 4 OVERLAY REPLACEMENT ──
            if current_level in [3, 4] and v_frame is not None:
                video_crop = cv2.resize(v_frame, (current_box_size, current_box_size), interpolation=cv2.INTER_AREA)
                frame[y_min:y_min + current_box_size, x_min:x_min + current_box_size] = video_crop
            else:
                if gesture_name in PRELOADED_IMAGES:
                    overlay_preloaded_picture(frame, PRELOADED_IMAGES[gesture_name], x_min, y_min, current_box_size)
                elif hand_label not in ["AICameraClass"] and hand_label in ["JointShape", "4HandsShape"]:
                    lookup_key = [k for k in templates.keys() if k[0] == gesture_name.lower().strip()]
                    target_landmarks = templates[lookup_key[0]][0]["raw_landmarks"] if lookup_key else np.zeros((21,3))
                    if np.any(target_landmarks):
                        lm = target_landmarks.copy()
                        lm[:, :2] -= np.mean(lm[:, :2], axis=0)
                        max_val = np.max(np.abs(lm[:, :2]))
                        if max_val > 0: lm[:, :2] /= max_val
                        lm[:, :2] = lm[:, :2] * (current_box_size // 3) + [center_x, center_y]
                        for start_idx, end_idx in mp_hands.HAND_CONNECTIONS:
                            cv2.line(frame, (int(lm[start_idx, 0]), int(lm[start_idx, 1])), (int(lm[end_idx, 0]), int(lm[end_idx, 1])), color, 1, cv2.LINE_AA)
            
            # ── CONDITIONAL VISUAL MATCH HIGHLIGHT FOR LEVEL 1, 2 & 3 ──────────────
            is_box_matched = False
            if current_level == 3:
                # Level 3 rules: Main box says matched ONLY when all 4 internal slots are simultaneously satisfied
                if all(matched_targets):
                    is_box_matched = True
            else:
                is_box_matched = matched_targets[i]

            if is_box_matched:
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2, cv2.LINE_AA)
                draw_sleek_text(frame, "MATCHED", (x_min + 5, y_min + 20), font_scale=0.45, thickness=1, color=(0, 255, 0))

        # ── PROCESS RECOGNITION LOGIC ────────────────────────────────────────
        matched_targets = [False] * len(target_keys)
        
        if current_level == 4 and model is not None:
            rgb_frame = cv2.cvtColor(raw_camera_feed, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_frame)
            processed_tensor = image_transforms(pil_img).float().unsqueeze(0).to(device)
            
            with torch.no_grad():
                output = model(processed_tensor)
                probabilities = torch.nn.functional.softmax(output, dim=1)
                confidence, predicted = torch.max(probabilities, 1)
                
                confidence_score = confidence.item()
                predicted_name = ai_classes[predicted.item()]
                
            if predicted_name.lower() == "background":
                ai_status_str = f"Not Detected [Room Baseline: {confidence_score * 100:.1f}%]"
                ai_text_color = (0, 0, 255)
            else:
                if confidence_score >= CONFIDENCE_THRESHOLD:
                    ai_status_str = f"{predicted_name.upper()} DETECTED ({confidence_score * 100:.1f}%)"
                    ai_text_color = (0, 255, 0)
                else:
                    ai_status_str = f"Analyzing... ({predicted_name}: {confidence_score * 100:.1f}%)"
                    ai_text_color = (0, 255, 255)
            
            # Render the dynamic AI recognition information overlays
            if not level4_unlocked:
                # ── LEVEL 4 UNLOCK INITIAL SHADOW OVERLAY WITH FULLSCREEN BACKGROUND ──
                if PIC6 is not None:
                    # Capture live tracking markers to embed before overwriting with background image
                    pip_feed_with_landmarks = frame.copy()
                    draw_fullscreen_image(frame, PIC6)
                    
                    # ── ADDED: Video Loop crop overlay inside Level 4 custom overlay bounds ──
                    current_box_size = 250
                    center_x, center_y = w // 2, margin_y + (current_box_size // 2) + 250
                    x_min, y_min = center_x - (current_box_size // 2), center_y - (current_box_size // 2)
                    x_max, y_max = center_x + (current_box_size // 2), center_y + (current_box_size // 2)
                    
                    if v_frame is not None:
                        video_crop = cv2.resize(v_frame, (current_box_size, current_box_size), interpolation=cv2.INTER_AREA)
                        frame[y_min:y_min + current_box_size, x_min:x_min + current_box_size] = video_crop
                    
                    # ── RENDER LIVE CAMERA FEED AS PICTURE-IN-PICTURE (PiP) ──
                    pip_w, pip_h = 400, 225
                    pip_x, pip_y = w - pip_w - 30, 30
                    pip_thumb = cv2.resize(pip_feed_with_landmarks, (pip_w, pip_h), interpolation=cv2.INTER_AREA)
                    frame[pip_y:pip_y+pip_h, pip_x:pip_x+pip_w] = pip_thumb
                    cv2.rectangle(frame, (pip_x, pip_y), (pip_x + pip_w, pip_y + pip_h), (0, 255, 255), 1, cv2.LINE_AA)
                    draw_sleek_text(frame, "LIVE FEED", (pip_x + 6, pip_y + 15), font_scale=0.35, thickness=1, color=(0, 255, 255))
                else:
                    current_box_size = 300 if current_level in [3, 4] else box_size
                    center_x, center_y = w // 2, margin_y + (current_box_size // 2)
                    x_min, y_min = center_x - (current_box_size // 2), center_y - (current_box_size // 2)
                    x_max, y_max = center_x + (current_box_size // 2), center_y + (current_box_size // 2)
                    cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (255, 0, 255), 1, cv2.LINE_AA)
                    draw_sleek_text(frame, "GESTURE DETECTION DAMAGED", (x_min - 35, y_min - 30), font_scale=0.55, thickness=2, color=(255, 0, 255))
                    draw_sleek_text(frame, "SHOW PALM SHADOW TO RESUME GAME", (x_min - 90, y_min - 10), font_scale=0.5, thickness=1, color=(0, 255, 255))

                    if v_frame is not None:
                        video_crop = cv2.resize(v_frame, (current_box_size, current_box_size), interpolation=cv2.INTER_AREA)
                        frame[y_min:y_min + current_box_size, x_min:x_min + current_box_size] = video_crop
                    elif "palm" in PRELOADED_IMAGES:
                        overlay_preloaded_picture(frame, PRELOADED_IMAGES["palm"], x_min, y_min, current_box_size)
                    else:
                        cv2.putText(frame, "PALM SHADOW", (x_min + 15, center_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 1, cv2.LINE_AA)

                draw_sleek_text(frame, f"AI Gateway Status: {ai_status_str}", (30, h - 50), font_scale=0.6, thickness=2, color=ai_text_color)
                
                # Check gate fulfillment criteria
                if predicted_name.lower().strip() == "palm" and confidence_score >= CONFIDENCE_THRESHOLD:
                    if match_hold_start_time is None:
                        match_hold_start_time = current_time
                    elif current_time - match_hold_start_time >= HOLD_REQUIRED_DURATION:
                        match_hold_start_time = None
                        level4_unlocked = True  # Unlock completed, standard gameplay loop activates now
                        round_start_time = current_time  # Reset stage clock timestamp so player gets complete countdown bar time
                else:
                    if match_hold_start_time is not None:
                        match_hold_start_time = None
            else:
                # Standard playing UI drawing sequence resumes after unlock gate pass
                draw_sleek_text(frame, f"AI Status: {ai_status_str}", (30, h - 50), font_scale=0.6, thickness=2, color=ai_text_color)
                
                req_target = target_keys[0][0].lower().strip()
                if predicted_name.lower().strip() == req_target and confidence_score >= CONFIDENCE_THRESHOLD:
                    matched_targets[0] = True

        # Run MediaPipe hand structure tracking against the raw camera stream matrix layout
        if (current_level != 4 or not level4_unlocked):
            small_rgb = cv2.resize(raw_camera_feed, (640, 360))
            small_rgb = cv2.cvtColor(small_rgb, cv2.COLOR_BGR2RGB)
            result = hands.process(small_rgb)

        if result and result.multi_hand_landmarks and result.multi_handedness:
            hand_colors = [(0, 165, 255), (255, 0, 150), (0, 255, 100), (255, 150, 0)]
            detected_hands = []
            for idx, (hand_landmarks, bandwidth) in enumerate(zip(result.multi_hand_landmarks, result.multi_handedness)):
                if idx >= 4: break
                detected_label = bandwidth.classification[0].label
                color = hand_colors[idx % len(hand_colors)]
                draw_cyber_hand(frame, hand_landmarks, color)
                
                lm_array = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark])
                hand_span = np.max(lm_array[:, :2], axis=0) - np.min(lm_array[:, :2], axis=0)
                if hand_span[0] < 0.05 or hand_span[1] < 0.05: continue
                detected_hands.append((lm_array, detected_label))

            if current_level == 3:
                # ── CUSTOM SIMULTANEOUS FOUR-HAND INDEPENDENT EVALUATION FOR LEVEL 3 ──
                if len(target_keys) >= 4 and len(detected_hands) >= 4:
                    raw_matches = [False] * 4
                    assigned_hands = set()
                    
                    for i, (req_gesture, _) in enumerate(target_keys):
                        for h_idx, (lm_arr, det_lbl) in enumerate(detected_hands[:4]):
                            if h_idx in assigned_hands: continue
                            
                            # First attempt matching with the observed handedness label
                            matched_gest, _ = match_gesture(lm_arr, det_lbl, templates, threshold=MATCH_THRESHOLD)
                            
                            # Fallback: if no match, check the inverted handedness label to account for flipped hand classification
                            if matched_gest != req_gesture:
                                fallback_lbl = "right" if det_lbl.lower().strip() == "left" else "left"
                                matched_gest, _ = match_gesture(lm_arr, fallback_lbl, templates, threshold=MATCH_THRESHOLD)
                                
                            if matched_gest == req_gesture:
                                raw_matches[i] = True
                                assigned_hands.add(h_idx)
                                break
                                
                    if all(raw_matches):
                        matched_targets = [True] * 4
                        
            elif current_level == 1:
                assigned_targets = set()
                for lm_array, detected_label in detected_hands:
                    for i, key in enumerate(target_keys):
                        if i in assigned_targets: continue
                        gesture_name, hand_label = key
                        if hand_label.lower().strip() == detected_label.lower().strip():
                            matched_gest, _ = match_gesture(lm_array, detected_label, templates, threshold=MATCH_THRESHOLD)
                            if matched_gest == gesture_name:
                                matched_targets[i] = True
                                assigned_targets.add(i)
                                break
            elif current_level == 2:
                # ── CUSTOM SIMULTANEOUS TWO-HAND EVALUATION FOR LEVEL 2 ──
                raw_matches = [False] * 4
                assigned_targets = set()
                for lm_array, detected_label in detected_hands:
                    for i, key in enumerate(target_keys):
                        if i in assigned_targets: continue
                        gesture_name, hand_label = key
                        if hand_label.lower().strip() == detected_label.lower().strip():
                            matched_gest, _ = match_gesture(lm_array, detected_label, templates, threshold=MATCH_THRESHOLD)
                            if matched_gest == gesture_name:
                                raw_matches[i] = True
                                assigned_targets.add(i)
                                break
                
                # Player 1 rule: Only mark as matched if BOTH index 0 AND index 1 are fulfilled
                if raw_matches[0] and raw_matches[1]:
                    matched_targets[0] = True
                    matched_targets[1] = True
                
                # Player 2 rule: Only mark as matched if BOTH index 2 AND index 3 are fulfilled
                if raw_matches[2] and raw_matches[3]:
                    matched_targets[2] = True
                    matched_targets[3] = True

        # ── STATE STAGE PROGRESSION HANDLER ──────────────────────────────────
        if all(matched_targets) and not (current_level == 4 and not level4_unlocked):
            if match_hold_start_time is None:
                match_hold_start_time = current_time
            elif current_time - match_hold_start_time >= HOLD_REQUIRED_DURATION:
                match_hold_start_time = None
                
                current_stage = current_cycle + 1
                if current_level in GAME_SHOW_MAP and current_stage in GAME_SHOW_MAP[current_level]:
                    cfg = GAME_SHOW_MAP[current_level][current_stage]
                    last_active_cue_cmd = cfg["cue_cmd"]
                    send_osc_signal(gma3_client, GMA3_ADDRESS, last_active_cue_cmd)
                
                current_cycle += 1
                if current_cycle <= 1: 
                    send_osc_signal(multiplay_client, "/cue/13/go", 1)

                # Dynamically set completion requirement limit depending on level limits
                max_cycles_needed = 3 if current_level == 4 else 2
                if current_cycle >= max_cycles_needed:
                    send_osc_signal(multiplay_client, f"/cue/{current_level}/stop", 1)
                    send_osc_signal(gma3_client, GMA3_ADDRESS, "Off Sequence 3")
                    send_osc_signal(gma3_client, GMA3_ADDRESS, MA3_PASS_LEVEL_CMD)
                    
                    if current_level == 4:
                        game_status, status_display_time = "GAME_CLEAR", current_time
                        send_osc_signal(multiplay_client, "/cue/14/go", 1)
                    else:
                        current_level += 1
                        current_cycle = 0
                        
                        if current_level == 4:
                            cap.release()
                            cap = cv2.VideoCapture(0 + cv2.CAP_DSHOW)
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                        game_status, status_display_time = "WIN", current_time
                        send_osc_signal(multiplay_client, f"/cue/{current_level}/go", 1)
                        send_osc_signal(multiplay_client, "/cue/14/go", 1)
                else:
                    target_keys = get_new_targets(lvl=current_level)
                    matched_targets = [False] * len(target_keys)
                    round_start_time = current_time
        elif not (current_level == 4 and not level4_unlocked):
            match_hold_start_time = None

    if game_status in ["WIN", "LOSE", "GAME_CLEAR", "GAMEOVER"]:
        if game_status == "WIN":
            draw_sleek_text(frame, f"LEVEL {current_level - 1} CLEAR", (w // 2 - 160, h // 2), font_scale=1.1, thickness=2, color=(0, 255, 0))
        elif game_status == "LOSE":
            draw_sleek_text(frame, "WEAPON UPGRADD FAILED", (w // 2 - 240, h // 2), font_scale=1.0, thickness=2, color=(0, 0, 255))
            draw_sleek_text(frame, f"DON'T WORRY... YOU STILL HAVE {player_lives} / 3 LEFT", (w // 2 - 400, h // 2+30), font_scale=1.0, thickness=2, color=(0, 0, 255))
        elif game_status == "GAMEOVER":
            draw_sleek_text(frame, "GAME OVER", (w // 2 - 130, h // 2), font_scale=1.2, thickness=2, color=(0, 0, 255))
            draw_sleek_text(frame, "YOU HAVE FAILED TO UPGRADE THE WEAPON", (w // 2 - 500, h // 2+50), font_scale=1.2, thickness=2, color=(0, 0, 255))
        elif game_status == "GAME_CLEAR":
            draw_sleek_text(frame, "WEAPON UPGRADE SUCCESSFULL!", (w // 2 - 380, h // 2 - 20), font_scale=1.0, thickness=2, color=(0, 255, 0))
            draw_sleek_text(frame, "RETURNING TO MAIN SCREEN...", (w // 2 - 240, h // 2 + 30), font_scale=0.8, thickness=2, color=(0, 255, 255))

    cv2.imshow("Gesture Recognition", frame)
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q') or key == 27: 
        send_osc_signal(multiplay_client, f"/cue/{current_level}/stop", 1)
        send_osc_signal(gma3_client, GMA3_ADDRESS, "ClearAll") 
        send_osc_signal(gma3_client, GMA3_ADDRESS, "Off Sequence 1; Off Sequence 2; Off Sequence 3")
        break
        
    elif key == ord('s') or key == ord('1'):
        if game_status == "START_SCREEN": start_game_sequence()

    elif key == ord('r') or key == ord('2'):
        if game_status == "START_SCREEN":
            player_lives = 3
            current_level, current_cycle = 2, 0
            level4_unlocked = False
            target_keys = get_new_targets(lvl=2)
            matched_targets = [False] * len(target_keys)
            round_duration = BASE_DURATION
            send_osc_signal(multiplay_client, f"/cue/{current_level}/go", 1)
            send_osc_signal(gma3_client, GMA3_ADDRESS, "Off Sequence 1; Off Sequence 2; Off Sequence 3")
            round_start_time, game_status = time.time(), "PLAYING"
            last_active_cue_cmd = None

    elif key == ord('t') or key == ord('3'):
        if game_status == "START_SCREEN":
            player_lives = 3
            current_level, current_cycle = 3, 0
            level4_unlocked = False
            target_keys = get_new_targets(lvl=3)
            matched_targets = [False] * len(target_keys)
            round_duration = BASE_DURATION
            send_osc_signal(multiplay_client, f"/cue/{current_level}/go", 1)
            send_osc_signal(gma3_client, GMA3_ADDRESS, "Off Sequence 1; Off Sequence 2; Off Sequence 3")
            round_start_time, game_status = time.time(), "PLAYING"
            last_active_cue_cmd = None

    elif key == ord('y') or key == ord('4'): 
        send_osc_signal(multiplay_client, f"/cue/{current_level}/stop", 1)
        
        if current_level != 4:
            cap.release()
            cap = cv2.VideoCapture(0 + cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        player_lives = 3
        current_level, current_cycle = 4, 0
        level4_unlocked = False  # Reset lock gate if hard skipped to Level 4 via hotkey
        target_keys = get_new_targets(lvl=4)
        matched_targets = [False] * len(target_keys)
        round_duration = BASE_DURATION
        
        send_osc_signal(multiplay_client, f"/cue/{current_level}/go", 1)
        send_osc_signal(gma3_client, GMA3_ADDRESS, "Off Sequence 1; Off Sequence 2; Off Sequence 3")
        
        round_start_time, game_status = time.time(), "PLAYING"
        last_active_cue_cmd = None
        match_hold_start_time = None

bg_video.release()
cap.release()
cv2.destroyAllWindows()