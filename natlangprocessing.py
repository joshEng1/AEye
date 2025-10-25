import re
from collections import Counter, deque

# ---------------- Config (camera spec + timing) ----------------
CONFIG = {
    "IMG_W": 640,
    "IMG_H": 480,
    "FPS": 24,
    "FRAME_PERIOD": 1/24.0,       # ≈41.67 ms
    "DEFAULT_WINDOW_SEC": 0.6,    # ~12 frames
    "DEFAULT_PERSIST_FRAC": 0.6   # require presence in ≥60% frames
}

# ---------------- Domain: synonyms, colors, regions -------------
OBJECT_SYNONYMS = {
    "person": ["person","people","someone","man","men","woman","women","kid","kids","child","children","girl","boy"],
    "dog": ["dog","puppy"],
    "cat": ["cat","kitten"],
    "car": ["car","vehicle","sedan","auto"],
    "bicycle": ["bicycle","bike","cycle"],
    "chair": ["chair","seat"],
    "bottle": ["bottle"],
    "cup": ["cup","mug"],
    "backpack": ["backpack","bag","rucksack"],
}

IRREG_PLURALS = {"person": "people"}
CANONICAL = {syn: k for k, syns in OBJECT_SYNONYMS.items() for syn in syns}

COLORS  = {"red","green","blue","yellow","black","white","gray","brown","orange","purple","pink"}
REGIONS = {"left","right","center","middle","top","bottom"}

NUM_WORDS = {
    "zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10
}

# ---------------- Precompiled patterns ----------------
P_COUNT    = re.compile(r"^(?:how many|count)\b|how many\b", re.IGNORECASE)
P_PRESENCE = re.compile(r"^(?:is there|are there)\b|(?:do you see\b)", re.IGNORECASE)
P_LOCATION = re.compile(r"^where\s+(?:is|are)\b", re.IGNORECASE)
P_DESCRIBE = re.compile(r"^describe\b|what (?:do you|can you) see|what's in front of me", re.IGNORECASE)
P_ALERT    = re.compile(r"(?:alert|notify|tell me)\s+(?:when|if)\b", re.IGNORECASE)

# captures number + optional percent sign near it
P_THRESH  = re.compile(r"(?:>=|>|over|above|at least|confidence(?:\s*of)?|threshold(?:\s*of)?)\s*(\d+(?:\.\d+)?)\s*(%)?", re.IGNORECASE)
P_MINCNT  = re.compile(r"(?:at least|>=)\s*(\d+|\w+)", re.IGNORECASE)
P_REGION  = re.compile(r"\b(left|right|center|middle|top|bottom)\b", re.IGNORECASE)
P_COLOR   = re.compile(r"\b(red|green|blue|yellow|black|white|gray|brown|orange|purple|pink)\b", re.IGNORECASE)
P_DURATION= re.compile(r"(?:for|over)\s*(\d+(?:\.\d+)?)\s*(seconds?|secs?|s|frames?)", re.IGNORECASE)

# ---------------- Helpers ----------------
def _pluralize(word, n):
    if n == 1: return word
    return IRREG_PLURALS.get(word, word + "s")

def parse_threshold(text: str, default=0.5):
    m = P_THRESH.search(text)
    if not m:
        return default
    val = float(m.group(1))
    is_percent = bool(m.group(2))
    return max(0.0, min(1.0, val/100.0 if is_percent or val > 1.0 else val))

def parse_region(text: str):
    m = P_REGION.search(text)
    if not m: return None
    rg = m.group(1).lower()
    return "center" if rg == "middle" else rg

def parse_color(text: str):
    m = P_COLOR.search(text)
    return m.group(1).lower() if m else None

def parse_object(text: str):
    tokens = re.findall(r"[a-z]+", text.lower())
    for t in tokens:
        if t in CANONICAL:
            return CANONICAL[t]
    return None

def _to_int_maybe(word_or_num: str):
    w = word_or_num.lower()
    if w.isdigit(): return int(w)
    return NUM_WORDS.get(w, None)

def parse_persist_duration_sec(text: str, fps=CONFIG["FPS"]):
    """Extract a persistence duration like 'for 0.5s' or 'for 12 frames'."""
    m = P_DURATION.search(text)
    if not m: return None
    qty = float(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("frame"):
        return qty / float(fps)
    return qty  # seconds

# ---------------- Intent parsing ----------------
def parse_command(text: str):
    t = text.lower().strip()
    if   P_COUNT.search(t):    intent = "QueryCount"
    elif P_PRESENCE.search(t): intent = "QueryPresence"
    elif P_LOCATION.search(t): intent = "QueryLocation"
    elif P_ALERT.search(t):    intent = "SetAlert"
    elif P_DESCRIBE.search(t): intent = "DescribeScene"
    else:
        if "how many" in t: intent = "QueryCount"
        elif "where" in t:  intent = "QueryLocation"
        elif "when" in t or "if" in t: intent = "SetAlert"
        else: intent = "DescribeScene"

    obj = parse_object(t)
    # Only upgrade to presence on 'any <object>' if we were otherwise describing.
    if intent == "DescribeScene" and obj is not None and re.search(r"\bany\b", t):
        intent = "QueryPresence"
    reg = parse_region(t)
    col = parse_color(t)
    thr = parse_threshold(t, default=0.5)

    # Alerts/count constraints like "at least two"
    min_count = 1
    m = P_MINCNT.search(t)
    if m:
        maybe = _to_int_maybe(m.group(1))
        if maybe is not None:
            min_count = max(1, maybe)

    persist_sec = parse_persist_duration_sec(t)  # optional for alerts/presence
    return {
        "intent": intent,
        "object": obj,
        "region": reg,
        "threshold": thr,
        "color": col,
        "min_count": min_count,
        "persist_sec": persist_sec,
        "cooldown_sec": 1.0
    }

# ---------------- Spatial reasoning over YOLO boxes ----------------
def region_of(box, img_w, img_h):
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    horizontal = "left"   if cx < img_w/3     else ("center" if cx < 2*img_w/3 else "right")
    vertical   = "top"    if cy < img_h/2     else "bottom"
    return horizontal, vertical

def matches_region(det, want):
    if not want: return True
    h, v = region_of(det["box"], det.get("img_w", CONFIG["IMG_W"]), det.get("img_h", CONFIG["IMG_H"]))
    return want in (h, v)

def matches_color(det, want_color):
    if not want_color: return True
    return det.get("color") == want_color  # compute upstream if needed

def filter_dets(dets, label=None, threshold=0.5, region=None, color=None):
    out = []
    for d in dets:
        if d.get("conf", 0.0) < threshold: continue
        if label and d.get("label") != label: continue
        if region and not matches_region(d, region): continue
        if color and not matches_color(d, color): continue
        out.append(d)
    return out

# ---------------- Executors (single-frame) ----------------
def exec_query_presence(frame, slots):
    objs = filter_dets(frame, label=slots["object"], threshold=slots["threshold"],
                       region=slots["region"], color=slots["color"])
    n = len(objs)
    where = f" {slots['region']}" if slots["region"] else ""
    target = slots["object"] or "object"
    target_plural = _pluralize(target, 2)
    return f"Yes, {n} {_pluralize(target, n)}{where}." if n > 0 else f"No {target_plural}{where}."

def exec_query_count(frame, slots):
    objs = filter_dets(frame, label=slots["object"], threshold=slots["threshold"],
                       region=slots["region"], color=slots["color"])
    where = f" on the {slots['region']}" if slots["region"] else ""
    target = slots["object"] or "object"
    return f"{len(objs)} {_pluralize(target, len(objs))}{where}."

def exec_query_location(frame, slots):
    objs = filter_dets(frame, label=slots["object"], threshold=slots["threshold"])
    if not objs:
        return f"I don't see a {slots['object'] or 'target'}."
    def score(d):
        w, h = d.get("img_w", CONFIG["IMG_W"]), d.get("img_h", CONFIG["IMG_H"])
        cx = (d["box"][0]+d["box"][2])/2; cy = (d["box"][1]+d["box"][3])/2
        ex = abs(cx - w/2)/w + abs(cy - h/2)/h
        return (d["conf"], -ex)
    best = max(objs, key=score)
    h, v = region_of(best["box"], best.get("img_w", CONFIG["IMG_W"]), best.get("img_h", CONFIG["IMG_H"]))
    
    # Enhanced description with natural language
    if len(objs) == 1:
        position = f"on the {h}" if v == "top" else f"on the {h} at the {v}"
        return f"The {best['label']} is {position}."
    else:
        position = f"on the {h}" if v == "top" else f"on the {h} at the {v}"
        return f"I see {len(objs)} {_pluralize(best['label'], len(objs))}. The closest one is {position}."

def exec_describe_scene(frame, slots):
    keep = [d for d in frame if d.get("conf",0.0) >= slots["threshold"]]
    if not keep:
        return "I don't see anything with enough confidence."
    counts = Counter(d["label"] for d in keep)
    lr_counts = Counter()
    for d in keep:
        h, _ = region_of(d["box"], d.get("img_w", CONFIG["IMG_W"]), d.get("img_h", CONFIG["IMG_H"]))
        lr_counts[h] += 1
    
    # Main objects description
    parts = [f"{cnt} {_pluralize(lbl, cnt)}" for lbl, cnt in counts.most_common(3)]
    
    # Spatial distribution (only if useful)
    spatial_desc = ""
    if lr_counts['left'] > 0 or lr_counts['right'] > 0 or lr_counts['center'] > 0:
        locations = []
        if lr_counts['left'] > 0:
            locations.append(f"{lr_counts['left']} on left")
        if lr_counts['center'] > 0:
            locations.append(f"{lr_counts['center']} in center")
        if lr_counts['right'] > 0:
            locations.append(f"{lr_counts['right']} on right")
        spatial_desc = " (" + ", ".join(locations) + ")"
    
    return "I see " + ", ".join(parts) + "." + spatial_desc

def exec_set_alert(slots):
    spec = {
        "object": slots["object"],
        "region": slots["region"],
        "threshold": float(slots["threshold"]),
        "min_count": int(slots["min_count"]),
        "persist_sec": float(slots["persist_sec"] or 0.3),
        "cooldown_sec": float(slots["cooldown_sec"]),
    }
    region_phrase = "appear " if not spec["region"] else f"appear in the {spec['region']} "
    return (
        "Alert armed. I'll notify you when "
        f"{spec['min_count']}+ {spec['object'] or 'target'} "
        f"{region_phrase}"
        f"for ≥{spec['persist_sec']:.1f}s at ≥{int(spec['threshold']*100)}%."
    )

def handle_command(text, yolo_frame):
    slots = parse_command(text)
    intent = slots["intent"]
    if intent == "QueryPresence":  return exec_query_presence(yolo_frame, slots)
    if intent == "QueryCount":     return exec_query_count(yolo_frame, slots)
    if intent == "QueryLocation":  return exec_query_location(yolo_frame, slots)
    if intent == "DescribeScene":  return exec_describe_scene(yolo_frame, slots)
    if intent == "SetAlert":       return exec_set_alert(slots)
    return "I can answer about counts, presence, locations, scene summaries, and set alerts."

# ---------------- OPTIONAL: temporal smoothing for streams --------------
class TemporalBuffer:
    """Keep recent frames to avoid one-frame flicker; useful at 24 fps."""
    def __init__(self, fps=CONFIG["FPS"], max_window_sec=2.0):
        self.fps = fps
        self.frames = deque(maxlen=int(fps*max_window_sec))

    def ingest(self, yolo_frame):
        for d in yolo_frame:
            d.setdefault("img_w", CONFIG["IMG_W"])
            d.setdefault("img_h", CONFIG["IMG_H"])
        self.frames.append(list(yolo_frame))

    def _last_n(self, window_sec):
        n = min(int(self.fps * window_sec), len(self.frames))
        return list(self.frames)[-n:], n

    def count(self, label=None, region=None, threshold=0.5, window_sec=CONFIG["DEFAULT_WINDOW_SEC"]):
        frames, n = self._last_n(window_sec)
        if n == 0: return 0
        per = [len(filter_dets(f, label, threshold, region)) for f in frames]
        per.sort()
        mid = len(per)//2
        return per[mid] if len(per)%2 else (per[mid-1]+per[mid])/2

    def present(self, label=None, region=None, threshold=0.5,
                window_sec=CONFIG["DEFAULT_WINDOW_SEC"],
                persist_frac=CONFIG["DEFAULT_PERSIST_FRAC"], min_count=1):
        frames, n = self._last_n(window_sec)
        if n == 0: return False
        hits = sum(1 for f in frames if len(filter_dets(f, label, threshold, region)) >= min_count)
        return (hits / n) >= persist_frac

    def location(self, label=None, threshold=0.5, window_sec=CONFIG["DEFAULT_WINDOW_SEC"]):
        frames, n = self._last_n(window_sec)
        if n == 0: return None
        flat = []
        for f in frames:
            flat.extend([d for d in f if d.get("conf",0.0) >= threshold and (label is None or d.get("label")==label)])
        if not flat: return None
        votes = Counter()
        for d in flat:
            h,v = region_of(d["box"], d.get("img_w", CONFIG["IMG_W"]), d.get("img_h", CONFIG["IMG_H"]))
            votes[h] += 1; votes[v] += 1
        return max(votes, key=votes.get)

def handle_command_over_buffer(text, tb: TemporalBuffer):
    s = parse_command(text)
    intent, obj, reg, thr = s["intent"], s["object"], s["region"], s["threshold"]
    if intent == "QueryCount":
        c = tb.count(label=obj, region=reg, threshold=thr)
        return f"{int(round(c))} {_pluralize(obj or 'object', int(round(c)))}" + (f" on the {reg}" if reg else "") + "."
    if intent == "QueryPresence":
        win = max(CONFIG["DEFAULT_WINDOW_SEC"], (s["persist_sec"] or 0.0))
        ok = tb.present(label=obj, region=reg, threshold=thr, window_sec=win, min_count=max(1, s["min_count"]))
        base = "Yes" if ok else "No"
        return base + (f", {obj}" if obj else "") + (f" ({reg})" if reg else "") + "."
    if intent == "QueryLocation":
        loc = tb.location(label=obj, threshold=thr)
        return (f"{(obj or 'target').capitalize()} is {loc}." if loc else f"I don’t see a {obj or 'target'}.")
    if intent == "DescribeScene":
        frames, n = tb._last_n(CONFIG["DEFAULT_WINDOW_SEC"])
        flat = [d for f in frames for d in f if d.get("conf",0.0) >= thr]
        if not flat: return "I don’t see anything with enough confidence."
        counts = Counter(d["label"] for d in flat)
        parts = [f"{k}: {v}" for k, v in counts.most_common(3)]
        return "I see " + ", ".join(parts) + "."
    if intent == "SetAlert":
        return exec_set_alert(s)
    return "I can count, check presence, tell location, describe, and set alerts."

if __name__ == "__main__":
    # --- Quick test with a fake frame ---
    frame = [
        {'label':'person','conf':0.92,'box':[50,120,220,460],'img_w':640,'img_h':480},
        {'label':'person','conf':0.81,'box':[420,130,560,460],'img_w':640,'img_h':480},
        {'label':'dog','conf':0.76,'box':[360,300,460,420],'img_w':640,'img_h':480,'color':'brown'}
    ]

    tests = [
        "how many people on the left?",
        "is there a dog over 70%?",
        "where is the dog?",
        "describe the scene",
        "alert me when a car appears at least 1 for 0.5 seconds"
    ]

    for q in tests:
        print(f"> {q}")
        print(handle_command(q, frame))
