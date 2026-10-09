import React from 'react';
import { CheckCircle2, Target, AlertOctagon, HelpCircle, Wrench } from 'lucide-react';
import { DecisionType } from '../types';
import { getDecisionBadgeInfo } from '../utils/formatters';

interface StatusBadgeProps {
  decision?: DecisionType | null;
  priority?: number | null;
  showPriority?: boolean;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  decision,
  priority,
  showPriority = true,
  size = 'md'
}) => {
  const badgeInfo = getDecisionBadgeInfo(decision);

  const getIcon = () => {
    switch (decision) {
      case 'TARGETED_INTERVENTION_RECOMMENDED':
        return <Target className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />;
      case 'INTERVENTION_RECOMMENDED':
        return <CheckCircle2 className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />;
      case 'INTERVENTION_DISCOURAGED':
      case 'INTERVENTION_NOT_RECOMMENDED':
        return <AlertOctagon className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />;
      case 'ALTERNATIVE_DUST_CONTROL_SUGGESTED':
        return <Wrench className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />;
      case 'ADVISORY_ONLY':
      default:
        return <HelpCircle className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />;
    }
  };

  const getBadgeClass = () => {
    switch (decision) {
      case 'TARGETED_INTERVENTION_RECOMMENDED':
        return 'bg-sage-500/15 text-sage-800 border-sage-500/40';
      case 'INTERVENTION_RECOMMENDED':
        return 'bg-sage-500/10 text-sage-700 border-sage-500/30';
      case 'INTERVENTION_DISCOURAGED':
      case 'INTERVENTION_NOT_RECOMMENDED':
        return 'bg-rose-500/10 text-rose-700 border-rose-500/30';
      case 'ALTERNATIVE_DUST_CONTROL_SUGGESTED':
        return 'bg-amber-500/15 text-amber-800 border-amber-500/40';
      case 'ADVISORY_ONLY':
      default:
        return 'bg-warm-200 text-earth-600 border-warm-300';
    }
  };

  const isRecommended = decision === 'INTERVENTION_RECOMMENDED' || decision === 'TARGETED_INTERVENTION_RECOMMENDED';

  return (
    <div className="inline-flex items-center gap-1.5 flex-wrap">
      <span
        className={`inline-flex items-center gap-1.5 font-sans font-medium border rounded-xl transition-colors ${getBadgeClass()} ${
          size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'
        }`}
      >
        {getIcon()}
        <span>{badgeInfo.label}</span>
      </span>

      {showPriority && isRecommended && priority && (
        <span
          className="font-mono font-semibold px-2 py-0.5 rounded-xl text-[11px] bg-accent-500/10 text-accent-600 border border-accent-500/30 flex items-center gap-1"
          title={`Priority Level ${priority} (1-5)`}
        >
          <span>P{priority}</span>
          <span className="text-[10px] text-accent-400">/5</span>
        </span>
      )}
    </div>
  );
};
