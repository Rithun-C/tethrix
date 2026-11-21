/**
 * The Tethrix logo, from the owner's logo canvas (docs/brand.md).
 *
 * Drawn as inline SVG so its colours come from the design tokens in styles.css: the orbit
 * and canyon lines switch to the reversed colours in dark mode by themselves.
 */

type MarkProps = {
  /** Width and height in pixels. */
  size?: number;
};

/** The mark alone: the moon Tethys, its crater and canyon, on an orbit arc. */
export function TethrixMark({ size = 32 }: MarkProps) {
  return (
    <svg viewBox="0 0 120 120" width={size} height={size} aria-hidden="true" className="logo-mark">
      <path className="logo-line" d="M37 101.84 A46 46 0 1 1 99.84 39" strokeWidth="6" />
      <circle className="logo-deep" cx="60" cy="62" r="30" />
      <path className="logo-violet" d="M81.21 40.79 A30 30 0 0 0 38.79 83.21 Z" />
      <circle className="logo-deep" cx="49" cy="52" r="11" />
      <circle className="logo-light" cx="50.5" cy="53.5" r="3.6" />
      <path className="logo-cut" d="M50 86 Q72 82 84 58" strokeWidth="4" />
      <circle className="logo-light" cx="99.84" cy="39" r="5" />
    </svg>
  );
}

/** Mark plus wordmark ("teth" in ink, "rix" in violet). Screen readers hear "Tethrix". */
export function TethrixLogo({ size = 32 }: MarkProps) {
  return (
    <span className="logo" role="img" aria-label="Tethrix">
      <TethrixMark size={size} />
      <span className="logo-word" aria-hidden="true">
        teth<span className="logo-word-accent">rix</span>
      </span>
    </span>
  );
}
