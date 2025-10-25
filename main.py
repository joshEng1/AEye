import keyboard
import time
from audio_output import speak_objects
from distance_output import speak_closest_object_distance

# Simulated YOLO output (replace with real output later)
detected_objects = ["person", "chair", "bottle"]
distances = [2.5, 1.0, 3.2]  # in meters

while True:
    if keyboard.is_pressed('a'):  # Press 'a' to speak objects
        speak_objects(detected_objects)
        time.sleep(0.5)  # avoid multiple triggers

    if keyboard.is_pressed('d'):  # Press 'd' to speak closest distance
        speak_closest_object_distance(detected_objects, distances)
        time.sleep(0.5)
