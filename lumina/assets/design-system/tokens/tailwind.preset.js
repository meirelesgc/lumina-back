// Preset Tailwind opcional para interfaces web LUMINA.
// Uso: presets: [require('./tokens/tailwind.preset.js')]
module.exports = {
  theme: {
    extend: {
      colors: {
        lumina: {
          laranja: '#f8580a', ouro: '#d9ae21', teal: '#0e90a0', claro: '#efefef',
          'laranja-claro': '#f77948', 'ouro-escuro': '#b58d1d', 'teal-escuro': '#0b6970',
          tinta: '#2b2b2b', 'laranja-texto': '#b04406'
        }
      },
      fontFamily: {
        titulo: ['Barlow', 'Arial Narrow', 'Arial', 'sans-serif'],
        corpo: ['Lexend', 'Arial', 'sans-serif']
      }
    }
  }
};
