# Final Game Tracks

---

## Audio Assets Breakdown

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

## REAPER Track Organization & Signal Routing

### 1. Ambient & System Tracks
> **Setup Reference:**  
> ![Common Track Routing](Reaper_Images/Common%20Track%20Routing.png)

| Track Name | Source File | Hardware / Bus Output Routing |
| :--- | :--- | :--- |
| **Track 2** | `proj_phantom_bgm.mp3` | `Output 1 / Output 2` |
| **Track 3** | `White_noise.wav` | `Output 3 / Output 4` |
| **Track 4** | `Electric_spark.mp3` | `Output 5 / Output 6` & `Output 7 / Output 8` |
| **Track 5** | `game_end.mp3` | `Output 9 / Output 10` & `Output 11 / Output 12` |
| **Track 6** | *Siera Voiceover Sequence* | `Output 13 / Output 14` & `Output 15 / Output 16` |

### 2. Gameplay Tracks
> **Setup Reference:**  
> ![Gameplay Routing](Reaper_Images/Gameplay.png)

| Track Name | Source File(s) | Hardware / Bus Output Routing |
| :--- | :--- | :--- |
| **Track 15** | `clock-ticking.mp3` | `Output 40` |
| **Track 16** | `loading_effect.mp3`, `recharge.mp3` | `Output 43 / Output 44` |
| **Track 17** | `fail.mp3` | `Output 41 / Output 42` |

---

## L-ISA Configuration

### Source & Timecode Setup
<p>
  <img src="L-ISA_Images/Sources_setup.png" width="100%" alt="Sources Setup 1" />
</p>
<p>
  <img src="L-ISA_Images/Sources_setup2.png" width="100%" alt="Sources Setup 2" />
</p>
<p>
  <img src="L-ISA_Images/Gameplay_Sources_Setup.png" width="100%" alt="Gameplay Sources Setup" />
</p>
<p>
    <i><u>Midi Timecode:</u></i>
</p>
<p>
  <img src="L-ISA_Images/Timecode_setup.png" width="100%" alt="Timecode Setup" />
</p>

### Timecode Markers (Team B)
| Timecode | Marker ID | Team / Event Description |
| :--- | :--- | :--- |
| `00:34:24:00` | Marker 11 | Team B - Start time ticking |
| `00:38:48:00` | Marker 12 | Team B - Failing |
| `00:41:28:00` | Marker 13 | Team B - Loading |
| `00:43:56:00` | Marker 14 | Team B - Recharge |
| `00:46:00:00` | Marker 15 | Team B - Good job |
| `00:47:44:00` | Marker 10 | Team B - Transition Team E |

### Snapshots & Spatialization
<p>
<u><i>Ambient:</i></u>
</p>
<p>
  <img src="L-ISA_GIF/Ambient_Snapshot.gif" width="100%" alt="Ambient Snapshot" />
</p>
<p>
<u><i>Clock-Ticking:</i></u>
</p>
<p>
  <img src="L-ISA_GIF/Clock-Ticking_Snapshot.gif" width="100%" alt="Clock Ticking Snapshot" />
</p>

---

*For detailed software configuration guides, refer to the **[L-ISA Setup Documentation](../../MVP/L-ISA/README.md)**.*

*For Reaper Setup Documentation, read [**Reaper Setup and Configuration**](../../MVP/reaper/README.md) only.*

## Reaper code used for `Final Assessment Game Code.py`
### Function

```python
def back_to_start():
    print(f"⌛ Buffer complete! Back to start")
    send_osc_signal(reaper_client, "/action/41251", 1)
    send_osc_signal(reaper_client, "/track/15/mute",1)
```
This function scripted under the GAMEOVER status, making sure that once user lost 3 lives/pressed 'q' (troubleshooting purposes), it will go back to `Marker 11`. *(line 840, 1218)*

### Reaper Marker Command
```python
send_osc_signal(reaper_client, "/action/40339", 1) #unmute all tracks
send_osc_signal(reaper_client, "/action/40161", 1) # Jump to marker 1 (tutorial game start)
time.sleep(5)
```
Before system is initialising, Reaper will jump to `Marker 1`, playing `station 2_gesture-tutorial.wav` for 5s. (line 324, 325)

```python
send_osc_signal(reaper_client, "/action/40162", 1) #game start
send_osc_signal(reaper_client, "/track/5/mute", 1) #game state track mute
```
After the `time.sleep(5)`, Reaper will jump to `Marker 2` to play `game_start.mp3`. *(line 429, 430)*

```python
send_osc_signal(reaper_client, "/action/41251", 1) #team B game start
send_osc_signal(reaper_client, "/track/15/mute", 0) #time-ticking unmute
```
Under the `start_game_sequence()`, Reaper will jump to `Marker 11`, **unmuting** the `Clock-Ticking.mp3` track.

> *This unmuting function is appliable during the **gameplay** only, not tutorial.*

```python
send_osc_signal(reaper_client, "/action/41253", 1) #loading
send_osc_signal(reaper_client, "/track/15/mute", 0) #time-ticking mute
```
Once the hand gesture is detected, a loading progress bar will be shown, calling Reaper to jump to `Marker 13`, playing `loading_effect.mp3`, while muting `Clocking-Ticking.mp3`. *(line 555, 556)*

> *These code is applicable during `gameplay` only, not tutorial.* *(line 745, )*

```python
send_osc_signal(reaper_client, "/action/41253", 1) #loading
send_osc_signal(reaper_client, "/track/15/mute", 1)# time-ticking mute
```
However, `Clock-Ticking.mp3` will be muted during both shadow and hand gesture tutorial. (line 702, 703)

```python
send_osc_signal(reaper_client, "/action/41255", 1)
```
Once the progress bar is full, Reaper jumps to `Marker 15`, playing `station 2_gesture-tutorial.wav`. *(lines 561)*
This code also applies when code is transiting from `TUTORIAL_STAGE_1` to `TUTORIAL_STAGE_2`, by playing `station 2_gesture-tutorial.wav`. *(lines 708)*

```python
send_osc_signal(reaper_client, "/action/40167", 1) #ai voice
```
When transiting from `hand gesture tutorial` to `hand gesture game`, Reaper jumps to marker 7, playing `station 2_gesture-start.wav`. *(lines 712)*


```python
send_osc_signal(reaper_client, "/action/41270", 1)
```
When shadow tutorial is cleared (`STAGE_CLEAR_TUT2`), Reaper jumps to `Marker 30`, playing `station 2_shadow-start.wav`. *(lines 718)*

```python
send_osc_signal(reaper_client, "/action/40163", 1) 
send_osc_signal(reaper_client, "/track/5/mute", 0)
```
When player lost 3 lives, Reaper jumps to `Marker 3`, playing `gameover.mp3`, while unmuting `Game State` track.

```python
send_osc_signal(reaper_client, "/action/41252", 1)
```
If players lost their lives less than 3 times, Reaper jumps to `Marker 12`, playing `fail.mp3`. 
> *Note: This will play when they fail the stage.*

```python
send_osc_signal(reaper_client, "/action/41253", 1) 
send_osc_signal(reaper_client, "/track/16/mute", 1)
send_osc_signal(reaper_client, "/track/15/mute", 0)
```
