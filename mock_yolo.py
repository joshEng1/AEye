# mock_yolo.py
# Generates synthetic YOLO-like detections (no external deps).

from dataclasses import dataclass
from typing import List, Callable, Optional
import math, random

IMG_W, IMG_H = 640, 480
FPS = 24

@dataclass
class Actor:
    label: str
    spawn_t: float
    despawn_t: float
    path: Callable[[float], tuple]  # returns (cx, cy, w, h) in pixels
    conf: float = 0.9
    color: Optional[str] = None

class Scenario:
    def __init__(self, actors: List[Actor], img_w=IMG_W, img_h=IMG_H, fps=FPS, jitter=0.0):
        self.actors = actors
        self.img_w, self.img_h, self.fps = img_w, img_h, fps
        self.dt = 1.0/fps
        self.t = 0.0
        self.jitter = jitter  # conf jitter

    def _box_from_center(self, cx, cy, w, h):
        x1, y1 = cx - w/2, cy - h/2
        x2, y2 = cx + w/2, cy + h/2
        # clamp
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(self.img_w-1, x2), min(self.img_h-1, y2)
        return [x1, y1, x2, y2]

    def next_frame(self):
        dets = []
        for a in self.actors:
            if self.t < a.spawn_t or self.t > a.despawn_t:
                continue
            cx, cy, w, h = a.path(self.t - a.spawn_t)
            conf = max(0.0, min(1.0, a.conf + (random.uniform(-self.jitter, self.jitter) if self.jitter else 0.0)))
            dets.append({
                "label": a.label,
                "conf": conf,
                "box": self._box_from_center(cx, cy, w, h),
                "img_w": self.img_w,
                "img_h": self.img_h,
                **({"color": a.color} if a.color else {})
            })
        self.t += self.dt
        return dets

# --- Path helpers ---
def linear_path(x0,y0,x1,y1,dur,w=80,h=160):
    def f(t):
        t = min(max(t, 0.0), dur)
        u = t/dur if dur>0 else 1.0
        return (x0*(1-u)+x1*u, y0*(1-u)+y1*u, w, h)
    return f

def static_path(cx, cy, w=80, h=160):
    return lambda t: (cx, cy, w, h)

# --- Prebuilt scenarios ---
def scenario_empty():
    return Scenario([])

def scenario_one_person_left_to_right(duration=5.0):
    a = Actor(
        label="person",
        spawn_t=0.0, despawn_t=duration,
        path=linear_path(80, 320, 560, 320, duration, w=70, h=160),
        conf=0.92
    )
    return Scenario([a])

def scenario_blinking_dog(duration=3.0):
    # Dog appears for a single frame around t=1.0s (to test persistence filter)
    a1 = Actor("person", 0.0, duration, static_path(200, 340, 70, 160), conf=0.95)
    a2 = Actor("dog", 0.98, 1.02, static_path(340, 380, 90, 70), conf=0.7)
    return Scenario([a1, a2])

def scenario_crowd_and_car(duration=6.0):
    people = [
        Actor("person", 0.0, duration, static_path(120, 330, 70, 160), conf=0.9),
        Actor("person", 0.0, duration, static_path(240, 330, 70, 160), conf=0.88),
        Actor("person", 0.0, duration, static_path(360, 330, 70, 160), conf=0.86),
        Actor("person", 0.0, duration, static_path(480, 330, 70, 160), conf=0.9),
    ]
    car = Actor("car", 2.0, duration, linear_path(600, 420, 80, 420, duration-2.0, w=160, h=90), conf=0.85, color="red")
    return Scenario(people+[car], jitter=0.03)