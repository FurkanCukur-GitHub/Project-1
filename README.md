The "Autonomous Image Analysis and Threat Assessment System" is an advanced system that analyzes video footage captured by drones to perform scene understanding, object detection, object tracking, threat assessment, and prioritization. Utilizing cutting-edge technologies such as computer vision and machine learning, it analyzes videos to evaluate entities and threats in the environment. Through its user-friendly interface, users can define relationships (e.g., friend or foe) and observe calculated threat levels. The system features a modular architecture that integrates the YOLOv8 model for object detection, the Deep SORT algorithm for object tracking, and rule-based threat assessment algorithms. This enhances the system's accuracy, scalability, and adaptability.

To run the program, certain requirements need to be downloaded.

--------------------------------------------------------------------

Requirements:

--index-url https://download.pytorch.org/whl/cu118
torch==2.5.0+cu118
torchvision==0.20.0+cu118
torchaudio==2.5.0+cu118
PyQt5
ultralytics
opencv-python
numpy
deep-sort-realtime

These requirements are available in the requirements.txt file.

--------------------------------------------------------------------

For the system to work using the GPU:

- CUDA Version (for PyTorch): 11.8
- cuDNN v8.9.7, for CUDA 11.x

These hardware components need to be installed.

--------------------------------------------------------------------

To download the CUDA Version (for PyTorch): 11.8, you need to visit the following site, download the file, and perform the installation.

https://developer.nvidia.com/cuda-11-8-0-download-archive

--------------------------------------------------------------------

To download cuDNN v8.9.7, for CUDA 11.x, visit the following site, download the ZIP file, and make some adjustments.

https://developer.nvidia.com/rdp/cudnn-archive

After downloading the file, the following adjustments need to be made:

Extract the cuDNN File
Extract the downloaded cuDNN v8.9.7 ZIP file into a folder.

Copy the Required Files
Inside the extracted folder, there will be folders such as bin, include, and lib. You need to copy these to the directory where CUDA is installed as follows:

cuDNN File Location (Source)	    Destination Location (New Location)
cudnn/bin/cudnn64_8.dll	          C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin
cudnn/include/cudnn.h	            C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\include
cudnn/lib/x64/cudnn.lib	          C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\lib\x64

In summary:
cudnn64_8.dll from cuDNN's bin folder → CUDA's bin folder
cudnn.h from cuDNN's include folder → CUDA's include folder
cudnn.lib from cuDNN's lib\x64 folder → CUDA's lib\x64 folder

--------------------------------------------------------------------

If the environment variables have not been updated, update them manually.

If the system has not added the cuDNN libraries to the PATH variable, follow these steps:

Control Panel → System → Advanced system settings → Environment Variables
Under "System Variables," select Path and click Edit.

Click New and add the following paths:
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\lib\x64

Save and close by clicking OK.

--------------------------------------------------------------------

Now you can run the application.
