import React from 'react';
import { LucideIcon } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  badge?: string;
  badgeColor?: 'emerald' | 'rose' | 'amber' | 'sky' | 'orange' | 'slate';
  accentBorder?: boolean;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  badge,
  badgeColor = 'slate',
  accentBorder = false
}) => {
  const getBadgeStyle = () => {
    switch (badgeColor) {
      case 'emerald':
        return 'bg-sage-500/10 text-sage-600 border-sage-500/30';
      case 'rose':
        return 'bg-accent-500/10 text-accent-600 border-accent-500/30';
      case 'amber':
        return 'bg-yellow-50 text-yellow-700 border-yellow-300';
      case 'sky':
        return 'bg-sage-500/10 text-sage-600 border-sage-500/30';
      case 'orange':
        return 'bg-accent-500/10 text-accent-600 border-accent-500/30';
      default:
        return 'bg-warm-200 text-earth-500 border-warm-300';
    }
  };

  return (
    <div
      className={`bg-white rounded-2xl p-4 border transition-all duration-200 hover:shadow-warm hover:-translate-y-0.5 ${
        accentBorder ? 'border-accent-400/40 shadow-warm-sm' : 'border-warm-200'
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-sans font-medium text-earth-400 uppercase tracking-wider">
          {title}
        </span>
        <div className="w-7 h-7 rounded-xl bg-warm-100 border border-warm-200 flex items-center justify-center text-earth-400">
          <Icon className="w-3.5 h-3.5" />
        </div>
      </div>

      <div className="flex items-baseline gap-2 mt-1">
        <span className="font-sentinel font-bold text-2xl text-earth-900 font-tabular tracking-tight">
          {value}
        </span>
        {badge && (
          <span className={`text-[10px] font-mono font-medium px-1.5 py-0.5 rounded-md border ${getBadgeStyle()}`}>
            {badge}
          </span>
        )}
      </div>

      {subtitle && (
        <p className="font-clarendon text-[11px] text-earth-500 mt-1.5 line-clamp-1">
          {subtitle}
        </p>
      )}
    </div>
  );
};
