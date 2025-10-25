# yolo_integration.py
from ultralytics import YOLO
import cv2

HAZARDS = {"knife", "fire", "scissors", "stop sign"}  # lowercase labels

def yolo_stream(cap_index=0, size=(640, 480), model_path="yolov8n.pt",
                conf_threshold=0.5, stop_evt=None):
    """
    Generator yielding (dets, img_w, img_h, hazards) continuously.
    dets: {'label','conf','box':[x1,y1,x2,y2],'img_w','img_h}
    """
    model = YOLO(model_path)

    # more reliable backend on Windows
    cap = cv2.VideoCapture(cap_index, cv2.CAP_DSHOW)
    w, h = size
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

    try:
        while True:
            if stop_evt is not None and stop_evt.is_set():
                break
            ok, frame = cap.read()
            if not ok:
                break
            if (frame.shape[1], frame.shape[0]) != (w, h):
                frame = cv2.resize(frame, (w, h))

            results = model(frame)
            boxes = results[0].boxes
            dets, hazards = [], []
            names = model.names  # id -> label

            for b in boxes:
                conf = float(b.conf[0])
                if conf < conf_threshold:
                    continue
                cls = int(b.cls[0])
                label = names[cls].lower()
                x1, y1, x2, y2 = map(float, b.xyxy[0].tolist())
                dets.append({"label": label, "conf": conf, "box": [x1, y1, x2, y2], "img_w": w, "img_h": h})
                if label in HAZARDS:
                    hazards.append(label)

            yield dets, w, h, hazards
    finally:
        cap.release()
        cv2.destroyAllWindows()
