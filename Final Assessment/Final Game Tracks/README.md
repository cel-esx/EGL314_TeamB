# Final Game Tracks

---

### Audio Assets Breakdown

#### Ambient Sound
*Plays continuously throughout gameplay:*
* [`Electric_spark.mp3`](Audio%20Tracks/Common%20BGM/Electric_spark.mp3)
* `White_noise.wav`
* [`proj_phantom_bgm.mp3`](Audio%20Tracks/Common%20BGM/proj_phantom_bgm.mp3)

#### Siera Voiceover
*Plays during transitions from tutorials to the hand-gesture game:*
1. [`station 2_gesture-tutorial.wav`](Audio%20Tracks/Siera/station%202_gesture-tutorial.wav)
2. [`station 2_gesture-start.wav`](Audio%20Tracks/Siera/station%202_gesture-start.wav)
3. [`staton 2_shadow-tutorial.wav`](Audio%20Tracks/Siera/staton%202_shadow-tutorial.wav)
4. [`station 2_shadow-start.wav`](Audio%20Tracks/Siera/station%202_shadow-start.wav)
5. [`Siera-Station-2-Complete.mp3`](Audio%20Tracks/Siera/Siera-Station-2-Complete.mp3) *(Station completion trigger)*

#### Gameplay Sound Effects
* [`loading_effect.mp3`](Audio%20Tracks/loading_effect.mp3) *(Used for progress bar)*
* [`recharge.mp3`](Audio%20Tracks/recharge.mp3)
* [`clock-ticking.mp3`](Audio%20Tracks/clock-ticking.mp3)

#### Game State Audio
* [`game_end.mp3`](Audio%20Tracks/Common%20BGM/game_end.mp3)

---

### REAPER Track Organization & Signal Routing

#### 1. Ambient & System Tracks
> **Setup Reference:**  
> ![Common Track Routing](Reaper_Images/Common%20Track%20Routing.png)

| Track Name | Source File | Hardware / Bus Output Routing |
| :--- | :--- | :--- |
| **Track 2** | `proj_phantom_bgm.mp3` | `Output 1 / Output 2` |
| **Track 3** | `White_noise.wav` | `Output 3 / Output 4` |
| **Track 4** | `Electric_spark.mp3` | `Output 5 / Output 6` & `Output 7 / Output 8` |
| **Track 5** | `game_end.mp3` | `Output 9 / Output 10` & `Output 11 / Output 12` |
| **Track 6** | *Siera Voiceover Sequence* | `Output 13 / Output 14` & `Output 15 / Output 16` |

#### 2. Gameplay Tracks
> **Setup Reference:**  
> ![Gameplay Routing](Reaper_Images/Gameplay.png)

| Track Name | Source File(s) | Hardware / Bus Output Routing |
| :--- | :--- | :--- |
| **Track 15** | `clock-ticking.mp3` | `Output 40` |
| **Track 16** | `loading_effect.mp3`, `recharge.mp3` | `Output 43 / Output 44` |
| **Track 17** | `fail.mp3` | `Output 41 / Output 42` |

---

### L-ISA Configuration

#### Source & Timecode Setup
<p align="center">
  <img src="L-ISA_Images/Sources_setup.png" width="45%" alt="Sources Setup 1" />
</p>
<p align="center">
    <img src="L-ISA_Images/Sources_setup2.png" width="45%" alt="Sources Setup 2" />
</p>
<p align="center">
  <img src="L-ISA_Images/Gameplay_Sources_Setup.png" width="45%" alt="Gameplay Sources Setup" />
</p>
<p align="center">
  <img src="L-ISA_Images/Timecode_setup.png" width="45%" alt="Timecode Setup" />
</p>

#### Snapshots & Spatialization
<p align="center">
  <img src="L-ISA_GIF/Ambient_Snapshot.gif" width="45%" alt="Ambient Snapshot" />
  <img src="L-ISA_GIF/Clock-Ticking_Snapshot.gif" width="45%" alt="Clock Ticking Snapshot" />
</p>

---

*For detailed software configuration guides, refer to the **[L-ISA Setup Documentation](../../MVP/L-ISA/README.md)** and **[REAPER Setup Documentation](../../MVP/reaper/README.md)**.*