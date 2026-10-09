/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        /* Sentinel — expressive editorial slab serif for headings */
        sentinel: ['"Sentinel"', '"Besley"', '"Playfair Display"', 'Georgia', 'serif'],
        /* Clarendon — sturdy archetypal slab-serif for editorial body & identity */
        clarendon: ['"Clarendon"', '"Besley"', '"Source Serif 4"', 'Georgia', 'serif'],
        heading: ['"Sentinel"', '"Clarendon"', '"Besley"', 'Georgia', 'serif'],
        body: ['"Clarendon"', '"Source Serif 4"', '"Besley"', 'Georgia', 'serif'],
        /* Clean sans for UI controls & metadata */
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      colors: {
        /* Warm cream/sand backgrounds */
        warm: {
          50:  '#FFFDF7',
          100: '#FFF9EC',
          150: '#FFF5E0',
          200: '#FFEFD1',
          300: '#FFE4B5',
          400: '#FFD699',
          500: '#E8C88A',
          600: '#C9A96B',
          700: '#9C7D4A',
          800: '#6B5530',
          900: '#3D2F1A',
          950: '#1F170C',
        },
        /* Bright accent — vivid coral / terracotta */
        accent: {
          300: '#FF9F7E',
          400: '#FF8362',
          500: '#F06B42',
          600: '#D95430',
          700: '#B5401F',
        },
        /* Teal / sage secondary accent */
        sage: {
          300: '#8BD4C0',
          400: '#5FBFA7',
          500: '#3DA88E',
          600: '#2D8870',
          700: '#1E6955',
        },
        /* Deep warm brown for text and panels */
        earth: {
          100: '#F5EDE3',
          200: '#E8DDD0',
          300: '#D4C5B3',
          400: '#A08B72',
          500: '#7A6651',
          600: '#5C4A39',
          700: '#3E3025',
          800: '#2A1F16',
          900: '#1A130D',
        },
        /* Status colours with warm tonality */
        status: {
          rec:      '#3DA88E',
          disc:     '#D95430',
          caution:  '#E5A83E',
          advisory: '#A08B72',
          info:     '#5FBFA7',
        },
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        'warm-sm': '0 1px 3px rgba(157,122,78,0.08)',
        'warm':    '0 4px 14px rgba(157,122,78,0.10)',
        'warm-lg': '0 10px 30px rgba(157,122,78,0.12)',
        'warm-xl': '0 20px 50px rgba(157,122,78,0.15)',
      },
    },
  },
  plugins: [],
}
