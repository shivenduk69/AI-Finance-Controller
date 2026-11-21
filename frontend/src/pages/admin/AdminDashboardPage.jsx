import React, { useState, useEffect } from 'react';
import {
  Building2,
  FolderGit2,
  FileSpreadsheet,
  TrendingUp,
  AlertTriangle,
  HelpCircle,
} from 'lucide-react';
import MetricCard from '../../components/common/MetricCard';
import StatusBadge from '../../components/common/StatusBadge';
import AdminVolumeChart from '../../components/charts/AdminVolumeChart';
import adminApi from '../../api/adminApi';

export default function AdminDashboardPage() {
  const [metrics, setMetrics] = useState(null);
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAdminMetrics = async () => {
      try {
        setLoading(true);
        const [metricRes, storeRes] = await Promise.all([
          adminApi.getMetrics(),
          adminApi.getStores(),
        ]);
        if (metricRes?.success) setMetrics(metricRes.data);
        if (storeRes?.success) setStores(storeRes.data || []);
      } catch (err) {
        console.error('Failed to load admin metrics:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAdminMetrics();
  }, []);

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-xl font-bold font-outfit text-navy">Platform Overview & Command Center</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Global reconciliation health, multi-merchant settlement clearing, and exception resolution velocity.
        </p>
      </div>

      {/* 6 Platform KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
        <MetricCard
          title="Merchants"
          value={metrics ? metrics.merchants_count : '...'}
          subtitle="Enterprise platforms"
          icon={Building2}
          accentColor="primary"
          loading={loading}
        />
        <MetricCard
          title="Active Stores"
          value={metrics ? metrics.stores_count : '...'}
          subtitle="Operating locations"
          icon={FolderGit2}
          accentColor="blue"
          loading={loading}
        />
        <MetricCard
          title="Platform TXs"
          value={metrics ? metrics.total_transactions : '...'}
          subtitle="Cross-platform records"
          icon={FileSpreadsheet}
          accentColor="emerald"
          loading={loading}
        />
        <MetricCard
          title="Volume Processed"
          value={metrics ? `₹${Number(metrics.total_volume_inr).toLocaleString('en-IN')}` : '...'}
          subtitle="Gross captured volume"
          icon={TrendingUp}
          accentColor="purple"
          loading={loading}
        />
        <MetricCard
          title="Open Exceptions"
          value={metrics ? metrics.unresolved_exceptions : '...'}
          subtitle="Requiring verification"
          icon={AlertTriangle}
          accentColor="rose"
          loading={loading}
        />
        <MetricCard
          title="Open Tickets"
          value={metrics ? metrics.open_tickets : '...'}
          subtitle="Store inquiries"
          icon={HelpCircle}
          accentColor="amber"
          loading={loading}
        />
      </div>

      {/* Chart Section */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold font-outfit text-navy">Multi-Merchant Volume Trajectory</h3>
            <p className="text-xs text-slate-500">Comparison of daily gross collections across Flipkart and Amazon networks</p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 rounded-lg text-slate-700">
            August 2026 Close
          </span>
        </div>
        <AdminVolumeChart />
      </div>

      {/* Store Performance Matrix */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm">
        <h3 className="text-sm font-bold font-outfit text-navy mb-1">Store Performance Matrix</h3>
        <p className="text-xs text-slate-500 mb-4">Reconciliation match rates and active exceptions by store location</p>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/75 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th className="py-2.5 px-3">Store ID</th>
                <th className="py-2.5 px-3">Store Name</th>
                <th className="py-2.5 px-3">Merchant</th>
                <th className="py-2.5 px-3">City</th>
                <th className="py-2.5 px-3">State</th>
                <th className="py-2.5 px-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {stores.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-400">
                    No stores registered.
                  </td>
                </tr>
              ) : (
                stores.map((s) => (
                  <tr key={s.store_id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-3 font-mono font-semibold text-primary">{s.store_id}</td>
                    <td className="py-2.5 px-3 font-medium text-slate-800">{s.name}</td>
                    <td className="py-2.5 px-3 font-semibold uppercase text-slate-600">{s.merchant_id}</td>
                    <td className="py-2.5 px-3 text-slate-600">{s.city}</td>
                    <td className="py-2.5 px-3 text-slate-500">{s.state}</td>
                    <td className="py-2.5 px-3">
                      <StatusBadge status={s.is_active ? 'completed' : 'failed'} customLabel={s.is_active ? 'ACTIVE' : 'INACTIVE'} size="sm" />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
