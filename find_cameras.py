#!/usr/bin/env python3
"""Test all available camera indices"""
import cv2

print("=" * 60)
print("SCANNING FOR CAMERAS")
print("=" * 60)

working_cameras = []

for i in range(5):  # Test indices 0-4
    print(f"\nTesting camera index {i}...")
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
    
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            mean_brightness = frame.mean()
            print(f"   ✓ Camera {i} works! Resolution: {frame.shape}, Brightness: {mean_brightness:.1f}")
            if mean_brightness > 5:
                working_cameras.append(i)
                print(f"   ✓ Camera {i} has valid image (not black)")
            else:
                print(f"   ⚠ Camera {i} produces black frames")
        else:
            print(f"   ❌ Camera {i} opened but can't read frames")
        cap.release()
    else:
        print(f"   ❌ Camera {i} not available")

print("\n" + "=" * 60)
if working_cameras:
    print(f"✓ Found {len(working_cameras)} working camera(s): {working_cameras}")
    print(f"\nRecommendation: Use camera index {working_cameras[0]}")
else:
    print("❌ No working cameras found!")
    print("\nTroubleshooting steps:")
    print("1. Close all apps using the camera (Zoom, Teams, Skype, etc.)")
    print("2. Check Windows camera privacy settings")
    print("3. Try running: Get-PnpDevice | Where-Object {$_.Class -eq 'Camera'}")
print("=" * 60)
