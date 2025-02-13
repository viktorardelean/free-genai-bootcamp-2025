from dataclasses import dataclass
from typing import Optional

@dataclass
class Word:
    id: Optional[int]
    spanish: str
    english: str 