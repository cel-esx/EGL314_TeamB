# 🖐️ Gesture Capture Tool 
## EGL314 Team B — Gesture Recognition Module 

A standalone utility for **recording, labelling, and managing hand gesture data** used by the Match The Gesture game. Built on **OpenCV** and **MediaPipe**, it captures 21 hand landmark coordinates per frame and saves them to a CSV file that the game engine reads at runtime.

---

## Table of Contents

1. [How It Works — OpenCV + MediaPipe](#how-it-works)
   - How Hands Are Detected
   - How It Is Stored for the Game
2. [File Structure](#file-structure)
3. [Requirements & Setup](#requirements--setup)
4. [How to Use](#how-to-use)
5. [Keyboard & Mouse Controls](#keyboard--mouse-controls)
6. [CSV Data Format](#csv-data-format)
7. [Troubleshooting](#troubleshooting)

---

## How It Works

### Part 1 — How Hands Are Detected

This script uses two libraries working together: **OpenCV** handles the camera feed and the window you see on screen, while **MediaPipe** does the actual hand detection.

Here is what happens every frame, step by step:

```
Webcam Frame → OpenCV reads it → Convert BGR to RGB → MediaPipe processes it
     ↓
MediaPipe finds up to 2 hands
     ↓
For each hand: outputs 21 landmark points (x, y, z coordinates)
     ↓
OpenCV draws the skeleton and labels on screen
```

**What are landmarks?**

MediaPipe does not give you a photo of a hand. Instead, it gives you **21 numbered points** that map to specific joints on the hand. Each point has:
- `x` — horizontal position (0.0 = left edge, 1.0 = right edge of frame)
- `y` — vertical position (0.0 = top, 1.0 = bottom)
- `z` — estimated depth (negative = closer to camera)

These 21 points are always in the same order, every time:

| ID | Name | Location |
|:--:|------|----------|
| 0 | WRIST | Base of hand |
| 1–4 | THUMB_CMC → THUMB_TIP | Thumb joints, base to tip |
| 5–8 | INDEX_MCP → INDEX_TIP | Index finger joints |
| 9–12 | MIDDLE_MCP → MIDDLE_TIP | Middle finger joints |
| 13–16 | RING_MCP → RING_TIP | Ring finger joints |
| 17–20 | PINKY_MCP → PINKY_TIP | Pinky joints |

> **MCP** = knuckle, **PIP** = middle joint, **DIP** = joint near tip, **TIP** = fingertip, **CMC** = base joint of thumb

Because MediaPipe always outputs the same 21 points in the same order, the game can mathematically compare your live hand pose against a saved gesture and check if they match.

**How MediaPipe knows which hand is which:**

MediaPipe also outputs a `handedness` label — either `"Left"` or `"Right"` — with a confidence score. The script uses this to colour-code the skeleton on screen (orange = Left, cyan = Right) and to correctly label which hand's data is being saved.

> ⚠️ Note: Because the webcam feed is mirrored (`cv2.flip(frame, 1)`), what MediaPipe calls "Left" appears on the right side of your screen. This is intentional and consistent.

---

### Part 2 — How It Is Stored for the Game

When you right-click to save a gesture, the script writes **one row per landmark point** into a CSV file called `new_gesture_definitions.csv`.

For a single right-click with both hands visible, that means **42 rows are written** (21 landmarks × 2 hands).

**The CSV structure:**

```
gesture_name, hand, capture_id, timestamp, landmark_id, landmark_name, x, y, z
```

| Column | Example | What it means |
|--------|---------|---------------|
| `gesture_name` | `rock` | The label you typed with G |
| `hand` | `Right` | Which hand this row belongs to |
| `capture_id` | `7` | Unique ID for this single capture snapshot |
| `timestamp` | `2026-06-18 11:05:32` | When it was saved |
| `landmark_id` | `8` | The landmark number (0–20) |
| `landmark_name` | `INDEX_TIP` | Human-readable joint name |
| `x` | `0.4812` | Normalised horizontal position |
| `y` | `0.3241` | Normalised vertical position |
| `z` | `-0.0523` | Estimated depth |

**How the game uses this file:**

At runtime, the game code loads `new_gesture_definitions.csv` and groups rows by `gesture_name` and `capture_id`. For each frame of live play, MediaPipe outputs the player's current 21 landmarks — and the game compares those coordinates against the saved samples to decide if the gesture matches.

**Multiple captures per gesture = better accuracy.** The more samples you save for a gesture (e.g., 30 captures of "rock"), the more variation the recognition model has to work with, making it more reliable across different hand sizes and angles.

---

## File Structure

```
Capture Gesture.py          ← This script
new_gesture_definitions.csv ← Auto-created on first run; stores all saved gestures
```

---

## Requirements & Setup

### Prerequisites
**Make sure to follow [SETUP](https://github.com/cel-esx/EGL314_TeamB/blob/main/Setup%20Guide.md) before proceeding**

### Webcam

Any USB or built-in webcam works. The script opens camera index `0` by default (your primary webcam). If it fails to open, check that no other application is using the webcam.

---

## How to Use

### Step 1 — Run the script

Capture Gesture.py [HERE](https://github.com/cel-esx/EGL314_TeamB/blob/main/POC/Capture%20Gesture.py)

```bash
python "Capture Gesture.py"
```


A fullscreen window will open showing your webcam feed with hand skeletons drawn over detected hands.

### Step 2 — Set a gesture name

Press **`G`** on your keyboard. A green input box appears at the bottom of the screen.  
Type the gesture name (e.g., `rock`, `paper`, `scissors`) and press **Enter**.

> Spaces are automatically converted to underscores. Names are stored in lowercase.

### Step 3 — Position your hand

Hold your hand in the shape of the gesture. Make sure:
- Your hand is fully in frame
- Fingers are clearly separated
- Lighting is decent (avoid strong backlight)

### Step 4 — Save the gesture

**Right-click** anywhere on the window. The script saves all currently detected hand landmarks to the CSV instantly.  
A green flash message confirms: `Saved #7 rock [Right(99%)]`

### Step 5 — Repeat for more samples

You do **not** need to restart the script between saves. Just keep right-clicking to save more samples of the same gesture, or press **G** again to switch to a different gesture name.

### Step 6 — Delete a gesture (if needed)

Press **`D`**, type the gesture name you want to remove, and press **Enter**. All rows for that gesture are permanently removed from the CSV.

### Step 7 — Quit

Press **`Q`** to stop the script. The CSV is saved throughout the session — no data is lost when you quit.

---

## Keyboard & Mouse Controls

| Input | Action |
|-------|--------|
| `G` | Start typing a gesture name to capture |
| `D` | Start typing a gesture name to delete/purge |
| `Enter` | Confirm the typed name |
| `Esc` | Cancel typing mode (safe exit if you pressed the wrong key) |
| `Right Click` | Save current hand landmarks to CSV |
| `Q` | Quit the script |

---

## CSV Data Format

The output file `new_gesture_definitions.csv` uses the following columns:

```
gesture_name, hand, capture_id, timestamp, landmark_id, landmark_name, x, y, z
```

**Example rows for one right-click capture:**

```csv
rock,Right,1,2026-06-18 11:05:32,0,WRIST,0.5012,0.7841,-0.0012
rock,Right,1,2026-06-18 11:05:32,1,THUMB_CMC,0.4823,0.7102,-0.0231
rock,Right,1,2026-06-18 11:05:32,2,THUMB_MCP,0.4601,0.6543,-0.0445
...
rock,Right,1,2026-06-18 11:05:32,20,PINKY_TIP,0.5841,0.5012,-0.0891
```

Each unique `capture_id` represents one complete snapshot of a gesture. A single right-click generates one `capture_id` with 21 rows per detected hand.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Webcam not detected` | Check another app is not using the webcam. Try changing `cv2.VideoCapture(0)` to `cv2.VideoCapture(1)` |
| Hand skeleton not appearing | Ensure your hand is fully in frame and well-lit. Avoid backlight from windows |
| `No hands detected!` flash on right-click | MediaPipe lost tracking for that frame — hold still and try again |
| Gesture name not saving | Make sure you pressed `Enter` after typing with `G`. The gesture name must be set before right-clicking |
| Script crashes on start | Confirm `mediapipe` and `opencv-python` are installed in the correct Python environment |

---

*Part of EGL314 Team B — Match The Gesture Game*  
*Gesture Capture Module | OpenCV + MediaPipe*
