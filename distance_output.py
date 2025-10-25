import pyttsx3

engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

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
    engine.say(sentence)
    engine.runAndWait()