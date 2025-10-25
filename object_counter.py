import inflect

p = inflect.engine()

def format_object_counts(objects):
    """
    objects: list of object names (can have duplicates)
    returns: natural language string like "2 people, 1 chair"
    """
    counts = {}
    for obj in objects:
        counts[obj] = counts.get(obj, 0) + 1

    parts = []
    for obj, count in counts.items():
        name = p.plural(obj, count)
        parts.append(f"{count} {name}")

    return ", ".join(parts)
