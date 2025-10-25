from audio_output import speak
from distance_output import speak_closest_object_distance
from object_counter import format_object_counts
from voice_listener import listen_command
import random

# Simulated YOLO output
possible_objects = ["person", "chair", "bottle", "laptop", "dog", "tree"]
detected_objects = []
distances = []

def simulate_yolo():
    global detected_objects, distances
    detected_objects = random.choices(possible_objects, k=random.randint(1, 6))
    distances = [round(random.uniform(0.5, 5.0), 2) for _ in detected_objects]

# Main loop
print("Say a command: 'what's in front of me', 'how close am I', 'how many X', or Ctrl+C to exit.")
while True:
    simulate_yolo()
    command = listen_command()

    if "what's in front" in command or "what is in front" in command:
        text = format_object_counts(detected_objects)
        speak(f"In front of you there are: {text}.")

    elif "how close" in command:
        speak_closest_object_distance(detected_objects, distances)

    elif "how many" in command:
        for obj in detected_objects:
            if obj in command:
                count = detected_objects.count(obj)
                speak(f"There {'is' if count==1 else 'are'} {count} {obj if count==1 else obj+'s'}.")

    else:
        speak("Sorry, I did not understand. Please ask again.")
