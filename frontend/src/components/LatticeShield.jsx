import React from 'react';

export function LatticeShieldIcon({ className = "w-6 h-6", glowing = false }) {
  return (
    <div className={`relative inline-flex items-center justify-center ${glowing ? 'filter drop-shadow-[0_0_12px_rgba(124,108,240,0.6)]' : ''}`}>
      <svg
        className={className}
        viewBox="0 0 32 36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Shield Outer Contour */}
        <path
          d="M16 2L3 7V17.5C3 25.5 8.5 32.5 16 34.5C23.5 32.5 29 25.5 29 17.5V7L16 2Z"
          stroke="#7C6CF0"
          strokeWidth="2"
          strokeLinejoin="round"
          fill="rgba(124, 108, 240, 0.08)"
        />
        {/* Lattice Grid Lines */}
        <path
          d="M16 4V32M7 11H25M5 19H27M8 27H24"
          stroke="#7C6CF0"
          strokeWidth="1.2"
          strokeOpacity="0.7"
          strokeDasharray="2 1.5"
        />
        {/* Center Node */}
        <circle cx="16" cy="19" r="2.5" fill="#7C6CF0" />
      </svg>
    </div>
  );
}

export function GlowingLatticeGraphic() {
  return (
    <div className="relative w-72 h-72 sm:w-88 sm:h-88 flex items-center justify-center">
      {/* Background Radial Glow */}
      <div className="absolute inset-0 rounded-full bg-[#7C6CF0]/15 blur-3xl" />
      <div className="absolute w-48 h-48 rounded-full bg-[#7C6CF0]/25 blur-2xl animate-pulse" />

      {/* Outer Rotating/Pulsing Geometric Rings */}
      <div className="absolute inset-4 rounded-3xl border border-[#232333] rotate-12 opacity-40 lattice-grid" />
      <div className="absolute inset-8 rounded-2xl border border-[#7C6CF0]/30 -rotate-6" />

      {/* Hero Lattice Shield */}
      <div className="relative z-10 flex flex-col items-center">
        <LatticeShieldIcon className="w-28 h-28" glowing />
        <div className="mt-4 px-3 py-1 rounded-full bg-[#12121A] border border-[#232333] text-xs font-mono tracking-widest text-[#7C6CF0] uppercase">
          Defense Kernel Active
        </div>
      </div>
    </div>
  );
}

