# ADR 0039 — Optional local spending gates

Status: Accepted
Date: 2026-10-11

## Context

The owner instructed Clue to ignore local spending allowances because external service limits are configured on the provider side. Repeatedly increasing app ceilings during evaluation was obstructing authorized work. Usage evidence still needs to be recorded.

## Decision

Introduce `CLUE_ENFORCE_LOCAL_SPEND_CAPS`. When false, OpenAI monthly/per-opportunity reservations and all Jev reservations (matching, factual support, final-CV approval) record usage without refusing requests for exceeding local ceilings. Authentication, consent, input/context limits, source checks, and writing/factual validation remain active. The default is true for backward compatibility. This installation explicitly sets the ignored local configuration to false.

The switch does not alter provider account configuration, which was neither accessed nor verified. Saved local allowance values remain in storage but are inactive. Settings displays the disabled state. Usage reservations, unknown outcomes and settlement records remain available for diagnosis. There is no database migration or data deletion.

## Evidence

A regression reserves OpenAI and Jev usage above very small local ceilings when enforcement is disabled and verifies that both ledger records still exist and OpenAI usage can settle. Existing cap-enforcement tests continue passing with the default configuration. The full repository suite passes 365 tests. The live letter clarification completed with this installation's disabled local gates.
