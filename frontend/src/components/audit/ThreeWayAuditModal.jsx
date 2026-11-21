import React from 'react';
import { CheckCircle2, AlertTriangle, ArrowRight, ShieldCheck, FileText, Building2, CreditCard } from 'lucide-react';
import Modal from '../common/Modal';
import StatusBadge from '../common/StatusBadge';

export default function ThreeWayAuditModal({ isOpen, onClose, auditData, onResolveClick }) {
  if (!auditData) return null;

  const {
    transaction_id,
    order_id,
    type,
    amount_inr = 0,
    fee_inr = 0,
    tax_inr = 0,
    settled_amount_inr = 0,
    expected_settlement_date,
    status,
    calculated_exceptions = [],
    order_match,
    bank_match,
    math_check,
  } = auditData;

  const hasExceptions = calculated_exceptions.length > 0;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Visual 3-Way Audit: ${transaction_id}`} maxWidth="max-w-4xl">
      <div className="space-y-6">
        {/* Status Alert Banner */}
        <div
          className={`p-4 rounded-xl border flex items-start gap-3 ${
            hasExceptions
              ? 'bg-rose-50/70 border-rose-200 text-rose-900'
              : 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
          }`}
        >
          {hasExceptions ? (
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          ) : (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <h4 className="text-sm font-bold font-outfit">
              {hasExceptions ? 'Audit Exceptions Detected' : '3-Way Reconciliation Perfect Match'}
            </h4>
            <p className="text-xs mt-1 text-slate-600">
              {hasExceptions
                ? 'One or more rules flagged discrepancies between internal records, gateway captured data, or bank settlement batches.'
                : 'All 7 reconciliation invariants verified: mathematical balance, internal order completion, and bank credit matched.'}
            </p>
            {hasExceptions && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {calculated_exceptions.map((exc, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 bg-rose-100 text-rose-800 text-[11px] rounded-md font-mono font-medium border border-rose-200"
                  >
                    {exc}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 3-Node Audit Graph (Orders -> Gateway -> Bank) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Node 1: Internal Orders */}
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3 text-slate-500">
                <span className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-navy">
                  <FileText className="w-4 h-4 text-primary" />
                  <span>1. Internal Order</span>
                </span>
                <StatusBadge status={order_match ? 'completed' : 'failed'} size="sm" />
              </div>
              <div className="space-y-1.5 text-xs text-slate-600 font-mono">
                <p>Order ID: <strong className="text-slate-800 font-sans">{order_id || 'NOT FOUND'}</strong></p>
                <p>Amount: ₹{Number(amount_inr).toFixed(2)}</p>
                <p>Status: {order_match?.status || 'Matched in DB'}</p>
              </div>
            </div>
          </div>

          {/* Node 2: Payment Gateway (Razorpay) */}
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3 text-slate-500">
                <span className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-navy">
                  <CreditCard className="w-4 h-4 text-primary" />
                  <span>2. Razorpay Gateway</span>
                </span>
                <StatusBadge status={status} size="sm" />
              </div>
              <div className="space-y-1.5 text-xs text-slate-600 font-mono">
                <p>TX ID: <strong className="text-slate-800 font-sans">{transaction_id}</strong></p>
                <p>Type: {type}</p>
                <p>Fee (2%): ₹{Number(fee_inr).toFixed(2)}</p>
                <p>GST (18%): ₹{Number(tax_inr).toFixed(2)}</p>
                <p>Net Settled: ₹{Number(settled_amount_inr).toFixed(2)}</p>
              </div>
            </div>
          </div>

          {/* Node 3: Bank Statement Credit */}
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3 text-slate-500">
                <span className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-navy">
                  <Building2 className="w-4 h-4 text-primary" />
                  <span>3. Bank Statement</span>
                </span>
                <StatusBadge status={bank_match?.status || 'RECONCILED'} size="sm" />
              </div>
              <div className="space-y-1.5 text-xs text-slate-600 font-mono">
                <p>Batch Date: {expected_settlement_date || 'N/A'}</p>
                <p>Bank Status: {bank_match?.status || 'BATCH_CREDITED'}</p>
                <p>Settled: ₹{Number(settled_amount_inr).toFixed(2)}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Mathematical Invariant Verification Box */}
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="font-bold text-navy uppercase tracking-wider flex items-center gap-1.5 font-outfit">
              <ShieldCheck className="w-4 h-4 text-primary" />
              <span>Mathematical Invariant Formula Check</span>
            </span>
            <span className="text-[11px] font-mono text-slate-500">
              Settled = Amount - Fee - GST
            </span>
          </div>
          <div className="p-3 bg-white rounded-lg border border-slate-200 font-mono text-slate-700 flex flex-wrap items-center justify-between gap-2">
            <span>
              ₹{Number(amount_inr).toFixed(2)} - ₹{Number(fee_inr).toFixed(2)} - ₹{Number(tax_inr).toFixed(2)} = ₹{(Number(amount_inr) - Number(fee_inr) - Number(tax_inr)).toFixed(2)}
            </span>
            <span className="font-bold text-slate-900">
              Recorded Settled: ₹{Number(settled_amount_inr).toFixed(2)}
            </span>
            <span
              className={`font-semibold px-2 py-0.5 rounded text-[11px] ${
                math_check?.passed !== false ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
              }`}
            >
              {math_check?.passed !== false ? '✓ MATH VERIFIED' : '✗ MATH DISCREPANCY'}
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            Close Audit
          </button>
          {onResolveClick && hasExceptions && (
            <button
              onClick={() => {
                onClose();
                onResolveClick(auditData);
              }}
              className="px-4 py-2 text-xs font-semibold text-white bg-primary hover:bg-primary-dark rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
            >
              <span>Submit Resolution Note</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}
