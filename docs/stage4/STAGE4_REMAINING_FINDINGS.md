# SAIN Smart Room — Stage 4 Remaining Findings and Decision Gate

**Scope:** Phase 2 only; PR #26 remains Draft. Maintainer approval is needed for any merge. Review date: 2026-11-23.

## Corrected in the working Stage 4 branch (pending final-SHA verification)

| Severity in original condition | ID | Symptom | Fix | Verification path |
|---|---|---|---|---|
| P1 usability | S4-01 | At 320×568 a design-scaled chat composer fell below viewport | One React-mounted fixed dock; one set of accessible controls | `stage4-ux.spec.ts`, responsive screenshots |
| P1 safety/UX | S4-02 | Decorative illustration resembled Retry even when transport result unknown | Remove misleading SVG, render safe action only when allowed, preserve write lock | `stage4-ux.spec.ts`, Stage 1 recovery tests |
| P2 usability | S4-03 | Plan R6 warning was buried in collapsed technical data | Alert before the full technical explanation | `stage4-ux.spec.ts` |
| P2 visual | S4-04 | Error card had fixed 205px blank area and weak information hierarchy | Compact error, title, consequence, independent close button | Real browser images 16/28; quality-history tests |
| P2 semantics | S4-05 | Climate Figma mock claimed applying/applied without server receipt | Remove fake status, real Save, draft preview, validated bounds | `stage4-ux.spec.ts`, devices POST tests |
| P2 semantics | S4-06 | Unsupported alarm Repeat looked interactive | Static unavailable panel, explicit signal/time labels | `stage4-ux.spec.ts`, journey manual settings |
| P2 usability | S4-07 | Header 24px icons created short physical hit targets | Expand true button boxes to 44 Figma units; preserve icon placement | Pointer center hit-test gate |
| P2 a11y | S4-08 | Voice start/record/wait/error state feedback was visually ambiguous | Explicit status/alert, discard empty STT results, preserve abort | `journey.spec.ts`, speech lifecycle tests |
| P2 QA | S4-09 | Overflows and font metrics collected but not asserted | Hard CI assertions across eight viewport sizes + 200% zoom check | `quality-responsive.spec.ts` |
| P3 aesthetics | S4-10 | Desktop chat and plan surfaces were visually inconsistent | Subtle warm-neutral depth, focus and layout refinements | Desktop 1440/1905/1920 browser screenshots |

## Still open / not independently established

| Priority | Finding / risk | Exact next verification | Release decision |
|---|---|---|---|
| P1 if reproduced | Input focus under actual iOS/Android virtual keyboard / safe areas | Device/browser manual check; record scroll reachability for composer at keyboard-open height | **Block final visual approval** if composer becomes inaccessible |
| P1 if reproduced | Unannounced stale TTS after guest switching on real provider | Keep Stage 3 negative regression and test network-delayed voice when safe provider is available | Block on any cross-guest sound |
| P2 | Live Figma current document cannot be queried (MCP Starter limit) | Compare checked-in exports and screenshots; owner/designer compare with current Figma | Do not claim pixel-perfect |
| P2 | Full 29-screen semantic/control focus walk not done on physical devices | Keyboard/AT traverse all controls, history/modal restore and transitions | Do not claim WCAG certification |
| P2 | Typography under very narrow width: design-scaled device captions ~10–11px | Prioritize critical text and interactive card labels; measure real legibility | Manual review |
| P2 | Native 200%/400% browser zoom and mobile dynamic text tests incomplete | Browser zoom and OS text enlargement checks | Manual a11y acceptance |
| P2 | Color contrast not measured by a dedicated calibrated tool | Calculate foreground/background contrast for dynamic device state, disabled controls, badges | Contrast acceptance |
| P2 | Chrome/Firefox tests represent browser simulation only | Real Android/iOS keyboard, viewport inset and touch interactions | Product acceptance |
| P3 | Live assistant aesthetics and TTS animation over slow network | Capture real UI under throttling or simulated latency | Visual polish |
| P3 | Fine-grained fidelity to individual exports | Visual difference inspection of each of 29 frames | Designer signoff |

## Mandatory end-of-stage gate

Do not mark ready just because workflows are green. Need all of: (a) same final SHA in Python, Node/TS/Vite, Chromium, Firefox, Windows; (b) actual browser screenshot archive and Before/After; (c) unresolved P0/P1 **zero under tested offline scope**, (d) owner/designer signoff on known Figma deltas, and (e) honest record of untested live features.

Official organizer Bifrost LLM/STT/TTS, official dev set and real hardware remain **NOT TESTED**. No Stage 5–7 work. No merge, no `main` edits and no new feature PR.
