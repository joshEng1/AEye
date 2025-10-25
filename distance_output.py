import pyttsx3

engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak_closest_object_distance(objects, distances):
    """
    objects: list of object names
    distances: list of floats in meters
    """
    if not objects or not distances:
        return

    # Find the closest object
    min_index = distances.index(min(distances))
    obj = objects[min_index]
    dist = distances[min_index]

    engine.say(f"The closest object is {obj} at {dist:.1f} meters")
    engine.runAndWait()
