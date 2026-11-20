/* Mapeo de nombres Tailwind -> tokens de tokens.css. Tailwind aporta solo layout; ningun color de su paleta. */
tailwind.config = {
  theme: { extend: {
    colors: {
      bg: "var(--color-bg)", surface: "var(--color-surface)", surface2: "var(--color-surface-2)",
      line: "var(--color-border)", ink: "var(--color-text)", muted: "var(--color-text-muted)",
      accent: { DEFAULT: "var(--color-accent)", hover: "var(--color-accent-hover)", contrast: "var(--color-accent-contrast)", text: "var(--color-accent-text)" },
      success: { DEFAULT: "var(--color-success)", fg: "var(--color-success-fg)", subtle: "var(--color-success-subtle)" },
      danger: { DEFAULT: "var(--color-danger)", on: "var(--color-on-danger)", fg: "var(--color-danger-fg)", subtle: "var(--color-danger-subtle)" },
      warning: { fg: "var(--color-warning-fg)", subtle: "var(--color-warning-subtle)" },
      info: { fg: "var(--color-info-fg)", subtle: "var(--color-info-subtle)" }
    },
    fontFamily: { sans: "var(--font-sans)", mono: "var(--font-mono)" },
    borderRadius: { sm: "var(--radius-sm)", md: "var(--radius-md)", lg: "var(--radius-lg)" },
    boxShadow: { lg: "var(--shadow-lg)" }
  } }
};
