---
name: Print & Scan Hub
colors:
  surface: '#fbf8ff'
  surface-dim: '#d9d9e6'
  surface-bright: '#fbf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f2ff'
  surface-container: '#ededfa'
  surface-container-high: '#e7e7f4'
  surface-container-highest: '#e2e1ef'
  on-surface: '#191b24'
  on-surface-variant: '#434656'
  inverse-surface: '#2e303a'
  inverse-on-surface: '#f0effd'
  outline: '#747688'
  outline-variant: '#c4c5d9'
  surface-tint: '#124af0'
  primary: '#0040e0'
  on-primary: '#ffffff'
  primary-container: '#2e5bff'
  on-primary-container: '#efefff'
  inverse-primary: '#b8c3ff'
  secondary: '#505f76'
  on-secondary: '#ffffff'
  secondary-container: '#d0e1fb'
  on-secondary-container: '#54647a'
  tertiary: '#993100'
  on-tertiary: '#ffffff'
  tertiary-container: '#c24100'
  on-tertiary-container: '#ffece6'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dde1ff'
  primary-fixed-dim: '#b8c3ff'
  on-primary-fixed: '#001356'
  on-primary-fixed-variant: '#0035be'
  secondary-fixed: '#d3e4fe'
  secondary-fixed-dim: '#b7c8e1'
  on-secondary-fixed: '#0b1c30'
  on-secondary-fixed-variant: '#38485d'
  tertiary-fixed: '#ffdbcf'
  tertiary-fixed-dim: '#ffb59b'
  on-tertiary-fixed: '#380d00'
  on-tertiary-fixed-variant: '#812800'
  background: '#fbf8ff'
  on-background: '#191b24'
  surface-variant: '#e2e1ef'
  soft-blue-bg: '#F8FAFC'
  scan-teal: '#0D9488'
  status-success: '#22C55E'
  status-error: '#EF4444'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Be Vietnam Pro
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Be Vietnam Pro
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Be Vietnam Pro
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-sm:
    fontFamily: Be Vietnam Pro
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-padding-mobile: 1.25rem
  container-padding-desktop: 2.5rem
  gutter: 1rem
  section-gap: 2rem
---

## Brand & Style
The brand personality is helpful, intuitive, and modern, moving away from industrial rigidity toward a welcoming home-office companion. The target audience includes remote workers, students, and creative hobbyists who value ease of use over technical complexity. The UI should evoke a sense of "digital calm"—making the chores of document management feel light and effortless.

The design system adopts a **Minimalist** style infused with **Soft Modernism**. This approach prioritizes heavy whitespace to reduce visual clutter, a gentle color palette to lower stress, and subtle transitions that feel fluid. While the structure remains professional and organized, the sharp edges of the previous industrial look are replaced with a "human-centric" geometry that feels tactile and approachable.

## Colors
The palette is centered on "Fresh Clarity," using a range of soft blues and slates to create a clean, airy environment.

*   **Primary (Action Blue):** A vibrant but friendly blue used for the most important actions like "Start Print" or "Confirm."
*   **Secondary (Slate):** Used for secondary navigation and utility icons, providing a grounded contrast to the airy background.
*   **Neutral (Cool White/Gray):** The foundation of the system. We use ample white space (`#FFFFFF`) and very light blue-tinted grays for backgrounds to maintain a "clean desk" feel.
*   **Named Accents:** "Scan Teal" is used specifically for scanning workflows to provide a distinct visual cue for different hardware functions. Success and Error states use refined, less aggressive shades of green and red.

## Typography
The typography transition moves from the rigid Inter to a pairing of **Plus Jakarta Sans** and **Be Vietnam Pro**. This combination offers a soft, rounded aesthetic that feels welcoming and contemporary.

*   **Headlines:** Plus Jakarta Sans provides a friendly, optimistic geometric structure for all display and title levels.
*   **Body & Labels:** Be Vietnam Pro ensures high legibility with a warm, approachable character.
*   **Scaling:** On mobile devices, large headlines scale down to prevent awkward word breaks, while body text remains generous at 16px to ensure accessibility in varied home lighting.

## Layout & Spacing
The layout follows a **Fluid Grid** model with an emphasis on "Visual Breathing Room." By moving to an 8px base unit, the UI feels less dense and more open than the previous industrial version.

*   **Rhythm:** Use `section-gap` (32px) to clearly separate functional blocks (e.g., File Preview vs. Printer Settings).
*   **Margins:** Generous side margins (20px on mobile, 40px+ on desktop) prevent the content from feeling cramped.
*   **Responsiveness:**
    *   **Mobile:** Single column with stacked controls for easy thumb reach.
    *   **Tablet/Desktop:** A 12-column grid where the document preview occupies a 7-column span and controls reside in a 5-column side panel.

## Elevation & Depth
Depth is conveyed through **Tonal Layers** and **Ambient Shadows** to create a soft, physical presence.

*   **Surface Tiering:** The main background is a soft gray-blue, while primary interaction cards are pure white. This subtle contrast guides the eye to the active content.
*   **Shadows:** Use very soft, diffused shadows (0% offset, 15px blur, 5% opacity) to lift cards off the background. This avoids the "flat" industrial look and makes elements feel like they are floating on a clean surface.
*   **Glassmorphism:** Use subtle backdrop blurs (8px) on top navigation bars and floating action buttons to maintain context and add a modern, premium touch.

## Shapes
The design system utilizes a **Rounded (0.5rem)** shape language to reinforce the friendly, consumer-oriented aesthetic.

*   **Buttons & Inputs:** Use the standard `rounded` (8px) for a soft but structured feel.
*   **Cards & Modals:** Use `rounded-lg` (16px) or `rounded-xl` (24px) for large surfaces to make them feel inviting.
*   **Selection States:** Active selection rings should follow the curvature of the element with a 2px offset.

## Components

### Buttons
*   **Primary:** High-pill roundedness with a subtle gradient (Primary Blue to a slightly lighter tint). White text.
*   **Secondary:** Slate-gray text on a very light gray background. No borders.
*   **Interaction:** 10% darkening on hover; subtle scale-down (0.98) on click for tactile feedback.

### Cards
Cards are the primary container for printer status and document previews. They feature `rounded-lg` corners, a 1px soft border, and a gentle ambient shadow. Avoid "heavy" borders; let the white surface do the work.

### Inputs & Selectors
Form fields use a soft gray background (`soft-blue-bg`) rather than white to distinguish them from the card surface. Labels are placed inside the field area for a more compact, modern look when not focused.

### Status Chips
Status indicators for "Ink Level" or "Ready" should use pill shapes with a soft tinted background and a darker text color (e.g., light green background with dark green text) rather than high-contrast solid blocks.

### Floating Action Button (FAB)
The core action (usually "Scan" or "Add File") is a large, circular FAB with a primary blue background and a prominent shadow, positioned at the bottom right for easy access.