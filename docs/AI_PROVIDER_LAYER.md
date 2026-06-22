# ApplyPilot — Provider-Agnostic AI Layer

The contract every AI-using piece of ApplyPilot depends on. Agents and routers call this
layer; they never touch a provider SDK. Switching from Sarvam to Anthropic, OpenAI, or a
local Ollama model is **one line in `.env`** and **zero code changes** anywhere else.

> **Status:** This layer is the **first deliverable of Phase 2**. The `services/ai/`
> package does not exist yet. This document is the binding contract — build to it. See
> `docs/phases/PHASE_2.md` for the file-by-file build order.

---

## 1. Architecture

```
  .env  (AI_PROVIDER=sarvam)
        │
        ▼
  services/ai/factory.py        ← the ONLY module that imports concrete providers
        │   get_ai_provider() reads settings.ai_provider, returns a cached instance
        ▼
  services/ai/providers/sarvam.py     (SarvamProvider)
  services/ai/providers/anthropic.py  (AnthropicProvider)   ← each implements AIProvider
  services/ai/providers/openai.py     (OpenAIProvider)
  services/ai/providers/ollama.py     (OllamaProvider)
        │   async generate(GenerationRequest) -> AIResponse
        ▼
  services/ai/base.py           ← AIProvider ABC, AIMessage, GenerationRequest, AIResponse
        │
        ▼
  agents/email_generator.py     ← imports ONLY from services.ai; zero SDK knowledge
```

Proposed package layout (Phase 2):
```
backend/services/ai/
├── __init__.py        # re-exports: get_ai_provider, GenerationRequest, AIResponse, AIMessage
├── base.py            # AIProvider (ABC) + dataclasses/Pydantic models for the contract
├── factory.py         # get_ai_provider() — the only provider-aware code
├── errors.py          # AIError, AIProviderUnavailable (→ 503 feature_unavailable), AIBadResponse
└── providers/
    ├── __init__.py
    ├── sarvam.py
    ├── anthropic.py
    ├── openai.py
    └── ollama.py
```

---

## 2. The contract

### `AIMessage`
| Field | Type | Description |
|-------|------|-------------|
| `role` | `"system" \| "user" \| "assistant"` | Message role |
| `content` | `str` | Message text |

### `GenerationRequest`
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `messages` | `list[AIMessage]` | — | Conversation; first is usually a `system` message |
| `model` | `str \| None` | provider default | Override the configured model for this call |
| `temperature` | `float` | `0.7` | Sampling temperature |
| `max_tokens` | `int` | `1024` | Output cap |
| `json_mode` | `bool` | `False` | Request strict JSON output (see §5 for per-provider mechanism) |
| `stop` | `list[str] \| None` | `None` | Optional stop sequences |
| `metadata` | `dict \| None` | `None` | Free-form (e.g. `user_id`, `task_type`) for logging/usage |

### `AIResponse`
| Field | Type | Description |
|-------|------|-------------|
| `text` | `str` | The generated content (a JSON string when `json_mode=True`) |
| `model` | `str` | Model that actually served the request |
| `provider` | `str` | Provider name that served it |
| `usage` | `{prompt_tokens, completion_tokens, total_tokens}` | Token accounting (best effort) |
| `raw` | `Any` | The provider's raw response object, for debugging |

### `AIProvider` (abstract base)
```python
class AIProvider(ABC):
    name: str
    @abstractmethod
    async def generate(self, req: GenerationRequest) -> AIResponse: ...
```

### `get_ai_provider() -> AIProvider`
Returns the provider named by `settings.ai_provider`, constructed once and cached. Raises
`AIProviderUnavailable` (→ HTTP 503 `feature_unavailable`) when the selected provider's
API key is missing.

---

## 3. The rule: agents must never import an AI SDK

**Why:**
- **Swappability** — provider choice is config, not code. Dev on free local Ollama, ship on Sarvam, switch to Anthropic for vision — no agent edits.
- **Testability** — agents are unit-tested with a fake `AIProvider`. No network, no keys, deterministic.
- **One retry/backoff/usage path** — rate limiting, retries, token accounting, and PII-safe logging live in the provider base, not scattered across agents.
- **No leakage** — a stray `from sarvamai import ...` in an agent couples business logic to a vendor and breaks all of the above.

**Enforced by** the close-out verification grep (and keep it in CI):
```bash
grep -rn "from sarvamai\|import sarvamai\|SarvamAI\|from anthropic\|import anthropic\|AsyncAnthropic\|from openai\|import openai" \
  backend/agents/ backend/routers/ backend/tasks/   # must return zero
```

---

## 4. Add a new provider in 4 steps

1. **Create** `backend/services/ai/providers/<name>.py` with a class implementing
   `AIProvider.generate(req) -> AIResponse`. Map `GenerationRequest` → the SDK's call,
   and the SDK's result → `AIResponse`. Translate SDK errors into `AIError`/`AIBadResponse`.
2. **Register** it in `factory.py` (`_PROVIDERS = {"<name>": <Name>Provider, ...}`) and add
   its config fields to `config.py` (`<NAME>_API_KEY`, `<NAME>_MODEL`, …).
3. **Document** the new env vars in `docs/ENVIRONMENT_VARIABLES.md` and add a row to the
   comparison table below.
4. **Test** with a contract test: a fake-keyed instance, assert `generate()` returns a
   well-formed `AIResponse` and that `json_mode=True` yields parseable JSON (mock the SDK).

No agent, router, or task changes — that is the whole point.

---

## 5. Provider comparison

| Provider | Cost | Vision | JSON mode | Context | Best for |
|----------|------|--------|-----------|---------|----------|
| **sarvam** (default) | ~₹4/1M in, ₹16/1M out | No | Yes (`response_format`) | 128K | English + Indian-language generation |
| anthropic | $3/1M in, $15/1M out | Yes | Via system prompt | 200K | Vision tasks, form-fill (Phase 6) |
| openai | $0.15/1M in, $0.60/1M out | Yes (4o) | Yes (`response_format`) | 128K | Fallback / comparison |
| ollama | Free (local) | Model-dependent | Model-dependent | Model-dependent | Dev/testing, zero data egress |

JSON-mode mechanism differs per provider — the provider class hides this:
- **sarvam / openai:** pass `response_format={"type": "json_object"}`.
- **anthropic:** instruct JSON in the system prompt (and optionally prefill `{`); no native flag.
- **ollama:** pass `format="json"` (model-dependent reliability).

---

## 6. Current provider: Sarvam AI

**SDK gotchas — get these right or it silently fails:**

- The chat method is **`client.chat.completions(...)`** — **NOT** `client.chat.completions.create(...)` (this is the most common mistake; it differs from the OpenAI SDK).
- The constructor param is **`api_subscription_key`** — **NOT** `api_key`.
- Use **`AsyncSarvamAI`** in async contexts (agents run under Celery/async).

**Canonical usage pattern** (inside `SarvamProvider.generate`):
```python
from sarvamai import AsyncSarvamAI

client = AsyncSarvamAI(api_subscription_key=settings.sarvam_api_key)
response = await client.chat.completions(
    model=settings.sarvam_model,                 # "sarvam-105b"
    messages=[{"role": m.role, "content": m.content} for m in req.messages],
    response_format={"type": "json_object"} if req.json_mode else None,
    temperature=req.temperature,
    max_tokens=req.max_tokens,
)
# Note: method is .completions() NOT .completions.create()
```

**Retry/backoff:** wrap `generate()` in exponential backoff (e.g. tenacity) on transient
HTTP/rate-limit errors; surface a non-retryable `AIProviderUnavailable` when the key is
missing so callers return 503. Keep this logic in the provider base, not in agents.

**Vision:** `sarvam-105b` is **text-only**. For the Phase 6 form-filler (needs to read
screenshots), set `AI_PROVIDER=anthropic` for that workload.
