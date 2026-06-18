# Setup Guide
###  This page contains all the materials required & the instructions on how to download those materials in order to run this game in the POC stage


## Hardware 
 1) **Desktop / Laptop** (Windows)
 2) **External USB Webcam** (Optional: Use if inbuilt webcam is spoilt or if you need better resolution)
 3) **Lighting Equipment** (Optional: You can also use the GrandMA3 3D viewer for visuals)
 4) **Speakers** (Optional)


## Software
  1. **Anaconda**
     * Click Here: [Anaconda Setup](#anaconda-set-up)
  2. **Microsoft Visual Studio Code**
     * Click Here: [Visual Studio Code Setup](#microsoft-visual-studio-code)
  3. **GrandMA3**
     * Click Here: [GrandMa3 Setup](#grandma3)
  4. **MultiPlay**
     * Click Here: [MultiPlay Setup](#multiPlay)

  ## Dependencies
  #### This code have been tested using **Python 3.10 or higher**   

  ## Setting Up - How to install?
   
   ### Anaconda Set-Up
   1. Install **Anaconda** in your laptop:<br>
   https://www.anaconda.com/docs/getting-started/anaconda/install/windows-gui-install

   2. Once installed, open ```Anaconda Prompt```<br>
   ![Ananconda prompt](/Images/conda.png)

   3. Type 
      ```bash
      conda create --name my_env python=3.11
      ```
      Accept all the conditions by pressing ``` a``` <br><br>
      ![Conda create Enviroment](/Images/Create%20env.png) <br>

   4. Confirm the installation <br>
      * The terminal will ask ``` Proceed ([y]/n)?```. 
      * Type ```y``` and press Enter 

   5. To activate the enviroment you just created. Type
      ```bash
      conda activate my_env
      ```
      ![Conda Activate Enviroment](/Images/activate%20env.png) <br>

   6. Install the following by typing ```conda install``` followed by the library.<br>
     
      ![Conda Install Libraries](/Images/install%20library.png) <br>

      ```bash
      opencv-python==4.13.0.92
      ```
      ```bash
      mediapipe==0.10.9
      ```
      ```bash
      pyautogui==0.9.54
      ```
      ```bash
      pynput==1.8.1
      ```
      ```bash
      numpy==2.2.6
      ```
      ```bash
      pygrabber==0.2
      ```
      ```bash
      python-osc==1.8.1
      ```
      ```bash
      pygame==2.6.1
      ```

   ### Microsoft Visual Studio Code
   1. Install **Microsoft Visual Studio Code** in your laptop by choosing the **Windows** option: <br>
   https://code.visualstudio.com/download
   ![VS Code](/Images/vscode.png)
   2. Once installed, open ```Visual Studio code``` ![VScodesearch](/Images/visual_search.png)
   3. Create a folder, then create a file named ```name.py```
   4. Click on the **Extensions** Icon on the left sidebar (**5th icon**, looks like **4 blocks**)
   ![VS Code Extension](/Images/Extension.png)
   5. Search for ``` Python``` and click on **Install**
   ![VS Code Python](/Images/Download%20Python.png)
   6. Add in the code from [POC Game code](https://github.com/cel-esx/EGL314_TeamB/blob/main/POC/POC%20Game%20Code) to your ```name.py``` file
   7. Press ```F5``` or click  ```Run``` . It should show e.g. ``` Python 3.13.2 (base) \miniconda3/python.exe ``` 
   8. If Step 7 fails to work as expected
      * Click on the top middle search bar
      * Type  ``` > ```
      * Click on ``` Python: Select Interpreter ```
      * Select your python enviroment

   ### GrandMA3
   (Add how to install GrandMA3)



   ### MultiPlay
   (Add how to install MultiPlay)
   

