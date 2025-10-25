from distance_output import speak_closest_object_distance
from object_counter import format_object_counts
from voice_listener import listen_command
import pyttsx3
import random
import time
import sys

def speak(text):
    """Local speak function for test simulation"""
    print(f"[Speaking: {text}]")
    sys.stdout.flush()  # Force print to show immediately
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 1.0)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        del engine
        time.sleep(0.2)  # Increased delay
    except Exception as e:
        print(f"Speech error: {e}")
        sys.stdout.flush()

possible_objects = ["person", "chair", "bottle", "laptop", "dog", "tree"]

def simulate_yolo():
    """Simulate YOLO detection with random objects and distances"""
    detected_objects = random.choices(possible_objects, k=random.randint(1, 6))
    distances = [round(random.uniform(0.5, 5.0), 2) for _ in detected_objects]
    return detected_objects, distances

# Interactive test mode
print("Interactive Test Mode")
print("Say commands like:")
print("  - 'what's in front of me'")
print("  - 'how close am I'")
print("  - 'how many chairs' (or any object)")
print("  - 'quit' or 'exit' to stop")
print("-" * 50)

while True:
    # Generate new simulated detection
    detected_objects, distances = simulate_yolo()
    
    print(f"\n[Simulated detection: {detected_objects}]")
    print(f"[Distances: {distances}]")
    
    # Listen for command
    command = listen_command()
    
    # Exit condition
    if "quit" in command or "exit" in command or "stop" in command:
        speak("Goodbye!")
        print("Exiting test mode.")
        break
    
    # Process commands
    if "what's in front" in command or "what is in front" in command:
        text = format_object_counts(detected_objects)
        speak(f"In front of you there are: {text}.")

    elif "how close" in command or "how far" in command:
        speak_closest_object_distance(detected_objects, distances)

    elif "how many" in command:
        found = False
        for obj in possible_objects:
            if obj in command:
                count = detected_objects.count(obj)
                if count > 0:
                    speak(f"There {'is' if count==1 else 'are'} {count} {obj if count==1 else obj+'s'}.")
                else:
                    speak(f"There are no {obj}s.")
                found = True
                break
        if not found:
            speak("I didn't catch which object you're asking about.")

    else:
        speak("Sorry, I did not understand. Please ask again.")
        