/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        client: '#0099ff',
        server: '#009900',
        error: '#990000',
        textSecondary: '#6e6e7f',
        border: '#e7e7e7',
        bgSecondary: '#ececf1',
        buttonText: '#101010',
        buttonHover: '#d8d8d8',
        buttonAction: '#404040',
        buttonDisabled: '#999',
        iconRed: '#cc0000',
        iconGreen: '#009900',
        iconGrey: '#909090',
      }
    },
  },
  plugins: [],
}

