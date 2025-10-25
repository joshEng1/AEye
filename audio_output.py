import pyttsx3
import time

def speak_closest_object_distance(objects, distances):
    if not objects or not distances:
        return

    # Find closest object
    min_index = distances.index(min(distances))
    obj = objects[min_index]
    dist_meters = distances[min_index]

    # Convert to feet and inches
    total_inches = dist_meters * 39.3701
    feet = int(total_inches // 12)
    inches = int(total_inches % 12)

    sentence = f"There is a {obj} {feet} feet {inches} inches away."
    print(f"[Speaking: {sentence}]")  # Debug output
    
    try:
        # Reinitialize engine each time to prevent blocking issues
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 1.0)
        engine.say(sentence)
        engine.runAndWait()
        del engine  # Force cleanup
        time.sleep(0.1)  # Small delay to ensure cleanup
    except Exception as e:
        print(f"Speech error: {e}")