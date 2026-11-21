import React, { useState, useEffect } from 'react';
import { CreditCard, Building2, TrendingUp } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import MetricCard from '../../components/common/MetricCard';
import adminApi from '../../api/adminApi';
import reconciliationApi from '../../api/reconciliationApi';

export default function AdminSettlementsPage() {
  const [batches, setBatches] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadSettlements = async () => {
      try {
        setLoading(true);
        const [metricRes, txRes] = await Promise.all([
          adminApi.getMetrics(),
          reconciliationApi.getTransactions({ limit: 120 }),
        ]);
        if (metricRes?.success) setMetrics(metricRes.data);
        if (txRes?.success) {
          const map = {};
          (txRes.data || []).forEach((t) => {
            const key = `${t.merchant_id}_${t.expected_settlement_date || 'N/A'}`;
            if (!map[key]) {
              map[key] = {
                id: key,
                merchant: t.merchant_id,
                date: t.expected_settlement_date || 'N/A',
                count: 0,
                volume: 0,
                net_nodal: 0,
                status: 'RECONCILED',
              };
            }
            map[key].count += 1;
            map[key].volume += Number(t.amount_inr || 0);
            map[key].net_nodal += Number(t.settled_amount_inr || 0);
            if (t.exception_flag === 'YES') map[key].status = 'NEEDS_REVIEW';
          });
          setBatches(Object.values(map));
        }
      } catch (err) {
        console.error('Failed to load admin settlements:', err);
      } finally {
        setLoading(false);
      }
    };
    loadSettlements();
  }, []);

  const columns = [
    {
      key: 'merchant',
      header: 'Merchant Organization',
      render: (row) => <span className="font-bold uppercase text-slate-800">{row.merchant}</span>,
    },
    {
      key: 'date',
      header: 'Nodal Clearing Date',
      render: (row) => <span className="font-mono font-semibold text-primary">{row.date}</span>,
    },
    {
      key: 'count',
      header: 'Total Transactions',
      render: (row) => <span className="font-mono">{row.count} payments</span>,
    },
    {
      key: 'volume',
      header: 'Gross Volume',
      render: (row) => <span className="font-mono">₹{row.volume.toFixed(2)}</span>,
    },
    {
      key: 'net_nodal',
      header: 'Net Settled to Bank',
      render: (row) => <span className="font-mono font-bold text-navy">₹{row.net_nodal.toFixed(2)}</span>,
    },
    {
      key: 'status',
      header: 'Nodal Status',
      render: (row) => <StatusBadge status={row.status} size="sm" />,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold font-outfit text-navy">Platform Settlements Oversight</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Central clearing monitoring across merchant nodal accounts, Razorpay batch transfers, and nodal bank credits.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          title="Total Clearing Volume"
          value={metrics ? `₹${Number(metrics.total_volume_inr).toLocaleString('en-IN')}` : '...'}
          subtitle="All platform settlement batches"
          icon={TrendingUp}
          accentColor="primary"
        />
        <MetricCard
          title="Merchants Covered"
          value={metrics ? metrics.merchants_count : '...'}
          subtitle="Flipkart & Amazon networks"
          icon={Building2}
          accentColor="emerald"
        />
        <MetricCard
          title="Active Clearing Batches"
          value={batches.length}
          subtitle="Scheduled nodal clearing days"
          icon={CreditCard}
          accentColor="blue"
        />
      </div>

      <DataTable
        columns={columns}
        data={batches}
        loading={loading}
        searchPlaceholder="Search settlement date or merchant..."
      />
    </div>
  );
}
