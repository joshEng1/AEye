import speech_recognition as sr
print("Devices:", sr.Microphone.list_microphone_names())
with sr.Microphone() as mic:
    r = sr.Recognizer()
    print("Listening 2s…")
    audio = r.listen(mic, timeout=2, phrase_time_limit=2)
print("OK")