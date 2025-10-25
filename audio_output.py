import pyttsx3

engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak_objects(objects):
    """
    objects: list of object names
    """
    if not objects:
        return
    text_to_speak = ", ".join(objects)
    engine.say(f"Detected objects: {text_to_speak}")
    engine.runAndWait()
