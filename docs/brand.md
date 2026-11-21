# Brand: Tethrix

- Decided: 2026-11-21 by the owner
- Source: the owner's logo canvas "Satrix & Tethrix Logos" (a private design artifact).
  Tethrix is a Satrix project, named after Tethys, a moon of Saturn.
- In the code: `app/frontend/src/brand/` (logo component, favicon) and the design tokens
  at the top of `app/frontend/src/styles.css`

## Logo

The mark is the moon Tethys with its large crater and canyon, on an orbit arc. The
wordmark is "teth" in ink and "rix" in violet, set in Sansation Bold (the canvas used
Sora SemiBold; the owner changed the font on 2026-11-22).

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
| `--surface` | `#F7F5FA` | `#0F0E15` | Menu and quiet panels |
| `--border` | `#E2DEE8` | `#2A2733` | Lines between areas |
| `--accent-soft` | `#F2EBFD` (violet tint) | `#22143C` | Hover, secondary buttons and badges |
| `--raised` | `#FFFFFF` | `#15131C` | Cards, inputs, the current menu item ("orbit 1") |
| `--border-strong` | `#CFC9D8` | `#3A3644` | Control edges |
| `--border-hover` | `#8A8594` | same | Hovered fields, checkbox edge (3:1) |
| `--ring` | `#7C3AED` | `#AA7FF3` | Focus ring (see below) |
| `--moon` | `#7C3AED` | `#AA7FF3` | "You are here" markers |
| `--ok`, `--error` | `#15803D`, `#DC2626` | `#4ADE80`, `#F87171` | Status |
| `--danger-text` | `#B91C1C` | `#F87171` | Danger words and badges |
| `--danger-button` | `#DC2626` | same | Delete buttons (white on it 4.8:1 in both themes) |

`--violet-deep` and `--lavender` are the canvas's own formulas applied to the violet
(72% of each channel; 35% of the way to white). Since B5 the other values come from the
owner's component library Satrix UI (`docs/bolts/B5-todos.md` section 15), with two
changes for contrast:

- Focus ring on light: the library draws it lavender, which is 2.98:1 on white, under
  the 3:1 a focus ring needs. It is violet on light (5.7:1) and lavender on dark (6.6:1).
- Delete button on dark: white on the dark theme's red `#F87171` is 2.77:1, so the
  button keeps the light red `#DC2626` (4.8:1) in both themes. Danger words on dark
  still use `#F87171`.

Contrast (WCAG 2.2, 4.5:1 for text): white on violet 5.7:1; violet on white 5.7:1;
muted on white about 7:1; off-white on the dark background about 17:1; lavender on the
dark background about 6.5:1. Added in B5: deep violet on the tint 7.7:1; danger text on
its badge 5.7:1 (light) and 5.5:1 (dark); muted on the dark card 7.1:1; checkbox edge
3.6:1 (light) and 5.1:1 (dark), above the 3:1 for controls.

## Type

Sansation, for all text and the wordmark (owner's choice, 2026-11-22; it replaced Sora
from the canvas). Weights 400 (Regular) and 700 (Bold), Latin only. Licence: SIL Open
Font Licence.

It is a Google Font, served from our own `/assets` through the pinned npm package
`@fontsource/sansation` 5.3.0, not from Google's servers. These are the same font files
Google serves. Linking Google Fonts directly would mean two things: the Content Security
Policy would have to allow `fonts.googleapis.com` and `fonts.gstatic.com`, and every
visitor's browser would tell Google each time the app opens. Self-hosting avoids both.

## What is not renamed

The app is called Tethrix everywhere a person sees it. The Terraform project name stays
`productivity-app` (resource names such as `productivity-app-api`): renaming would make
Terraform replace the table, the user pool and the ECR repository, losing data and user
accounts, for no gain.

## Component library

Satrix UI, the owner's design (B5). Shapes, spacing, sizes, elevation and motion are
tokens in `styles.css`; the React components are in `app/frontend/src/ui/`. The library
uses Sora, Inter and JetBrains Mono; the app keeps Sansation, the owner's later choice.
