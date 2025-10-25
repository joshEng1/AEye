"""
Test microphone with current settings to debug the issue
"""
import speech_recognition as sr
import time

print("Testing microphone with debug info...")
print("=" * 60)

r = sr.Recognizer()
r.dynamic_energy_threshold = True

print("\nMicrophone devices:")
for index, name in enumerate(sr.Microphone.list_microphone_names()):
    print(f"  [{index}] {name}")

mic_index = 1
print(f"\nUsing microphone index: {mic_index}")

try:
    with sr.Microphone(device_index=mic_index) as source:
        print("\n🔊 Adjusting for ambient noise (0.5 seconds)...")
        start = time.time()
        r.adjust_for_ambient_noise(source, duration=0.5)
        elapsed = time.time() - start
        
        print(f"✅ Calibration complete in {elapsed:.2f}s")
        print(f"📊 Energy threshold: {r.energy_threshold}")
        print(f"📊 Dynamic threshold: {r.dynamic_energy_threshold}")
        print(f"📊 Pause threshold: {r.pause_threshold}")
        
        print("\n🎤 Speak now! (10 second timeout, 10 second max phrase)")
        print("-" * 60)
        
        start = time.time()
        audio = r.listen(source, timeout=10, phrase_time_limit=10)
        listen_time = time.time() - start
        
        print(f"✅ Captured audio in {listen_time:.2f}s")
        print(f"📊 Audio data length: {len(audio.get_raw_data())} bytes")
        
        print("\n🔄 Recognizing with Google Speech API...")
        start = time.time()
        text = r.recognize_google(audio)
        recog_time = time.time() - start
        
        print(f"✅ Recognition complete in {recog_time:.2f}s")
        print(f"\n✨ Result: '{text}'")
        
except sr.WaitTimeoutError:
    print("\n❌ Timeout: No speech detected within 10 seconds")
    print("   Possible causes:")
    print("   - Microphone is muted or not working")
    print("   - Energy threshold too high")
    print("   - Wrong microphone selected")
    
except sr.UnknownValueError:
    print("\n❌ Could not understand audio")
    print("   The audio was captured but couldn't be recognized")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
