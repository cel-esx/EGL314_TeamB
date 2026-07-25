# Huats 2023 oscstarterkit
# This python script demonstrate controlling Reaper (trigger play/stop playback) using a Raspberry Pi through the
# OSC messaging protocol
from pythonosc import udp_client
import tkinter as tk
import threading

def send_message(receiver_ip, receiver_port, address, message):
	try:
		# Create an OSC client to send messages
		client = udp_client.SimpleUDPClient(receiver_ip, receiver_port)

		# Send an OSC message to the receiver
		client.send_message(address, message)

		print("Message sent successfully.")
	except:
		print("Message not sent")


# FOR INFO: IP address and port of the receiving Raspberry Pi
PI_A_ADDR = "192.168.254.12"		# wlan ip
REAPER_PORT = 8000

# 1. go to marker 21
addr = "/action/41261"
msg = float(1) 
send_message(PI_A_ADDR, REAPER_PORT, addr, msg)

# 2. Trigger Custom Action (40044 is "Transport: Play/stop")
addr = "/action/40044"
msg = float(1) 
send_message(PI_A_ADDR, REAPER_PORT, addr, msg)

current_level = 1
stage_failed = 0
stage_cleared = 0
LEVEL_MAP = {
    1: "_b5b9b1aa3433a54f8efb7058fd9dc212",  # level 1 track unmuted only
    2: "_8003a43cdba0624b948270f6b5224ee8",  # Level 2 track unmuted only
    3: "_fed26a77af3cb841b8ae1156e64de1ec",  # level 3 track unmuted only
    4: "_82a10b90ef7428438ddfd101c8195d19"   # bonus track unmuted only
}

MAX_STAGES_PER_LEVEL = {
    1: 2,  # Level 1 has 2 stages
    2: 2,  # Level 2 has 2 stages
    3: 2,  # Level 3 has 2 stages
    4: 3   # Bonus Level 4 has 3 stages
}

# REAPER Action IDs for stage markers
STAGE_MARKER_MAP = {
    1: "41263",  # Marker 23 (Stage 1)
    2: "41264",  # Marker 24 (Stage 2)
    3: "41265"   # Marker 25 (Stage 3 / Bonus)
}

def jump_to_stage(level, stage_number):
    """Jumps to the specific stage marker for the given level and sets track mutes."""
    marker_action = STAGE_MARKER_MAP.get(stage_number, "41263")
    print(f"⌛ Buffer complete! Transitioning to Level {level}, Stage {stage_number} (Marker Action: {marker_action})...")
    
    # 1. Jump to stage marker in REAPER
    send_message(PI_A_ADDR, REAPER_PORT, f"/action/{marker_action}", 1)
    
    # 2. Apply level track state
    if level in LEVEL_MAP:
        action_id = LEVEL_MAP[level]
        send_message(PI_A_ADDR, REAPER_PORT, f"/action/{action_id}", 1)
    else:
        print(f"Warning: No REAPER action defined for level {level}")

def retry_stage(level, stage_number):
    """Retries the current stage by jumping to its specific stage marker 
    and re-applying the track state for the level."""
    marker_action = STAGE_MARKER_MAP.get(stage_number, "41263")
    print(f"🔄 Retrying Level {level}, Stage {stage_number} (Marker Action: {marker_action})...")
    
    # 1. Jump to the marker for the current stage being retried
    send_message(PI_A_ADDR, REAPER_PORT, f"/action/{marker_action}", 1)
    
    # 2. Re-apply level track state
    if level in LEVEL_MAP:
        action_id = LEVEL_MAP[level]
        send_message(PI_A_ADDR, REAPER_PORT, f"/action/{action_id}", 1)
    else:
        print(f"Warning: No REAPER action defined for level {level}")

def back_to_start():
    print(f"⌛ Buffer complete! Back to start")
    
    # 1. Jump back to Marker 21
    send_message(PI_A_ADDR, REAPER_PORT, "/action/41261", 1)

def pressed(audio_track_marker):
    global n
    global current_level 
    global stage_failed
    global stage_cleared
    
    n = audio_track_marker
    print(f"The audio track is {n}")     

    if n == 1: # When press start
        send_message(PI_A_ADDR, REAPER_PORT, "/action/41262", 1)
        send_message(PI_A_ADDR, REAPER_PORT, "/action/_b5b9b1aa3433a54f8efb7058fd9dc212", 1)
 
    elif n == 13: # Stage Cleared
        stage_cleared += 1
        max_required_stages = MAX_STAGES_PER_LEVEL.get(current_level, 2)
        BUFFER_SECONDS = 3.5
        TRANSIT_SEC = 30

        print(f"Stage Cleared ({stage_cleared}/{max_required_stages}) on Level {current_level}!")

        # ==========================================
        # CASE A: Intermediate Stage Clear (Advance to Next Stage)
        # ==========================================
        if stage_cleared < max_required_stages:
            next_stage = stage_cleared + 1  # e.g., Cleared Stage 1 -> Target Stage 2 (Marker 24)
            
            # Play intermediate sting audio setup
            send_message(PI_A_ADDR, REAPER_PORT, "/action/_b4dd8381edb3cf4a82f2f1d2a56622e0", 1)
            send_message(PI_A_ADDR, REAPER_PORT, "/action/41267", 1)

            # Buffer delay -> Jumps to the NEXT stage marker (e.g. Marker 24 for Stage 2) on the SAME level
            threading.Timer(BUFFER_SECONDS, jump_to_stage, args=[current_level, next_stage]).start()

        # ==========================================
        # CASE B: Final Stage Cleared -> Level Complete!
        # ==========================================
        else:
            print(f"🏆 Level {current_level} Fully Cleared!")
            
            # Advance to new level & reset stage counter back to 1
            current_level += 1
            stage_cleared = 0

            if current_level > 4:
                print("🎉 ENTIRE GAME CLEARED! Playing Victory/Ending Sequence...")
                
                # Trigger your final victory audio sequence / Marker 30 (41270)
                send_message(PI_A_ADDR, REAPER_PORT, "/action/_7f4e8ad275963d4c8547d96d2538d0be", 1) #unmute all tracks
                send_message(PI_A_ADDR, REAPER_PORT, "/action/41270", 1)
                
                # Optional: Reset current_level back to 1 for the next session/player
                current_level = 1 
                
                # DO NOT start threading.Timer here! 
                # Letting the code finish without starting a timer allows REAPER to keep playing freely.
            
            elif current_level > 3:
                print(f"✨ Transitioning to Bonus Level {current_level}, Stage 1...")
                
                # 1. Mute all tracks macro
                send_message(PI_A_ADDR, REAPER_PORT, "/action/_b4dd8381edb3cf4a82f2f1d2a56622e0", 1) 
                
                # 2. Trigger Transition audio marker (Marker 26 / 41266)
                send_message(PI_A_ADDR, REAPER_PORT, "/action/41266", 1)
                
                # 3. Pass stage '1' explicitly instead of variable 'next_stage'
                threading.Timer(TRANSIT_SEC, jump_to_stage, args=[current_level, 1]).start()


            # ==========================================
            # ADVANCE TO NEXT LEVEL (Levels 1 -> 2 -> 3 -> 4)
            # ==========================================
            else:
                # Play final sting / "Well Played" audio setup for normal level clears
                send_message(PI_A_ADDR, REAPER_PORT, "/action/_b4dd8381edb3cf4a82f2f1d2a56622e0", 1) # mute all music tracks
                send_message(PI_A_ADDR, REAPER_PORT, "/action/41267", 1)

                # Buffer delay -> Advances to NEW level at Stage 1 (Marker 23 / 41263)
                threading.Timer(BUFFER_SECONDS, jump_to_stage, args=[current_level, 1]).start()
    
    elif n == 15: # Stage Failed
        stage_failed += 1
        BUFFER_SECONDS = 3.5
        GAMEOVER_BUFFER_SECONDS = 6.5
        
        # Determine which stage the player is currently on (1, 2, or 3)
        # stage_cleared tracks COMPLETED stages, so current stage = completed + 1
        current_stage = stage_cleared + 1

        print(f"❌ Stage Failed! (Attempt #{stage_failed} on Level {current_level}, Stage {current_stage})")

        # ==========================================
        # CASE A: Standard Retry (Attempts 1 & 2)
        # ==========================================
        if stage_failed <= 2:
            # Play fail sting audio setup
            send_message(PI_A_ADDR, REAPER_PORT, "/action/41269", 1)
            send_message(PI_A_ADDR, REAPER_PORT, "/action/_b4dd8381edb3cf4a82f2f1d2a56622e0", 1)

            # Buffer delay -> Retries the SAME level and SAME stage marker
            threading.Timer(BUFFER_SECONDS, retry_stage, args=[current_level, current_stage]).start()

        # ==========================================
        # CASE B: Hard Game Over (> 2 Failures)
        # ==========================================
        else:
            print("💀 Hard Game Over triggered!")
            
            # Trigger Hard Game Over sequence in REAPER
            send_message(PI_A_ADDR, REAPER_PORT, "/action/41268", 1)
            send_message(PI_A_ADDR, REAPER_PORT, "/action/_b4dd8381edb3cf4a82f2f1d2a56622e0", 1)

            # Reset counters for a fresh run starting at Stage 1
            current_level = 1
            stage_failed = 0
            stage_cleared = 0
            
            # Buffer delay -> Resets back to the start of the game
            threading.Timer(GAMEOVER_BUFFER_SECONDS, back_to_start, args=[]).start()

# elif n == 16: #gameover
    # if stage_failed > 2:
    #     print("💀 Hard Game Over triggered!")
        
    #     GAMEOVER_OFFSET = 2 
    #     game_over_marker = current_level + GAMEOVER_OFFSET
        
    #     # Command REAPER to jump to the current level's specific Game Over section
    #     send_message(PI_A_ADDR, PORT, f"/action/{game_over_marker}", 1)
        
    #     # Reset the failure counter for their next life/run
    #     stage_failed = 0
    # send_message(PI_A_ADDR, PORT, "/track/8/mute", 0)
    # send_message(PI_A_ADDR, PORT, "/track/6/mute", 0)
    # send_message(PI_A_ADDR, PORT, "/track/7/mute", 0)
    # send_message(PI_A_ADDR, PORT, f"/action/40165", 1) 
    # time.sleep(8.5)
    # send_message(PI_A_ADDR, PORT, "/track/2/mute", 1)
    # time.sleep(3)
    # send_message(PI_A_ADDR, PORT, "/track/8/mute", 1)
    # send_message(PI_A_ADDR, PORT, "/track/2/mute", 0)
    # send_message(PI_A_ADDR, PORT, "/action/40042", 1)

main = tk.Tk()
n = 0

## Add title
title = tk.Label(main, text="My Fantasic GUI", font=(40))
title.grid(row=0, column=0, columnspan=3)

# # Add colour buttons
color1= tk.Button(main, text='Start', font=('Arial', 20), bg="red", command=lambda m=1:pressed(m))

color1.grid(row=2, column=0)

button_frame = tk.Frame(main)
button_frame.grid(row=5, column=0, columnspan=10)

array_button = [[j for j in range(5)] for i in range(1)]
for i in range(1):
    for j in range(1,5):
        if j == 1:
            array_button[i][j] = tk.Button(button_frame, text="stage cleared", command=lambda m=13:pressed(m))
        # elif j == 2:
        #     array_button[i][j] = tk.Button(button_frame, text="level cleared", bg="green", fg="white", command=lambda m=14:pressed(m)) 
        elif j == 3:
            array_button[i][j] = tk.Button(button_frame, text="stage failed", command=lambda m=15:pressed(m)) 
        # elif j == 4:
        #     array_button[i][j] = tk.Button(button_frame, text="Gameover", bg="Red", fg="white", command=lambda m=16:pressed(m)) 
        else:
            array_button[i][j] = tk.Button(button_frame, text=i)
        array_button[i][j].grid(row=i, column=j)
       

main.mainloop()
        