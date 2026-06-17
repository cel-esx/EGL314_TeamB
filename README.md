# Match The Gesture Game
##  EGL 314 - Proof Of Concept (POC)

This file contains our "Match The Gesture" game that uses **OpenCV + Mediapipe**. Additionally, this comprises also the use of **GrandMA3** Software for lighting controls and **Multiplayer** Software for audio controls <br>



## Table Of Contents
1) Project Overview
    * Purpose of this project
    * How to set it
2) System Architecture
    * Data Flowchart
3) Game Rules
    * Game Rules & Regulation
    * How to play

## Project Overview
This project is a Proof Of Concept (POC) interactive, motion-controlled live production game where players step into the role of a mystical blacksmith enchanting a legendary weapon. Using a camera to detect physical hand gestures, players must match sequences across 6 progressively faster levels to unlock a high-intensity Bonus Round.

What sets this project apart is its integration with live theater tech: the game script acts as a show controller, broadcasting real-time **OSC network signals** to instantly drive professional stage lighting (**grandMA3**) and dynamic sound effects (**Multiplayer**) based on the player's performance

### How to Set up
Please refer to [Setup Guide](./Prerequisits.md) to learn what are the **Software Used** and how to **run** the game

>Note: This version is in the POC stage which means that the game is still in development. There will be more changes added to this game on a later date
```mermaid
graph TD
    %% Style Definitions
    classDef inputs fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef master fill:#cce5ff,stroke:#333,stroke-width:2px;
    classDef target fill:#d4edda,stroke:#333,stroke-width:2px;
    classDef hardware fill:#fff3cd,stroke:#333,stroke-width:2px;

    %% Main Input and Master Controller
    A[Webcam] -->|Internal / External Webcam| B[Laptop 1:<br>Running Main Py]

    %% Network Distribution via Wi-Fi
    B -->|Send OSC Command via wifi<br>Using IP and Port Number| C[Laptop 2:<br>Running GrandMA]
    B -->|Send OSC Command via wifi<br>Using IP and Port Number| D[Laptop 3:<br>Running Multiplayer]

    %% Laptop 2 / Lighting Hardware Pipeline
    C -->|LAN| E[Network Switch]
    E -->|LAN| F[LAN - DMX Converter]
    F -->|DMX Out| G[Lighting Fixtures]

    %% Assign Styles to Match Hardware Roles
    class A inputs;
    class B master;
    class C,D target;
    class E,F,G hardware;
```
