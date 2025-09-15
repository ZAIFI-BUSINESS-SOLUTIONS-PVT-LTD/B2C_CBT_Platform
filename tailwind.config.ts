import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./client/index.html", "./client/src/**/*.{js,jsx,ts,tsx}"],
  theme: {
  	extend: {
  		fontFamily: {
  			sans: [
  				'Tenorite',
  				'sans-serif'
  			]
  		},
  		colors: {
  			background: 'hsl(0, 0%, 99%)',
  			foreground: 'hsl(240, 9%, 14%)',
  			card: {
  				DEFAULT: 'hsl(0, 0%, 100%)',
  				foreground: 'hsl(240, 9%, 14%)'
  			},
  			popover: {
  				DEFAULT: 'hsl(0, 0%, 100%)',
  				foreground: 'hsl(240, 9%, 14%)'
  			},
  			primary: {
  				DEFAULT: 'hsl(220, 90%, 56%)',
  				foreground: 'hsl(0, 0%, 100%)'
  			},
  			secondary: {
  				DEFAULT: 'hsl(240, 4%, 95%)',
  				foreground: 'hsl(240, 6%, 10%)'
  			},
  			muted: {
  				DEFAULT: 'hsl(240, 4%, 95%)',
  				foreground: 'hsl(240, 4%, 46%)'
  			},
  			accent: {
  				DEFAULT: 'hsl(240, 4%, 95%)',
  				foreground: 'hsl(240, 6%, 10%)'
  			},
  			destructive: {
  				DEFAULT: 'hsl(0, 84%, 60%)',
  				foreground: 'hsl(0, 0%, 98%)'
  			},
  			border: 'hsl(240, 6%, 90%)',
  			input: 'hsl(240, 6%, 90%)',
  			ring: 'hsl(220, 90%, 56%)',
  			chart: {
  				'1': 'hsl(12, 76%, 61%)',
  				'2': 'hsl(173, 58%, 39%)',
  				'3': 'hsl(197, 37%, 24%)',
  				'4': 'hsl(43, 74%, 66%)',
  				'5': 'hsl(27, 87%, 67%)'
  			},
  			sidebar: {
  				DEFAULT: 'hsl(0, 0%, 100%)',
  				foreground: 'hsl(240, 9%, 14%)',
  				primary: 'hsl(220, 90%, 56%)',
  				'primary-foreground': 'hsl(0, 0%, 100%)',
  				accent: 'hsl(240, 4%, 95%)',
  				'accent-foreground': 'hsl(240, 6%, 10%)',
  				border: 'hsl(240, 6%, 90%)',
  				ring: 'hsl(220, 90%, 56%)'
  			}
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			},
  			shine: {
  				'0%': {
  					'background-position': '0% 0%'
  				},
  				'50%': {
  					'background-position': '100% 100%'
  				},
  				to: {
  					'background-position': '0% 0%'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out',
  			shine: 'shine var(--duration) infinite linear'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate"), require("@tailwindcss/typography")],
} satisfies Config;
