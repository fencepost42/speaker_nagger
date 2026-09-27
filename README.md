\# speaker\_nagger



Listens to \*\*Windows speaker output\*\* (WASAPI loopback).  

If nothing is playing for 20 seconds, it says:



> why no talking.. we need more talking



Works on anything that comes out the default playback device (X Spaces in a browser, Zoom, YouTube, etc.). It does \*\*not\*\* join an X Space or inject audio into X.



\## Install



```powershell

pip uninstall pyaudio -y

pip install PyAudioWPatch numpy pyttsx3

