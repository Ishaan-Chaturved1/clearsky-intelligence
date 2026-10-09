import React from 'react';
import { ArrowRight } from 'lucide-react';
import { AlertRecord } from '../types';
import { formatDateTime } from '../utils/formatters';

interface AlertsFeedProps {
  alerts: AlertRecord[];
  onSelectZone?: (zoneId: string) => void;
}

export const AlertsFeed: React.FC<AlertsFeedProps> = ({ alerts, onSelectZone }) => {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-earth-400 bg-warm-100/50 rounded-xl border border-warm-200">
        No high-priority alerts in current window.
      </div>
    );
  }

  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case 'HIGH':
        return 'text-accent-600 bg-accent-500/10 border-accent-500/30';
      case 'MEDIUM':
        return 'text-yellow-700 bg-yellow-50 border-yellow-300';
      default:
        return 'text-earth-500 bg-warm-100 border-warm-300';
    }
  };

  return (
    <div className="space-y-2.5">
      {alerts.slice(0, 5).map((alert) => (
        <div
          key={alert.alert_id}
          className="bg-white rounded-xl p-3 border border-warm-200 hover:border-warm-400 hover:shadow-warm-sm transition-all text-xs"
        >
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <div className="flex items-center gap-1.5">
              <span className={`font-mono text-[9px] font-bold px-1.5 py-0.5 rounded-md border ${getSeverityStyle(alert.severity)}`}>
                {alert.severity}
              </span>
              <span className="font-sentinel font-bold text-earth-900">
                {alert.zone_name}
              </span>
            </div>
            <span className="text-[10px] text-earth-400 font-mono">
              {formatDateTime(alert.created_at)}
            </span>
          </div>

          <p className="text-earth-500 text-[11px] leading-relaxed mb-2">
            {alert.message}
          </p>

          {onSelectZone && (
            <button
              onClick={() => onSelectZone(alert.zone_id)}
              className="text-[10px] font-sans font-semibold text-accent-500 hover:text-accent-600 flex items-center gap-1 transition-colors"
            >
              <span>View Details</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>
      ))}
    </div>
  );
};
