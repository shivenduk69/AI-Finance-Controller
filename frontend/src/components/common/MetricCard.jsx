import React from 'react';

export default function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  trendPositive,
  accentColor = 'primary',
  loading = false,
}) {
  const accentBorder = {
    primary: 'border-l-primary',
    emerald: 'border-l-emerald-500',
    rose: 'border-l-rose-500',
    amber: 'border-l-amber-500',
    blue: 'border-l-blue-500',
    purple: 'border-l-purple-500',
  }[accentColor] || 'border-l-primary';

  return (
    <div className={`bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm border-l-4 ${accentBorder} card-hover flex flex-col justify-between`}>
      <div className="flex items-center justify-between text-slate-500 mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</span>
        {Icon && (
          <div className="p-2 rounded-lg bg-slate-50 text-slate-600 border border-slate-100">
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      <div className="my-1">
        {loading ? (
          <div className="h-8 w-28 bg-slate-100 rounded animate-pulse" />
        ) : (
          <div className="text-2xl font-bold font-outfit text-navy tracking-tight">{value}</div>
        )}
      </div>

      {(subtitle || trend) && (
        <div className="mt-2 text-xs text-slate-500 flex items-center gap-1.5">
          {trend && (
            <span className={`font-semibold ${trendPositive ? 'text-emerald-600' : 'text-rose-600'}`}>
              {trend}
            </span>
          )}
          <span>{subtitle}</span>
        </div>
      )}
    </div>
  );
}
