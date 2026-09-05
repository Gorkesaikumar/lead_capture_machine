---
name: Nextora Systems
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#5c3f40'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#906f70'
  outline-variant: '#e5bdbe'
  surface-tint: '#be0037'
  primary: '#b80035'
  on-primary: '#ffffff'
  primary-container: '#e11d48'
  on-primary-container: '#fffaf9'
  inverse-primary: '#ffb3b6'
  secondary: '#795900'
  on-secondary: '#ffffff'
  secondary-container: '#ffc329'
  on-secondary-container: '#6f5100'
  tertiary: '#535b71'
  on-tertiary: '#ffffff'
  tertiary-container: '#6c738a'
  on-tertiary-container: '#fcfaff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdada'
  primary-fixed-dim: '#ffb3b6'
  on-primary-fixed: '#40000c'
  on-primary-fixed-variant: '#920028'
  secondary-fixed: '#ffdf9f'
  secondary-fixed-dim: '#f9bd22'
  on-secondary-fixed: '#261a00'
  on-secondary-fixed-variant: '#5c4300'
  tertiary-fixed: '#dae2fd'
  tertiary-fixed-dim: '#bec6e0'
  on-tertiary-fixed: '#131b2e'
  on-tertiary-fixed-variant: '#3f465c'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
  surface-tint-red: '#FFF1F2'
  surface-tint-yellow: '#FEFCE8'
  border-subtle: '#E2E8F0'
typography:
  display-lg:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.04em
  display-lg-mobile:
    fontFamily: Geist
    fontSize: 36px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.03em
  headline-md:
    fontFamily: Geist
    fontSize: 30px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Geist
    fontSize: 22px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Geist
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-sm:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.08em
  label-sm:
    fontFamily: Geist
    fontSize: 11px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 8px
  gutter-desktop: 24px
  gutter-mobile: 16px
  margin-desktop: 64px
  margin-mobile: 20px
  max-width: 1280px
---

## Brand & Style
The design system for the product is built on a **High-Contrast / Bold** aesthetic that balances high-velocity energy with sophisticated professional rigor. It targets a modern enterprise audience that demands both speed and clarity. 

The mood is defined by the tension between "Urgency" (vibrant red) and "Optimism" (bright yellow). To avoid a casual or "fast food" association, the system utilizes a **Minimalist** framework: heavy white space, razor-sharp typography, and surgical use of color. Chromatic accents are treated as functional indicators of momentum and priority, while the overall interface remains "airy" and expansive to ensure a premium, high-performance feel.

## Colors
The palette is dominated by high-key neutrals to maintain professional composure, with intense chromatic bursts for interaction.

- **Primary (#E11D48):** An energetic, professional red. Used for critical actions, core branding, and urgent notifications.
- **Secondary (#FBBF24):** A warm, sun-drenched yellow. Used for highlights, secondary CTA accents, and optimistic progress indicators.
- **Neutral:** A light, airy foundation. The primary background is white, while sectioning is achieved through `surface-tint-red` and `surface-tint-yellow`—extremely pale washes that provide warmth without clutter.
- **Tertiary/Ink:** Slate-900 (#0F172A) is used for maximum typographic contrast, ensuring the bold Geist font remains grounded and authoritative.

## Typography
The system exclusively uses **Geist** to maintain a unified, technical, and precise aesthetic. 

Weights are strictly controlled: use **SemiBold (600)** and **Bold (700)** for headlines to project confidence. For body text, **Regular (400)** is the standard, but for high-legibility data points or interactive labels, **Medium (500)** is preferred. To avoid the palette feeling overwhelming, typography remains dark and high-contrast (#0F172A) against the light backgrounds. Large display types should utilize aggressive negative letter-spacing to create a "locked-in" architectural feel.

## Layout & Spacing
This design system uses a **Fixed Grid** approach for internal content containers to ensure structured data presentation, while using **Fluid** margins for the outer layout.

- **Desktop:** A 12-column grid with 24px gutters. Use generous side margins (64px) to center the focus and create the "airy" feel requested.
- **Mobile:** A 4-column grid with 16px gutters.
- **Spacing Rhythm:** Based on an 8px scale. To maintain the "sophisticated" feel, vertical padding in sections should be aggressive (spacing units of 10x or 12x), allowing the red and yellow elements room to breathe without crowding the user.

## Elevation & Depth
Hierarchy is achieved through **Low-Contrast Outlines** and **Tonal Layers**. Instead of heavy shadows which can feel "muddy" against vibrant colors, this system uses:

- **Level 0:** Base background (White).
- **Level 1:** Section backgrounds using `surface-tint-red` or `surface-tint-yellow` to subtly group content.
- **Level 2:** Elements like cards use a crisp 1px border (#E2E8F0) rather than a shadow. 
- **Interaction:** When an element is active or hovered, a "Hard Shadow" is used—a 4px offset with no blur in the `secondary` yellow color, creating a modern, flat-depth effect.

## Shapes
The shape language is **Soft (1)**. This slight rounding (4px for small elements, 8px for cards) softens the inherent "urgency" of the red palette, making the interface feel more approachable and "friendly" (optimistic). It prevents the design from feeling too industrial or sharp-edged.

## Components

### Buttons
- **Primary:** Solid #E11D48 (Red) with White text. Use for the single most important action on a page.
- **Secondary:** Solid #FBBF24 (Yellow) with #0F172A (Dark) text. Used for supporting actions to maintain "optimism."
- **Tertiary:** Transparent with a 2px #E11D48 border.

### Input Fields
- Use a minimalist approach: 1px bottom border only (#E2E8F0) that transforms into a 2px Primary Red border on focus. Labels should be `label-md` and placed 8px above the field.

### Cards
- Pure white background, 8px radius, 1px #E2E8F0 border. For "featured" cards, use a 4px left-border accent in Secondary Yellow.

### Chips
- Use the `surface-tint` colors. A red chip uses `surface-tint-red` background with Primary Red text. This keeps the color "present" but not "aggressive."

### Progress Bars
- Background: #F1F5F9. Fill: A gradient from Secondary Yellow to Primary Red to visualize the "energy" of completion.

### Navigation
- High-contrast sidebar (Dark Slate #0F172A) with active states highlighted in Secondary Yellow. This provides a professional "anchor" for the vibrant content area.