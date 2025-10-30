/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        telegram: {
          bg: 'var(--tg-theme-bg-color)',
          text: 'var(--tg-theme-text-color)',
          hint: 'var(--tg-theme-hint-color)',
          link: 'var(--tg-theme-link-color)',
          button: 'var(--tg-theme-button-color)',
          'button-text': 'var(--tg-theme-button-text-color)',
        }
      },
      animation: {
        'swipe-out-up': 'swipeOutUp 0.3s ease-in-out forwards',
        'swipe-out-down': 'swipeOutDown 0.3s ease-in-out forwards',
        'card-enter': 'cardEnter 0.3s ease-out',
        'bounce-gentle': 'bounce 1s ease-in-out infinite',
      },
      keyframes: {
        swipeOutUp: {
          '0%': { transform: 'translateY(0) rotate(0deg)', opacity: '1' },
          '100%': { transform: 'translateY(-100vh) rotate(-30deg)', opacity: '0' }
        },
        swipeOutDown: {
          '0%': { transform: 'translateY(0) rotate(0deg)', opacity: '1' },
          '100%': { transform: 'translateY(100vh) rotate(30deg)', opacity: '0' }
        },
        cardEnter: {
          '0%': { transform: 'scale(0.8) translateY(20px)', opacity: '0' },
          '100%': { transform: 'scale(1) translateY(0)', opacity: '1' }
        }
      }
    },
  },
  plugins: [],
}
