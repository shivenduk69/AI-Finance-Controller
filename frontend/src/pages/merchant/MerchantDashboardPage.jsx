import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileSpreadsheet,
  AlertTriangle,
  Building2,
  TrendingUp,
  Clock,
  ArrowRight,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import MetricCard from '../../components/common/MetricCard';
import StatusBadge from '../../components/common/StatusBadge';
import ReconciliationTrendChart from '../../components/charts/ReconciliationTrendChart';
import ThreeWayAuditModal from '../../components/audit/ThreeWayAuditModal';
import ResolutionSubmitModal from '../../components/audit/ResolutionSubmitModal';
import reconciliationApi from '../../api/reconciliationApi';
import exceptionApi from '../../api/exceptionApi';

export default function MerchantDashboardPage() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recentExceptions, setRecentExceptions] = useState([]);
  const [selectedAuditTx, setSelectedAuditTx] = useState(null);
  const [resolveTarget, setResolveTarget] = useState(null);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [metricsRes, excRes] = await Promise.all([
        reconciliationApi.getSummary(),
        exceptionApi.getExceptions({ status: 'NEEDS_REVIEW', limit: 5 }),
      ]);
      if (metricsRes?.success) setMetrics(metricsRes.data);
      if (excRes?.success) setRecentExceptions(excRes.data?.slice(0, 5) || []);
    } catch (err) {
      console.error('Failed to load merchant dashboard metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleRowAudit = async (txId) => {
    try {
      const res = await reconciliationApi.getTransactionAudit(txId);
      if (res?.success) {
        setSelectedAuditTx(res.data);
      }
    } catch (err) {
      console.error('Failed to load transaction audit:', err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold font-outfit text-navy">Store Reconciliation Dashboard</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Continuous 3-way audit across order ledgers, gateway captures, and bank settlement batches.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/exceptions')}
            className="px-3.5 py-1.5 text-xs font-semibold text-white bg-primary hover:bg-primary-dark rounded-lg transition-all shadow-sm flex items-center gap-1.5"
          >
            <span>Resolve Exceptions ({metrics?.needs_review_count || 0})</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 5 KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          title="Total Transactions"
          value={metrics ? metrics.total_transactions : '...'}
          subtitle={`${metrics?.total_payments_processed || 0} payments captured`}
          icon={FileSpreadsheet}
          accentColor="primary"
          loading={loading}
        />
        <MetricCard
          title="Auto-Match Rate"
          value={metrics ? `${metrics.auto_match_accuracy_pct}%` : '...'}
          subtitle={`${metrics?.auto_resolved_count || 0} resolved`}
          icon={CheckCircle2}
          accentColor="emerald"
          trend="+0.5%"
          trendPositive={true}
          loading={loading}
        />
        <MetricCard
          title="Active Exceptions"
          value={metrics ? metrics.needs_review_count : '...'}
          subtitle="Requires controller sign-off"
          icon={AlertTriangle}
          accentColor="rose"
          loading={loading}
        />
        <MetricCard
          title="Settled to Bank"
          value={metrics ? `₹${Number(metrics.settled_to_bank_inr).toLocaleString('en-IN')}` : '...'}
          subtitle="Direct nodal statement credit"
          icon={Building2}
          accentColor="blue"
          loading={loading}
        />
        <MetricCard
          title="Expected T+2 Queue"
          value={metrics ? `₹${Number(metrics.expected_next_2_days_inr).toLocaleString('en-IN')}` : '...'}
          subtitle="Pending bank deposit"
          icon={Clock}
          accentColor="amber"
          loading={loading}
        />
      </div>

      {/* Main Grid: Chart + Close Readiness Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Reconciliation Trend Chart */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold font-outfit text-navy">Reconciliation Volume Trend</h3>
              <p className="text-xs text-slate-500">Daily matched volume vs. flagged audit exceptions</p>
            </div>
            <span className="text-xs px-2.5 py-1 bg-slate-100 text-slate-700 rounded-lg font-medium">
              August 2026 Batch
            </span>
          </div>
          <ReconciliationTrendChart />
        </div>

        {/* Daily Close Workflow Status Card */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold font-outfit text-navy">Financial Close Status</h3>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                  (metrics?.needs_review_count || 0) === 0
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-amber-100 text-amber-800'
                }`}
              >
                {(metrics?.needs_review_count || 0) === 0 ? 'READY TO CLOSE' : 'PENDING ACTIONS'}
              </span>
            </div>

            <div className="space-y-3 mt-4 text-xs">
              <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg">
                <span className="text-slate-600">Gateway Captured:</span>
                <strong className="text-slate-800 font-mono">₹{Number(metrics?.gross_collections_inr || 0).toFixed(2)}</strong>
              </div>
              <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg">
                <span className="text-slate-600">Total Gateway Fees + GST:</span>
                <strong className="text-slate-800 font-mono">₹{Number(metrics?.fees_gst_inr || 0).toFixed(2)}</strong>
              </div>
              <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg">
                <span className="text-slate-600">Bank Statement Total:</span>
                <strong className="text-slate-800 font-mono">₹{Number(metrics?.settled_to_bank_inr || 0).toFixed(2)}</strong>
              </div>
            </div>

            {/* AI Executive Insight */}
            <div className="mt-4 p-3 bg-primary/5 border border-primary/20 rounded-xl text-xs">
              <div className="flex items-center gap-1.5 font-bold text-primary mb-1">
                <Sparkles className="w-3.5 h-3.5" />
                <span>AI Controller Insight</span>
              </div>
              <p className="text-slate-600 text-[11px] leading-relaxed">
                {(metrics?.needs_review_count || 0) > 0
                  ? `There are ${metrics?.needs_review_count} active exceptions pending verification. The primary drivers are missing internal order IDs and bank credit timing offsets.`
                  : 'All transaction sets and daily bank settlements are mathematically balanced. Store batch is clear for daily close.'}
              </p>
            </div>
          </div>

          <button
            onClick={() => navigate('/reports')}
            className="mt-4 w-full py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold rounded-lg border border-slate-200 transition-colors"
          >
            Export Close Summary Report
          </button>
        </div>
      </div>

      {/* Bottom Section: Top Active Exceptions Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold font-outfit text-navy">Priority Exception Queue</h3>
            <p className="text-xs text-slate-500">Unresolved discrepancies flagged by 3-way matching rules</p>
          </div>
          <button
            onClick={() => navigate('/exceptions')}
            className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
          >
            <span>View All Exceptions</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/75 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th className="py-2.5 px-3">TX ID</th>
                <th className="py-2.5 px-3">Order ID</th>
                <th className="py-2.5 px-3">Amount</th>
                <th className="py-2.5 px-3">Discrepancy</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {recentExceptions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-400">
                    No active exceptions in queue.
                  </td>
                </tr>
              ) : (
                recentExceptions.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-3 font-mono font-medium text-primary">
                      {item.transaction_id}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-600">
                      {item.order_id || '—'}
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      ₹{Number(item.amount_inr || 0).toFixed(2)}
                    </td>
                    <td className="py-2.5 px-3 text-slate-700 max-w-xs truncate">
                      {item.anomaly_type || 'Discrepancy'}
                    </td>
                    <td className="py-2.5 px-3">
                      <StatusBadge status={item.severity || 'HIGH'} size="sm" />
                    </td>
                    <td className="py-2.5 px-3">
                      <StatusBadge status={item.status || 'NEEDS_REVIEW'} size="sm" />
                    </td>
                    <td className="py-2.5 px-3 text-right space-x-2">
                      <button
                        onClick={() => handleRowAudit(item.transaction_id)}
                        className="text-xs text-primary font-medium hover:underline"
                      >
                        Audit
                      </button>
                      <button
                        onClick={() => setResolveTarget(item)}
                        className="text-xs text-emerald-600 font-medium hover:underline"
                      >
                        Resolve
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modals */}
      <ThreeWayAuditModal
        isOpen={Boolean(selectedAuditTx)}
        onClose={() => setSelectedAuditTx(null)}
        auditData={selectedAuditTx}
        onResolveClick={(item) => setResolveTarget(item)}
      />

      <ResolutionSubmitModal
        isOpen={Boolean(resolveTarget)}
        onClose={() => setResolveTarget(null)}
        exceptionItem={resolveTarget}
        onSuccess={loadDashboardData}
      />
    </div>
  );
}
