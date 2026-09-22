// Mismo dibujo que _balanza() en gui/components/icons.py (app de
// escritorio), pasado a SVG en un lienzo de 24x24 -- que las dos apps se
// reconozcan como el mismo producto.
export function IconoBalanza({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 2.4v18.24M3.84 5.76h16.32M7.2 20.64h9.6" />
      <path d="M3.84 5.76L0.96 10.08M3.84 5.76l2.88 4.32M0.96 10.08a2.88 1.92 0 0 0 5.76 0" />
      <path d="M20.16 5.76l-2.88 4.32M20.16 5.76l2.88 4.32M17.28 10.08a2.88 1.92 0 0 0 5.76 0" />
    </svg>
  )
}
