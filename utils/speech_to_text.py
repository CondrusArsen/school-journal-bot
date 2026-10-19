import speech_recognition as sr
from pydub import AudioSegment
import os
import logging
import shutil


def ensure_ffmpeg():
    """Prepare optional audio tooling only when voice input is requested."""
    if shutil.which("ffmpeg"):
        return
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except ImportError:
        logging.warning("static_ffmpeg not found. Ensure ffmpeg is installed manually.")

async def convert_voice_to_text(file_path: str) -> str:
    """
    Converts a voice message (OGG/OGA) to text using SpeechRecognition.
    Requires ffmpeg to be installed on the system for pydub's conversion.
    """
    print(f"Starting STT for: {file_path}")
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return "ERROR_FILE_NOT_FOUND"

    wav_path = file_path.replace(".oga", ".wav").replace(".ogg", ".wav")
    print(f"Target WAV path: {wav_path}")
    
    try:
        ensure_ffmpeg()
        # Convert OGG to WAV
        print("Converting OGG to WAV...")
        audio = AudioSegment.from_file(file_path)
        audio.export(wav_path, format="wav")
        print("Conversion successful.")
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            print("Reading WAV file...")
            audio_data = recognizer.record(source)
            # Using Google Speech Recognition (free, no API key required for small use)
            print("Requesting Google STT...")
            text = recognizer.recognize_google(audio_data, language="ru-RU")
            print(f"Recognized text: {text}")
            return text
    except sr.UnknownValueError:
        print("Google STT: Speech was unintelligible")
        return "ERROR_UNINTELLIGIBLE"
    except sr.RequestError as e:
        print(f"Google STT: Request error: {e}")
        return f"ERROR_REQUEST_FAILED: {e}"
    except Exception as e:
        import traceback
        print(f"STT Exception: {e}")
        traceback.print_exc()
        return f"ERROR_GENERAL: {str(e)}"
    finally:
        # Cleanup temporary WAV file
        if os.path.exists(wav_path):
            os.remove(wav_path)
            print("Cleaned up WAV file.")
