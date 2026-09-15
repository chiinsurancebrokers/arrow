# HAL v3 feature matrix

| Capability | Employee | Arrow Admin | CHI Admin |
|---|---:|---:|---:|
| Explain current policy cover | Yes | Yes | Yes |
| "Am I covered if...?" guidance | Yes | Yes | Yes |
| Make an individual claim decision | **No** | **No** | **No** |
| Show claim procedure | Yes | Yes | Yes |
| Route to Healix / Crawford / Constellis | Yes | Yes | Yes |
| Full 39-page wording retrieval | Yes | Yes | Yes |
| Exact PDF-page evidence in AI context | Yes | Yes | Yes |
| Arrow trip/day-pool intelligence | **No** | **Yes** | **No** |
| 250-day pool visibility | **No** | **Yes** | **No** |
| Employee/trip table | **No** | **Yes** | **No** |
| Claude provider status | No | No | Yes |
| OpenAI fallback status | No | No | Yes |
| Employee AI usage-guard summary | No | No | Yes |
| Employee AI rate limiting | **Yes** | N/A | N/A |
| Deterministic emergency/claims answers when quota reached | **Yes** | N/A | N/A |
| Unrelated-prompt blocking without AI call | **Yes** | N/A | N/A |

## AI spend protections

1. Common benefit limits are answered from JSON without an AI call.
2. Claim procedure and contacts are deterministic and never blocked by employee AI quota.
3. Non-policy prompts are rejected before a provider call.
4. Browser-session, IP and global daily ceilings are enforced server-side.
5. A short cooldown blocks rapid-fire clicking.
6. User messages, history length, history characters, full-policy excerpts and model output tokens are capped.
7. Claude failure falls back to OpenAI; it does not repeatedly retry Claude.
