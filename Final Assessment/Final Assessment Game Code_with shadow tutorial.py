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

# Thread-safe result holder for Async MediaPipe
_mp_result = None
_mp_lock = threading.Lock()
_mp_is_processing = False

def _run_mediapipe_async(frame_rgb):
    global _mp_result, _mp_is_processing
    result = hands.process(frame_rgb)
    with _mp_lock:
        _mp_result = result
        _mp_is_processing = False

CSV_FILE = "Final Assessment/Final_gesture_definitions.csv"

# ── PICTURE SLIDESHOW CONFIGURATION ───────────────────────────────────────────
TRANSITION_INTERVAL = 1.5  

# Pre-load and scale slideshow images to full screen (1280x720)
PIC1 = cv2.resize(cv2.imread("Final Assessment/MVP Pictures/Pack Recharge Start Page 2.jpg"), (1280, 720)) if os.path.exists("Final Assessment/MVP Pictures/Pack Recharge Start Page 2.jpg") else None
PIC2 = cv2.imread("Final Assessment/MVP Pictures/3 2.jpg") 
PIC3 = cv2.imread("Final Assessment/MVP Pictures/2 2.jpg") 
PIC4 = cv2.imread("Final Assessment/MVP Pictures/1 2.jpg") 
PIC5 = cv2.imread("Final Assessment/MVP Pictures/Begin 2.jpg")
PIC6 = cv2.resize(cv2.imread("Final Assessment/MVP Pictures/Level 4.jpg"), (1280, 720)) if os.path.exists("Final Assessment/MVP Pictures/Level 4.jpg") else None
PIC7 = cv2.imread("Final Assessment/MVP Pictures/Are You Ready.jpg") 

TRANSITION_SLIDES = [PIC7, PIC2, PIC3, PIC4, PIC5]
TRANSITION_SLIDES = [cv2.resize(img, (1280, 720)) for img in TRANSITION_SLIDES if img is not None]
# ──────────────────────────────────────────────────────────────────────────────

# ── OSC CONFIGURATION ─────────────────────────────────────────────────────────
GMA3_LAPTOP_IP   = "192.168.254.252s"
GMA3_PORT        = 8080           
GMA3_ADDRESS     = "/gma3/cmd"      


REAPER_LAPTOP_IP = "192.168.254.12s"
REAPER_PORT      = 8000
# ──────────────────────────────────────────────────────────────────────────────



MAX_STAGES_PER_LEVEL = {
    1: 1,  
    2: 1,  
    3: 3   
}

def back_to_start():
    print(f"⌛ Buffer complete! Back to start")
    send_osc_signal(reaper_client, "/action/41251", 1)
    send_osc_signal(reaper_client, "/track/15/mute",1)

# ── LEVEL 3 PYTORCH MODEL INITIALIZATION ──────────────────────────────────────
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
try:
    model = torch.load('Final Assessment/best_model.pth', map_location=device, weights_only=False)
    model = model.to(device)
    model.eval()
    print("[+] PyTorch Level 3 Model Successfully Loaded!")
except Exception as e:
    print(f"[!] Failed to load Level 3 model: {e}")
    model = None

ai_classes = [ 
 "Background", 
  "Bird", 
  "Moose",
  "Palm",
  "Spider",
  "Swan",
  "Wolf"]
mean = [0.4363, 0.4328, 0.3291]
std = [0.2129, 0.2075, 0.2037]
CONFIDENCE_THRESHOLD = 0.75

image_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(torch.Tensor(mean), torch.Tensor(std))
])

MANUAL_LEVEL_3_TARGETS = {
    0: "bird",    
    1: "swan",    #wolf
    2: "moose",  #spider
    3: "wolf",    # swan
    4: "spider"    # moose
}

MANUAL_LEVEL_1_GESTURES = {
    0: ("left_3", "right_2", "game_start_left", "right_4"), 
    1: ("left_4", "right_2", "left_3", "right_3")  
}

mp_hands = mp.solutions.hands 
hands = mp_hands.Hands(max_num_hands=4, model_complexity=0, min_detection_confidence=0.50, min_tracking_confidence=0.50) 

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
    folder = "Final Assessment/MVP Pictures"
    if not os.path.exists(folder): return
    all_names = set([k[0] for k in templates_keys if isinstance(k, tuple)]) | set([k for k in templates_keys if isinstance(k, str)])
    
    # Explicitly include hand-specific display names
    all_names.add("level2_stage2_2_left")
    all_names.add("level2_stage2_2_right")

    for g_name in all_names:
        for ext in [".png", ".jpg", ".jpeg"]:
            img_path = os.path.join(folder, f"{g_name}{ext}")
            if os.path.exists(img_path):
                img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
                if img is None: continue
                img = cv2.resize(img, (box_size, box_size), interpolation=cv2.INTER_LINEAR)
            
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
    thickness = int(thickness)
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
    if roi.shape[0] != box_size or roi.shape[1] != box_size:
        return False
    if img_data["has_alpha"]:
        img_rgb = cv2.resize(img_data["rgb_f32"], (box_size, box_size), interpolation=cv2.INTER_LINEAR)
        alpha = cv2.resize(img_data["alpha"], (box_size, box_size), interpolation=cv2.INTER_LINEAR)
        inv_alpha = cv2.resize(img_data["inv_alpha"], (box_size, box_size), interpolation=cv2.INTER_LINEAR)
        
        if alpha.ndim == 2:
            alpha = alpha[:, :, np.newaxis]
            inv_alpha = inv_alpha[:, :, np.newaxis]

        blended = img_rgb * alpha + roi.astype(np.float32) * inv_alpha
        frame[y_min:y_min + box_size, x_min:x_min + box_size] = blended.astype(np.uint8)
    else:
        img_bgr = cv2.resize(img_data["bgr"], (box_size, box_size), interpolation=cv2.INTER_LINEAR)
        frame[y_min:y_min + box_size, x_min:x_min + box_size] = img_bgr
    return True

def draw_fullscreen_image(frame, image):
    if image is None: return    
    np.copyto(frame, image)

def draw_dotted_rectangle(frame, pt1, pt2, color, thickness=2, gap=15):
    """Draws a dashed/dotted outline rectangle for hand positioning zones."""
    x1, y1 = pt1
    x2, y2 = pt2
    
    for x in range(x1, x2, gap * 2):
        cv2.line(frame, (x, y1), (min(x + gap, x2), y1), color, thickness, cv2.LINE_AA)
        cv2.line(frame, (x, y2), (min(x + gap, x2), y2), color, thickness, cv2.LINE_AA)
        
    for y in range(y1, y2, gap * 2):
        cv2.line(frame, (x1, y), (x1, min(y + gap, y2)), color, thickness, cv2.LINE_AA)
        cv2.line(frame, (x2, y), (x2, min(y + gap, y2)), color, thickness, cv2.LINE_AA)

# Add a state tracker variable
last_sent_reaper_cmd = None

last_sent_osc_states = {}

def send_osc_once(client, address, message):
    global last_sent_osc_states
    if last_sent_osc_states.get(address) != message:
        send_osc_signal(client, address, message)
        last_sent_osc_states[address] = message

# Use send_osc_once instead of send_osc_signal inside your main loop for continuous states

# ── INITIALIZATION ────────────────────────────────────────────────────────────
box_size = 150
     
templates = load_gesture_definitions(CSV_FILE)
all_keys = list(templates.keys()) + ["palmm","palm", "bird", "wolf", "spider", "swan", "moose"] 
cache_target_images(all_keys, box_size) 

gma3_client   = create_osc_client(GMA3_LAPTOP_IP, GMA3_PORT, "grandMA3")
reaper_client = create_osc_client(REAPER_LAPTOP_IP, REAPER_PORT, "REAPER")

HEART_SIZE = 60 
heart_img = cv2.imread("Final Assessment/MVP Pictures/Heart.png", cv2.IMREAD_UNCHANGED)
if heart_img is not None:
    heart_img = cv2.resize(heart_img, (HEART_SIZE, HEART_SIZE), interpolation=cv2.INTER_LINEAR)
    if heart_img.ndim == 3 and heart_img.shape[2] == 4:
        heart_alpha = heart_img[:, :, 3:4].astype(np.float32) / 255.0
        heart_rgb   = heart_img[:, :, :3].astype(np.float32)
        heart_inv   = 1.0 - heart_alpha
        HEART_DATA  = {"has_alpha": True, "rgb_f32": heart_rgb, "alpha": heart_alpha, "inv_alpha": heart_inv}
    else:
        HEART_DATA  = {"has_alpha": False, "bgr": heart_img[:, :, :3]}
else:
    HEART_DATA = None

print("Script started! Initializing system, reaper, and grandMA3 connection...")
send_osc_signal(reaper_client, "/action/40339", 1) #unmute all tracks
send_osc_signal(reaper_client, "/action/40161", 1) # Jump to marker 1 (tutorial game start)
time.sleep(5)
send_osc_signal(gma3_client, GMA3_ADDRESS, "go macro 10;")

EXCLUDED_GESTURES = ["game_start"]

left_gestures = [k for k in all_keys if isinstance(k, tuple) and k[1] == "left" and k[0].startswith("left_") and k[0] not in EXCLUDED_GESTURES] or [k for k in all_keys if isinstance(k, tuple) and k[1] == "left" and k[0] not in EXCLUDED_GESTURES]
right_gestures = [k for k in all_keys if isinstance(k, tuple) and k[1] == "right" and k[0].startswith("right_") and k[0] not in EXCLUDED_GESTURES] or [k for k in all_keys if isinstance(k, tuple) and k[0] not in EXCLUDED_GESTURES]
joint_gestures = list(set([k[0] for k in all_keys if isinstance(k, tuple) and not k[0].startswith("left_") and not k[0].startswith("right_") and k[0] not in EXCLUDED_GESTURES])) or list(set([k[0] for k in all_keys if isinstance(k, tuple) and k[0] not in EXCLUDED_GESTURES]))

MANUAL_LEVEL_2_GESTURES = {
    0: ("stage2_level1", "stage2_level1", "palm", "palm"), 
    1: ("level2_stage2_1", "level2_stage2_1", "level2_stage2_2", "level2_stage2_2")  
}

def get_new_targets(lvl=1):
    global current_cycle
    stage = current_cycle if 'current_cycle' in globals() else 0

    if lvl == 3:
        target_name = MANUAL_LEVEL_3_TARGETS.get(stage, "palm")
        return [(target_name, "AICameraClass")]
    elif lvl == 2:
        if stage in MANUAL_LEVEL_2_GESTURES:
            g1, g2, g3, g4 = MANUAL_LEVEL_2_GESTURES[stage]
        else:
            g1 = random.choice(left_gestures)[0]
            g2 = random.choice(right_gestures)[0]
            g3 = random.choice(left_gestures)[0]
            g4 = random.choice(right_gestures)[0]
            
        return [(g1, "Left"), (g2, "Right"), (g3, "Left"), (g4, "Right")]
    
    if stage in MANUAL_LEVEL_1_GESTURES:
        g1, g2, g3, g4 = MANUAL_LEVEL_1_GESTURES[stage]
    else:
        g1 = random.choice(left_gestures)[0]
        g2 = random.choice(right_gestures)[0]
        g3 = random.choice(left_gestures)[0]
        g4 = random.choice(right_gestures)[0]
        
    return [(g1, "Left"), (g2, "Right"), (g3, "Left"), (g4, "Right")]

target_keys = get_new_targets(lvl=1)
cap = cv2.VideoCapture(1 + cv2.CAP_DSHOW)  
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 

if not cap.isOpened(): exit()  

VIDEO_STAGE_MAP = {
    (3, 0): "Final Assessment/MVP Pictures/level_bg.mp4",  
    (3, 1): "Final Assessment/MVP Pictures/Bird.mp4",  
    (3, 2): "Final Assessment/MVP Pictures/Swan.mp4",      
    (3, 3): "Final Assessment/MVP Pictures/Moose.mp4",
    (3, 4): "Final Assessment/MVP Pictures/Wolf.mp4",       
    (3, 5): "Final Assessment/MVP Pictures/Spider.mp4",

    ("SHADOW_TUTORIAL_STAGE_1", 0): "Final Assessment/MVP Pictures/Spider.mp4",
    ("SHADOW_TUTORIAL_STAGE_2", 0): "Final Assessment/MVP Pictures/Spider.mp4"
}

default_bg_path = "MVP Pictures/level_bg.mp4"
bg_video = cv2.VideoCapture(default_bg_path)
last_loaded_video_path = default_bg_path

# ── EXTENDED DISPLAY CONFIGURATION ───────────────────────────────────────────
window_name = "Gesture Recognition"

# Create normal window first so OS handles window geometry properly
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

MONITOR_X_OFFSET = 1920  

# Move window to extended monitor before toggling fullscreen
cv2.moveWindow(window_name, MONITOR_X_OFFSET, 0)

# Brief pause to give the OS window manager time to relocate the window
cv2.waitKey(100)

# Enable borderless fullscreen on the target monitor
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
# ─────────────────────────────────────────────────────────────────────────────

MATCH_MIN_THRESHOLD = 0.15    
MATCH_THRESHOLD     = 0.48 
BASE_DURATION, MAX_LEVELS = 30.0, 3  

current_level, current_cycle = 1, 0
player_lives = 3
round_duration = BASE_DURATION
matched_targets = [False] * 4 
HOLD_REQUIRED_DURATION = 2.0 
match_hold_start_time = None  

transition_start_time = None
round_start_time = time.time()

game_status = "TUTORIAL_STAGE_1"

status_display_time = 0.0
last_active_cue_cmd = None
level3_unlocked = False  
send_osc_signal(reaper_client, "/action/40162", 1) #game start
send_osc_signal(reaper_client, "/track/5/mute", 1) #game state track mute

tutorial_targets_stage2 = [("level2_stage2_2", "Left"), ("game_start_right", "Right"), ("left_3", "Left"), ("level2_stage2_1", "Right")]
tutorial_targets_stage1 = [("left_3", "Left"), ("right_2", "Right"), ("left_4", "Left"), ("right_3", "Right")]

shadow_tutorial_targets_stage1 = [("spider", "AICameraClass")]
shadow_tutorial_targets_stage2 = [("spider", "AICameraClass")]

def start_game_sequence():
    global game_status, round_start_time, transition_start_time, current_level, current_cycle, player_lives, target_keys, matched_targets, round_duration, last_active_cue_cmd, level3_unlocked
    print("[+] Starting game sequence...")
    player_lives = 3
    current_level = 1
    current_cycle = 0
    level3_unlocked = False
    round_duration = BASE_DURATION
    last_active_cue_cmd = None
    target_keys = get_new_targets(lvl=1)
    matched_targets = [False] * len(target_keys)
    transition_start_time = time.time()
    game_status = "TRANSITION_SCENE"
    round_start_time = time.time()
    send_osc_signal(reaper_client, "/action/41251", 1) #team B game start
    send_osc_signal(reaper_client, "/track/15/mute", 0) #time-ticking unmute
    game_status = "PLAYING"

while True:
    ret, frame = cap.read() 
    if not ret: continue
    if current_level == 3:  
        frame = cv2.flip(frame, 1) 
    raw_camera_feed = frame.copy()
    h, w, _ = frame.shape
    
    # ── DYNAMIC STAGE VIDEO LOADING ENGINE ──
    if game_status in ["SHADOW_TUTORIAL_STAGE_1", "SHADOW_TUTORIAL_STAGE_2"]:
        target_video_path = VIDEO_STAGE_MAP.get((game_status, 0), default_bg_path)
    elif current_level == 3 and not level3_unlocked:
        target_video_path = VIDEO_STAGE_MAP.get((3, 0), default_bg_path)
    else:
        stage_idx = current_cycle + 1 if current_level == 3 else current_cycle
        target_video_path = VIDEO_STAGE_MAP.get((current_level, stage_idx), default_bg_path)
    
    if target_video_path != last_loaded_video_path:
        bg_video.release()
        bg_video = cv2.VideoCapture(target_video_path)
        last_loaded_video_path = target_video_path

    VIDEO_SPEED_MULTIPLIER = 4  
    v_frame = None
    if bg_video.isOpened():
        for _ in range(VIDEO_SPEED_MULTIPLIER - 1):
            if not bg_video.grab():
                bg_video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                break
        v_ret, v_frame = bg_video.read()
        if not v_ret:
            bg_video.set(cv2.CAP_PROP_POS_FRAMES, 0)
            v_ret, v_frame = bg_video.read()

    # ── ASYNCHRONOUS MEDIAPIPE PROCESSING ──
    if game_status in ["START_SCREEN", "TUTORIAL_STAGE_1", "TUTORIAL_STAGE_2"] or (game_status not in ["TRANSITION_SCENE", "GAME_CLEAR", "WIN", "LOSE", "GAMEOVER", "STAGE_CLEAR", "STAGE_CLEAR_TUT1", "STAGE_CLEAR_TUT2", "SHADOW_START_PAGE", "SHADOW_TUTORIAL_STAGE_1", "SHADOW_TUTORIAL_STAGE_2", "TRANSITION_TO_SHADOW_TUTORIAL"] and current_level != 3): 
        if not _mp_is_processing:
            _mp_is_processing = True
            small_rgb = cv2.resize(raw_camera_feed, (320, 180), interpolation=cv2.INTER_LINEAR) 
            small_rgb = cv2.cvtColor(small_rgb, cv2.COLOR_BGR2RGB) 
            threading.Thread(target=_run_mediapipe_async, args=(small_rgb,), daemon=True).start()

    with _mp_lock:
        result = _mp_result
    
    hud_lines, current_time = [], time.time() 

    if game_status == "START_SCREEN":
        player_lives = player_lives
        round_duration = BASE_DURATION
        time_left = round_duration
        
        total_hands_detected = 0
        if result and result.multi_hand_landmarks:
            hand_colors = [(0, 165, 255), (255, 0, 150), (0, 255, 100), (255, 150, 0)]
            for idx, hand_landmarks in enumerate(result.multi_hand_landmarks):
                if idx >= 4: break
                total_hands_detected += 1
                draw_cyber_hand(frame, hand_landmarks, hand_colors[idx % len(hand_colors)])
        
        if PIC1 is not None:
            pip_feed_with_landmarks = frame.copy()
            draw_fullscreen_image(frame, PIC1)
            pip_w, pip_h = 400, 225
            pip_x, pip_y = w - pip_w - 30, 30
            pip_thumb = cv2.resize(pip_feed_with_landmarks, (pip_w, pip_h), interpolation=cv2.INTER_LINEAR)
            frame[pip_y:pip_y+pip_h, pip_x:pip_x+pip_w] = pip_thumb
            cv2.rectangle(frame, (pip_x, pip_y), (pip_x + pip_w, pip_y + pip_h), (0, 255, 255), 1, cv2.LINE_AA)
            draw_sleek_text(frame, "LIVE FEED", (pip_x + 6, pip_y + 15), font_scale=0.35, thickness=1, color=(0, 255, 255))
            draw_sleek_text(frame, f"Total Hands Detected : {total_hands_detected}/4", (pip_x - 40, pip_y + pip_h + 20), font_scale=0.45, thickness=1, color=(0, 255, 255))
        else:
            draw_sleek_text(frame, "WEAPON UPGRADE ARENA", (w // 2 - 280, h // 2 - 40), font_scale=1.3, thickness=2, color=(0, 255, 255))

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
            if match_hold_start_time is None: 
                match_hold_start_time = current_time
                send_osc_signal(reaper_client, "/action/41253", 1) #loading
                send_osc_signal(reaper_client, "/track/15/mute", 0) #time-ticking mute
            elif current_time - match_hold_start_time >= HOLD_REQUIRED_DURATION:
                match_hold_start_time = None
                game_status = "TUTORIAL_STAGE_1"
                matched_targets = [False] * 4
                send_osc_signal(reaper_client, "/action/41255", 1) 
        else:
            if match_hold_start_time is not None:
                match_hold_start_time = None

    elif game_status in ["TUTORIAL_STAGE_1", "TUTORIAL_STAGE_2", "SHADOW_TUTORIAL_STAGE_1", "SHADOW_TUTORIAL_STAGE_2"]:
        if game_status == "TUTORIAL_STAGE_1":
            active_tut_targets = tutorial_targets_stage1
        elif game_status == "TUTORIAL_STAGE_2":
            active_tut_targets = tutorial_targets_stage2
        elif game_status == "SHADOW_TUTORIAL_STAGE_1":
            active_tut_targets = shadow_tutorial_targets_stage1
        else:
            active_tut_targets = shadow_tutorial_targets_stage2

        if len(matched_targets) != len(active_tut_targets):
            matched_targets = [False] * len(active_tut_targets)

        frame = raw_camera_feed.copy()
            
        if "SHADOW" in game_status:
            draw_dotted_rectangle(frame, (100, 220), (750, 600), (0, 255, 255), thickness=2, gap=12)
            draw_sleek_text(frame, "PLAYERS ZONE", (220, 200), font_scale=0.55, thickness=1, color=(0, 255, 255))
        else:
            draw_dotted_rectangle(frame, (100, 320), (550, 700), (0, 255, 255), thickness=2, gap=12)
            draw_dotted_rectangle(frame, (730, 320), (1180, 700), (0, 255, 255), thickness=2, gap=12)
            draw_sleek_text(frame, "PLAYER 1 ZONE", (220, 300), font_scale=0.55, thickness=1, color=(0, 255, 255))
            draw_sleek_text(frame, "PLAYER 2 ZONE", (850, 300), font_scale=0.55, thickness=1, color=(0, 255, 255))

        tut_box_x, tut_box_y, tut_box_w, tut_box_h = 420, 30, 440, 150
        cv2.rectangle(frame, (tut_box_x, tut_box_y), (tut_box_x + tut_box_w, tut_box_y + tut_box_h), (20, 20, 20), -1, cv2.LINE_AA)
        cv2.rectangle(frame, (tut_box_x, tut_box_y), (tut_box_x + tut_box_w, tut_box_y + tut_box_h), (0, 255, 255), 2, cv2.LINE_AA)
        
        if "SHADOW" in game_status:
            stage_num_str = "1/1: ANIMAL SHADOWS"
            title_prefix = "SHADOW TUTORIAL "
        else:
            stage_num_str = "1/2: SAME GESTURES" if game_status == "TUTORIAL_STAGE_1" else "2/2: DIFFERENT GESTURES"
            title_prefix = "TUTORIAL "

        draw_sleek_text(frame, f"{title_prefix}{stage_num_str}", (tut_box_x + 30, tut_box_y + 30), font_scale=0.55, thickness=2, color=(0, 255, 255))
        draw_sleek_text(frame, "HOW TO PLAY:", (tut_box_x + 20, tut_box_y + 60), font_scale=0.5, thickness=2, color=(255, 255, 255))
        draw_sleek_text(frame, "1) Match the gestures on screen within the dotted box.", (tut_box_x + 20, tut_box_y + 90), font_scale=0.38, thickness=1, color=(200, 200, 200))
        draw_sleek_text(frame, "2) Hold the gesture steady until the bar below fills up.", (tut_box_x + 20, tut_box_y + 120), font_scale=0.38, thickness=1, color=(200, 200, 200))

        if "SHADOW" in game_status:
            matched_targets = [False] * len(active_tut_targets)
            target_gname = active_tut_targets[0][0]
            
            b_size = 300
            margin_y = 50
            bx, by = (w // 2) + 480 - (b_size // 2), margin_y
            
            if model is not None:
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
                
                draw_sleek_text(frame, f"AI Status: {ai_status_str}", (30, h - 50), font_scale=0.6, thickness=2, color=ai_text_color)
                
                if predicted_name.lower().strip() == target_gname.lower().strip() and confidence_score >= CONFIDENCE_THRESHOLD:
                    matched_targets[0] = True

            box_color = (0, 255, 0) if matched_targets[0] else (0, 255, 255)
            draw_dotted_rectangle(frame, (bx, by), (bx + b_size, by + b_size), box_color, thickness=2, gap=12)
            draw_sleek_text(frame, f"AI TARGET: {target_gname.upper()}", (bx - 20, by - 10), font_scale=0.5, thickness=1, color=box_color)

            if v_frame is not None:
                v_resized = cv2.resize(v_frame, (b_size, b_size), interpolation=cv2.INTER_LINEAR)
                frame[by:by + b_size, bx:bx + b_size] = v_resized
            elif target_gname in PRELOADED_IMAGES:
                overlay_preloaded_picture(frame, PRELOADED_IMAGES[target_gname], bx, by, b_size)
                
            if matched_targets[0]:
                cv2.rectangle(frame, (bx, by), (bx + b_size, by + b_size), (0, 255, 0), 2, cv2.LINE_AA)
                draw_sleek_text(frame, "MATCHED", (bx + 5, by + 20), font_scale=0.45, thickness=1, color=(0, 255, 0))

        else:
            positions = [(20, 50), (210, 50), (890, 50), (1080, 50)]
            for i, (g_name, h_label) in enumerate(active_tut_targets):
                bx, by = positions[i]
                b_size = 180
                box_color = (0, 255, 0) if matched_targets[i] else (0, 255, 255)
                
                cv2.rectangle(frame, (bx, by), (bx + b_size, by + b_size), box_color, 2, cv2.LINE_AA)
                p_lbl = f"P1 {h_label.upper()}" if i < 2 else f"P2 {h_label.upper()}"
                draw_sleek_text(frame, p_lbl, (bx + 10, by - 10), font_scale=0.45, thickness=1, color=box_color)
                
                img_key_hand_specific = f"{g_name}_{h_label.lower()}"
                img_key_to_use = img_key_hand_specific if img_key_hand_specific in PRELOADED_IMAGES else g_name

                if img_key_to_use in PRELOADED_IMAGES:
                    overlay_preloaded_picture(frame, PRELOADED_IMAGES[img_key_to_use], bx, by, b_size)
                
                if matched_targets[i]:
                    draw_sleek_text(frame, "MATCHED", (bx + 20, by + b_size - 15), font_scale=0.5, thickness=2, color=(0, 255, 0))

            matched_targets = [False] * 4
            if result and result.multi_hand_landmarks and result.multi_handedness:
                detected_hands = []
                for idx, (hand_landmarks, bandwidth) in enumerate(zip(result.multi_hand_landmarks, result.multi_handedness)):
                    if idx >= 4: break
                    detected_label = bandwidth.classification[0].label
                    draw_cyber_hand(frame, hand_landmarks, (0, 255, 255))
                    lm_array = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark])
                    detected_hands.append((lm_array, detected_label))

                assigned_targets = set()
                for lm_array, detected_label in detected_hands:
                    for i, (g_name, h_label) in enumerate(active_tut_targets):
                        if i in assigned_targets: continue
                        if h_label.lower().strip() == detected_label.lower().strip():
                            matched_gest, _ = match_gesture(lm_array, detected_label, templates, threshold=MATCH_THRESHOLD)
                            if matched_gest == g_name:
                                matched_targets[i] = True
                                assigned_targets.add(i)
                                break

        if all(matched_targets):
            if match_hold_start_time is None:
                match_hold_start_time = current_time
                # send_osc_signal(reaper_client, "/track/16/mute", 0) #mute the loading -- left the time ticking
                send_osc_signal(reaper_client, "/action/41253", 1) #loading
                send_osc_signal(reaper_client, "/track/15/mute", 1) #time-ticking mute
            elif current_time - match_hold_start_time >= HOLD_REQUIRED_DURATION:
                match_hold_start_time = None
                if game_status == "TUTORIAL_STAGE_1":
                    game_status = "TUTORIAL_STAGE_2"
                    send_osc_signal(reaper_client, "/action/41255", 1) #good job
                    matched_targets = [False] * 4
                elif game_status == "TUTORIAL_STAGE_2":
                    game_status, status_display_time = "STAGE_CLEAR_TUT1", current_time
                    send_osc_signal(reaper_client, "/action/40167", 1) #ai voice
                elif game_status == "SHADOW_TUTORIAL_STAGE_1":
                    game_status, status_display_time = "STAGE_CLEAR_TUT2", current_time
                    # send_osc_signal(reaper_client, "/action/41255", 1) #good job
                    # send_osc_signal(reaper_client, "/track/15/mute",1) #unmute time-ticking
                    # time.sleep(2)
                    send_osc_signal(reaper_client, "/action/41270", 1)
                    matched_targets = [False] * 4


                #not using
                elif game_status == "SHADOW_TUTORIAL_STAGE_2":
                    game_status, status_display_time = "STAGE_CLEAR_TUT2", current_time
                    matched_targets = [False] * 4
        else:
            match_hold_start_time = None

    elif game_status == "TRANSITION_SCENE":
        elapsed_transition = current_time - transition_start_time
        slide_idx = int(elapsed_transition // TRANSITION_INTERVAL)
        if slide_idx < len(TRANSITION_SLIDES): draw_fullscreen_image(frame, TRANSITION_SLIDES[slide_idx])
        else:
            game_status = "PLAYING"
            round_start_time = time.time()

    elif game_status == "TRANSITION_TO_SHADOW_TUTORIAL":
        draw_sleek_text(frame, "Initilising shadow tutorial....", (w // 2 - 300, h // 2), font_scale=1.1, thickness=2, color=(0, 255, 255))
        if current_time - status_display_time > 6.0:
            game_status = "SHADOW_TUTORIAL_STAGE_1"

    elif game_status == "PLAYING":
        if current_level == 3 and not level3_unlocked:
            time_left = round_duration
            send_osc_signal(reaper_client, "/action/41253", 1) #loading
            send_osc_signal(reaper_client, "/track/15/mute", 0)#time-ticking mute
        else:
            time_left = max(0.0, round_duration - (current_time - round_start_time))
            if time_left <= 0:
                player_lives -= 1
                
                if player_lives <= 0:
                    game_status, status_display_time = "GAMEOVER", current_time 
                    send_osc_signal(gma3_client, GMA3_ADDRESS, "go macro 12 ")
                    send_osc_signal(reaper_client, "/action/40163", 1) 
                    send_osc_signal(reaper_client, "/track/5/mute", 0)
                else:
                    game_status, status_display_time = "LOSE", current_time
                    send_osc_signal(gma3_client, GMA3_ADDRESS, "on sequence 120 cue 1") 
                    send_osc_signal(reaper_client, "/action/41252", 1) 

    elif game_status in ["WIN", "LOSE", "GAME_CLEAR", "GAMEOVER", "STAGE_CLEAR", "STAGE_CLEAR_TUT1", "STAGE_CLEAR_TUT2"]:
        time_left = 0
        GAMEOVER_BUFFER_SECONDS = 2.5
        BUFFER_SECONDS = 1.5
        LOSE_DISPLAY_SECONDS = 3.5  
        STAGE_CLEAR_BUFFER_SECONDS =5.0
        WELL_PLAYED = 120.0
        if game_status == "GAMEOVER":
            # send_osc_signal(reaper_client, "/action/40163", 1) 
            display_timeout = GAMEOVER_BUFFER_SECONDS
        elif game_status == "GAME_CLEAR":
            
            display_timeout = WELL_PLAYED
        elif game_status == "LOSE":
            # send_osc_signal(reaper_client, "/action/41252", 1) 
            display_timeout = LOSE_DISPLAY_SECONDS 
        elif game_status in ["STAGE_CLEAR", "STAGE_CLEAR_TUT1", "STAGE_CLEAR_TUT2"]:
            # send_osc_signal(reaper_client, "/action/41254", 1) 
            display_timeout = STAGE_CLEAR_BUFFER_SECONDS
        else:
            display_timeout = BUFFER_SECONDS

        if current_time - status_display_time > display_timeout:  
            if game_status == "STAGE_CLEAR":
                target_keys = get_new_targets(lvl=current_level)
                matched_targets = [False] * len(target_keys)
                round_duration = BASE_DURATION
                round_start_time, game_status = time.time(), "PLAYING" 
                # 2. Only return to Marker 11 AFTER the 3-second display time finishes
                send_osc_signal(reaper_client, "/action/41253", 1) 
                send_osc_signal(reaper_client, "/track/16/mute", 1)
                send_osc_signal(reaper_client, "/track/15/mute", 0)

                last_active_cue_cmd = None

            elif game_status == "STAGE_CLEAR_TUT1":
                start_game_sequence()

            elif game_status == "STAGE_CLEAR_TUT2":
                # send_osc_signal(reaper_client, "/action/41270",1)
                # time.sleep(5)
                send_osc_signal(reaper_client, "/action/41251", 1)
                send_osc_signal(reaper_client, "/track/15/mute",0)
                level3_unlocked = True
                round_start_time = current_time
                game_status = "PLAYING"
                matched_targets = [False] * len(target_keys)
                last_active_cue_cmd = None

            elif game_status == "WIN":
                target_keys = get_new_targets(lvl=current_level)
                send_osc_signal(reaper_client, "/action/41251", 1) 
                send_osc_signal(reaper_client, "/track/15/mute", 0)
                matched_targets = [False] * len(target_keys)
                round_duration = BASE_DURATION
                round_start_time, game_status = time.time(), "PLAYING" 

            elif game_status == "LOSE":
                target_keys = get_new_targets(lvl=current_level)
                send_osc_signal(reaper_client, "/action/41251", 1) 
                send_osc_signal(reaper_client, "/track/15/mute", 0)
                matched_targets = [False] * len(target_keys)
                round_duration = BASE_DURATION
                round_start_time, game_status = time.time(), "PLAYING"
                last_active_cue_cmd = None
         
            elif game_status == "GAMEOVER":
                cap.release()
                cap = cv2.VideoCapture(1 + cv2.CAP_DSHOW) 
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                current_level, current_cycle, game_status = 1, 0, "TUTORIAL_STAGE_1"
                level3_unlocked = False
                target_keys, matched_targets = get_new_targets(lvl=1), [False] * 4
                threading.Timer(GAMEOVER_BUFFER_SECONDS, back_to_start, args=[]).start()
                send_osc_signal(gma3_client, GMA3_ADDRESS, "go macro 12")
                back_to_start()
                last_active_cue_cmd = None
              
            elif game_status == "GAME_CLEAR":
                pass

    # ── RENDER OVERLAYS ───────────────────────────────────────────────────────
    margin_x, margin_y, spacing = 50, 50, 200 
    colors = [(0, 255, 255), (0, 0, 255), (0, 255, 0), (255, 0, 0)]

    if game_status == "PLAYING" and not (current_level == 3 and not level3_unlocked):
        time_left = max(0.0, round_duration - (current_time - round_start_time))

        max_stages = MAX_STAGES_PER_LEVEL.get(current_level, 1)
        title = f"LEVEL {current_level} STAGE {current_cycle + 1}/{max_stages}"
        draw_sleek_text(frame, title, (530, 45), font_scale=0.55, thickness=1, color=(255, 255, 255))

        timer_ratio = time_left / round_duration if round_duration > 0 else 0
        timer_ratio = max(0.0, min(1.0, timer_ratio))
        if timer_ratio > 0.5:
            factor = (1.0 - timer_ratio) * 2.0
            timer_color = (0, 255, int(255 * factor))
        else:
            factor = timer_ratio * 2.0
            timer_color = (0, int(255 * factor), 255)

        show_timer = True
        if time_left <= 10.0:
            show_timer = (int(current_time * 4) % 2) == 0

        if show_timer:
            draw_sleek_text(frame, f"Time Left: {time_left:.1f}s", (500, 80), font_scale=0.8, thickness=2, color=timer_color)
        
        draw_hearts(frame, player_lives, max_lives=3, x_start=500, y=100, size=60, gap=8)

        if current_level in [1, 2]:
            draw_dotted_rectangle(frame, (100, 320), (550, 700), (0, 255, 255), thickness=2, gap=12)
            draw_dotted_rectangle(frame, (730, 320), (1180, 700), (0, 255, 255), thickness=2, gap=12)
            draw_sleek_text(frame, "PLAYER 1 ZONE", (220, 300), font_scale=0.55, thickness=1, color=(0, 255, 255))
            draw_sleek_text(frame, "PLAYER 2 ZONE", (850, 300), font_scale=0.55, thickness=1, color=(0, 255, 255))
        elif current_level == 3 and level3_unlocked:
            draw_dotted_rectangle(frame, (100, 220), (750, 600), (0, 255, 255), thickness=2, gap=12)
            draw_sleek_text(frame, "PLAYERS ZONE", (220, 200), font_scale=0.55, thickness=1, color=(0, 255, 255))

    if match_hold_start_time is not None:
        elapsed_hold = current_time - match_hold_start_time
        hold_ratio = min(1.0, elapsed_hold / HOLD_REQUIRED_DURATION)
        bar_x, bar_y, bar_w, bar_h = 480, 640 if game_status in ["TUTORIAL_STAGE_1", "TUTORIAL_STAGE_2", "SHADOW_TUTORIAL_STAGE_1", "SHADOW_TUTORIAL_STAGE_2"] else 520, 320, 20
        fill_w = int(bar_w * hold_ratio)
        
        overlay = frame.copy()
        cv2.rectangle(overlay, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (80, 40, 0), -1, cv2.LINE_AA)
        if fill_w > 0: cv2.rectangle(overlay, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), (255, 255, 0), -1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)
        
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (0, 255, 255), 1, cv2.LINE_AA)
        for marker in range(bar_x + 20, bar_x + bar_w, 20):
            cv2.line(frame, (marker, bar_y), (marker, bar_y + bar_h), (0, 255, 255), 1)
        draw_sleek_text(frame, f"SYSTEM SYNC: {int(hold_ratio * 100)}%", (bar_x, bar_y - 8), font_scale=0.45, thickness=1, color=(0, 255, 255))

    if game_status not in ["START_SCREEN", "TUTORIAL_STAGE_1", "TUTORIAL_STAGE_2", "SHADOW_TUTORIAL_STAGE_1", "SHADOW_TUTORIAL_STAGE_2", "STAGE_CLEAR_TUT1", "STAGE_CLEAR_TUT2", "TRANSITION_SCENE", "GAME_CLEAR", "WIN", "LOSE", "GAMEOVER", "STAGE_CLEAR", "TRANSITION_TO_SHADOW_TUTORIAL"]:
        if current_level == 3:
            current_box_size = 300
        elif current_level == 2:
            current_box_size = 200
        else:
            current_box_size = box_size
        
        if current_level == 3:
            render_spacing = 0
            render_margin = (w // 2) - (current_box_size // 2)
        else:
            render_spacing = spacing
            render_margin = margin_x

        for i, key in enumerate(target_keys):
            if current_level == 3 and not level3_unlocked:
                break

            if current_level == 2 and i in [1, 3]:
                continue

            gesture_name, hand_label = key
            
            if match_hold_start_time is not None:
                elapsed_hold = current_time - match_hold_start_time
                hold_ratio = min(1.0, max(0.0, elapsed_hold / HOLD_REQUIRED_DURATION))
            else:
                hold_ratio = 0.0

            if current_level == 3:
                center_x_start, center_y_start = (w // 2)+480, margin_y + (current_box_size // 2)
                size_start = 300
                size_end = 150
                center_x_end, center_y_end = 40 + (size_end // 2), h - 40 - (size_end // 2)
                
                active_box_size = int(size_start + (size_end - size_start) * hold_ratio)
                center_x = int(center_x_start + (center_x_end - center_x_start) * hold_ratio)
                center_y = int(center_y_start + (center_y_end - center_y_start) * hold_ratio)
                
                x_min, y_min = center_x - (active_box_size // 2), center_y - (active_box_size // 2)
                x_max, y_max = center_x + (active_box_size // 2), center_y + (active_box_size // 2)

                if v_frame is not None and active_box_size > 0:
                    y1, y2 = max(0, y_min), min(h, y_max)
                    x1, x2 = max(0, x_min), min(w, x_max)
                    target_w = x2 - x1
                    target_h = y2 - y1
                    if target_w > 0 and target_h > 0:
                        v_resized = cv2.resize(v_frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
                        frame[y1:y2, x1:x2] = v_resized
            else:
                size_start = current_box_size
                size_end = int(current_box_size * 0.5)

                p1_hand_gap = 40 
                p2_hand_gap = 40 
                player_gap  = 320 
                if i == 0: offset = 0
                elif i == 1: offset = p1_hand_gap
                elif i == 2: offset = p1_hand_gap + player_gap
                elif i == 3: offset = p1_hand_gap + player_gap + p2_hand_gap
                else: offset = 0

                center_x_start = render_margin + (i * render_spacing) + offset + (size_start // 2)
                center_y_start = margin_y + (size_start // 2)

                if current_level == 2:
                    if i == 0:
                        center_x_start = 325
                        center_y_start = 170
                    elif i == 2:
                        center_x_start = 955
                        center_y_start = 170

                center_x_end = center_x_start
                center_y_end = h - 40 - (size_end // 2)
                
                active_box_size = int(size_start + (size_end - size_start) * hold_ratio)
                center_x = int(center_x_start + (center_x_end - center_x_start) * hold_ratio)
                center_y = int(center_y_start + (center_y_end - center_y_start) * hold_ratio)
                
                x_min, y_min = center_x - (active_box_size // 2), center_y - (active_box_size // 2)
                x_max, y_max = center_x + (active_box_size // 2), center_y + (active_box_size // 2)
            
            color = colors[i % len(colors)]
            
            if current_level == 3:
                draw_dotted_rectangle(frame, (x_min, y_min), (x_max, y_max), color, thickness=2, gap=12)
                draw_sleek_text(frame, f"AI TARGET: {gesture_name.upper()}", (x_min - 20, y_min - 10), font_scale=0.5, thickness=1, color=color)
            elif current_level == 2:
                player_lbl = "PLAYER 1" if i == 0 else "PLAYER 2"
                draw_sleek_text(frame, player_lbl, (x_min - 10, y_min - 10), font_scale=0.45, thickness=1, color=color)
            elif current_level == 1:
                player_lbl = "PLAYER 1" if i in [0, 1] else "PLAYER 2"
                draw_sleek_text(frame, player_lbl, (x_min + 5, y_min - 10), font_scale=0.5, thickness=1, color=color)
            else:
                draw_sleek_text(frame, f"TARGET {i+1}", (x_min + 5, y_min - 10), font_scale=0.5, thickness=1, color=color)

            img_key_hand_specific = f"{gesture_name}_{hand_label.lower()}"
            img_key_to_use = img_key_hand_specific if img_key_hand_specific in PRELOADED_IMAGES else gesture_name

            if img_key_to_use in PRELOADED_IMAGES:
                overlay_preloaded_picture(frame, PRELOADED_IMAGES[img_key_to_use], x_min, y_min, active_box_size)
            
            if matched_targets[i]:
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2, cv2.LINE_AA)
                draw_sleek_text(frame, "MATCHED", (x_min + 5, y_min + 20), font_scale=0.45, thickness=1, color=(0, 255, 0))

        # ── PROCESS RECOGNITION LOGIC ────────────────────────────────────────
        matched_targets = [False] * len(target_keys)
        
        if (current_level == 3 or game_status == "SHADOW_START_PAGE") and model is not None:
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
            
            if game_status == "SHADOW_START_PAGE" or (current_level == 3 and not level3_unlocked):
                if PIC6 is not None:
                    pip_feed_with_landmarks = frame.copy()
                    draw_fullscreen_image(frame, PIC6)
                    
                    pip_w, pip_h = 400, 225
                    pip_x, pip_y = w - pip_w - 30, 30
                    pip_thumb = cv2.resize(pip_feed_with_landmarks, (pip_w, pip_h), interpolation=cv2.INTER_LINEAR)
                    frame[pip_y:pip_y+pip_h, pip_x:pip_x+pip_w] = pip_thumb
                    cv2.rectangle(frame, (pip_x, pip_y), (pip_x + pip_w, pip_y + pip_h), (0, 255, 255), 1, cv2.LINE_AA)
                    draw_sleek_text(frame, "LIVE FEED", (pip_x + 6, pip_y + 15), font_scale=0.35, thickness=1, color=(0, 255, 255))
                else:
                    current_box_size = 280
                    center_x, center_y = w // 2, h // 2 - 30
                    x_min, y_min = center_x - (current_box_size // 2), center_y - (current_box_size // 2)
                    x_max, y_max = center_x + (current_box_size // 2), center_y + (current_box_size // 2)

                    cv2.rectangle(frame, (x_min - 10, y_min - 10), (x_max + 10, y_max + 10), (20, 20, 20), -1, cv2.LINE_AA)
                    cv2.rectangle(frame, (x_min - 10, y_min - 10), (x_max + 10, y_max + 10), (0, 255, 255), 2, cv2.LINE_AA)
                    
                    draw_sleek_text(frame, "LEVEL 3 - START PAGE", (x_min - 15, y_min - 50), font_scale=0.8, thickness=2, color=(255, 255, 0))
                    draw_sleek_text(frame, "DO THIS GESTURE TO START", (x_min - 35, y_min - 20), font_scale=0.65, thickness=2, color=(0, 255, 255))

                    if "palmm" in PRELOADED_IMAGES:
                        overlay_preloaded_picture(frame, PRELOADED_IMAGES["palmm"], x_min, y_min, current_box_size)
                    else:
                        draw_sleek_text(frame, "SHOW PALM GESTURE", (x_min + 30, center_y), font_scale=0.6, thickness=2, color=(0, 255, 255))

                draw_sleek_text(frame, f"AI Gateway Status: {ai_status_str}", (30, h - 50), font_scale=0.6, thickness=2, color=ai_text_color)
                
                if predicted_name.lower().strip() == "palm" and confidence_score >= CONFIDENCE_THRESHOLD:
                    if match_hold_start_time is None:
                        match_hold_start_time = current_time
                        send_osc_signal(reaper_client, "/action/41253", 1) #loading
                        send_osc_signal(reaper_client, "/track/15/mute", 1) #time-ticking mute
                    elif current_time - match_hold_start_time >= HOLD_REQUIRED_DURATION:
                        send_osc_signal(reaper_client, "/action/41270",1) #shadow game
                        time.sleep(5)
                        send_osc_signal(reaper_client, "/action/41251",1) #start game team b
                        send_osc_signal(reaper_client, "/track/15/mute",0) #unmute time-ticking
                        match_hold_start_time = None
                        level3_unlocked = True  
                        round_start_time = current_time  
                        game_status = "PLAYING"    
                else:
                    if match_hold_start_time is not None:
                        match_hold_start_time = None
                        # send_osc_signal(reaper_client, "/action/41251", 1) 
                        # send_osc_signal(reaper_client, "/track/15/mute", 0)    
            else:
                draw_sleek_text(frame, f"AI Status: {ai_status_str}", (30, h - 50), font_scale=0.6, thickness=2, color=ai_text_color)
                req_target = target_keys[0][0].lower().strip()
                if predicted_name.lower().strip() == req_target and confidence_score >= CONFIDENCE_THRESHOLD:
                    matched_targets[0] = True

        if result and result.multi_hand_landmarks and result.multi_handedness:
            hand_colors = [(0, 165, 255), (255, 0, 150), (0, 255, 100), (255, 150, 0)]
            detected_hands = []
            for idx, (hand_landmarks, bandwidth) in enumerate(zip(result.multi_hand_landmarks, result.multi_handedness)):
                if idx >= 4: break
                detected_label = bandwidth.classification[0].label
                color = hand_colors[idx % len(hand_colors)]
                
                if current_level != 3:
                    draw_cyber_hand(frame, hand_landmarks, color)
                lm_array = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark])
                hand_span = np.max(lm_array[:, :2], axis=0) - np.min(lm_array[:, :2], axis=0)
                if hand_span[0] < 0.05 or hand_span[1] < 0.05: continue
                detected_hands.append((lm_array, detected_label))

            if current_level == 1:
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
                
                if raw_matches[0] and raw_matches[1]:
                    matched_targets[0] = True
                    matched_targets[1] = True
                
                if raw_matches[2] and raw_matches[3]:
                    matched_targets[2] = True
                    matched_targets[3] = True

        # ── STATE STAGE PROGRESSION HANDLER ──────────────────────────────────
        if all(matched_targets) and not (current_level == 3 and not level3_unlocked):
            if match_hold_start_time is None:
                match_hold_start_time = current_time
                send_osc_signal(reaper_client, "/action/41253", 1) 
                send_osc_signal(reaper_client, "/track/16/mute", 0)

            elif current_time - match_hold_start_time >= HOLD_REQUIRED_DURATION:
                match_hold_start_time = None
                
                current_stage = current_cycle + 1
                current_cycle += 1
                max_cycles_needed = MAX_STAGES_PER_LEVEL.get(current_level, 1)
                send_osc_signal(reaper_client, "/action/41254", 1)
                send_osc_signal(gma3_client,GMA3_ADDRESS,"go sequence 120 cue 2")

                # Send REAPER OSC marker based on game state
                if current_cycle < max_cycles_needed:
                    game_status, status_display_time = "STAGE_CLEAR", current_time
                    send_osc_signal(reaper_client, "/action/41254", 1)
                else:
                    # send_osc_signal(reaper_client, "/action/41251", 1)
                    
                    if current_level == 3:
                        game_status, status_display_time = "GAME_CLEAR", current_time
                        send_osc_signal(reaper_client, "/track/5/mute", 0)
                        send_osc_signal(reaper_client, "/action/40164", 1) #test it
                        time.sleep(5)
                        send_osc_signal(reaper_client, "/action/40160", 1) #transition to team e
                        send_osc_signal(gma3_client,GMA3_ADDRESS,"go macro 13")

                          
                    else:
                        current_level += 1
                        current_cycle = 0
                        
                        if current_level == 3:
                            # cap.release()
                            # cap = cv2.VideoCapture(0 + cv2.CAP_DSHOW)
                            # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                            # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                            # cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            target_keys = get_new_targets(lvl=3) # Refreshes level 3 targets starting from index 0
                            game_status, status_display_time = "TRANSITION_TO_SHADOW_TUTORIAL", current_time # Transition text before shadow tutorial
                            # send_osc_signal(reaper_client, "/action/41251", 1) 
                            # send_osc_signal(reaper_client, "/track/15/mute", 1) 
                            send_osc_signal(reaper_client, "/action/41268", 1) #ai voice
                            send_osc_signal(gma3_client,GMA3_ADDRESS,"go macro 11")

                        
                            match_hold_start_time = None
                        else:
                            game_status, status_display_time = "WIN", current_time
        elif not (current_level == 3 and not level3_unlocked):
                match_hold_start_time = None  

    if game_status in ["WIN", "LOSE", "GAME_CLEAR", "GAMEOVER", "STAGE_CLEAR", "STAGE_CLEAR_TUT1", "STAGE_CLEAR_TUT2"]:
        if game_status == "STAGE_CLEAR":
            draw_sleek_text(frame, "WELL PLAYED!", (w // 2 - 140, h // 2), font_scale=1.2, thickness=2, color=(0, 255, 0))
        elif game_status == "STAGE_CLEAR_TUT1":
            draw_sleek_text(frame, "TUTORIAL 1 COMPLETED!", (w // 2 - 240, h // 2), font_scale=1.2, thickness=2, color=(0, 255, 0))
        elif game_status == "STAGE_CLEAR_TUT2":
            draw_sleek_text(frame, "SHADOW TUTORIAL COMPLETED!", (w // 2 - 300, h // 2), font_scale=1.2, thickness=2, color=(0, 255, 0))
        elif game_status == "WIN":
            draw_sleek_text(frame, f"LEVEL {current_level - 1} CLEAR", (w // 2 - 160, h // 2), font_scale=1.1, thickness=2, color=(0, 255, 0))
        elif game_status == "LOSE":
            draw_sleek_text(frame, "PHANTOM BLASTER CHARGE FAILED", (w // 2 - 240, h // 2), font_scale=1.0, thickness=1, color=(0, 0, 255))
            draw_sleek_text(frame, f"DON'T WORRY... YOU STILL HAVE {player_lives} LIVE(S) LEFT", (w // 2 - 400, h // 2+30), font_scale=1.0, thickness=1, color=(0, 0, 255))
        elif game_status == "GAMEOVER":
            draw_sleek_text(frame, "GAMEOVER", (w // 2 - 130, h // 2), font_scale=1.2, thickness=2, color=(0, 0, 255))
            draw_sleek_text(frame, "YOU HAVE FAILED TO CHARGE THE PHANTOM BLASTER", (w // 2 - 500, h // 2+50), font_scale=1.2, thickness=2, color=(0, 0, 255))
        elif game_status == "GAME_CLEAR":
            frame[:] = 0

    cv2.imshow("Gesture Recognition", frame)
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q') or key == 27: 
        back_to_start()
        send_osc_signal(gma3_client, GMA3_ADDRESS, "off sequence * ") 
        # send_osc_signal(reaper_client, "/action/40044", 1) 
        break
        
    elif key == ord('1') or key == ord('s'):
        if current_level == 3:
            cap.release()
            cap = cv2.VideoCapture(1 + cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        player_lives = 3
        current_level, current_cycle = 1, 0
        level3_unlocked = False
        target_keys = get_new_targets(lvl=1)
        matched_targets = [False] * len(target_keys)
        round_duration = BASE_DURATION
        send_osc_signal(reaper_client, "/action/41251", 1) 
        send_osc_signal(reaper_client, "/track/15/mute", 1) 
        round_start_time, game_status = time.time(), "PLAYING"
        last_active_cue_cmd = None
        match_hold_start_time = None

    elif key == ord('2') or key == ord('r'):
        if current_level == 3:
            cap.release()
            cap = cv2.VideoCapture(1 + cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            send_osc_signal(reaper_client, "/action/41251", 1) 
            send_osc_signal(reaper_client, "/track/15/mute", 0) 

        player_lives = 3
        current_level, current_cycle = 2, 0
        level3_unlocked = False
        target_keys = get_new_targets(lvl=2)
        matched_targets = [False] * len(target_keys)
        round_duration = BASE_DURATION
        send_osc_signal(reaper_client, "/action/41251", 1) 
        send_osc_signal(reaper_client, "/track/15/unmute", 0) 
        round_start_time, game_status = time.time(), "PLAYING"
        last_active_cue_cmd = None
        match_hold_start_time = None

    elif key == ord('3') or key == ord('t'):
        if current_level != 3:
            cap.release()
            cap = cv2.VideoCapture(0 + cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        player_lives = 3
        current_level, current_cycle = 3, 0
        level3_unlocked = False  
        target_keys = get_new_targets(lvl=3)
        matched_targets = [False] * len(target_keys)
        round_duration = BASE_DURATION
        send_osc_signal(reaper_client, "/action/41251", 1) 
        send_osc_signal(reaper_client, "/track/15/mute", 0) 
        round_start_time, game_status = time.time(), "SHADOW_START_PAGE"
        last_active_cue_cmd = None
        match_hold_start_time = None
        send_osc_signal(gma3_client,GMA3_ADDRESS,"on seq 26")

    elif key == ord('4'):
        if current_level != 3:
            cap.release()
            cap = cv2.VideoCapture(0 + cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        player_lives = 3
        current_level, current_cycle = 3, 0
        level3_unlocked = False  
        target_keys = get_new_targets(lvl=3)
        matched_targets = [False] * len(target_keys)
        round_duration = BASE_DURATION
        send_osc_signal(reaper_client, "/action/41251", 1) 
        send_osc_signal(reaper_client, "/track/15/mute", 0) 
        round_start_time, game_status = time.time(), "SHADOW_TUTORIAL_STAGE_1"
        last_active_cue_cmd = None
        match_hold_start_time = None

    elif key == ord('7'):
        if current_level != 3:
            cap.release()
            cap = cv2.VideoCapture(0 + cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        player_lives = 3
        current_level, current_cycle = 3, 0
        level3_unlocked = True  
        target_keys = get_new_targets(lvl=3)
        matched_targets = [False] * len(target_keys)
        round_duration = BASE_DURATION
        send_osc_signal(reaper_client, "/action/41251", 1) 
        send_osc_signal(reaper_client, "/track/15/mute", 0) 
        round_start_time, game_status = time.time(), "PLAYING"
        last_active_cue_cmd = None
        match_hold_start_time = None