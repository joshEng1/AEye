#!/usr/bin/env python3
"""Quick microphone test script"""
import speech_recognition as sr

print("=" * 50)
print("MICROPHONE TEST")
print("=" * 50)

# Test 1: List devices
print("\n1. Available Microphones:")
mics = sr.Microphone.list_microphone_names()
for i, name in enumerate(mics):
    if "microphone" in name.lower() or "array" in name.lower():
        print(f"   [{i}] {name}")

# Test 2: Try to record
print("\n2. Testing microphone recording...")
print("   Please say something when prompted...")

try:
    r = sr.Recognizer()
    # Use device 1 (Realtek Microphone Array) by default
    with sr.Microphone(device_index=1) as source:
        print("   🎤 Listening for 3 seconds... Speak now!")
        r.adjust_for_ambient_noise(source, duration=0.5)
        audio = r.listen(source, timeout=3, phrase_time_limit=5)
        print("   ✓ Audio captured successfully!")
        
        # Try to recognize
        print("   🔍 Recognizing speech...")
        text = r.recognize_google(audio)
        print(f"   ✓ Recognized: '{text}'")
        
except sr.WaitTimeoutError:
    print("   ⚠ Timeout: No speech detected")
except sr.UnknownValueError:
    print("   ⚠ Could not understand audio")
except sr.RequestError as e:
    print(f"   ❌ API Error: {e}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    print("\nTry running with a different device index:")
    print("   python test_mic_quick.py")

print("\n" + "=" * 50)
