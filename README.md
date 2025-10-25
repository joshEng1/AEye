# YOLO NLP MockKit (no real YOLO required)

This lets you **test your NLP + temporal logic** at **640×480, 24fps** without the real YOLO code.

## Files
- `nlp_core.py` — intent/slot parser and `TemporalBuffer` smoothing.
- `mock_yolo.py` — generates synthetic detections for several scenarios.
- `run_mock.py` — CLI that streams a scenario and lets you type questions.
- `tests/test_nlp.py` — optional pytest tests.

## Quick start (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
# No heavy deps needed (pytest optional)
pip install pytest -q
# Run the mock stream and ask questions
python run_mock.py --scenario person_lr
# Try:
# > how many people on the left?
# > is there a dog?
# > where is the car?
# > describe the scene
```

### Scenarios
- `person_lr` — one person walking left→right for 5s.
- `blink_dog` — steady person + a dog that appears only one frame (tests persistence).
- `crowd_car` — four people (static) + a red car driving across.
- `empty` — nothing detected.

Use `--duration` to control how many seconds of synthetic frames are created each cycle, and `--window-sec` to tune the temporal smoothing window (default **0.6 s ≈ 12 frames**).

### How answers are produced
- We fill the `TemporalBuffer` with synthetic frames.
- Each question is parsed into an intent + slots.
- The buffer computes **median count**, **presence with persistence**, or **most-frequent region** to avoid one-frame flicker.

### Plug in the real YOLO later
When you get the real detector, replace the scenario filler with real frames and call `tb.ingest(real_detections)`, where each detection is:
```json
{"label": "person", "conf": 0.92, "box": [x1,y1,x2,y2], "img_w": 640, "img_h": 480}
```
(Optionally include `"color": "red"` if you compute per-box colors upstream.)

### Tests
Run `pytest` to exercise the parser and temporal buffer.
```powershell
pytest -q
```