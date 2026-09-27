"""
Listen to Windows speaker OUTPUT via WASAPI loopback.
If output is quiet too long, speak the nag line.
"""
import time
import threading
import numpy as np
import pyttsx3
import pyaudiowpatch as pyaudio

SILENCE_SECONDS = 7.0
COOLDOWN_SECONDS = 45.0
RMS_THRESHOLD = 0.002
PHRASE = "why no talking.. we need more talking"
CHUNK = 2048

speaking = False
last_sound_t = time.monotonic()
last_nag_t = 0.0
lock = threading.Lock()

def find_loopback(p):
    wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    speakers = p.get_device_info_by_index(wasapi["defaultOutputDevice"])
    print(f"Default output: {speakers['name']}")

    if speakers.get("isLoopbackDevice"):
        return speakers

    for lb in p.get_loopback_device_info_generator():
        # match "Speakers (darkskull)" to "Speakers (darkskull) [Loopback]"
        if speakers["name"] in lb["name"] or lb["name"].startswith(speakers["name"]):
            return lb

    # last resort: first loopback device
    for lb in p.get_loopback_device_info_generator():
        return lb
    return None

def speak():
    global speaking, last_nag_t, last_sound_t
    with lock:
        speaking = True
    try:
        eng = pyttsx3.init()
        eng.setProperty("rate", 175)
        eng.say(PHRASE)
        eng.runAndWait()
    finally:
        now = time.monotonic()
        with lock:
            speaking = False
            last_nag_t = now
            last_sound_t = now

def main():
    global last_sound_t
    p = pyaudio.PyAudio()
    try:
        dev = find_loopback(p)
        if not dev:
            print("No WASAPI loopback device found.")
            print("Enable Stereo Mix or use a different output device.")
            return

        rate = int(dev["defaultSampleRate"])
        chans = int(dev["maxInputChannels"] or 2)
        print(f"Hooking loopback: [{dev['index']}] {dev['name']}")
        print(f"{rate} Hz, {chans} ch. Play anything. Ctrl+C to quit.\n")

        def callback(in_data, frame_count, time_info, status):
            global last_sound_t
            with lock:
                if speaking:
                    return (None, pyaudio.paContinue)
            samples = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
            if chans > 1:
                samples = samples.reshape(-1, chans).mean(axis=1)
            rms = float(np.sqrt(np.mean(samples * samples) + 1e-16))
            if rms >= RMS_THRESHOLD:
                last_sound_t = time.monotonic()
            return (None, pyaudio.paContinue)

        stream = p.open(
            format=pyaudio.paInt16,
            channels=chans,
            rate=rate,
            input=True,
            input_device_index=dev["index"],
            frames_per_buffer=CHUNK,
            stream_callback=callback,
        )
        stream.start_stream()
        last_sound_t = time.monotonic()
        print("Listening to speaker output...")

        while stream.is_active():
            time.sleep(0.25)
            now = time.monotonic()
            with lock:
                quiet = now - last_sound_t
                busy = speaking
                since_nag = now - last_nag_t
            if (not busy) and quiet >= SILENCE_SECONDS and since_nag >= COOLDOWN_SECONDS:
                print(f"quiet {quiet:.0f}s — saying the line")
                threading.Thread(target=speak, daemon=True).start()
                time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        p.terminate()

if __name__ == "__main__":
    main()