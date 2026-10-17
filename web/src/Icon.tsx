const paths = {
  home: ['M3 10 12 3l9 7v11H3Z', 'M9 21V12h6v9'],
  grid: ['M3 3h7v7H3ZM14 3h7v7h-7ZM3 14h7v7H3ZM14 14h7v7h-7Z'],
  layers: ['m12 3 10 5-10 5L2 8Z', 'm2 12 10 5 10-5M2 16l10 5 10-5'],
  spread: ['M3 4h18M3 12h18M3 20h18', 'm9 7 3-3 3 3M9 17l3 3 3-3'],
  eye: ['M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z', 'M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0'],
  eyeOff: ['m3 3 18 18M10.6 5.1A12 12 0 0 1 12 5c6 0 10 7 10 7a21 21 0 0 1-3 3.8M6 6.5A22 22 0 0 0 2 12s4 7 10 7c2 0 3.8-.7 5.3-1.7'],
  focus: ['M8 3H3v5M16 3h5v5M21 16v5h-5M8 21H3v-5', 'M8 8h8v8H8Z'],
  reset: ['M3 11a9 9 0 1 1 2 7M3 4v7h7'],
  arrow: ['M5 12h14m-6-6 6 6-6 6'],
  close: ['m6 6 12 12M6 18 18 6'],
  info: ['M12 11v6M12 7h.01', 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'],
  sun: ['M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5', 'M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0'],
  chevron: ['m9 5 7 7-7 7'],
} satisfies Record<string, string[]>

export type IconName = keyof typeof paths

export default function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {paths[name].map((d) => <path d={d} key={d} />)}
  </svg>
}
