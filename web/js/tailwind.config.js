/* Tailwind CDN runtime configuration — must load after the CDN script. */
tailwind.config = {
  theme: {
    extend: {
      colors: {
        ink:    '#0c0a09',
        coal:   '#141110',
        paper:  '#f3ece1',
        muted:  '#a39a8d',
        coral:  '#ff5436',
        ember:  '#ff8a5b',
        lime:   '#c8f54e',
        sand:   '#2a2522',
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', 'sans-serif'],
        mono:    ['"Space Mono"', 'monospace'],
        serif:   ['"Newsreader"', 'serif'],
      },
    },
  },
};
