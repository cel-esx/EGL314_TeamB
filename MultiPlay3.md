# OSC MultiPlay3

## Purpose
This software allows the track to play one or more audio tracks at any time, enhancing players' experience by controlling the different cues on the MultiPlay using OSC commands.

## Configuration and set up
1. Download [MultiPlay3 Version 3.0.50.0](https://da-share.com/forum/index.php?topic=74.0)
2. Once downloaded, allow/agree all preferences and options before launching the software.
3. In MultiPlay, under file, click Preferences. Then, go to OSC Control tab.
   ![Alt text](main/MultiPlayConfig.png)
4. Under OSC Control, enable "Control (Incoming)" and change the port number to 8000
    This is to allow MultiPlay to receive commands from the POC code

## Flow Chart
```mermaid
graph LR
A[POC Code] <--Wifi <br> (IP Address and PORT No.)--> B[Multiplay 3]
```
**Disclaimer:
MAKE SURE THE POC CODE HAS THE SAME PORT AND IP ADDRESS IN THE MULTIPLAY3!**

## Dummy Game
Before implementing the POC Code to control the cues in MultiPlay, ~/dummy_game was made to achieve the desired result for the game.

````
dummy_game.py
````

## The Desired Results
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

