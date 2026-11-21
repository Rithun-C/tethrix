# Brand: Tethrix

- Decided: 2026-11-21 by the owner
- Source: the owner's logo canvas "Satrix & Tethrix Logos" (a private design artifact).
  Tethrix is a Satrix project, named after Tethys, a moon of Saturn.
- In the code: `app/frontend/src/brand/` (logo component, favicon) and the design tokens
  at the top of `app/frontend/src/styles.css`

## Logo

The mark is the moon Tethys with its large crater and canyon, on an orbit arc. The
wordmark is "teth" in ink and "rix" in violet, set in Sora SemiBold.

| File | Use |
|---|---|
| [brand/tethrix-mark.svg](brand/tethrix-mark.svg) | The mark on light backgrounds |
| [brand/tethrix-mark-dark.svg](brand/tethrix-mark-dark.svg) | The mark on dark backgrounds: orbit line off-white, canyon cut out in the background colour |
| [brand/tethrix-favicon.svg](brand/tethrix-favicon.svg) | Browser tab icon, simplified for 16 and 32 px, on an ink square |

In the app, the logo is drawn by `TethrixLogo` and `TethrixMark` as inline SVG. Its
colours come from the tokens, so it reverses in dark mode by itself. Screen readers hear
"Tethrix" once; the drawing itself is hidden from them.

## Colours

| Token | Light | Dark | Use |
|---|---|---|---|
| `--violet` | `#7C3AED` | same | Brand colour, buttons, "rix" on light |
| `--violet-deep` | `#592AAB` | same | Shadow side of the moon, button hover |
| `--lavender` | `#AA7FF3` | same | Highlights, "rix" and focus ring on dark |
| `--text` | `#111015` (ink) | `#F3EFFA` (off-white) | Text, logo lines |
| `--text-muted` | `#5B5762` | `#A39FAD` | Secondary text |
| `--bg` | `#FFFFFF` | `#0B0A10` | Page background |
| `--surface` | `#F7F5FA` | `#15131B` | Menu and panels |
| `--border` | `#E2DEE8` | `#2A2733` | Lines between areas |
| `--accent-soft` | `#F2EBFD` | `#22143C` | Hover and current menu item |
| `--ok`, `--error` | `#1A7F37`, `#CF222E` | `#3FB950`, `#F85149` | Status text |

`--violet-deep` and `--lavender` are the canvas's own formulas applied to the violet
(72% of each channel; 35% of the way to white). The surface, border and soft-accent dark
values and the status colours are not on the canvas; they were chosen to sit with it and
may change with the component library design.

Contrast (WCAG 2.2, 4.5:1 for text): white on violet 5.7:1; violet on white 5.7:1;
muted on white about 7:1; off-white on the dark background about 17:1; lavender on the
dark background about 6.5:1.

## Type

| Font | Used for | Weights | Licence |
|---|---|---|---|
| Permanent Marker | All text in the app (owner's choice, 2026-11-22) | 400 only | Apache 2.0 |
| Sora | The "tethrix" wordmark in the logo, as on the canvas | 600 only | SIL Open Font Licence |

Both are Google Fonts, Latin only, served from our own `/assets` through pinned npm
packages (`@fontsource/permanent-marker` 5.3.0, `@fontsource/sora` 5.3.0), not from
Google's servers. These are the same font files Google serves. Linking Google Fonts
directly would mean two things: the Content Security Policy would have to allow
`fonts.googleapis.com` and `fonts.gstatic.com`, and every visitor's browser would tell
Google each time the app opens. Self-hosting avoids both.

Permanent Marker has one weight, so bold text is turned off
(`font-synthesis-weight: none`) instead of letting the browser smear a fake bold. It is a
handwritten display font; if long text such as journal entries becomes hard to read, the
component library design can give body text a plainer font and keep the marker for
headings.

## What is not renamed

The app is called Tethrix everywhere a person sees it. The Terraform project name stays
`productivity-app` (resource names such as `productivity-app-api`): renaming would make
Terraform replace the table, the user pool and the ECR repository, losing data and user
accounts, for no gain.

## Next

The owner will provide the design for the component library. It builds on these tokens:
components use the tokens, never raw colours.
