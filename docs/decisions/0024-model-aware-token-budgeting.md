# ADR 0024 — Model-aware token budgeting for application preparation

Status: Accepted for implementation
Date: 2026-10-07
Related: [ADR 0023](0023-application-preparation-and-action-boundaries.md), [PLAN-021](../plans/PLAN-021-evidence-led-generation-quality.md)

## Context

Clue previously stopped a preparation when selected technical profile text exceeded 40,000 combined characters, descriptive profile text exceeded 32,000 characters, or a writing sample exceeded 4,000 characters. Those thresholds were app-authored checks, not GPT-6 Luna context limits. Clue also reserved OpenAI input usage using UTF-8 payload bytes plus a fixed allowance, rather than the model's input-token count.

The official GPT-6 Luna model page lists a 1,050,000-token context window and a 128,000-token maximum output. The Responses API exposes an input-token counting endpoint that accepts the prompt, instructions, output schema, and tools and returns the exact input count. Its documentation also states that `max_output_tokens` covers visible and non-visible generated tokens. Requests over 272,000 input tokens are priced at twice the input rate and 1.5 times the output rate for the full request.

## Decision

Before each GPT generation request, Clue sends the exact model, instructions, input, tools, structured-output configuration, reasoning configuration, and other supported input fields to the Responses API token counter. Clue checks the returned input count plus the request's configured maximum output tokens against the documented model context window. It reserves local app-side spend using that exact input count and configured maximum output allowance, applies the long-context pricing multipliers when input exceeds 272,000 tokens, then settles against the generation response's actual usage receipt.

After the per-listing trigger and OpenAI consent, Clue passes each selected, permitted technical profile, descriptive profile, and writing reference in full to its authorized stage. It does not silently shorten candidate material. If a request exceeds model context or its configured local spending limit, Clue stops before generation and records a clear reason. Per-stage output limits remain; they are tuned from captured completion data and each request remains bounded by its local reserve.

Generation uses a 600-second client timeout, aligned with the current OpenAI Python SDK's documented default request timeout; the smaller input-token preflight uses 60 seconds. Clue does not automatically retry an uncertain generation request. If a timeout occurs after the provider has returned response headers, Clue retains a validated `x-request-id` with the sanitized error so usage can be reconciled; if no response ID arrived, the reservation stays unknown and blocks retry for that request.

Jev remains the sole authority for job fit, ranking, filtering, and eligibility. Its generated-claim evidence check remains separate and cannot change the saved match decision. No model output submits an application or sends outreach.

## Consequences

- Relevant profile evidence is no longer blocked by arbitrary character cutoffs.
- Input reservations reflect model tokenization and the exact input shape, including system instructions, JSON schema, and the Researcher tool definition.
- Each manually triggered generation stage incurs an additional input-token count request to OpenAI with the same stage input. OpenAI consent and the per-listing trigger still govern disclosure.
- If the token counter is unavailable, malformed, or disagrees with the actual generation usage, Clue fails closed and retains any generation reserve that may have reached the provider.
- Generation and preflight timeouts are separate. A generation timeout is not treated as a provider rejection; usage remains unresolved unless a complete response receipt is received. No automatic retry can duplicate an uncertain charge.
- Local app-side spending caps remain independent from provider account settings and Jev budgets.
- The context and rate card must be rechecked when the configured model changes or before a live run if the pricing check is stale.

## References

- [GPT-6 Luna model limits](https://developers.openai.com/api/docs/models)
- [Responses API token counting](https://developers.openai.com/api/docs/guides/token-counting)
- [Count input tokens API reference](https://developers.openai.com/api/reference/resources/responses/subresources/input_tokens/methods/count)
- [GPT-6 Luna pricing and limits](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [OpenAI Python SDK timeout and retry behavior](https://developers.openai.com/api/reference/python)
