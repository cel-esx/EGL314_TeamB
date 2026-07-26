# OSC GrandMA3
## Purpose
This software allows user to do pre-programming and create lighting design for efficient and effective control of lighting setups. 
## Setup of software
1. Download software [grandMA3 onPC Software for Windows, 2.4.2.2](https://www.malighting.com/downloads/products/grandma3/)
2. Once downloaded, click Accept and download
3. Extract the software's zip file 
4. Click on "ma" in file
5. Click on "grandMA3_onPC_win_v2.4.2.2" in file 
6. Click "Yes"
7. A pop-up will appear, click "Next", "I agree", and lastly "Install"
<img src="images/image.png" width="400" height="400">

   <div align="left">
   <p> It takes some time to install... Roughly 5 minutes! :sleeping: </p>
     <img src="images/image-3.png" alt="GrandMA3 Search" width="400">
   </div>


8. Once installation completed, click "Next" 
<img src="images/Screenshot 2026-06-18 124051.png" width="400" height="400">

9. Check box "Create GrandMA3 onPC Desktop Link" and click "Finish"
<img src="images/image-4.png" width="400" height="400">

## Downloading of Show File

(This is the show file used for reference and example for the game)

 [PROJECT PHANTOM](<project Phantom.backup_2026.07.24_13.56.16UTC.show>)

1. Once downloaded, click on your CDRIVE, "View", "Show", and lastly, "Hidden Items" (This will unhide the folder that needs to be used, "Program Data")
<img src="images/TurnOffHidden.png" width="400" height="300">

2. Locate "Program Data" and click on it
3. Open "MALightingTechnology" 
<img src="images/MATechnology.png" width="400" height="300">

4. Click on "gma3_2.4.2", "shared", and lastly, "Shows"
<img src="images/OpenShows-1.png" width="400" height="300">


5. Alternatively copy this line and input it into 
 ```bash
 C:\ProgramData\MALightingTechnology\gma3_x.y.z\shared\shows
 ```
 

6. Lastly, copy & paste the downloaded file "[Project phantom](<Project Phantom.backup_2026.07.24_13.56.16UTC.show>)" into the "Shows" file

## How to use software
1. Locate GrandMA3 software on your laptop by searching...
   <div align="left">
     <img src="images/image-5.png" alt="GrandMA3 Search" width="400">
   </div>

2. Click "I agree"
<img src="images/image-6.png" width="450" height="150">

3. Click on the :gear: "Gear" icon. Subpage will open, click on "Backup"
<img src="images/StartPage.png" width="400" height="300">

4. Click on the show file "PROJECT PHANTOM", click "Check all" and "Load"
<img src="images/Showfile.png" width="400" height="300"> 

5. In the end, you will see this interface.
<img src="images/ShowfileOpen.png" width="400" height="300"> 



# GrandMA3 Network Configuration
1. Click on the :gear: "Gear" icon. Subpage will open, click on "Network"

<img src="images/Network.png" width="400" height="300">

2. Remember Ip Address to put into the code

<img src="images/ipaddress.png" width="300" height="100">

3. Configure the following in GrandMA3: **Menu → In & Out → OSC**

<img src="images/inout.png" width="400" height="300"><img src="images/osc.png" width="" height="">



  | Setting | Value |
  |---|---|
  | Destination IP | IP address of the Python game computer |
  | Port | `8080` |
  | Prefix | `gma3` |
  | Receive | Yes |
  | Receive Command | Yes |
  | Echo Input | Yes |

  > **Note:** Echo Input allows you to verify incoming OSC commands in the GrandMA3 System Monitor — useful for debugging.



  Congratulations! Once all steps are completed, your lighting is ready to be used with the game!