"""logic-probe: fail-closed Logic Pro actuation envelopes.

Semantic status is confirmed | uncertain | failed only.
Without Logic, status is uncertain. Skip is never pass.
This package will not emit confirmed until independent readback exists.
"""

__version__ = "0.0.1"

SEMANTIC_STATUSES = ("confirmed", "uncertain", "failed")
