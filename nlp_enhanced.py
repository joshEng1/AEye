"""
Enhanced NLP with Semantic Matching
Understands similar questions using AI embeddings (runs locally, ~10ms)
"""
import numpy as np
from sentence_transformers import SentenceTransformer
from natlangprocessing import (
    parse_command, 
    handle_command_over_buffer,
    exec_set_alert,
    CONFIG,
    _pluralize
)
from collections import Counter

# Load small, fast model (only ~80MB, loads in 1-2 seconds)
print("[nlp] Loading semantic model...")
semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
print("[nlp] Model loaded!")

# Define question patterns for each intent
QUESTION_PATTERNS = {
    "QueryCount": [
        "how many people",
        "how many people are there",
        "count the people",
        "number of people",
        "how many humans",
        "how many persons",
        "tell me how many",
        "count people",
        "how many do you see",
        "people count",
        "how many chairs",
        "count chairs",
        "how many objects"
    ],
    "QueryPresence": [
        "is there a person",
        "is there anyone",
        "do you see a person",
        "can you see anyone",
        "is anyone there",
        "are there people",
        "person present",
        "anyone here",
        "is there a chair",
        "do you see a chair"
    ],
    "QueryLocation": [
        "where is the person",
        "where is the chair", 
        "location of person",
        "find the person",
        "person location",
        "where's the person",
        "show me where",
        "position of person",
        "where can I find",
        "which side is the person"
    ],
    "DescribeScene": [
        "describe the scene",
        "what do you see",
        "tell me what's there",
        "what's in front of me",
        "describe what you see",
        "what's around me",
        "scene description",
        "tell me about the scene",
        "what objects are there",
        "give me details"
    ]
}

# Pre-compute embeddings for all patterns (do once at startup)
print("[nlp] Computing pattern embeddings...")
all_patterns = []
pattern_intents = []
for intent, patterns in QUESTION_PATTERNS.items():
    for pattern in patterns:
        all_patterns.append(pattern)
        pattern_intents.append(intent)

pattern_embeddings = semantic_model.encode(all_patterns, show_progress_bar=False)
print(f"[nlp] Ready! {len(all_patterns)} patterns loaded.")

def find_similar_intent(user_query, threshold=0.6):
    """
    Find the most similar pattern and return its intent.
    
    Args:
        user_query: User's question
        threshold: Minimum similarity score (0-1)
    
    Returns:
        (intent, similarity_score) or (None, 0) if no match
    """
    query_embedding = semantic_model.encode(user_query, show_progress_bar=False)
    
    # Calculate cosine similarity with all patterns
    similarities = np.dot(pattern_embeddings, query_embedding)
    
    best_idx = np.argmax(similarities)
    best_score = similarities[best_idx]
    
    if best_score >= threshold:
        matched_pattern = all_patterns[best_idx]
        intent = pattern_intents[best_idx]
        return intent, best_score, matched_pattern
    
    return None, best_score, None

def enhanced_handle_command(text, tb, debug=False):
    """
    Enhanced command handler that uses semantic matching as fallback.
    
    First tries exact pattern matching, then falls back to semantic similarity.
    """
    # Try original parser first (fast, rule-based)
    result = parse_command(text)
    original_intent = result["intent"]
    
    # Use semantic matching when rule-based parser is uncertain or wrong
    # Conditions where we should use semantic fallback:
    # 1. Intent defaulted to DescribeScene (catch-all)
    # 2. QueryCount but found unexpected objects (like "humans" -> None)
    # 3. QueryPresence with weird results
    
    use_semantic = False
    
    if original_intent == "DescribeScene":
        # Only keep DescribeScene if explicitly asked
        if not any([
            "describe" in text.lower(),
            "what do you see" in text.lower(),
            "what's in front" in text.lower(),
            "scene" in text.lower()
        ]):
            use_semantic = True
    
    elif original_intent == "QueryPresence":
        # If asking "what do you see", it's probably DescribeScene not QueryPresence
        if any([
            "what do you see" in text.lower(),
            "what are you seeing" in text.lower(),
            "tell me what" in text.lower(),
            "what's there" in text.lower()
        ]):
            use_semantic = True
    
    elif original_intent == "QueryCount" and result["object"] is None:
        # Counting but didn't recognize the object (e.g., "humans")
        use_semantic = True
    
    if use_semantic:
        # Use semantic matching
        semantic_intent, score, matched = find_similar_intent(text, threshold=0.6)
        
        if semantic_intent:
            if debug:
                print(f"[semantic] '{text}' -> {semantic_intent} (score: {score:.2f}, matched: '{matched}')")
            
            # Update intent based on semantic match
            result["intent"] = semantic_intent
            
            # Re-parse with better understanding
            if semantic_intent == "QueryCount":
                # Check if asking about people/humans
                if any(word in text.lower() for word in ["people", "person", "human", "humans", "man", "woman", "men", "women"]):
                    result["object"] = "person"
    
    # Execute based on corrected intent (don't re-parse!)
    intent = result["intent"]
    obj = result["object"]
    reg = result["region"]
    thr = result["threshold"]
    
    if intent == "QueryCount":
        c = tb.count(label=obj, region=reg, threshold=thr)
        return f"{int(round(c))} {_pluralize(obj or 'object', int(round(c)))}" + (f" on the {reg}" if reg else "") + "."
    
    if intent == "QueryPresence":
        win = max(CONFIG["DEFAULT_WINDOW_SEC"], (result["persist_sec"] or 0.0))
        ok = tb.present(label=obj, region=reg, threshold=thr, window_sec=win, min_count=max(1, result["min_count"]))
        base = "Yes" if ok else "No"
        return base + (f", {obj}" if obj else "") + (f" ({reg})" if reg else "") + "."
    
    if intent == "QueryLocation":
        loc = tb.location(label=obj, threshold=thr)
        return (f"{(obj or 'target').capitalize()} is {loc}." if loc else f"I don't see a {obj or 'target'}.")
    
    if intent == "DescribeScene":
        # Get recent frames and describe
        frames, n = tb._last_n(CONFIG["DEFAULT_WINDOW_SEC"])
        flat = [d for f in frames for d in f if d.get("conf",0.0) >= thr]
        if not flat: 
            return "I don't see anything with enough confidence."
        counts = Counter(d["label"] for d in flat)
        parts = [f"{cnt} {_pluralize(lbl, cnt)}" for lbl, cnt in counts.most_common(3)]
        return "I see " + ", ".join(parts) + "."
    
    if intent == "SetAlert":
        return exec_set_alert(result)
    
    return "I can count, check presence, tell location, describe, and set alerts."


def test_semantic_matching():
    """Test the semantic matching with various phrasings"""
    test_queries = [
        "how many humans are in the room",
        "tell me the number of people",
        "can you count the people",
        "is anyone there",
        "do you see any person",
        "find where the person is",
        "person's location please",
        "tell me what you're seeing",
        "give me a description",
    ]
    
    print("\n" + "="*60)
    print("SEMANTIC MATCHING TEST")
    print("="*60)
    
    for query in test_queries:
        intent, score, matched = find_similar_intent(query)
        print(f"\nQuery: '{query}'")
        print(f"  Intent: {intent}")
        print(f"  Score: {score:.3f}")
        print(f"  Matched: '{matched}'")

if __name__ == "__main__":
    test_semantic_matching()
