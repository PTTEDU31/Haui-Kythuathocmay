"""Stable, separately named transforms for saved classifiers and FAQ retrieval."""
import re
import unicodedata

NORMALIZATION_VERSION = 'nfc-lower-space-v1'


def normalize_classification(text):
    """Keep Vietnamese accents, punctuation and negation; no stopword removal."""
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text).lower()).strip()
