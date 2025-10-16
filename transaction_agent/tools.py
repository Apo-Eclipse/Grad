# tools.py

import os
import speech_recognition as sr
from pydub import AudioSegment
from langchain.agents import tool
from dotenv import load_dotenv

load_dotenv()


@tool
def process_audio_transaction(audio_path: str) -> str:
    """
    Processes an audio file to extract transaction details by transcribing it to text.
    Use this tool when the input is a file path to an audio file (e.g., /path/to/transaction.wav).
    This tool supports formats like wav, mp3, m4a, etc.
    """
    print(f"--- Calling Audio Tool with path: {audio_path} ---")
    
    if not os.path.exists(audio_path):
        return "Error: The audio file was not found at the specified path."

    try:
        if not audio_path.lower().endswith('.wav'):
            sound = AudioSegment.from_file(audio_path)
            wav_path = "temp_transaction.wav"
            sound.export(wav_path, format="wav")
        else:
            wav_path = audio_path
    except Exception as e:
        return f"Error converting audio file: {e}"

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
        try:
            transcribed_text = recognizer.recognize_google(audio_data, language="ar-EG")
            print(f"Transcribed Text: {transcribed_text}")
            return f"Extracted from audio: {transcribed_text}"
        except sr.UnknownValueError:
            return "Speech Recognition could not understand the audio."
        except sr.RequestError as e:
            return f"Could not request results from Speech Recognition service; {e}"
        finally:
            if wav_path == "temp_transaction.wav" and os.path.exists(wav_path):
                os.remove(wav_path)
