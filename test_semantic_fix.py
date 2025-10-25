"""
Quick test to verify semantic matching now gives correct answers
"""
from nlp_enhanced import enhanced_handle_command
from natlangprocessing import TemporalBuffer

# Create a mock detection buffer
tb = TemporalBuffer()

# Add some fake detections (like seeing 2 people)
fake_frame = [
    {'label': 'person', 'conf': 0.92, 'box': [50, 120, 220, 460], 'img_w': 640, 'img_h': 480},
    {'label': 'person', 'conf': 0.88, 'box': [300, 100, 450, 450], 'img_w': 640, 'img_h': 480},
    {'label': 'chair', 'conf': 0.75, 'box': [100, 300, 200, 400], 'img_w': 640, 'img_h': 480},
]

tb.ingest(fake_frame)

# Test queries
print("Testing semantic matching with fake detections...")
print("=" * 60)

test_queries = [
    "how many humans",
    "how many people",
    "count the people",
    "describe what you see",
    "what do you see",
    "where is the person",
]

for query in test_queries:
    answer = enhanced_handle_command(query, tb, debug=True)
    print(f"\n[you] {query}")
    print(f"[answer] {answer}")
    print("-" * 60)

print("\n✅ Test complete! Answers should now be correct.")
