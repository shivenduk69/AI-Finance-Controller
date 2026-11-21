import React from 'react';
import { Settings, ShieldCheck, Database, Building2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function StoreSettingsPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Title */}
      <div>
        <h2 className="text-xl font-bold font-outfit text-navy">Store Settings & Parameters</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Active operational parameters, commission benchmarks, and tenant configuration.
        </p>
      </div>

      {/* Store Identity Card */}
      <div className="p-6 bg-white rounded-xl border border-slate-200/80 shadow-sm space-y-4">
        <h3 className="text-sm font-bold font-outfit text-navy uppercase tracking-wider flex items-center gap-2">
          <Building2 className="w-4 h-4 text-primary" />
          <span>Tenant Store Identity</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-slate-500 font-semibold uppercase text-[10px] block">Merchant Organization</span>
            <span className="text-sm font-bold text-navy font-outfit uppercase mt-0.5 block">
              {user?.merchant_id || 'Global Enterprise'}
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-slate-500 font-semibold uppercase text-[10px] block">Assigned Store ID</span>
            <span className="text-sm font-mono font-bold text-primary mt-0.5 block">
              {user?.store_id || 'All Stores Managed'}
            </span>
          </div>
        </div>
      </div>

      {/* Active Commission & Tax Invariants Card */}
      <div className="p-6 bg-white rounded-xl border border-slate-200/80 shadow-sm space-y-4">
        <h3 className="text-sm font-bold font-outfit text-navy uppercase tracking-wider flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-primary" />
          <span>Mathematical Invariant Benchmarks</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-slate-500 font-semibold">Standard Gateway Fee Rate:</span>
            <p className="text-base font-mono font-bold text-navy mt-1">2.0%</p>
            <p className="text-[11px] text-slate-500 mt-1">Benchmark fee calculated on gross captured payments.</p>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-slate-500 font-semibold">GST on Processing Fees:</span>
            <p className="text-base font-mono font-bold text-navy mt-1">18.0%</p>
            <p className="text-[11px] text-slate-500 mt-1">Statutory Goods & Services Tax on gateway fee lines.</p>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-slate-500 font-semibold">Standard Payout Fixed Fee:</span>
            <p className="text-base font-mono font-bold text-navy mt-1">₹5.00 / txn</p>
            <p className="text-[11px] text-slate-500 mt-1">Flat nodal transfer fee on vendor/merchant payouts.</p>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-slate-500 font-semibold">Nodal Clearing Settlement Delay:</span>
            <p className="text-base font-mono font-bold text-primary mt-1">T+2 Business Days</p>
            <p className="text-[11px] text-slate-500 mt-1">Standard payment settlement cycle to bank statements.</p>
          </div>
        </div>

        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
          <p className="font-semibold">Central Administrative Governance</p>
          <p className="text-[11px] text-amber-700 mt-0.5">
            Parameters are centrally managed by the platform administrator. Store managers have read-only visibility into active calculation rates.
          </p>
        </div>
      </div>
    </div>
  );
}
