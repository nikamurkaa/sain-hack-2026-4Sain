# SAIN Smart Room — Stage 4 Accessibility Report

**Revision:** Phase 2, 2026-11-23. **PR:** #26, branch `stage4/premium-ui-ux`. Figma mobile export is 375×812 and is scaled by `DesignScreen`; desktop uses a different React grid.

## Principles and scope

WCAG 2.2 AA is a review target, **not a conformance claim**. Audit covers known React behavior and Playwright using desktop-browser emulation at 320×568, 375×812, 390×844, 768×1024, 1024×768, 1440×900, 1905×911 and 1920×1080, plus CSS 200% zoom, keyboard and reduced motion. Real mobile assistive technologies (VoiceOver/TalkBack), hardware keyboard overlays and live organizer services are **not tested**.

## Findings, remediation and evidence

| Domain | Implementation / source evidence | What the test must verify | Limit |
|---|---|---|---|
| Keyboard navigation | Header Menu is a real button; Escape in `main.tsx` closes menu and returns focus. `MobileStay.tsx` uses semantic buttons instead of empty SVG hit regions. | `quality-responsive.spec.ts` menu Enter/Escape; Playwright keyboard routes | No independent physical keyboard usability session |
| Pointer target size | `layout.css` expands real icon button boxes to 44×44 Figma units while retaining 24px art position | hit-test center/coverage gate at 320, 375, 390 and desktop | Mobile scaling produces ~37px at 320; 44px CSS physical size not claimed |
| Critical text | `quality-responsive.spec.ts` asserts chat composer font size ≥13 CSS px; `layout.css` supplies larger error headings and readable warning hierarchy | Actual pixel size and clipping screenshots | Some decorative device captions remain 10–11px; no blanket numeric claim |
| Focus visibility | `layout.css` uses a high-visibility outline; `style.css` adds active composer border | Keyboard Tab/Enter and screenshots | Need full visual focus-walk review for every screen |
| Native form semantics | Climate number input has step/min/max; alarm has native time and labeled select; sound track, sliders and volume have accessible names | `stage4-ux.spec.ts` and `journey.spec.ts` | Browser-localized time-input behavior may differ |
| Errors and uncertain writes | `MobileStay.tsx` renders a single alert, truthful error title, consequence, and safe action; blocked POST never silently repeats. `ActionNotice.tsx` keeps verify-first logic | `stage4-ux.spec.ts`, `stage1-*.spec.ts`, `quality-history.spec.ts` | Server-side out-of-band recovery not exercised with official tokens |
| Warnings / R6 | Warning is visible before collapsed technical details in mobile and desktop plans, exposed as an alert | `stage4-ux.spec.ts` R6 scenario | Repetitive ARIA role alerts in collapsed explanation can be reviewed further |
| Voice lifecycle | `Voice.tsx` uses explicit role=status and single role=alert on error; empty STT result is error, not a command. Mic cleanup aborts pending work | `journey.spec.ts` microphone and `speech-reply-lifecycle.test.ts` replay-isolation | Real provider latency, microphone permission UI and VoiceOver not tested |
| Modal history | Native `dialog` has accessible name and close control; Escape handler closes | History E2E and keyboard paths | Need explicit focus-return verification on history close |
| Read-only mode | Current source displays explicit `final` / `read_only` and hides controls | `quality-responsive.spec.ts` final session | Avoid leaking synthetic guest info in screenshots |
| Zoom / reflow | CSS 200% zoom measured; design frame responds through `ResizeObserver`; root overflow checked on standard sizes | `quality-responsive.spec.ts`; screenshots `zoom-200-*` | Not equal to real OS/browser text-only zoom; manual audit still needed |
| Reduced motion | `prefers-reduced-motion: reduce` suppresses skeleton/orb and UI transitions where added | Playwright emulated reduced motion | Does not prove all motion effects comply |
| Color contrast | Warm-white-on-charcoal for actions and text; peach focus outlines/error titles improved | Browser screenshot review plus contrast measurements | **Contrast ratios not measured with an audited contrast tool** |
| Screen-reader structure | Real form elements, accessible labels and log/alert/status semantics | Source review, accessible role selectors in Playwright | Axe-core and AT screen-reader audit **NOT RUN** |

## What is proven vs not proven

- **Proven by source inspection:** component intent, API locking, ARIA role assignment, presence of labels, focus styles and noninteractive decorative drawings.
- **Proven only after final green SHA:** automated browser behavior at specified viewports, screenshot generation and associated CI reports.
- **Not proven:** full WCAG 2.2 AA compliance, exact live Figma fidelity, native mobile accessibility, real Bifrost LLM/STT/TTS integration and physical device results.

## Acceptance checklist for independent reviewer

1. Keyboard-only traverse: Connect → Plan → Room → Settings → Chat → Voice → History → Reconnect, checking focus order and Escape.
2. Run 320×568, 375×812, 390×844, tablet and 1905×911 desktop; inspect all eight viewports and short-screen virtual keyboard.
3. Compare real light/dark text colors using WCAG relative luminance; target 4.5:1 normal text and 3:1 larger text/essential UI graphics.
4. Test at 200% and 400% real browser zoom and OS text-only enlargement.
5. Test VoiceOver/TalkBack, reduced-motion and forced-colors manually.
6. Exercise uncertain POST / verified recovery, no accidental duplicate write, and stale TTS after guest switch.

**Verdict:** automated accessibility hardening performed; independent hands-on and assistive-technology review is still required before asserting WCAG conformance. Not ready to claim pixel-perfect or full accessibility certification.
