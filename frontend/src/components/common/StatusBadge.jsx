import React from 'react';

const STATUS_CONFIGS = {
  // Reconciliation & Resolution
  AUTO_RESOLVED: { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'Auto Resolved' },
  RESOLVED: { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'Resolved' },
  NEEDS_REVIEW: { bg: 'bg-rose-50 text-rose-700 border-rose-200', label: 'Needs Review' },
  PENDING_ADMIN: { bg: 'bg-amber-50 text-amber-700 border-amber-200', label: 'Pending Admin' },
  REOPENED: { bg: 'bg-orange-50 text-orange-700 border-orange-200', label: 'Reopened' },
  
  // Transaction Gateway Statuses
  captured: { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'Captured' },
  refunded: { bg: 'bg-blue-50 text-blue-700 border-blue-200', label: 'Refunded' },
  failed: { bg: 'bg-rose-50 text-rose-700 border-rose-200', label: 'Failed' },
  disputed: { bg: 'bg-purple-50 text-purple-700 border-purple-200', label: 'Disputed' },
  processed: { bg: 'bg-teal-50 text-teal-700 border-teal-200', label: 'Processed' },
  completed: { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'Completed' },
  
  // Bank Settlement Statuses
  RECONCILED: { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'Reconciled' },
  MISSING_BANK_CREDIT: { bg: 'bg-rose-50 text-rose-700 border-rose-200', label: 'Missing Bank Credit' },
  SETTLEMENT_AMOUNT_MISMATCH: { bg: 'bg-amber-50 text-amber-700 border-amber-200', label: 'Amount Mismatch' },
  
  // Severity Levels
  HIGH: { bg: 'bg-rose-100 text-rose-800 border-rose-300 font-bold', label: 'HIGH' },
  MEDIUM: { bg: 'bg-amber-100 text-amber-800 border-amber-300 font-semibold', label: 'MEDIUM' },
  LOW: { bg: 'bg-slate-100 text-slate-700 border-slate-300', label: 'LOW' },
  
  // Ticket Status
  OPEN: { bg: 'bg-blue-50 text-blue-700 border-blue-200', label: 'Open' },
  PENDING: { bg: 'bg-amber-50 text-amber-700 border-amber-200', label: 'Pending' },
  CLOSED: { bg: 'bg-slate-100 text-slate-600 border-slate-200', label: 'Closed' },
};

export default function StatusBadge({ status, customLabel, size = 'md' }) {
  const normStatus = String(status || '').trim();
  const config = STATUS_CONFIGS[normStatus] || {
    bg: 'bg-slate-100 text-slate-700 border-slate-200',
    label: normStatus || 'Unknown',
  };

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center rounded-full border ${sizeClasses} font-medium tracking-wide ${config.bg}`}
    >
      <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-current opacity-70" />
      {customLabel || config.label}
    </span>
  );
}
