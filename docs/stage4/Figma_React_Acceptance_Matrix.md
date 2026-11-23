# Stage 4 — Figma ↔ React acceptance matrix

Baseline: `3c240169cc858c6df820d513b02e8f462a0ecd14`, 2026-11-23. Issue #25. Work only in `stage4/premium-ui-ux`.
Source: supplied Figma 29-screen contact sheets; checked-in `frontend/src/design/frames.json`, `art-01.svg` … `art-29.svg`, `MobileStay.tsx`, `Layout.tsx`, `views.tsx`, `main.tsx`. The direct Figma node retrieval is blocked by a selection-required tool error; pixel parity with the current live Figma document remains NOT VERIFIED.

| Figma screens | React route / file | Behavioral implementation | Stage 4 discrepancy / validation |
|---|---|---|---|
| 01,03,05,07 Plans (4 periods) | `MobileStay.tsx` (`page=plan`) | dynamic period tabs and `Plan` from preparation | R6/warnings only in collapsed explanation; surface actionable warning outside `details` |
| 02,04,06,08 My room (4 periods) | `MobileStay.tsx` (`page=room`) | device controls bound to confirmed `snapshot.state` | audit card wrapping + 320px viewport scroll and tap areas |
| 09 chat suggestion | `MobileStay.tsx` (`page=chat`) | empty-state suggestion, mic, composer | verify suggestion hidden while unsafe / blocked |
| 10 chat reply | same | last reply + history dialog; `SpeechReply` | long content may be scroll-contained; verify 320px and keyboard |
| 11 check-in | `MobileStay.tsx` (`page=welcome`) | admission via Plan | check accessible label/viewport |
| 12–14 voice recording/transcribing/transcript | `Voice.tsx` and `views.tsx` | recording and edit state | browser recording, cancel and request race tests; live provider NOT TESTED |
| 15–16 refusal/error | `MobileStay.tsx` (`page=chat`) | API-derived response and error | **UX-NEW-01** Figma error illustration contains decorative Retry; never show as active affordance unless a safe retry really exists |
| 17–20 virtual time (4 periods) | `MobileStay.tsx` (`page=virtual`) | GET preview, read-only period and state | check 320px label readability and no accidental write |
| 21 climate settings | `views.tsx` (`Settings`) | numeric input, -/+ and save | static Figma status labels can imply success before confirmation; remove/rework decorative states |
| 22 alarm settings | `views.tsx` (`Settings`) | time/mode, save | 'Повтор' visually exposed without backend support; verify unavailable state |
| 23 sound settings | `views.tsx` (`Settings`) | select, volume, save | verify track wrapping and visual feedback |
| 24 loading | `main.tsx` (`expired/loading`) | loading state | ensure no pseudo controls |
| 25 sending | `MobileStay.tsx` (`page=chat`) | pending command | prevent double POST; keep confirmed vs pending distinct |
| 26 success | same | reply + confirmed state | success only on acknowledged simulator result |
| 27 refusal | same | result response_class | no changes falsely reported |
| 28 network error | same | error state | **UX-NEW-01** actual Retry only when safe; error card should not display clickable-looking SVG when retry is prohibited |
| 29 session expiration | `main.tsx` | reconnect/new session | no guest text/audio leakage |

## Confirmed implementation findings (source review, not rendered-browser reproduction)
- `Layout.tsx` maps 375×812 Figma widget coordinates to scaled HTML elements, and `layout.css` fixes the virtual design frame to 812px with overflow hidden. Short viewports (e.g. 320×568) require direct browser verification of actionable content, horizontal overflow and scroll reachability. **P2 until reproduced blocking → P1.**
- `MobileStay.tsx` error widget currently retains decorative SVG drawing and overlays a `Hit` only when `retryAllowed`; the SVG can mislead users when it shows a retry-looking element without permitted Retry. **P2 UX-NEW-01.**
- `views.tsx` climate mobile settings uses imported Figma response widgets as faux “save”/status UI. Confirmed operation state must come from the API, not static Figma labels. **P2 UX-NEW-01.**
- `prepared.explanations` warnings are rendered only inside collapsed `details` on plan/profile, making R6 warnings hard to discover. **P2 UX-01.**
- `ActionNotice.tsx` already reports uncertain actions with a verify-first recovery path; do not replace it with a naive “Retry”. Stage 3 audio guest isolation must remain intact. **Regression safeguard / possible P1 if broken.**
- Desktop renders native `main.tsx` dashboard and settings, not the mobile screenshot scaled to 1440px. Its matching criteria are semantic/token alignment, not identical geometry.

## Acceptance
Run TypeScript + Vite, Node tests, Chromium + Firefox at 320×568, 375×812, 390×844, 1440×900, 1920×1080; capture actual browser viewport screenshots; check keyboard/scroll/hit targets, no misleading fake actions; verify current HEAD SHA on CI. Actual official Bifrost / STT / TTS remains NOT TESTED. No merge authorized.

## State
Initial code audit completed; screenshot comparisons, live Figma API read, and full multi-resolution browser verification still pending.
