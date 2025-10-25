# Quick Test: Install sentence-transformers for semantic matching
# This runs LOCALLY - no API needed!

# Install with:
# pip install sentence-transformers

# Small, fast model: all-MiniLM-L6-v2
# - Size: 80MB
# - Speed: ~5-10ms per query
# - Quality: Good for short sentences

# Example usage:
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')

# Example question patterns
patterns = [
    "how many people",
    "count the people", 
    "number of persons",
    "how many humans",
    "where is the person",
    "location of person",
    "find the person",
    "person position",
    "describe the scene",
    "what do you see",
    "tell me what's there",
    "what's in front"
]

# Compute embeddings once (cache these!)
pattern_embeddings = model.encode(patterns)

# User asks something similar
user_query = "how many humans are there"
query_embedding = model.encode(user_query)

# Find most similar pattern
similarities = np.dot(pattern_embeddings, query_embedding)
best_match_idx = np.argmax(similarities)
best_match = patterns[best_match_idx]
similarity_score = similarities[best_match_idx]

print(f"User: '{user_query}'")
print(f"Matched to: '{best_match}' (score: {similarity_score:.3f})")

# You can then use the matched pattern to determine intent!
