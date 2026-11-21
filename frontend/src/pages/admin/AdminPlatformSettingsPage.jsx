import React, { useState, useEffect } from 'react';
import { Sliders, Save, CheckCircle2, ShieldAlert } from 'lucide-react';
import adminApi from '../../api/adminApi';

export default function AdminPlatformSettingsPage() {
  const [feeRate, setFeeRate] = useState(0.02);
  const [gstRate, setGstRate] = useState(0.18);
  const [payoutFee, setPayoutFee] = useState(5.0);
  const [settlementDelay, setSettlementDelay] = useState(2);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setLoading(true);
        const res = await adminApi.getConfig();
        if (res?.success && res.data) {
          const cfg = res.data;
          if (cfg.gateway_fee_rate) setFeeRate(Number(cfg.gateway_fee_rate));
          if (cfg.gst_rate) setGstRate(Number(cfg.gst_rate));
          if (cfg.payout_fixed_fee) setPayoutFee(Number(cfg.payout_fixed_fee));
          if (cfg.settlement_delay_days) setSettlementDelay(Number(cfg.settlement_delay_days));
        }
      } catch (err) {
        console.error('Failed to load platform config:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchConfig();
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      setErrorMsg('');
      setSuccessMsg('');
      await adminApi.updateConfig({
        gateway_fee_rate: feeRate,
        gst_rate: gstRate,
        payout_fixed_fee: payoutFee,
        settlement_delay_days: settlementDelay,
      });
      setSuccessMsg('Platform mathematical parameters updated and synchronized.');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to update configuration.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-bold font-outfit text-navy">Platform Mathematical Parameters</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Global benchmark rates governing the 7-rule reconciliation engine, tax auditor, and cash forecasting.
        </p>
      </div>

      {successMsg && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <form onSubmit={handleSave} className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm space-y-6">
        <h3 className="text-sm font-bold font-outfit text-navy uppercase tracking-wider flex items-center gap-2">
          <Sliders className="w-4 h-4 text-primary" />
          <span>Reconciliation Engine Invariants</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 text-xs">
          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Gateway Commission Fee Benchmark Rate
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                step="0.001"
                min="0"
                max="0.2"
                value={feeRate}
                onChange={(e) => setFeeRate(parseFloat(e.target.value))}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono text-slate-800"
              />
              <span className="text-xs font-bold text-slate-500 font-mono">({(feeRate * 100).toFixed(1)}%)</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Default 0.02 (2.0%) benchmark fee on captured digital transactions.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Statutory GST Rate on Gateway Fee
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                step="0.01"
                min="0"
                max="0.5"
                value={gstRate}
                onChange={(e) => setGstRate(parseFloat(e.target.value))}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono text-slate-800"
              />
              <span className="text-xs font-bold text-slate-500 font-mono">({(gstRate * 100).toFixed(0)}%)</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Statutory 18% GST charged on processing fee lines.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Fixed Payout Transfer Fee (₹)
            </label>
            <input
              type="number"
              step="0.5"
              min="0"
              value={payoutFee}
              onChange={(e) => setPayoutFee(parseFloat(e.target.value))}
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono text-slate-800"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Flat fee charged per outgoing vendor/partner payout record.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Nodal Bank Settlement Delay (Days)
            </label>
            <input
              type="number"
              step="1"
              min="0"
              max="10"
              value={settlementDelay}
              onChange={(e) => setSettlementDelay(parseInt(e.target.value, 10))}
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono text-slate-800"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Expected bank credit timeline for payment captures (T+2).
            </p>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-100 flex items-center justify-end">
          <button
            type="submit"
            disabled={saving || loading}
            className="px-5 py-2.5 bg-primary hover:bg-primary-dark text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Updating...' : 'Save Configuration'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
