/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // ── Nextora Design System Colors ──────────────────────────────
      colors: {
        // Primary brand red
        primary: {
          DEFAULT: "#b80035",
          foreground: "#ffffff",
        },
        "primary-container":  "#e11d48",
        "on-primary":         "#ffffff",
        "on-primary-container": "#fffaf9",
        "primary-fixed":      "#ffdada",
        "primary-fixed-dim":  "#ffb3b6",
        "on-primary-fixed":   "#40000c",
        "on-primary-fixed-variant": "#920028",
        "inverse-primary":    "#ffb3b6",
        "surface-tint":       "#be0037",
        // Secondary amber/yellow
        secondary: {
          DEFAULT: "#795900",
          foreground: "#ffffff",
        },
        "on-secondary":       "#ffffff",
        "secondary-container":"#ffc329",
        "on-secondary-container": "#6f5100",
        "secondary-fixed":    "#ffdf9f",
        "secondary-fixed-dim":"#f9bd22",
        "on-secondary-fixed": "#261a00",
        "on-secondary-fixed-variant": "#5c4300",
        // Tertiary slate-blue
        tertiary:             "#535b71",
        "on-tertiary":        "#ffffff",
        "tertiary-container": "#6c738a",
        "on-tertiary-container": "#fcfaff",
        "tertiary-fixed":     "#dae2fd",
        "tertiary-fixed-dim": "#bec6e0",
        "on-tertiary-fixed":  "#131b2e",
        "on-tertiary-fixed-variant": "#3f465c",
        // Surfaces
        background:           "#f7f9fb",
        foreground:           "hsl(var(--foreground))",
        "on-background":      "#191c1e",
        surface:              "#f7f9fb",
        "surface-dim":        "#d8dadc",
        "surface-bright":     "#f7f9fb",
        "surface-container-lowest": "#ffffff",
        "surface-container-low":    "#f2f4f6",
        "surface-container":  "#eceef0",
        "surface-container-high":   "#e6e8ea",
        "surface-container-highest":"#e0e3e5",
        "on-surface":         "#191c1e",
        "on-surface-variant": "#5c3f40",
        "inverse-surface":    "#2d3133",
        "inverse-on-surface": "#eff1f3",
        "surface-variant":    "#e0e3e5",
        // Semantic tints
        "surface-tint-red":   "#FFF1F2",
        "surface-tint-yellow":"#FEFCE8",
        // Outlines
        outline:              "#906f70",
        "outline-variant":    "#e5bdbe",
        "border-subtle":      "#E2E8F0",
        // Error
        error:                "#ba1a1a",
        "on-error":           "#ffffff",
        "error-container":    "#ffdad6",
        "on-error-container": "#93000a",
        // shadcn compatibility overrides
        border:               "hsl(var(--border))",
        input:                "hsl(var(--input))",
        ring:                 "hsl(var(--ring))",
        card: {
          DEFAULT:            "hsl(var(--card))",
          foreground:         "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT:            "hsl(var(--popover))",
          foreground:         "hsl(var(--popover-foreground))",
        },
        muted: {
          DEFAULT:            "hsl(var(--muted))",
          foreground:         "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT:            "hsl(var(--accent))",
          foreground:         "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT:            "hsl(var(--destructive))",
          foreground:         "hsl(var(--destructive-foreground))",
        },
      },

      // ── Typography ────────────────────────────────────────────────
      fontFamily: {
        sans:   ["Geist", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
        geist:  ["Geist", "ui-sans-serif", "system-ui", "sans-serif"],
        mono:   ["Geist Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        "display-lg": ["48px", { lineHeight: "1.1", letterSpacing: "-0.04em", fontWeight: "700" }],
        "display-lg-mobile": ["36px", { lineHeight: "1.1", letterSpacing: "-0.03em", fontWeight: "700" }],
        "headline-md": ["30px", { lineHeight: "1.2", letterSpacing: "-0.02em", fontWeight: "600" }],
        "headline-sm": ["22px", { lineHeight: "1.3", letterSpacing: "-0.01em", fontWeight: "600" }],
        "body-lg":  ["18px", { lineHeight: "1.6", fontWeight: "400" }],
        "body-md":  ["16px", { lineHeight: "1.6", fontWeight: "400" }],
        "body-sm":  ["14px", { lineHeight: "1.5", fontWeight: "400" }],
        "label-md": ["12px", { lineHeight: "1.2", letterSpacing: "0.08em", fontWeight: "600" }],
        "label-sm": ["11px", { lineHeight: "1.2", letterSpacing: "0.05em", fontWeight: "700" }],
      },

      // ── Spacing ───────────────────────────────────────────────────
      spacing: {
        unit:              "8px",
        xs:                "4px",
        sm:                "12px",
        md:                "24px",
        lg:                "48px",
        xl:                "80px",
        gutter:            "24px",
        "gutter-desktop":  "24px",
        "gutter-mobile":   "16px",
        "margin-desktop":  "64px",
        "margin-mobile":   "20px",
        "max-width":       "1280px",
      },

      // ── Border Radius ─────────────────────────────────────────────
      borderRadius: {
        none:    "0",
        sm:      "0.125rem",
        DEFAULT: "0.25rem",
        md:      "0.375rem",
        lg:      "0.5rem",
        xl:      "0.75rem",
        "2xl":   "1rem",
        "3xl":   "1.5rem",
        full:    "9999px",
      },

      // ── Shadows ───────────────────────────────────────────────────
      boxShadow: {
        sm:     "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        DEFAULT:"0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
        md:     "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
        lg:     "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
        xl:     "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)",
        "2xl":  "0 25px 50px -12px rgb(0 0 0 / 0.25)",
        // Brand hard shadow (yellow offset)
        "hard-yellow": "4px 4px 0px #f9bd22",
        "hard-red":    "4px 4px 0px #e11d48",
      },

      // ── Max Width ─────────────────────────────────────────────────
      maxWidth: {
        "8xl": "1280px",
        "9xl": "1440px",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
