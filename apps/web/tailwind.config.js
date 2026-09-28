/**
 * Zomato-style dark theme.
 *
 * Token NAMES are unchanged from the previous light theme on purpose: every
 * page already speaks in semantic tokens (surface, on-surface, primary), so
 * retheming is a change of values rather than a rewrite of markup. Anything
 * that still looks wrong after this is markup that hardcoded a colour instead
 * of using a token, which is worth finding.
 *
 * The palette is read off the Zomato app: a near-black page, one red that does
 * all the brand work, a green reserved for status, and a gold used once. The
 * greys are true neutrals - Zomato's chrome has no colour cast, and a tinted
 * grey next to that red reads as a mistake.
 */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Zomato red. One accent, used for brand, primary actions and nothing
        // decorative - on a near-black page it is loud enough that spending it
        // on ornament would leave nothing for the buttons.
        primary: '#E23744',
        'primary-hover': '#C72C38',
        'primary-accent': '#FF7A85',
        // Tint on dark is a translucent wash, not a pastel: a light pink block
        // would punch a hole in the page.
        'primary-tint': 'rgba(226, 55, 68, 0.14)',
        'on-primary': '#FFFFFF',

        // Ink, descending: headings, body, metadata.
        'on-surface': '#FFFFFF',
        'on-surface-medium': '#C7C7C7',
        'on-surface-variant': '#9C9C9C',

        // Surfaces, ascending by elevation. Dark themes lift with lighter
        // fills rather than shadow, which is invisible on black.
        surface: '#0D0D0D',
        'surface-container-lowest': '#1C1C1C',
        'surface-container': '#2A2A2A',
        'surface-container-high': '#383838',
        outline: '#3A3A3A',
        'outline-variant': '#2A2A2A',

        // Status. The green is the rating-pill green; it means "good/open" and
        // is never used as a second brand colour.
        success: '#267E3E',
        // Zomato's Gold amber. Kept as the warning tone rather than as a
        // second brand colour - there is no membership here to spend it on.
        warning: '#E5B45B',
        error: '#FF5A5F',
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'display-hero': ['44px', { lineHeight: '50px', fontWeight: '800', letterSpacing: '-0.02em' }],
        'display-hero-mobile': ['30px', { lineHeight: '36px', fontWeight: '800', letterSpacing: '-0.02em' }],
        'headline-lg': ['30px', { lineHeight: '38px', fontWeight: '700', letterSpacing: '-0.01em' }],
        'headline-md': ['22px', { lineHeight: '30px', fontWeight: '700', letterSpacing: '-0.01em' }],
        'headline-sm': ['17px', { lineHeight: '24px', fontWeight: '700' }],
        'body-lg': ['17px', { lineHeight: '26px', fontWeight: '400' }],
        'body-md': ['15px', { lineHeight: '23px', fontWeight: '400' }],
        'body-sm': ['13px', { lineHeight: '19px', fontWeight: '400' }],
        'label-lg': ['15px', { lineHeight: '20px', fontWeight: '600' }],
        'label-md': ['13px', { lineHeight: '18px', fontWeight: '600' }],
        'label-sm': ['11px', { lineHeight: '15px', fontWeight: '700' }],
        // The muted, widely-tracked section heading above each row.
        eyebrow: ['12px', { lineHeight: '16px', fontWeight: '700', letterSpacing: '0.08em' }],
      },
      spacing: {
        gutter: '1.5rem',
        'gutter-mobile': '0.75rem',
        margin: '2rem',
        'margin-mobile': '1rem',
        'space-xs': '0.25rem',
        'space-sm': '0.5rem',
        'space-md': '1rem',
        'space-lg': '1.5rem',
        'space-xl': '2.5rem',
      },
      borderRadius: {
        DEFAULT: '0.75rem',
        md: '0.875rem',
        lg: '1rem',
        xl: '1.25rem',
      },
      boxShadow: {
        // Shadow barely reads on #0D0D0D, so it is kept for the things that
        // genuinely float above the page and elevation is otherwise carried by
        // the surface ramp above.
        card: 'none',
        'card-hover': '0 8px 28px rgba(0, 0, 0, 0.55)',
        overlay: '0 2px 12px rgba(0, 0, 0, 0.4)',
        sheet: '0 18px 44px rgba(0, 0, 0, 0.6)',
        nav: '0 6px 28px rgba(0, 0, 0, 0.7)',
      },
      maxWidth: {
        content: '1200px',
      },
    },
  },
  plugins: [],
};
