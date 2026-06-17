# Version 1

#import tkinter
#main = tkinter.Tk()

# Version 2

# from tkinter import * 
# main = TK()

# Version 3

import tkinter as tk
import socket
import time

def send_message(IP, Port, Message):

  try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    MESSAGE = bytes(Message, 'UTF-8')
    sock.sendto(MESSAGE, (IP, Port))
    sock.close()
    print(f'message sent: {Message}')
  except:
    print(f'message not sent: {Message}')


if __name__ == "__main__":
# UDP_IP is target IP address
  IP = "127.0.0.1" #Local Host Address
  PORT = 8000

current_level = 1

def set_all_buttons_state(new_state):
    """
    Loops through our list of 7 color buttons and changes their state.
    """
    global all_level_buttons
    for button in all_level_buttons:
        button.config(state=new_state)

def pressed(audio_track_level):
    global n
    global current_level  
    
    n = audio_track_level
    print(f"The audio track is {n}")

    # --- 1. SMART MANUAL CUE BUTTONS (Handles 0 to 6 automatically) ---
    if 0 <= n <= 6:
        # If n is between 0 and 6, we calculate the tracks dynamically:
        if n > 0:
            send_message(IP, PORT, f"/cue/{n}/stop") # Stops the previous track
            
        current_level = n + 1                       # Math sets the exact level
        send_message(IP, PORT, f"/cue/{current_level}/go") # Starts the new track

        set_all_buttons_state(tk.DISABLED)

    # --- 2. GAME EVENT BUTTONS (Keep these separate since they don't follow the math pattern) ---
    elif n == 12:                               # incorrect hand gesture
        send_message(IP, PORT, "/cue/12/go")    

    elif n == 13:                               # stage cleared
        send_message(IP, PORT, "/cue/13/go")    

    elif n == 14:                               # level cleared
        send_message(IP, PORT, "/cue/14/go")    # Play victory sting
        send_message(IP, PORT, f"/cue/{current_level}/stop") # Stop the current level
        
        current_level += 1                      # Move up exactly 1 level
        send_message(IP, PORT, f"/cue/{current_level}/go")   # Play the next level
        if current_level > 7:
            set_all_buttons_state(tk.NORMAL)

    elif n == 15:                               # Gameover
        send_message(IP, PORT, "/cue/15/go")    # Then sends the go
        send_message(IP, PORT, f"/cue/{current_level}/stop")
        set_all_buttons_state(tk.NORMAL)
    

# this is your parent
main = tk.Tk()
n = 0

## Add title
title = tk.Label(main, text="My Fantasic GUI", font=(40))
title.grid(row=0, column=0, columnspan=3)

# # Add colour buttons
color1= tk.Button(main, text='Level 1', font=('Arial', 20), bg="red", command=lambda m=0:pressed(m))
color2= tk.Button(main, text='Level 2', font=('Arial', 20), bg="green", command=lambda m=1:pressed(m))
color3= tk.Button(main, text='Level 3', font=('Arial', 20), bg="blue", command=lambda m=2:pressed(m))
color4= tk.Button(main, text='Level 4', font=('Arial', 20), bg="gold", command=lambda m=3:pressed(m))
color5= tk.Button(main, text='Level 5', font=('Arial', 20), bg="orange", command=lambda m=4:pressed(m))
color6= tk.Button(main, text='Level 6', font=('Arial', 20), bg="pink", command=lambda m=5:pressed(m))
color7= tk.Button(main, text='Bonus', font=('Arial', 20), bg="purple", command=lambda m=6:pressed(m))

color1.grid(row=2, column=0)
color2.grid(row=2, column=1)
color3.grid(row=2, column=2)
color4.grid(row=2, column=3)
color5.grid(row=2, column=4)
color6.grid(row=2, column=5)
color7.grid(row=2, column=6)

# Create a list holding all of your individual level buttons
all_level_buttons = [color1, color2, color3, color4, color5, color6, color7]

## This is a frame for the buttons arrays

button_frame = tk.Frame(main)
button_frame.grid(row=5, column=0, columnspan=10)

array_button = [[j for j in range(5)] for i in range(1)]
for i in range(1):
    for j in range(1,5):
        # Check if the current column is column 8
        if j == 1:
            # Create a green button for column 8
            array_button[i][j] = tk.Button(button_frame, text="stage cleared", command=lambda m=13:pressed(m))
        elif j == 2:
            # Create a red button for column 
            array_button[i][j] = tk.Button(button_frame, text="level cleared", bg="green", fg="white", command=lambda m=14:pressed(m)) 
        elif j == 3:
            # Create a red button for column 
            array_button[i][j] = tk.Button(button_frame, text="Enchanment failed", command=lambda m=12:pressed(m))
        elif j == 4:
            # Create a red button for column 
            array_button[i][j] = tk.Button(button_frame, text="Gameover", bg="red", fg="white", command=lambda m=15:pressed(m))  
        else:
            # Create a normal button for all other columns
            array_button[i][j] = tk.Button(button_frame, text=i)
        array_button[i][j].grid(row=i, column=j)
       

main.mainloop()