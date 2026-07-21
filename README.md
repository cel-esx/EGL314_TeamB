# EGL 314 - Media Solutioning Project 1 - Team B 
##  Project Phantom
## Table of Contents
1. **[Project Overview](#project-overview)**
   * Backstory of this project
   * Purpose of this project
   * Game Rules & Objective
   * Game Tutorial
   * How to set up
2. **[System Architecture](#system-architecture)**
   * Data Flowchart
3. **[Repository Structure](#repository-structure)**
    * Location Of Files
4. **[Versions](#versions)**
    * Types of game state-of-play
5. **[References and Sources](#references-and-sources)**
    * Location of where we got our informations from
6. **[Contributers](#done-by-yours-truly)**
    * Team members who have contributed in this repository
---
# Project Overview
## Quick Backstory Of This Project
[Description of project phantom goes here]
 <br>

 ****
 ## Purpose of this Project
 ## Station 2 - Gun Recharge
In this station, players are suppose to recharge the gun which would be found in player's backpack. They have to place them on the table to maximise it's fullest potential

Players are suppose to mimic the hand gestures shown on the laptop. But there will be a twist. As the round goes on, they will slowly come to realise that they have to work together in order to clear the level. Especially in level 4, where the they would have to move locations and do a shadow gesture together with the other player in order to finish the game

Once the game is finished, the player's gun will be fully recharged and they will be automatically directed to the next station

---
# Game Rules & Objective

The **main objective** of the game is to successfully complete all 4 levels to upgrade the weapon before running out of lives and time
* **Beat the Clock:** Every stage is bound by a strict countdown timer. If the timer hits zero before you match the required gestures / shadows, you fail the stage and will have to restart

* **Progressive Co-Op:** As you advance through the game, you realise that eventually both players must follow the same target gestures shown on the screen

* **The 3-Life Rule:** You begin your journey with 3 lives. If you fail a stage, you lose a life and are sent back to the start of the stage. Losing all lives results in a Game Over

* **The Ultimate Test:** Completing Level 3 unlocks the shadow Upgrading Round. Both player have to use 1 of their hands to form a shadow and must survive 3 of such rounds in order to finish the game.
---
# How To Play?
* **Position:** Stand clearly in front of the laptop's webcam, ensuring both player's left and right hands are fully visible in the frame

* **Start the Game:** Both players are requireed to show their palms to begin the upgrading sequence

* **Replicate the Runes:** Look at the active gesture boxes displayed on the screen. Physically mirror the exact left and right hand shapes using your own hands for levels 1-3

* **Team Bonding Challenge:** Upon reaching level4, player's will need to repoisiton themselves to where the spotlight is showing. Each players need to use only 1 hand and they have to work together in order to replicate the gesture shown on the screen

* **Charge the Bar:** Once you match the target gestures, hold the positions steady. A green "Charging" progress bar will appear—maintain the pose for 2 seconds to complete the stage

* **Watch the Magic:** As you successfully progress or trigger game states, watch and listen as the script instantly changes your real-world room environment via theater tech integrations (grandMA3 lighting and Reaper + L-ISA audio)

---
## How to Set up

Please refer to [Setup Guide](/Setup%20Guide.md) to see what do you need to have in order to run the game
***

## System Architecture
```mermaid
graph TD
    %% Style Definitions
    classDef inputs fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef master fill:#cce5ff,stroke:#333,stroke-width:2px;
    classDef lighting fill:#e2d9f3,stroke:#333,stroke-width:2px;
    classDef audio fill:#d4edda,stroke:#333,stroke-width:2px;
    classDef hardware fill:#fff3cd,stroke:#333,stroke-width:2px;

    %% Visual & Input Hardware
    CAM1[Laptop Webcam] -->|Video Feed| B
    CAM2[External Webcam] -->|Video Feed| B
    B -->|HDMI| MON[External Monitor]

    %% Main Controller
    B[Laptop 1:<br>Running Main Py]

    %% Lighting Pipeline (Laptop 2)
    B -->|Send OSC Command<br>via Wi-Fi| C[Laptop 2:<br>Running grandMA]
    C -->|LAN| E[Network Switch]
    E -->|LAN| F[LAN-to-DMX Converter]
    F -->|DMX Out| G[Lighting Fixtures]

    %% Audio Pipeline (Laptop 3)
    B -->|Send OSC Command<br>via Wi-Fi| D[Laptop 3:<br>Running REAPER + L-ISA via MIDI ]
    D -->|Dante Protocol| QL1[Yamaha QL1 Console]
    QL1 -->|Audio Out| SPK[Speakers]

    %% Assign Styles
    class CAM1,CAM2 inputs;
    class B master;
    class MON hardware;
    class C,E,F,G lighting;
    class D,LISA,QL1,SPK audio;
```
---
# Repository Structure
| Folder Location | File Name | Technical Roles & Functions |
| :---: | :---: | :---: |
| Main (Outside POC folder) |  README.md| Main readme file talking about the purpose of the project and the game itself |
| Main (Outside POC folder)|  Setup Guide.md| Contains the steps required in order the set up viewer's laptop to play the game |
| Main (Outside POC folder) |  LICENSE| Contains the license for this repository |
| POC |  Hand_Images| Contains all the hand images that are used in the game |
| POC |  Capture Gesture.py| Contains python code for saving / deleting gesture|
| POC | CAPTURE_GESTURE_README.md| Instructions on setup of capture gesture.py and how it works to add new gestures to new_gesture_definition.csv |
| POC | new_gesture_definitions.csv | Stores all captured gestures in a format that is understood by the game |
| POC | POC GAME CODE | Contains entire game code |
| POC |  grandma3| Folder containing all grandma3 setup and related pictures|
| POC |  Multiplay| Folder containing all Multiplay setup and related pictures|
| POC |  POC README.py| File that contains all the instruction on how the POC game is suppose to be played|
|POC/Multiplay| Images&MultiPlay | Contains all the images on the GitHub and the MultiPlay file that was used for the POC Code|
|POC/Multiplay| dummy_game.py| Game Simulation to test OSC commands |
|POC/Multiplay| MultiPlay.md| Contains all the set up and configuration in the Multiplay with POC and dummy_game codes explained |
|POC/grandMA3|Images| Contains images for more visual understanding |
|POC/grandMA3| grandMA3setup.md |Instructions on how to download and use GrandMA3|
|POC/grandMA3| TEAMB_Proj.show | Pre-made Show File for reference and use. Feel free to make changes in this file |
|MVP| MVP Game Code.py | Contains the entire game code |
|MVP| new_gesture_definitions.csv | Stores all captured gestures in a format that is understood by the game |

---
# Versions
* [Proof Of Concept (POC)](/POC/POC%20Game%20Code.py) - This file contains the inital version of the game
* [Minimum Viable Product (MVP)](/MVP/MVP%20GameCode_NEW.py) - This file contains a enhanced version of the POC gameplay
***
# References and Sources:
* [Huats Club - OSC Starter Kit ](https://github.com/huats-club/oscstarterkit)
* [AI Machine Learning Link - Pls add this]()
***

### Done by yours truly:
<table>
  <tr>
    <td align="center">
      <a href="https://github.com/Devesty8">
        <img src="https://github.com/Devesty8.png" width="100px;" alt="Devesty8"/><br />
        <sub><b>Devesty8</b></sub>
      </a><br />
    </td>
    <td align="center">
      <a href="https://github.com/cel-esx">
        <img src="https://github.com/cel-esx.png" width="100px;" alt="cel-esx"/><br />
        <sub><b>cel-esx</b></sub>
      </a><br />
    </td>
    <td align="center">
      <a href="https://github.com/ilyaaqilah">
        <img src="https://github.com/ilyaaqilah.png" width="100px;" alt="ilyaaqilah"/><br />
        <sub><b>ilyaaqilah</b></sub>
      </a><br />
    </td>
    <td align="center">
      <a href="https://github.com/trippyfiq">
        <img src="https://github.com/trippyfiq.png" width="100px;" alt="trippyfiq"/><br />
        <sub><b>trippyfiq</b></sub>
      </a><br />
    </td>
  </tr>
</table>

