import React from 'react';

export interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  hoverEffect?: boolean;
  depthLevel?: 1 | 2 | 3;
  isElevated?: boolean;
  peekMode?: boolean;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = '',
  onClick,
  hoverEffect = true,
  depthLevel = 1,
  isElevated = false,
  peekMode = true,
}) => {
  // Base depth shadows
  const depthClasses =
    depthLevel === 1
      ? 'shadow-[0_14px_36px_rgba(15,23,42,0.08),0_1px_3px_rgba(0,0,0,0.04)]'
      : depthLevel === 2
      ? 'shadow-[0_18px_44px_rgba(15,23,42,0.10),0_1px_3px_rgba(0,0,0,0.05)]'
      : 'shadow-[0_15px_38px_rgba(15,23,42,0.09),0_1px_3px_rgba(0,0,0,0.04)]';

  // Hover and click-elevated states:
  // In peekMode: kept down at rest; comes fully up on hover or click!
  const elevationClasses = peekMode
    ? isElevated
      ? 'translate-y-0 sm:-translate-y-3.5 scale-[1.015] shadow-[0_38px_90px_-15px_rgba(15,23,42,0.32),0_0_0_2px_rgba(16,185,129,0.55)] bg-white/98 border-emerald-500/60 z-[600] ring-4 ring-emerald-500/20'
      : 'translate-y-[calc(100%-54px)] sm:translate-y-[calc(100%-58px)] hover:translate-y-0 sm:hover:-translate-y-3 hover:scale-[1.015] hover:shadow-[0_32px_75px_rgba(15,23,42,0.22)] hover:border-emerald-500/50 hover:bg-white hover:z-[600]'
    : isElevated
    ? '-translate-y-60 sm:-translate-y-72 md:-translate-y-80 lg:-translate-y-[330px] xl:-translate-y-[370px] scale-[1.03] shadow-[0_45px_100px_-15px_rgba(15,23,42,0.40),0_0_0_2.5px_rgba(16,185,129,0.65)] bg-white/98 border-emerald-500/60 z-[600] ring-8 ring-emerald-500/20'
    : hoverEffect
    ? 'hover:-translate-y-5 sm:hover:-translate-y-6 hover:border-emerald-500/40 hover:bg-white hover:shadow-[0_28px_60px_rgba(15,23,42,0.18)]'
    : '';

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-pressed={isElevated}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          if (onClick) onClick();
        }
      }}
      className={`glass-panel group p-4 sm:p-5 lg:p-6 rounded-3xl border border-white/90 bg-white/92 backdrop-blur-2xl transition-all duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] will-change-transform select-none pointer-events-auto cursor-pointer relative ${depthClasses} ${elevationClasses} ${className}`}
    >
      {/* Peek mode subtle cue when card is resting down */}
      {peekMode && !isElevated && (
        <div className="absolute top-3.5 right-5 text-[10px] text-slate-400 font-semibold flex items-center gap-1 group-hover:opacity-0 transition-opacity pointer-events-none">
          <span className="text-emerald-600 font-bold">▲</span>
          <span>Hover to reveal</span>
        </div>
      )}

      {/* Click-elevated visual indicator pill with dismiss cue */}
      {isElevated && (
        <div className="absolute -top-3.5 right-6 z-50 bg-slate-900 text-white text-[10px] font-bold px-3 py-1 rounded-full shadow-lg flex items-center gap-1.5 animate-fade-up border border-slate-700/60">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>Locked In View</span>
          <span className="text-[9px] text-slate-300 font-normal">• Click to lower</span>
        </div>
      )}
      {children}
    </div>
  );
};

export default GlassCard;
