/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    '../../apps/**/templates/**/*.html',
    '../../templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        'scd-primary':      '#1e40af',
        'scd-primary-hover':'#1d3a9e',
        'scd-accent':       '#3b82f6',
        'scd-accent-soft':  '#dbeafe',
        'scd-private':      '#7c3aed',
      },
    },
  },
  plugins: [],
}
