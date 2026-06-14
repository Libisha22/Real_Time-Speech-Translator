import whisper, asyncio, numpy as np, sounddevice as sd
from deep_translator import GoogleTranslator
from gtts import gTTS
import pygame
import tempfile, os, queue, threading, time
LANGUAGES = {
    'en': 'English', 'hi': 'Hindi', 'ta': 'Tamil', 'ml': 'Malayalam', 'te': 'Telugu',
    'kn': 'Kannada', 'mr': 'Marathi', 'gu': 'Gujarati', 'pa': 'Punjabi', 'bn': 'Bengali',
    'ur': 'Urdu', 'or': 'Odia','fr':'French', 'de': 'German', 'es': 'Spanish', 'it': 'Italian', 'pt': 'Portuguese', 
    'ru': 'Russian', 'ja':' Japanese', 'ko': 'Korean', 'zh-CN': 'Chinese (Simplified)', 'zh-TW': 'Chinese (Traditional)',
      'ar': 'Arabic', 'tr': 'Turkish', 'th': 'Thai', 'vi': 'Vietnamese', 'pl': 'Polish', 'ro': 'Romanian', 'cs': 'Czech', 
      'nl': 'Dutch', 'fa': 'Persian (Farsi)', 'uk': 'Ukrainian', 'id': 'Indonesian', 'sw': 'Swahili',
}
SAMPLE_RATE, BLOCK_SIZE, CHANNELS, BUFFER_DURATION, THRESHOLD = 16000, 1024, 1, 5, 0.01
audio_q, stop_event = queue.Queue(), threading.Event()
model = whisper.load_model("base")
[print(f"{k}: {v}") for k, v in LANGUAGES.items()]
TARGET = input("Enter target language code : ").strip().lower()
TARGET = TARGET if TARGET in LANGUAGES else 'en'
print(f"Translating to {LANGUAGES[TARGET]}...")
def audio_callback(indata, *_): audio_q.put(indata.copy())
def is_loud(audio): return np.abs(audio).mean() > THRESHOLD
def clean(text): return text.replace("uh", "").replace("um", "").replace("you know", "").replace("like", "").strip()
def translate_official(text, retries=3):
    for attempt in range(1, retries + 1):
        try:
            return GoogleTranslator(source='auto', target=TARGET).translate(text)
        except Exception as e:
            print(f"Translation attempt {attempt} failed:", e)
            time.sleep(1)
    return "Translation Error: connection timed out"
def speak(text):
    try:
        tts = gTTS(text, lang=TARGET)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            temp_path = f.name
            tts.save(temp_path)
        if os.path.exists(temp_path):
            pygame.mixer.quit()
            pygame.mixer.init()
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.music.unload()
            pygame.mixer.quit()
            os.remove(temp_path)
        else:
            print("TTS error: file not saved.")
    except Exception as e:
        print("TTS error:", e)
def process_audio():
    buf, limit = [], int(BUFFER_DURATION * SAMPLE_RATE / BLOCK_SIZE)
    while not stop_event.is_set():
        try:
            buf.append(audio_q.get(timeout=0.1))
            if len(buf) < limit: continue
            audio = np.concatenate(buf).flatten().astype(np.float32); buf.clear()
            if not is_loud(audio): print("Silent."); continue

            result = model.transcribe(audio, fp16=False, temperature=0)
            if result.get("no_speech_prob", 0) > 0.6: print("Background noise."); continue
            raw = result.get("text", "").strip()
            cleaned = clean(raw)
            if not cleaned: print("Filler filtered."); continue
            print("Original:", raw)
            print("Cleaned:", cleaned)
            translated = translate_official(cleaned)
            print("Translated:", translated)
if not translated.startswith("Translation Error"):
                speak(translated)
            else:
                print("Skipping TTS due to translation failure.")

        except queue.Empty:
            continue
def main():
    threading.Thread(target=process_audio).start()
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, blocksize=BLOCK_SIZE, callback=audio_callback):
            print("\nListening... Press Ctrl+C to stop.\n")
            while not stop_event.is_set(): time.sleep(0.1)
    except KeyboardInterrupt: print("Stopping...")
    finally: stop_event.set()
if __name__ == "__main__": main()
