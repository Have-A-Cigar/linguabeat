export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        lb: {
          bg:       '#07070F',
          surface:  '#0C0C1A',
          card:     '#101022',
          elevated: '#161630',
          border:   '#1E1B38',
        },
      },
      fontFamily: {
        display: ['"Righteous"', 'cursive'],
        body:    ['"Poppins"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
