# SAIN Smart Room — External Approvals Required

Date: 2026-11-22. **Status: NOT APPROVED / outside automated test scope.**
SAIN Smart Room is a post-hackathon independent engineering demonstration by team 4Sain, **not** an official SAIN product or a guaranteed licensed commercial integration.

## Approval and provenance register

| Material or planned action | Present evidence | Required before external distribution or operation | Current status |
|---|---|---|---|
| Official API / original hackathon simulator, dataset and Bifrost | Tournament instruction authorizes event-scoped use only; no verified post-event authorization | Written post-hackathon permission specifying endpoint, purpose, validity, quota and responsibility | PENDING |
| Official team and guest tokens / starter kit | Starter kit was provided privately and MUST NOT be published, reproduced in PRs or copied to test artifacts | New separately provisioned credentials under authorized secret management; revoke stale event tokens as advised by owner | PROHIBITED IN STAGE 1 |
| Closed official /run and final guest | Official final state documented read-only; HTTP 409 is a contractual boundary | Explicit integration/contract change from API owner; never bypass 409 | NO BYPASS |
| SAIN name, logos, UI imagery and visual identity | Assets and layout were used during the hackathon; repository presence does not prove a perpetual sublicense | Written authorization for continued public demo, derivative designs, distribution and marketing use, or replace with original licensed materials | PENDING |
| Figma-derived pictures, stock/icons and external media | Per-asset authorship, origin, redistribution and derivative rights not independently cleared | Asset provenance manifest and signed usage/redistribution rights, or replace any unresolved assets | PENDING |
| Fonts (Manrope / Unbounded / Inter) | Corresponding SIL OFL text files included in public repository | Preserve original license notices and validate bundled file coverage | PRELIMINARY |
| Team/third-party code/IP and open-source software | Public repository and package manifests exist; publication itself does not prove all ownership and licenses | Confirm authorship/team agreement, license compatibility, dependency notices, source attribution and commercial rights | PENDING |
| Synthetic/guest records and conversation history | Offline REHEARSAL uses synthetic data; no approved retention policy for real guest data | Data minimization policy, retention/deletion rules, lawful basis, guest access controls and any required consent | PENDING |
| Expert handoff/demo outside team | Prototype is a portfolio candidate, not a certified product | Approvals above, threat/QA acceptance and confirmation of delivery channel and scope | BLOCKED |

## Hard restrictions

- Do not run the official closed /run, make requests to the original organizers' protected servers, use historical tokens, or bypass final read-only.
- Do not upload the supplied starter ZIP, API keys, SSH keys, credentials, private screenshots or raw audio to GitHub, CI, artifacts or external experts.
- Do not treat expert consultation, participation in the tournament, repository visibility, or a successful test as an IP license or approval for production.
- REDACTION: incident evidence must contain only filenames, hashes (nonsecret), synthetic identifiers and minimal error categories; never values of live secrets.
- External requests for permission must be initiated by an authorized human; this document does not send them.

## Technical review separation

Stage 1 can confirm local safety properties (API token boundaries, replay avoidance, synthetic simulations). It **cannot** prove who owns SAIN trademarks, the post-event API licensing scope, rights to distribute proprietary assets, or permission to show guests' data. These remain external blockers S-023 and part of S-014.
