#!/usr/bin/env python3
"""Quick camera test to diagnose video feed issues"""
import cv2
import sys

print("=" * 60)
print("CAMERA DIAGNOSTIC TEST")
print("=" * 60)

# Test 1: Try default camera with DSHOW backend (Windows)
print("\n1. Testing camera with CAP_DSHOW backend...")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("   ❌ Failed to open camera with DSHOW backend")
    print("   Trying default backend...")
    cap = cv2.VideoCapture(0)
    
if not cap.isOpened():
    print("   ❌ Failed to open camera with any backend")
    print("\nPossible issues:")
    print("   - Camera is being used by another application")
    print("   - Camera permissions not granted")
    print("   - No camera connected")
    sys.exit(1)

print("   ✓ Camera opened successfully")

# Get camera properties
width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
fps = cap.get(cv2.CAP_PROP_FPS)
print(f"   Resolution: {int(width)}x{int(height)}")
print(f"   FPS: {fps}")

# Test 2: Try to read frames
print("\n2. Testing frame capture...")
ret, frame = cap.read()

if not ret or frame is None:
    print("   ❌ Failed to capture frame")
    cap.release()
    sys.exit(1)

print(f"   ✓ Frame captured: {frame.shape}")
print(f"   Frame stats: min={frame.min()}, max={frame.max()}, mean={frame.mean():.1f}")

if frame.mean() < 5:
    print("   ⚠ WARNING: Frame is very dark (mean < 5)")
    print("   This might indicate:")
    print("   - Camera lens is covered")
    print("   - Lighting is very low")
    print("   - Camera driver issue")

# Test 3: Display video feed
print("\n3. Opening video window...")
print("   Press 'q' to quit the test")
print("   The window should show your camera feed")

frame_count = 0
while True:
    ret, frame = cap.read()
    if not ret:
        print(f"\n   ❌ Failed to read frame {frame_count}")
        break
    
    # Add frame counter
    cv2.putText(frame, f"Frame: {frame_count}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame, "Press 'q' to quit", (10, 70), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    cv2.imshow("Camera Test", frame)
    frame_count += 1
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print(f"\n   ✓ Successfully captured {frame_count} frames")
        break

cap.release()
cv2.destroyAllWindows()

print("\n" + "=" * 60)
print("Camera test complete!")
print("=" * 60)
