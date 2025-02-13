from dataclasses import dataclass
from typing import Optional, List
from .word import Word

@dataclass
class Group:
    id: Optional[int]
    name: str
    words: Optional[List[Word]] = None 