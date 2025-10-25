"""
Quick performance test for the command handling pipeline
"""
import time
from nlp_enhanced import enhanced_handle_command
from natlangprocessing import TemporalBuffer, handle_command_over_buffer

# Create a mock detection buffer
tb = TemporalBuffer()

# Add some fake detections
fake_frame = [
    {'label': 'person', 'conf': 0.92, 'box': [50, 120, 220, 460], 'img_w': 640, 'img_h': 480},
    {'label': 'person', 'conf': 0.88, 'box': [300, 100, 450, 450], 'img_w': 640, 'img_h': 480},
    {'label': 'chair', 'conf': 0.75, 'box': [100, 300, 200, 400], 'img_w': 640, 'img_h': 480},
]
tb.ingest(fake_frame)

print("Testing command handling performance...")
print("=" * 60)

# Test queries
queries = [
    "how many people",
    "where is the person",
    "describe what you see",
]

print("\n🔍 Testing ENHANCED (with semantic matching):")
for query in queries:
    start = time.perf_counter()
    answer = enhanced_handle_command(query, tb, debug=False)
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"  {query:30s} → {elapsed_ms:6.1f}ms")

print("\n🔍 Testing ORIGINAL (rule-based only):")
for query in queries:
    start = time.perf_counter()
    answer = handle_command_over_buffer(query, tb)
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"  {query:30s} → {elapsed_ms:6.1f}ms")

print("\n" + "=" * 60)
print("⏱️  Target: < 20ms for accessibility")
