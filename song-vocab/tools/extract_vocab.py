## This tool takes a text file for a song lyrics and returns a list of vocabulary words found in the lyrics in a specific json format.

import re
from typing import List, Dict

async def extract_vocab(text: str) -> List[Dict]:
    """Extract vocabulary from text"""
    # Split into words and clean
    words = re.findall(r'\b\w+\b', text.lower())
    unique_words = list(set(words))
    
    # Basic vocab structure - you'll want to enhance this
    vocab = []
    for word in unique_words:
        if len(word) > 2:  # Skip very short words
            vocab.append({
                "word": word,
                "frequency": words.count(word),
                "context": find_context(text, word)
            })
    
    return sorted(vocab, key=lambda x: x["frequency"], reverse=True)

def find_context(text: str, word: str) -> str:
    """Find a sample context for the word"""
    pattern = f".{{0,30}}{word}.{{0,30}}"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(0) if match else ""

