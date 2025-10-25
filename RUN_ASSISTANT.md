# AEye Assistant - Quick Start Guide

## Important: Always Activate Virtual Environment First!
```powershell
.\.venv311\Scripts\Activate.ps1
```

## Recommended Commands

### 1. Standard Mode (Fast, Good Accuracy)
```powershell
.\.venv311\Scripts\python.exe assist_loop_hardened.py --source yolo --stt mic --mic-index 1 --trigger enter
```

### 2. High Accuracy Mode (Slightly Slower, Better Detection)
```powershell
.\.venv311\Scripts\python.exe assist_loop_hardened.py --source yolo --stt mic --mic-index 1 --trigger enter --model yolov8s.pt
```

### 3. More Sensitive Detection (Lower Threshold)
```powershell
.\.venv311\Scripts\python.exe assist_loop_hardened.py --source yolo --stt mic --mic-index 1 --trigger enter --model yolov8s.pt --confidence 0.4
```

### 4. Debug Mode (See All Detections)
```powershell
.\.venv311\Scripts\python.exe assist_loop_hardened.py --source yolo --stt mic --mic-index 1 --trigger enter --debug
```

## Model Options

| Model | Speed | Accuracy | Best For |
|-------|-------|----------|----------|
| `yolov8n.pt` | ⚡⚡⚡ Fastest | ⭐⭐ Good | Quick scanning, low-end hardware |
| `yolov8s.pt` | ⚡⚡ Very Fast | ⭐⭐⭐ Better | **RECOMMENDED - Best balance** |
| `yolov8m.pt` | ⚡ Moderate | ⭐⭐⭐⭐ Great | Challenging conditions |

## Confidence Threshold

- **0.5 (default)**: Standard - fewer false positives
- **0.4**: More sensitive - catches more objects
- **0.3**: Very sensitive - may have false positives
- **0.6+**: Strict - only very confident detections

## How It Works

### Spatial Awareness (Already Built-in!)
The system divides the camera view into regions:
- **Horizontal**: left, center, right
- **Vertical**: top, bottom

### Example Questions:

#### Counting
- "how many people?"
- "how many chairs on the left?"
- "count the people"

#### Location
- "where is the person?"
- "where is the closest chair?"
- ➜ Answers like: "on the left at the bottom"

#### Presence Check
- "is there a person?"
- "do you see a cup on the right?"
- "are there any chairs?"

#### Scene Description
- "describe the scene"
- "what do you see?"
- "what's in front of me?"
- ➜ Answers like: "I see 2 people, 1 chair (1 on left, 2 in center)"

#### Alerts (Future Use)
- "alert me when a person appears"
- "tell me if a car shows up on the left"

## Quick Voice Commands (when running)
- `a` or `objects` - List all detected objects
- `d` or `closest` - Describe closest object
- `debug:status` - Show buffer status

## Troubleshooting

### Black Camera Screen
```powershell
# Kill old Python processes
Get-Process python* | Stop-Process -Force

# Then run again
.\.venv311\Scripts\python.exe find_cameras.py
```

### Microphone Not Working
```powershell
# List available microphones
.\.venv311\Scripts\python.exe assist_loop_hardened.py --list-devices

# Use different mic index (try 1, 2, 7, etc.)
--mic-index 2
```

### Better Detection Tips
1. **Good lighting** - YOLO needs light to see well
2. **Use yolov8s.pt model** - Better accuracy with minimal lag
3. **Lower confidence to 0.4** - Catch more objects
4. **Position camera** - Face objects directly when possible

## Exit Commands
- Press **'q' in video window**
- Press **Ctrl+C in terminal**
