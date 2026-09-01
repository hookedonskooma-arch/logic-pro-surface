"""logic-probe: fail-closed Logic Pro actuation envelopes.

Semantic status is confirmed | uncertain | failed only.
Without Logic, status is uncertain. Skip is never pass.
confirmed requires independent readback (MCU echo). ax_live cannot be the pass bit.
"""

__version__ = "0.0.2"

SEMANTIC_STATUSES = ("confirmed", "uncertain", "failed")
