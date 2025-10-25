# Model Performance Comparison
# For visually impaired assistance, we want FAST and ACCURATE

## YOLOv8 Model Options:

### yolov8n.pt (Nano) - CURRENTLY USING
- **Speed**: Fastest (~2-5ms per frame)
- **Accuracy**: Good for common objects
- **Size**: 6 MB
- **Best for**: Real-time on lower-end hardware
- ✅ **Recommended for**: Quick scanning, high FPS needed

### yolov8s.pt (Small)
- **Speed**: Very fast (~5-10ms per frame)
- **Accuracy**: Better than nano
- **Size**: 22 MB
- **Best for**: Balance of speed and accuracy
- ✅ **Recommended for**: Better object recognition with minimal latency

### yolov8m.pt (Medium)
- **Speed**: Moderate (~15-25ms per frame)
- **Accuracy**: Significantly better
- **Size**: 52 MB
- **Best for**: High accuracy needs
- ⚠️ **May add noticeable lag**: Test first

### yolov8l.pt (Large)
- **Speed**: Slower (~30-50ms per frame)
- **Accuracy**: Excellent
- **Size**: 87 MB
- ❌ **Too slow for accessibility**: Not recommended

## Recommendation for Visually Impaired:

**Use yolov8s.pt** - Best balance of speed and accuracy
- Downloads automatically on first use
- Only ~5-10ms slower than nano
- Much better at detecting objects in challenging conditions
- Still fast enough for real-time assistance

## How to Switch Models:

### Option 1: Edit yolo_integration.py
Change line: `model_path="yolov8n.pt"` to `model_path="yolov8s.pt"`

### Option 2: Command line (if we add parameter)
```powershell
python assist_loop_hardened.py --source yolo --model yolov8s.pt
```

## Other Improvements (No API needed):

1. **Lower confidence threshold** for better detection
   - Current: 0.5 (50%)
   - Try: 0.4 (40%) for more detections
   
2. **Better lighting** = Better detection
   - YOLO struggles in dark environments
   - Consider suggesting room lighting

3. **Object-specific thresholds**
   - People: 0.5 (keep high to avoid false positives)
   - Small objects (cups, phones): 0.3 (allow lower confidence)
