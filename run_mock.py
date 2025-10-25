# run_mock.py
# Drive a synthetic scenario at 24fps and let you query via text.

import time, argparse
from natlangprocessing import parse_command, TemporalBuffer, CONFIG
import mock_yolo as my

SCENARIOS = {
    "empty": my.scenario_empty,
    "person_lr": my.scenario_one_person_left_to_right,
    "blink_dog": my.scenario_blinking_dog,
    "crowd_car": my.scenario_crowd_and_car,
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", choices=SCENARIOS.keys(), default="person_lr")
    ap.add_argument("--duration", type=float, default=5.0, help="seconds to simulate per refill")
    ap.add_argument("--window-sec", type=float, default=0.6, help="temporal window used for answering")
    args = ap.parse_args()

    CONFIG["IMG_W"] = 640
    CONFIG["IMG_H"] = 480
    CONFIG["FPS"]   = 24
    CONFIG["FRAME_PERIOD"] = 1/24.0

    print(f"Starting scenario '{args.scenario}' at 640x480 @24fps.")
    print("Type questions like: 'how many people on the left?', 'is there a dog?', 'where is the car?', 'describe the scene'.")
    tb = TemporalBuffer(fps=CONFIG["FPS"], max_window_sec=2.0)

    while True:
        scen = SCENARIOS[args.scenario](duration=args.duration)
        # Fill ~duration seconds of frames; this simulates "recent history"
        frames_to_make = int(args.duration * CONFIG["FPS"])
        for _ in range(frames_to_make):
            frame = scen.next_frame()
            tb.ingest(frame)
            # We simulate real time loosely
            time.sleep(min(0.01, CONFIG["FRAME_PERIOD"]))

        try:
            text = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break
        if not text: 
            continue
        print(short_answer(tb, text))

if __name__ == "__main__":
    main()