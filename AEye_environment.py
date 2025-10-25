from ultralytics import YOLO
import cv2
import pyttsx3
import threading
from queue import Queue
import time


# List of objects considered hazardous
HAZARDS = ["knife", "fire","scissors", "Stop sign"]  # Example, adjust as needed

def detect_hazards(frame, model, conf_threshold=0.5):
    """
    Detect hazardous objects in a frame using YOLOv8.

    Args:
        frame: the image/frame to analyze
        model: YOLOv8 model
        conf_threshold: minimum confidence to consider detection valid

    Returns:
        hazards_found: list of hazardous object labels
        results: full YOLO detection results (for plotting/other use)
    """
    results = model(frame)  # Run YOLOv8 inference
    hazards_found = []

    for box in results[0].boxes:
        conf = box.conf[0].item()
        cls = int(box.cls[0].item())
        label = model.names[cls]

        if conf > conf_threshold and label.lower() in HAZARDS:
            hazards_found.append(label)

    return hazards_found, results



# Load YOLOv8 model
model = YOLO("yolov8n.pt")

# Initialize speech engine
engine = pyttsx3.init()
engine.setProperty("rate", 170)
engine.setProperty("volume", 1.0)

speech_queue = Queue()
last_spoken = {}
speak_delay = 3  # seconds
stop_signal = threading.Event()  # signal to stop threads

# Speech thread function
def speech_worker():
    while not stop_signal.is_set():
        try:
            sentence = speech_queue.get(timeout=0.1)
        except:
            continue
        if sentence is None:
            break
        engine.say(sentence)
        engine.runAndWait()
        speech_queue.task_done()

speech_thread = threading.Thread(target=speech_worker, daemon=True)
speech_thread.start()

# Frame queue
frame_queue = Queue(maxsize=1)
annotated_frame = None

# Video capture thread
def capture_frames():
    global annotated_frame
    cap = cv2.VideoCapture(0)
    while not stop_signal.is_set():
        ret, frame = cap.read()
        if not ret:
            break

        # Optional: resize for faster processing
        small_frame = cv2.resize(frame, (640, 480))
        if not frame_queue.full():
            frame_queue.put(small_frame)

        # Show annotated frame if available
        if annotated_frame is not None:
            cv2.imshow("YOLOv8 with Speech", annotated_frame)

        # Quit on 'k'
        if cv2.waitKey(1) & 0xFF == ord('k'):
            stop_signal.set()
            break

    cap.release()
    cv2.destroyAllWindows()
    frame_queue.put(None)  # signal processing thread to stop

# Start capture thread
threading.Thread(target=capture_frames, daemon=True).start()

# Process frames from queue
while not stop_signal.is_set():
    frame = frame_queue.get()
    if frame is None:
        break

    hazards, results = detect_hazards(frame, model)

    # Output hazards first
    if hazards:
        print("⚠️ Hazards detected:", ", ".join(hazards))
        for hazard in hazards:
            current_time = time.time()
            if hazard not in last_spoken or (current_time - last_spoken[hazard]) > speak_delay:
                speech_queue.put(f"Hazard detected: {hazard}")
                last_spoken[hazard] = current_time

    annotated_frame = results[0].plot()

    # Optional: announce normal objects (same as before)
    current_time = time.time()
    for box in results[0].boxes:
        conf = box.conf[0].item()
        cls = int(box.cls[0].item())
        label = model.names[cls]

        if conf > 0.5 and label.lower() not in HAZARDS:
            if label not in last_spoken or (current_time - last_spoken[label]) > speak_delay:
                speech_queue.put(f"I see a {label}")
                last_spoken[label] = current_time

# Cleanup
stop_signal.set()
speech_queue.put(None)
speech_thread.join()
engine.stop()
