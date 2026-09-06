import {defineTheme} from '@astryxdesign/core/theme';

export const teslaTheme = defineTheme({
  name: 'tesla',

  color: {accent: '#127436', neutralStyle: 'cool', contrast: 'standard'},

  typography: {
    scale: {base: 16, ratio: 1.2},
    heading: {weight: 'bold', weights: {1: 'bold', 2: 'bold', 3: 'semibold'}},
  },

  radius: {base: 4, multiplier: 1},

  tokens: {
    '--color-background-body': ['#FFFFFF', '#171A20'],
    '--color-background-surface': ['#F0F0F2', '#222226'],
    '--color-background-card': ['#F0F0F2', '#222226'],
    '--color-background-muted': ['#E7E7EA', '#1B1E23'],
    '--color-background-popover': ['#FFFFFF', '#2A2A2E'],
    '--color-text-primary': ['#171A20', '#FFFFFF'],
    '--color-text-secondary': ['#5C5E62', '#9B9B9B'],
    '--color-text-disabled': ['#A6A8AC', '#5A5C60'],
    // Brand green. The seed #16A34A only reaches 3.30:1 on white and 2.67:1 on
    // muted, so light mode uses #127436 — the same hue (142deg) and saturation
    // darkened until it clears AA on the palest surface. The dark slot is
    // re-derived independently: #17AB4E is the lightest step on that same hue
    // ladder that stays inside the 5.2-5.8:1 band on the three dark
    // backgrounds. Lifting #127436 by the ratio that produced #FF5A5A from
    // #CC0000 would land past 10:1 and read as neon.
    '--color-text-accent': ['#127436', '#17AB4E'],
    '--color-accent': ['#127436', '#127436'],
    '--color-on-accent': ['#FFFFFF', '#FFFFFF'],
    '--color-border': ['#00000000', '#00000000'],
    '--color-border-emphasized': ['#D4D5D8', '#3A3C41'],
    // These default to a warm-brown tint (from the old red accent seed) in
    // both schemes, which clashes with the cool Tesla grays — overridden
    // fully in both light and dark so nothing keeps a stray red/brown tint
    // now that the accent is green.
    '--color-icon-primary': ['#171A20', '#FFFFFF'],
    '--color-icon-secondary': ['#5C5E62', '#9B9B9B'],
    '--color-icon-disabled': ['#A6A8AC', '#5A5C60'],
    '--color-neutral': ['#171D181A', '#DCE5DD33'],
    '--color-overlay': ['#171D1866', '#171D1899'],
    '--color-track': ['#D8D9DC', '#3A3C41'],
    '--color-skeleton': ['#D8D9DC', '#3A3C41'],
    '--color-background-inverted': ['#171A20', '#FFFFFF'],
    // --color-accent stays true green (#127436) in dark mode for fills, but
    // that's only 2.97:1 against dark backgrounds - too low for a focus
    // ring (non-text UI needs 3:1). --color-text-accent's dark slot
    // (#17AB4E, 5.79:1) is already the lightened variant built for exactly
    // this contrast problem, so the focus ring uses that instead of the
    // accent fill color.
    '--focus-outline-color': 'var(--color-text-accent)',
    '--font-family-body':
      'var(--font-inter), system-ui, -apple-system, sans-serif',
    '--font-family-heading':
      'var(--font-inter), system-ui, -apple-system, sans-serif',
  },

  components: {
    section: {
      base: {
        borderRadius: 'var(--radius-container)',
        boxShadow: 'var(--shadow-low)',
      },
    },
    button: {
      base: {
        borderRadius: 'var(--radius-full)',
        fontWeight: 'var(--font-weight-medium)',
      },
    },
    'segmented-control': {
      base: {
        borderRadius: 'var(--radius-full)',
        backgroundColor: 'var(--color-background-muted)',
        borderWidth: '0',
      },
    },
    'segmented-control-item': {
      base: {borderRadius: 'var(--radius-full)'},
    },
    selector: {
      base: {
        backgroundColor: 'var(--color-background-muted)',
        borderColor: 'transparent',
      },
    },
  },
});
