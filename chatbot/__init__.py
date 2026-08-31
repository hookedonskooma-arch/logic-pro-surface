"""A musically coherent chat bot: text and local offline voice.

Key, mode, tempo and meter live in `state.MusicalState` and every answer is
derived from it. Unset state is UNKNOWN and produces a question, never a guess.
"""

from .bot import MusicalChatBot, Turn
from .state import MusicalState, Verdict

__all__ = ["MusicalChatBot", "Turn", "MusicalState", "Verdict"]
