# yolo_integration.py
from ultralytics import YOLO
import cv2
# put near the top of the file that calls model(...)
import logging
from ultralytics.utils import LOGGER
LOGGER.setLevel(logging.ERROR)  # silence "0: 480x640 ..." lines

HAZARDS = {"knife", "fire", "scissors", "stop sign"}  # lowercase labels

def yolo_stream(cap_index=0, size=(640, 480), model_path="yolov8n.pt",
                conf_threshold=0.5, stop_evt=None, show_window=True):
    """
    Generator yielding (dets, img_w, img_h, hazards) continuously.
    dets: {'label','conf','box':[x1,y1,x2,y2],'img_w','img_h}
    
    Args:
        show_window: If True, displays annotated video feed in window
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

            results = model(frame, conf=conf_threshold, verbose=False)

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

            # Show annotated video if requested
            if show_window:
                annotated = results[0].plot()
                cv2.imshow("AEye - YOLO Detection", annotated)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    if stop_evt:
                        stop_evt.set()
                    break

            yield dets, w, h, hazards
    finally:
        cap.release()
        cv2.destroyAllWindows()
