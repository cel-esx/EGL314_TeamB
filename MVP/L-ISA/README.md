# OSC L-ISA Integration Guide

## Overview & Purpose

Controlled by REAPER during soundtrack playback, this software orchestrates room surround sound using snapshots and timecode synchronization over the MIDI Loop protocol.
---

## L-ISA Setup & Configuration

### 1. Installation

* Download and install **[L-ISA](https://www.l-acoustics.com/products/l-isa-studio/?pk_vid=86afed12eb3149cc16861759426ba57c)**, and **[loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)**.
* 📹 **[L-ISA Video Installation & Setup Guide](https://youtu.be/eVM-51u1GbI?si=CHgpuxDxQGSGWfBy)**

### 2. L-ISA Set Up Configuration
1. Open **L-ISA Controller** and go to 'Processor', and click 'connect' and 'auto-connect'. <br>
![Alt Text](Images/L_ISA_Controller_Config1.png)
2. Once done, open **L-ISA Processor** and proceed do the configuration below. <br>
![Alt Text](Images/L-ISA_config1.png)

### 3. Reaper loopMIDI Configuration
3. 
---

### Finding Your Laptop's IP Address (Windows)

1. Open **Command Prompt** (`cmd`). <br>
![Alt Text](../../POC/Multiplay/Images&MultiPlay/ipconfig.png)
2. Type `ipconfig` and press **Enter**. <br>
3. Locate your active network adapter and note the **IPv4 Address**. <br>
(../../POC/Multiplay/Images&MultiPlay/cmd.png)

---

## Network Architecture

```mermaid
graph LR
    A[REAPER DAW] --> B[Timecode] --> |loopMIDI| B[L-ISA Snapshots]

```

> ⚠️ **IMPORTANT:** Ensure the IP address and port configured in your Python scripts match the REAPER OSC network settings exactly.

---

## L-ISA Snapshots