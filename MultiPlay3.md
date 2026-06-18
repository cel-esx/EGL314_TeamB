# OSC MultiPlay3

## Purpose
This software allows the track to play one or more audio tracks at any time, enhancing players' experience by controlling the different cues on the MultiPlay using OSC commands.

## Configuration and set up
1. Download [MultiPlay3 Version 3.0.50.0](https://da-share.com/forum/index.php?topic=74.0)

2. Once downloaded, allow/agree all preferences and options before launching the software.

3. In MultiPlay, under file, click Preferences. Then, go to OSC Control tab.

   ![Alt text](MultiPlayConfig.png)

4. Under OSC Control, select your laptop's IP Address first before enabling "Control (Incoming)" and change the port number to 8000.
    *This is to allow MultiPlay to receive commands from the POC code*
   
   ![Alt text](OSCControl.png)
   Once done, click **OK**.
## Flow Chart
```mermaid
graph LR
A[POC Code] <--Wifi <br> (IP Address and PORT No.)--> B[Multiplay 3]
```
**Disclaimer:
MAKE SURE THE POC CODE HAS THE SAME PORT AND IP ADDRESS IN THE MULTIPLAY3!**

## Dummy Game
Before implementing the POC Code to control the cues in MultiPlay, ~/dummy_game was another game simulation to make sure the code is working.

````
dummy_game.py
````
## Expectations
1. When user pressed the "level 1" button, cue 1 in MultiPlay will start playing, frozing all the level buttons in the tkinter.
   <br> *This is for the game tester to jump into different level for checking purpose without having to declare the level itself*
   ```mermaid
   graph LR
    A[Level 1 Button Pressed] --> B[dummy_game.py sends <br> command]
    B --> C[MultiPlay Plays Cue 1]
   ```
   *Note: Level number and cue track are the same number. Eg. Level 1 = cue 1, Level 2 = cue 2*
   
2. As the level sound track is playing, user can pressed the second row buttons.
   <br>
   a. staged cleared - *the button can be pressed multiple times as the level track is playing*
   b. level cleared - *the code will send command to MultiPlay to play the next level sound track*
   c. Enchantment failed - *the button can be pressed multiple times as the level track is playing (user is failling the stage)*
   d. Gameover - *the code will send command to MultiPlay to stop all sound track*

## The Desired Results in the POC Code
1. When player pressed "S", POC Code will play cue 1.
2. Every level has a audio track in the MultiPlay
    eg. Level 1 will play cue 1 play on MultiPlay, level 2 will play cue 2 on MultiPlay
3. If players lose a life, cue 13 will be played, alerting user that they have lost a life.
4. If players lose all 3 lives, cue 14 will be played to indicate that they have lost the game.
5. If players managed to passed the stage(s), cue 12 will be played, alerting players that they have passed the stage.
6. After passing 3 stages, cue 14 will be played for players to know that they have passed onto the next level.
7. Once the next level is played, the POC Code will run the next "current level" audio track. 
    eg. current_level is 1, multiplay will play cue 1
        if the next current_level is 2, multiplay will play cue 1.
8. Once game has ended, all cue(s) will stopped playing.

