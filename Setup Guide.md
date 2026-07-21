# Setup Guide
###  This page contains all the materials required & the instructions on how to download those materials in order to run this game


## Hardware 
 1) **Desktop / Laptop** (Windows)
 2) **External USB Webcam**
 3) **Lighting Equipment** (Minimally, you need a spotlight to do the shadow OR a stationary light source)
 4) **Speakers** (Optional)
 5) **Webcam Tripod Stand**
 6) **External Monitor**


## Software
  1. **Anaconda**
     * Click Here: [Anaconda Setup](#anaconda-set-up)
  2. **Microsoft Visual Studio Code**
     * Click Here: [Visual Studio Code Setup](#microsoft-visual-studio-code)
     * You also need [Jupyter Notebook](#jupyter-notebook-installation-steps) within Visual Studio Code
     > Note: Jupyter Notebook is **Not Required For POC Game**
  3. **GrandMA3**
     * Click Here: [GrandMa3 Setup](#grandma3)
  4. **MultiPlay**
     * Click Here: [MultiPlay Setup](#multiPlay)
   5. **Reaper**
   6. **L-ISA**


   ## Hardware Placement
   [Picture Of The Table Where Laptop setup]

  ## Dependencies
  #### This code have been tested using **Python 3.10 or higher**   

  ## Setting Up - How to install?
   
   ### Anaconda Set-Up
   1. Install **Anaconda** in your laptop:<br>
   https://www.anaconda.com/download
   > If you need more help, Please click [here](https://www.anaconda.com/docs/getting-started/anaconda/install/windows-gui-install) for a video demonstation

   2. Once installed, open ```Anaconda Prompt```<br>
   ![Ananconda prompt](/POC/Images/conda.png)

   3. Type 
      ```bash
      conda create --name my_env python=3.11
      ```
      Accept all the conditions by pressing ``` a``` or ```y``` <br><br>
      ![Conda create Enviroment](/POC/Images/Create%20env.png) <br>

   4. Confirm the installation <br>
      * The terminal will ask ``` Proceed ([y]/n)?```. 
      * Type ```y``` and press Enter 

   5. To activate the enviroment you just created. Type
      ```bash
      conda activate my_env
      ```
      ![Conda Activate Enviroment](/POC/Images/activate%20env.png) <br>

   6. Install the following by typing ```pip install``` followed by the library.<br>
     
      ![Conda Install Libraries](/POC/Images/install%20library.png) <br>
      ```bash
      pip install mediapipe==0.10.9
      ```
      ```bash
      pip install pyautogui==0.9.54
      ```
      ```bash
      pip install pynput==1.8.1
      ```
      ```bash
      pip install numpy==2.2.6
      ```
      ```bash
      pip install pygrabber==0.2
      ```
      ```bash
      pip install python-osc==1.8.1
      ```
      ```bash
      pip install pygame==2.6.1
      ```

   ### Microsoft Visual Studio Code
   1. Install **Microsoft Visual Studio Code** in your laptop by choosing the **Windows** option: <br>
   https://code.visualstudio.com/download
   ![VS Code](/POC/Images/vscode.png)
   2. Once installed, open ```Visual Studio code``` ![VScodesearch](/POC/Images/visual_search.png)
   3. Create a folder, then create a file named ```name.py```
   4. Click on the **Extensions** Icon on the left sidebar (**5th icon**, looks like **4 blocks**)
   ![VS Code Extension](/POC/Images/Extension.png)
   5. Search for ``` Python``` and click on **Install**
   ![VS Code Python](/POC/Images/Download%20Python.png)
   6. Add in the code from [POC Game code](https://github.com/cel-esx/EGL314_TeamB/blob/main/POC/POC%20Game%20Code) to your ```name.py``` file
      * Ensure that your **Visual Studio Code** folder contains the following
         * [Gesture Definition](/POC/new_gesture_definitions.csv) file
         * [Hand Images](/POC/Hand_Images) file
      >Add the ```POC Game Code```, ```Gesture Definition```, ```Hand_Images``` in the same folder. Refer to [Example](/POC/Images/Req%20Files.png)
      * Refer to [Capture Gesture](/POC/CAPTURE_GESTURE_README.md) ReadMe file to know how to add / delete gestures
   7. Ensure that the ```IP Addess``` & ```Port Number``` is to your own laptop
   ![POC IP Change](/POC/Images/IP%20Config.png)
   > Type **Command Prompt** in your search bar & Type **ipconfig** to see your IP Address
   ![Laptop IP Address](/POC/Images/Wifi.png)

   > Note: If you are doing the **POC version** of the game, the script will have **Multiplay** <br>If you are doing the **MVP version** of the game, the script will have **Reaper** & **L-ISA**
   8. Press ```F5``` or click  ```Run``` . It should show e.g. ``` Python 3.13.2 (base) \miniconda3/python.exe ``` 
   9. If Step 8 fails to work as expected
   * Click on the top middle search bar
   * Type  ``` > ```
   * Click on ``` Python: Select Interpreter ```
   * Select your python enviroment

   ### Jupyter Notebook Installation Steps

   [Aqliah Pls Update Here]

   ### GrandMA3
   Please click on this [link](/POC/grandma3/grandMA3setup.md) to learn how to setup GrandMA3 on your laptops



   ### MultiPlay
   Click here to go [Multiplay](/POC/Multiplay/MultiPlay.md) folder

   ### Reaper
   Click here to go [Reaper](/POC/Multiplay/MultiPlay.md) folder

   ### L-ISA
   Click here to go [L-ISA](/POC/Multiplay/MultiPlay.md) folder


   

