# ADR 0032 — Jev-guided cover-letter repair

- Status: Accepted
- Date: 2026-10-07
- Related: [ADR 0023](0023-application-preparation-and-action-boundaries.md), [ADR 0026](0026-jev-categorical-evidence-support.md), [ADR 0031](0031-public-recruitment-inboxes-and-draft-integrity.md), [PLAN-020](../plans/PLAN-020-end-to-end-evaluation-and-grounding.md)

## Context

The live three-listing evaluation showed that a syntactically complete letter could fail Jev's evidence-support gate. Failed paragraphs mixed a candidate project fact with an inferred connection to role responsibilities. One also used a project label absent from the supplied evidence. A different supported letter repeated a formulaic relevance bridge, and the DOCX omitted a greeting and closing. The Rewriter prompt allowed fewer than two paragraphs while the packet gate still required two, so its fallback instruction could not produce a valid packet.

The saved Jev fit decisions were stable and separate from these content failures. The defect was in generation guidance and packet completion, not in matching authority.

## Decision

1. Keep Jev as the sole matching authority. Its saved match, fit score, eligibility, and filter evidence remain immutable during content generation and repair.
2. Ask the Rewriter to state candidate evidence and role requirements as distinct, separately sourced facts. Preserve exact project names and contribution verbs. Do not infer candidate actions, transferability, fit, impact, or likely success from adjacent evidence.
3. After the initial Jev support check, permit one targeted GPT-6 Luna repair call for letter paragraphs Jev marked unsupported/unresolved or the local exact-duplicate-sentence check flagged. Initially supported paragraphs stay locked unless they themselves contain an exact duplicated sentence requiring local repair.
4. Bind repair outputs to the exact failed paragraph indices and existing approved evidence set. Omitted repair outputs remain omitted. Run the full final letter through Jev again, including any previously supported paragraph, before artifact generation.
5. Keep the existing two-paragraph, 2/2 Jev-support requirement and explicit final-CV approval requirement. Any incomplete repair, failed Jev recheck, or failed quality gate creates no documents. The repair is not a softer fallback.
6. Render a generic greeting and closing locally. Use a candidate name only when the selected CV has one unambiguous name in its first non-empty header line; otherwise use a generic signature.
7. Charge the repair call through the existing exact-token preflight, local spend reservation, and usage settlement. Do not change OpenAI or Jev provider-side caps or settings.
8. Apply the same evidence discipline to CV bullet edits: a project or technology excerpt does not prove that the owner built, designed, trained, deployed, or led it. Require owner-attributed source wording for such action verbs; Jev-unresolved edits remain omitted.
9. Label the automated quality result as an evidence/completeness gate, not a writing-quality verdict. Require owner review of relevance and voice; do not use an arbitrary word-count threshold because concise copy can meet the owner's writing rubric.

## Consequences

- A first-draft paragraph can be corrected once when it cites a valid but insufficient source or makes an unsupported relationship claim.
- A repaired letter must satisfy the same full Jev evidence gate as a first-draft letter; matching decisions remain unchanged.
- The additional model call can add latency and Clue-local usage only when a paragraph requires repair.
- Mechanical duplicate detection and a complete letter scaffold address specific style/document defects; they do not establish personal voice acceptance or hiring effectiveness. The two M6 letters passed factual checks but remained sparse and weakly connected to role duties; they are review drafts, not proven final copy.
- Accenture's live `.17` retest completed one targeted repair, Jev supported 2/2 final paragraphs, and Jev approved the final CV. Bending Spoons first hit Researcher's 2,200-token allowance, then completed under prompt `.18` after the local ceiling rose to 4,000 and findings were capped at eight; Jev supported 2/2 paragraphs and approved the CV. Both saved listing decisions remained unchanged. Both cover letters were rendered as one page with no clipping/overlap but substantial unused space.
- The first Accenture retry stopped before generation because this environment could not resolve `api.openai.com`; it incurred no provider usage. A later network-enabled retry completed. No provider settings/caps changed.

## Validation

- Offline regression coverage verifies targeted paragraph repair, locked supported paragraphs, a Jev recheck of the complete revised letter, fail-closed behavior, duplicate-sentence detection, greeting/closing rendering, the 4,000-token Researcher allowance, and conservative owner-action wording for CV edits.
- Five focused tests and 57 workflow tests passed with seven `TestClient` cases deselected. Ruff, byte-compilation, and `git diff --check` passed. A full-suite attempt stalled without a summary and was stopped; a full-suite pass is not claimed.
- Live OpenAI usage settled for Accenture (`$0.0193504` local estimate), the incomplete Bending attempt (`$0.0018726`), and the completed Bending retest (`$0.0127743`). The initial DNS failure had no usage row; no usage remains reserved or unknown. No provider caps or settings changed.
- Jev's original Accenture `review` and Bending `match` results and eligibility remained unchanged. Both final CVs were explicitly approved, but both retained zero bullet edits because Jev marked one proposed action claim unresolved and Clue omitted it.
- Prompt `.19` makes the owner-action rule explicit. It has offline prompt coverage but was not used for either live packet; those packets used `.17` and `.18`.
