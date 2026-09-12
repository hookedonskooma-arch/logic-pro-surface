"""voz: the one mouth.

Every spoken line in this repo goes through `voz.mouth`. Not because a
document says so - because there is exactly one implementation and everything
else imports it.

"One mouth" used to be a convention, and conventions regrow: a second `say`
call appeared in chatbot/voice.py three days after Decision 004 cut six voices
to one. A rule the architecture enforces cannot regrow that way.
"""

from __future__ import annotations

__all__ = ["mouth"]
