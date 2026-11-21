import React, { useState, useEffect } from 'react';
import { CreditCard, Download, Building2 } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import MetricCard from '../../components/common/MetricCard';
import reconciliationApi from '../../api/reconciliationApi';

export default function SettlementsLedgerPage() {
  const [settlements, setSettlements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [metricsRes, txRes] = await Promise.all([
          reconciliationApi.getSummary(),
          reconciliationApi.getTransactions({ limit: 100 }),
        ]);
        if (metricsRes?.success) setMetrics(metricsRes.data);
        if (txRes?.success) {
          // Group transactions by expected_settlement_date to form daily nodal settlement batches
          const batches = {};
          (txRes.data || []).forEach((t) => {
            const date = t.expected_settlement_date || 'Undetermined';
            if (!batches[date]) {
              batches[date] = {
                date,
                count: 0,
                gross_amount: 0,
                fees: 0,
                tax: 0,
                net_settled: 0,
                status: 'RECONCILED',
              };
            }
            batches[date].count += 1;
            batches[date].gross_amount += Number(t.amount_inr || 0);
            batches[date].fees += Number(t.fee_inr || 0);
            batches[date].tax += Number(t.tax_inr || 0);
            batches[date].net_settled += Number(t.settled_amount_inr || 0);
            if (t.exception_flag === 'YES') batches[date].status = 'NEEDS_REVIEW';
          });
          setSettlements(Object.values(batches));
        }
      } catch (err) {
        console.error('Failed to load settlements:', err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const columns = [
    {
      key: 'date',
      header: 'Settlement Batch Date',
      render: (row) => <span className="font-mono font-semibold text-primary">{row.date}</span>,
    },
    {
      key: 'count',
      header: 'Transaction Count',
      render: (row) => <span className="font-mono">{row.count} txs</span>,
    },
    {
      key: 'gross_amount',
      header: 'Gross Capture',
      render: (row) => <span className="font-mono">₹{row.gross_amount.toFixed(2)}</span>,
    },
    {
      key: 'fees',
      header: 'Gateway Fee',
      render: (row) => <span className="font-mono text-slate-500">₹{row.fees.toFixed(2)}</span>,
    },
    {
      key: 'tax',
      header: 'GST (18%)',
      render: (row) => <span className="font-mono text-slate-500">₹{row.tax.toFixed(2)}</span>,
    },
    {
      key: 'net_settled',
      header: 'Net Settled to Nodal',
      render: (row) => <span className="font-mono font-bold text-navy">₹{row.net_settled.toFixed(2)}</span>,
    },
    {
      key: 'status',
      header: 'Batch Verification',
      render: (row) => <StatusBadge status={row.status} size="sm" />,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold font-outfit text-navy">Settlements Ledger</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Daily gateway clearing batches transferred into merchant nodal bank accounts.
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          title="Total Settled to Bank"
          value={metrics ? `₹${Number(metrics.settled_to_bank_inr).toLocaleString('en-IN')}` : '...'}
          subtitle="Processed deposits"
          icon={Building2}
          accentColor="emerald"
        />
        <MetricCard
          title="Expected Next 2 Days"
          value={metrics ? `₹${Number(metrics.expected_next_2_days_inr).toLocaleString('en-IN')}` : '...'}
          subtitle="T+2 clearing queue"
          icon={CreditCard}
          accentColor="amber"
        />
        <MetricCard
          title="Total Gateway Fees + GST"
          value={metrics ? `₹${Number(metrics.fees_gst_inr).toLocaleString('en-IN')}` : '...'}
          subtitle="Commission deductions"
          icon={CreditCard}
          accentColor="primary"
        />
      </div>

      {/* Settlements Table */}
      <DataTable
        columns={columns}
        data={settlements}
        loading={loading}
        searchPlaceholder="Search settlement date..."
        emptyMessage="No settlement batches found."
      />
    </div>
  );
}
