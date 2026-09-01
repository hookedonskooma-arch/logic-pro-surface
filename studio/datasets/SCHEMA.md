# studio/datasets schema

JSONL. One record per line. Runtime logs (`*.jsonl`) are gitignored; this schema is the contract.

| Field | Type | Notes |
| --- | --- | --- |
| ts | string | ISO-8601 UTC |
| role | string | printed studio role (engineer, producer, mix, …) |
| user | string | who asked; not a secret |
| said | string | original operational text; never lyrics |
| spoken | string | after the Logic lexicon |
| probe_status | string or null | `confirmed` / `uncertain` / `failed`; `null` if speak-only |
| evidence | string | why; e.g. `say -v Reed (English (US))`. Not an AX receipt as truth. |

Do not store API keys, tokens, credentials, home-directory dumps, songs, lyrics, or bounce audio.
