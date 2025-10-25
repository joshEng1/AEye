# assist_loop_hardened.py
import time, threading, queue, argparse, io, wave, sys, os
from typing import Optional

# ---- Optional hotkeys ----
try:
    from pynput import keyboard
    HAVE_PYNPUT = True
except Exception:
    keyboard = None
    HAVE_PYNPUT = False

# ---- TTS (run in a worker to avoid deadlocks) ----
import pyttsx3

# ---- SpeechRecognition + optional sounddevice (no PyAudio) ----
try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    import sounddevice as sd
except Exception:
    sd = None

from natlangprocessing import CONFIG, TemporalBuffer, handle_command_over_buffer

# Try to load enhanced NLP with semantic matching (optional)
try:
    from nlp_enhanced import enhanced_handle_command
    print("[nlp] Enhanced semantic matching enabled!")
    USE_SEMANTIC = True
except Exception as e:
    print(f"[nlp] Semantic matching not available ({e}), using basic NLP")
    USE_SEMANTIC = False

import mock_yolo as my

# ---- Fault handling / logs ----
import faulthandler, signal, logging
faulthandler.enable()
logging.basicConfig(level=logging.INFO, format='[%(asctime)s %(levelname)s] %(message)s', datefmt='%H:%M:%S')

# ==== object summaries from buffer (no extra engines) ====
from collections import Counter
import math

def last_detections(tb, thr=0.5):
    frames, n = tb._last_n(CONFIG["DEFAULT_WINDOW_SEC"])
    return [d for f in frames for d in f if d.get("conf", 0.0) >= thr]

def objects_now(tb, thr=0.5):
    dets = last_detections(tb, thr)
    return sorted(set(d["label"] for d in dets))

def closest_object_by_area(tb, thr=0.5):
    """Use largest bounding-box area as a proxy for closeness."""
    dets = last_detections(tb, thr)
    if not dets:
        return None, None, None
    def area(d):
        x1,y1,x2,y2 = d["box"]
        return max(1.0, (x2-x1)*(y2-y1))
    best = max(dets, key=area)
    norm = area(best) / (best["img_w"] * best["img_h"])
    return best["label"], norm, best

def speak_objects_tts(tts, tb, thr=0.5):
    objs = objects_now(tb, thr)
    if not objs:
        tts.say("I don't see anything with enough confidence.")
        return
    tts.say("Detected objects: " + ", ".join(objs))

def speak_closest_tts(tts, tb, thr=0.5):
    label, norm, _ = closest_object_by_area(tb, thr)
    if not label:
        tts.say("I don't see anything close.")
        return
    if   norm >= 0.06: bucket = "very close"
    elif norm >= 0.02: bucket = "nearby"
    else:              bucket = "far"
    tts.say(f"The closest object is {label}, {bucket}.")

def install_thread_excepthook(stop_evt):
    def _hook(args):
        logging.error("Thread %s crashed", args.thread.name,
                      exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
        stop_evt.set()
    threading.excepthook = _hook

def debug_status(tb: TemporalBuffer):
    frames, n = tb._last_n(CONFIG["DEFAULT_WINDOW_SEC"])
    last = frames[-1] if n > 0 else []
    print(f"[debug] frames_in_buffer={len(tb.frames)} window_n={n} last_dets={len(last)} "
          f"labels={Counter(d['label'] for d in last)}")

# ---------------- TTS worker ----------------
class TTSWorker:
    def __init__(self, rate: Optional[int] = None):
        self.q = queue.Queue()
        self.engine = pyttsx3.init()
        if rate:
            self.engine.setProperty("rate", rate)
        self._stop = threading.Event()
        self.t = threading.Thread(target=self._loop, daemon=True, name="tts")
        self.t.start()

    def _loop(self):
        while not self._stop.is_set():
            try:
                msg = self.q.get(timeout=0.1)
            except queue.Empty:
                continue
            if msg is None:
                break
            try:
                self.engine.say(msg)
                self.engine.runAndWait()
            except Exception as e:
                print(f"[TTS Worker Error] {e}")
                import traceback
                traceback.print_exc()

    def say(self, text: str):
        if not self._stop.is_set():
            self.q.put(text)
            print(f"[TTS] Queued: '{text[:50]}...' (queue size: {self.q.qsize()})")
    
    def clear_queue(self):
        """Clear all pending TTS messages"""
        cleared = 0
        while not self.q.empty():
            try:
                self.q.get_nowait()
                cleared += 1
            except queue.Empty:
                break
        if cleared > 0:
            print(f"[TTS] Cleared {cleared} pending message(s)")

    def close(self):
        self._stop.set()
        try:
            self.engine.stop()
        except Exception:
            pass
        try:
            self.engine.endLoop()
        except Exception:
            pass
        try:
            self.q.put_nowait(None)
        except Exception:
            pass
        self.t.join(timeout=0.5)
        try:
            del self.engine
        except Exception:
            pass

# ---------------- Helpers ----------------
def list_input_devices_str():
    if sd is None:
        return "(sounddevice not installed)"
    try:
        devs = sd.query_devices()
        apis = sd.query_hostapis()
        lines = []
        for i, d in enumerate(devs):
            if d.get("max_input_channels", 0) > 0:
                api = apis[d["hostapi"]]["name"]
                lines.append(f"{i:2d}: {d['name']} [{api}] ch:{d['max_input_channels']}")
        return "\n".join(lines) if lines else "(no input devices)"
    except Exception as e:
        return f"(could not query devices: {e})"

def record_via_sounddevice(seconds=5, fs=16000, device=None):
    if sd is None:
        raise RuntimeError("sounddevice not available")
    if device is not None:
        sd.default.device = (device, None)
    print(f"🎤 Recording for {seconds} seconds... Speak now!")
    audio = sd.rec(int(seconds*fs), samplerate=fs, channels=1, dtype='int16', device=device)
    sd.wait()
    print("✓ Recording complete, processing...")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(fs)
        wf.writeframes(audio.tobytes())
    buf.seek(0)
    return buf.read()

def recognize_with_timeout(recognizer, audio, timeout_s=5.0):
    result = {}
    done = threading.Event()
    def _work():
        try:
            result["text"] = recognizer.recognize_google(audio)
        except Exception as e:
            result["error"] = e
        finally:
            done.set()
    t = threading.Thread(target=_work, daemon=True)
    t.start()
    ok = done.wait(timeout_s)
    if not ok:
        raise TimeoutError("speech recognition timed out")
    if "text" in result:
        return result["text"]
    raise result.get("error", RuntimeError("speech recognition failed"))

# ---------------- Hotkey plumbing ----------------
def start_trigger_listener(trigger_mode: str, signal_q: "queue.Queue[bool]"):
    """
    Returns a stopper callable that you should call on exit.
    trigger_mode: 'ctrlq' | 'f9' | 'enter'
    """
    if trigger_mode in ("ctrlq", "f9") and HAVE_PYNPUT:
        combo = '<ctrl>+q' if trigger_mode == 'ctrlq' else '<f9>'
        def on_activate():
            try: signal_q.put_nowait(True)
            except queue.Full: pass
        hk = keyboard.GlobalHotKeys({combo: on_activate})
        hk.start()
        return hk.stop
    else:
        # Enter handled in main thread (no background input() on Windows).
        return lambda: None

# ---------------- Feeders ----------------
def feed_scenario(tb: TemporalBuffer, scen_fn, stop_evt: threading.Event, debug: bool = False):
    scen = scen_fn()
    period = 1.0 / CONFIG["FPS"]
    k = 0
    while not stop_evt.is_set():
        try:
            dets = scen.next_frame()
            tb.ingest(dets)
            if debug and (k % 12 == 0):  # ~every 0.5s
                print(f"[feeder] t={scen.t:.2f}s  dets={len(dets)}  "
                      f"labels={Counter(d['label'] for d in dets)}  frames={len(tb.frames)}")
            k += 1
            time.sleep(period * 0.9)
        except Exception as e:
            print(f"[feeder error] {e!r}")
            stop_evt.set()
            break

def feed_mock(tb: TemporalBuffer, scen_fn, stop_evt: threading.Event, debug: bool = False, auto_restart=True):
    scen = scen_fn()
    period = 1.0 / CONFIG["FPS"]
    k = 0
    idle = 0
    while not stop_evt.is_set():
        dets = scen.next_frame()
        tb.ingest(dets)
        if debug and (k % 12 == 0):
            print(f"[feeder/mock] t={scen.t:.2f}s dets={len(dets)} "
                  f"labels={Counter(d['label'] for d in dets)} frames={len(tb.frames)}")
        k += 1
        if auto_restart:
            idle = 0 if dets else idle + 1
            if idle >= int(CONFIG["FPS"] * 0.5):
                if debug: print("[feeder/mock] scenario idle → restarting")
                scen = scen_fn(); idle = 0
        time.sleep(period * 0.9)

def feed_yolo_from_stream(tb, stream_iter, stop_evt, fps=CONFIG["FPS"], debug=False, tts=None):
    """If you wire yolo_integration.yolo_stream(), consume it here."""
    period = 1.0 / fps
    last_spoken = {}
    cooldown = 3.0
    while not stop_evt.is_set():
        try:
            dets, w, h, hazards = next(stream_iter)
        except StopIteration:
            break
        except Exception as e:
            print(f"[feeder/yolo error] {e!r}")
            break
        tb.ingest(dets)
        if debug:
            print(f"[feeder/yolo] dets={len(dets)} labels={Counter(d['label'] for d in dets)} frames={len(tb.frames)}")
        if tts and hazards:
            now = time.time()
            for hz in hazards:
                if now - last_spoken.get(hz, 0) > cooldown:
                    tts.say(f"Hazard detected: {hz}")
                    last_spoken[hz] = now
        time.sleep(period * 0.2)

# ---------------- Capture command (mic or typing) ----------------
def capture_command(mode: str, tts: TTSWorker, in_dev=None, mic_index=None, fast_mode=False, energy_threshold=None, debug=False) -> str:
    # sounddevice -> SpeechRecognition
    if mode == "sd" and sr is not None and sd is not None:
        try:
            if not fast_mode:
                tts.say("Listening.")
            wav_bytes = record_via_sounddevice(seconds=5, device=in_dev)
            with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
                r = sr.Recognizer()
                audio = r.record(source)
            text = recognize_with_timeout(r, audio, timeout_s=7.0)
            if debug: print(f"[heard/sd] {text}")
            print(f"[you] {text}")
            return text
        except TimeoutError:
            tts.say("Sorry, that took too long. Please type it.")
        except sr.UnknownValueError:
            tts.say("Sorry, I didn’t catch that. Please type it.")
        except sr.RequestError:
            tts.say("Speech service unavailable. Type your command.")
        except Exception as e:
            if debug: print("[sd error]", e)

    # PyAudio Microphone path
    if mode == "mic" and sr is not None:
        try:
            r = sr.Recognizer()
            r.dynamic_energy_threshold = (energy_threshold is None)  # Only auto if not manual
            
            with sr.Microphone(device_index=mic_index) as source:
                if not fast_mode:
                    print("🎤 Listening...")
                else:
                    print("🎤")  # Minimal feedback even in fast mode
                    
                if debug:
                    print(f"[mic] Adjusting for ambient noise...")
                    
                # Calibrate if using auto threshold
                if energy_threshold is None:
                    r.adjust_for_ambient_noise(source, duration=0.5)
                else:
                    r.energy_threshold = energy_threshold
                
                if debug:
                    print(f"[mic] Energy threshold: {r.energy_threshold}")
                    print(f"[mic] Waiting for speech...")
                    
                audio = r.listen(source, timeout=10, phrase_time_limit=10)
                
            print("🔄 Processing...")
            text = recognize_with_timeout(r, audio, timeout_s=7.0)
            if debug: print(f"[heard/mic] {text}")
            print(f"[you] {text}")
            return text
        except sr.WaitTimeoutError:
            print("⏱️ Timeout - no speech detected")
            tts.say("I didn't hear anything. Press Enter to try again.")
            return ""
        except TimeoutError:
            print("⏱️ Recognition timeout")
            tts.say("That took too long. Press Enter to try again.")
            return ""
        except sr.UnknownValueError:
            print("❓ Could not understand audio")
            tts.say("I didn't catch that. Press Enter to try again.")
            return ""
        except sr.RequestError as e:
            print(f"🌐 Speech service error: {e}")
            tts.say("Speech service unavailable. Press Enter to try again.")
            return ""
        except Exception as e:
            if debug: print(f"[mic error] {e}")
            tts.say("Microphone error. Press Enter to try again.")
            return ""

    # typing fallback (only if in typing mode)
    if mode == "typing":
        try:
            val = input("> ").strip()
            print(f"[you] {val}")
            return val
        except EOFError:
            return ""
    
    # If mic/sd failed, return empty instead of blocking
    return ""


# ---------------- Main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["mock","yolo"], default="mock",
                    help="mock=test generator; yolo=real detector stream")
    ap.add_argument("--scenario", choices=["person_lr","blink_dog","crowd_car","empty"], default="crowd_car")
    ap.add_argument("--stt", choices=["mic","sd","typing"], default=None,
                    help="mic=PyAudio Microphone; sd=sounddevice; typing=manual")
    ap.add_argument("--trigger", choices=["ctrlq","f9","enter"], default="enter",
                    help="how to trigger listening")
    ap.add_argument("--in-dev", type=int, default=None, help="sounddevice input device index")
    ap.add_argument("--mic-index", type=int, default=None, help="SpeechRecognition Microphone device_index")
    ap.add_argument("--model", type=str, default="yolov8n.pt", 
                    help="YOLO model: yolov8n.pt (fast), yolov8s.pt (balanced), yolov8m.pt (accurate)")
    ap.add_argument("--confidence", type=float, default=0.5,
                    help="detection confidence threshold (0.0-1.0), lower=more detections")
    ap.add_argument("--energy", type=int, default=300,
                    help="microphone energy threshold (lower=more sensitive), default=500")
    ap.add_argument("--fast", action="store_true",
                    help="skip 'Listening' audio cue for faster response")
    ap.add_argument("--list-devices", action="store_true", help="list input devices and exit")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    stop_hotkey = lambda: None  # always defined

    if args.list_devices:
        print("Input devices:\n" + list_input_devices_str())
        sys.exit(0)

    # Resolve STT mode with graceful fallbacks
    mode = args.stt or "sd"
    if mode == "mic":
        try:
            import pyaudio  # noqa
        except Exception:
            print("[info] PyAudio not available; switching to sounddevice path.")
            mode = "sd" if sd is not None else "typing"
    if mode == "sd" and sd is None:
        print("[info] sounddevice not available; switching to typing.")
        mode = "typing"

    tts = TTSWorker(rate=185)
    tb = TemporalBuffer(fps=CONFIG["FPS"], max_window_sec=2.0)

    # --- shutdown/event plumbing ---
    stop_evt = threading.Event()
    install_thread_excepthook(stop_evt)
    def _sig(_sig, _frm):
        logging.info("Signal %s received, shutting down…", _sig)
        stop_evt.set()
    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)

    # Scenario factory (for mock)
    scen_name_map = {
        "person_lr": "scenario_one_person_left_to_right",
        "blink_dog": "scenario_blinking_dog",
        "crowd_car": "scenario_crowd_and_car",
        "empty":     "scenario_empty",
    }
    base = getattr(my, scen_name_map[args.scenario])
    def scen_fn():
        try:
            return base(duration=60.0)
        except TypeError:
            return base()

    # Start feeder
    if args.source == "mock":
        feeder = threading.Thread(
            target=feed_mock,
            args=(tb, scen_fn, stop_evt, args.debug, True),
            daemon=True, name="feeder"
        )
        feeder.start()
    else:
        # Try to import real YOLO adapter; if missing, fall back to mock
        try:
            from yolo_integration import yolo_stream
            print(f"[info] Using model: {args.model}, confidence threshold: {args.confidence}")
            stream = yolo_stream(cap_index=0, size=(CONFIG["IMG_W"], CONFIG["IMG_H"]),
                                 model_path=args.model, conf_threshold=args.confidence, 
                                 stop_evt=stop_evt, show_window=True)
            feeder = threading.Thread(
                target=feed_yolo_from_stream,
                args=(tb, iter(stream), stop_evt, CONFIG["FPS"], args.debug, tts),
                daemon=True, name="feeder"
            )
            feeder.start()
        except Exception as e:
            print(f"[warn] yolo_integration not available ({e!r}); using mock.")
            feeder = threading.Thread(
                target=feed_mock,
                args=(tb, scen_fn, stop_evt, args.debug, True),
                daemon=True, name="feeder"
            )
            feeder.start()

    time.sleep(0.5)  # small warm-up so first answer has frames

    prompt = {
        "ctrlq": "Press Control plus Q to ask.",
        "f9":    "Press F9 to ask.",
        "enter": "Press Enter to ask.",
    }[args.trigger]
    print(f"Assistant ready. {prompt}")
    tts.say(f"Assistant ready. {prompt}")

    SPEAK_OBJECTS_ALIASES = {"speak objects", "say objects", "objects", "a"}
    SPEAK_CLOSEST_ALIASES = {"speak closest", "closest", "d"}

    try:
        if args.trigger == "enter":
            # Main-thread, safe console I/O. No background input().
            while not stop_evt.is_set():
                try:
                    line = input()  # user presses Enter (or types a full question)
                except (EOFError, KeyboardInterrupt):
                    break

                # If typing mode and user already typed a question on this line, use it.
                if (mode == "typing") and line.strip():
                    cmd = line.strip()
                    print(f"[you] {cmd}")  # <-- echo typed line captured directly
                else:
                    if args.debug: print("[triggered]")
                    cmd = capture_command(mode, tts, in_dev=args.in_dev, mic_index=args.mic_index, 
                                        fast_mode=args.fast, energy_threshold=args.energy, debug=args.debug)

                if not cmd:
                    continue

                low = cmd.strip().lower()
                # Developer & quick voice utilities
                if low.startswith("debug:status"):
                    debug_status(tb); continue
                if low in SPEAK_OBJECTS_ALIASES:
                    speak_objects_tts(tts, tb); continue
                if low in SPEAK_CLOSEST_ALIASES:
                    speak_closest_tts(tts, tb); continue

                # Use enhanced semantic matching if available
                if USE_SEMANTIC:
                    reply = enhanced_handle_command(cmd, tb, debug=args.debug)
                else:
                    reply = handle_command_over_buffer(cmd, tb)
                    
                print(f"[answer] {reply}")
                
                # Ensure TTS says the reply
                try:
                    tts.say(reply)
                    if args.debug:
                        print("[tts] Speaking...")
                except Exception as e:
                    print(f"[tts error] {e}")
                    
                time.sleep(0.2)  # debounce

        else:
            # Hotkey modes (Ctrl+Q or F9) via pynput
            signal_q: "queue.Queue[bool]" = queue.Queue()
            stop_hotkey = start_trigger_listener(args.trigger, signal_q)
            try:
                while not stop_evt.is_set():
                    try:
                        _ = signal_q.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    if args.debug: print("[triggered]")
                    cmd = capture_command(mode, tts, in_dev=args.in_dev, mic_index=args.mic_index, 
                                        fast_mode=args.fast, energy_threshold=args.energy, debug=args.debug)
                    if not cmd:
                        continue

                    low = cmd.strip().lower()
                    if low.startswith("debug:status"):
                        debug_status(tb); continue
                    if low in SPEAK_OBJECTS_ALIASES:
                        speak_objects_tts(tts, tb); continue
                    if low in SPEAK_CLOSEST_ALIASES:
                        speak_closest_tts(tts, tb); continue

                    # Use enhanced semantic matching if available
                    if USE_SEMANTIC:
                        reply = enhanced_handle_command(cmd, tb, debug=args.debug)
                    else:
                        reply = handle_command_over_buffer(cmd, tb)
                        
                    print(f"[answer] {reply}")
                    
                    # Ensure TTS says the reply
                    try:
                        tts.say(reply)
                        if args.debug:
                            print("[tts] Speaking...")
                    except Exception as e:
                        print(f"[tts error] {e}")
                        
                    time.sleep(0.2)
            finally:
                try: stop_hotkey()
                except Exception: pass

    except KeyboardInterrupt:
        pass
    finally:
        stop_evt.set()
        try: stop_hotkey()
        except Exception: pass
        try: feeder.join(timeout=1.0)
        except Exception: pass
        tts.close()

        # Last-resort hard exit to avoid lingering COM/hook threads on Windows
        if os.name == "nt":
            threading.Timer(0.5, lambda: os._exit(0)).start()

if __name__ == "__main__":
    main()
