import React, { useState, useRef, useEffect } from 'react';
import { Info } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from './tooltip';

interface StatProps {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode | string | number;
  badge?: React.ReactNode;
  info?: string;
  className?: string;
  style?: React.CSSProperties;
  iconBgClass?: string;
}

/**
 * Stat Card UI component for displaying a statistic with icon, label, value, and optional badge.
 */
const Stat: React.FC<StatProps> = ({
  icon,
  label,
  value,
  badge,
  info,
  className = '',
  style = {},
  iconBgClass = 'bg-gray-100'
}) => {
  const [tooltipOpen, setTooltipOpen] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);

  // Handle click outside and keyboard events to close tooltip
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent | TouchEvent) => {
      if (tooltipRef.current && !tooltipRef.current.contains(event.target as Node)) {
        setTooltipOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setTooltipOpen(false);
      }
    };

    if (tooltipOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('touchstart', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [tooltipOpen]);

  return (
    <div
      className={`card rounded-xl shadow-md bg-white flex flex-col justify-between w-48 h-28 ${className} px-3 py-2 mb-1`}
      style={{ ...style }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className={`inline-flex items-center justify-center w-8 h-8 rounded-lg ${iconBgClass} text-[1rem] p-1.5`}>
          {icon}
        </span>
      </div>
      <span className="block text-gray-500 text-xs font-medium mb-1 text-left">
        <span className="inline-flex items-center">
          {label}
          {info && (
            <span ref={tooltipRef} style={{ position: 'relative', display: 'inline-block', marginLeft: '4px', top: '-0.5em' }}>
              <TooltipProvider>
                <Tooltip open={tooltipOpen}>
                  <TooltipTrigger asChild>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setTooltipOpen(!tooltipOpen);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          e.stopPropagation();
                          setTooltipOpen(!tooltipOpen);
                        }
                      }}
                      className="inline-block text-gray-400 hover:text-primary cursor-pointer rounded p-0.5 focus:outline-none"
                      aria-label={`Info about ${label}`}
                      aria-expanded={tooltipOpen}
                    >
                      <Info size={12} />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs">{info}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </span>
          )}
        </span>
      </span>
      <div className="flex items-center">
        <span className="text-xl font-extrabold text-gray-900 tracking-tight flex-1 text-left">{value}</span>
        {badge && (
          <span className="ml-1">{badge}</span>
        )}
      </div>
    </div>
  );
};

/**
 * Skeleton loading state for the Stat component.
 * Displays placeholder content with pulse animation while data is loading.
 */
const StatSkeleton: React.FC = () => (
  <div className="card rounded-2xl bg-white flex flex-col justify-between w-48 h-28 p-3 animate-pulse">
    <div className="flex items-center gap-2 mb-2">
      <div className="w-8 h-8 bg-gray-200 rounded-lg"></div>
    </div>
    <div className="block text-gray-500 text-xs font-medium mb-1 text-left">
      <div className="h-3 bg-gray-200 rounded w-3/4"></div>
    </div>
    <div className="flex items-center">
      <div className="h-5 bg-gray-200 rounded w-1/2 flex-1"></div>
      <div className="h-4 bg-gray-200 rounded w-8 ml-1"></div>
    </div>
  </div>
);

export default Stat;
export { StatSkeleton };