import speech_recognition as sr

recognizer = sr.Recognizer()
mic = sr.Microphone()

def listen_command():
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print("Listening...")
        # Remove timeout - wait indefinitely for speech
        audio = recognizer.listen(source, timeout=None, phrase_time_limit=10)
    try:
        print("Processing...")
        # Google API call without timeout parameter
        command = recognizer.recognize_google(audio)
        print(f"You said: {command}")
        return command.lower()
    except sr.UnknownValueError:
        print("Could not understand audio")
        return ""
    except sr.RequestError as e:
        print(f"Speech recognition service failed: {e}")
        return ""
    except Exception as e:
        print(f"Unexpected error: {e}")
        return ""