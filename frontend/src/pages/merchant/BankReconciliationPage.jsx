import React, { useState, useEffect } from 'react';
import { Building2, AlertTriangle, CheckCircle2 } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import MetricCard from '../../components/common/MetricCard';
import reconciliationApi from '../../api/reconciliationApi';

export default function BankReconciliationPage() {
  const [bankRecords, setBankRecords] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadBankData = async () => {
      try {
        setLoading(true);
        // We get bank statement data from summary or transactions audit
        const res = await reconciliationApi.getSummary();
        // Create standard side-by-side view for August 2026 dates
        const sampleDays = [
          { date: '10-08-2026', expected: 6805.21, actual: 6705.21, diff: -100.0, ref: 'UTR892189021', status: 'SETTLEMENT_AMOUNT_MISMATCH' },
          { date: '11-08-2026', expected: 8940.50, actual: 8940.50, diff: 0.0, ref: 'UTR892189022', status: 'RECONCILED' },
          { date: '12-08-2026', expected: 12450.00, actual: 12450.00, diff: 0.0, ref: 'UTR892189023', status: 'RECONCILED' },
          { date: '13-08-2026', expected: 7850.30, actual: 7850.30, diff: 0.0, ref: 'UTR892189024', status: 'RECONCILED' },
          { date: '14-08-2026', expected: 15300.00, actual: 15300.00, diff: 0.0, ref: 'UTR892189025', status: 'RECONCILED' },
          { date: '15-08-2026', expected: 9200.00, actual: 9200.00, diff: 0.0, ref: 'UTR892189026', status: 'RECONCILED' },
          { date: '16-08-2026', expected: 11400.00, actual: 11400.00, diff: 0.0, ref: 'UTR892189027', status: 'RECONCILED' },
          { date: '17-08-2026', expected: 13500.00, actual: 13500.00, diff: 0.0, ref: 'UTR892189028', status: 'RECONCILED' },
          { date: '18-08-2026', expected: 4407.40, actual: 0.00, diff: -4407.40, ref: 'MISSING', status: 'MISSING_BANK_CREDIT' },
          { date: '19-08-2026', expected: 10800.00, actual: 10800.00, diff: 0.0, ref: 'UTR892189029', status: 'RECONCILED' },
          { date: '20-08-2026', expected: 14200.00, actual: 14200.00, diff: 0.0, ref: 'UTR892189030', status: 'RECONCILED' },
          { date: '21-08-2026', expected: 11500.00, actual: 11500.00, diff: 0.0, ref: 'UTR892189031', status: 'RECONCILED' },
          { date: '22-08-2026', expected: 5350.00, actual: 0.00, diff: -5350.00, ref: 'MISSING', status: 'MISSING_BANK_CREDIT' },
          { date: '23-08-2026', expected: 15200.00, actual: 15000.00, diff: -200.0, ref: 'UTR892189032', status: 'SETTLEMENT_AMOUNT_MISMATCH' },
        ];
        setBankRecords(sampleDays);
      } catch (err) {
        console.error('Failed to load bank reconciliation data:', err);
      } finally {
        setLoading(false);
      }
    };
    loadBankData();
  }, []);

  const totalDiscrepancies = bankRecords.filter((b) => b.status !== 'RECONCILED').length;
  const totalActual = bankRecords.reduce((acc, b) => acc + b.actual, 0);
  const totalExpected = bankRecords.reduce((acc, b) => acc + b.expected, 0);

  const columns = [
    {
      key: 'date',
      header: 'Settlement Date',
      render: (row) => <span className="font-mono font-semibold text-primary">{row.date}</span>,
    },
    {
      key: 'ref',
      header: 'Bank Reference (UTR)',
      render: (row) => <span className="font-mono text-xs text-slate-600">{row.ref}</span>,
    },
    {
      key: 'expected',
      header: 'Expected Deposit (₹)',
      render: (row) => <span className="font-mono">₹{row.expected.toFixed(2)}</span>,
    },
    {
      key: 'actual',
      header: 'Actual Bank Credit (₹)',
      render: (row) => (
        <span className={`font-mono font-bold ${row.actual === 0 ? 'text-rose-600' : 'text-navy'}`}>
          ₹{row.actual.toFixed(2)}
        </span>
      ),
    },
    {
      key: 'diff',
      header: 'Variance (₹)',
      render: (row) => (
        <span
          className={`font-mono font-semibold ${
            Math.abs(row.diff) > 0.05 ? 'text-rose-600' : 'text-emerald-600'
          }`}
        >
          {row.diff > 0 ? `+₹${row.diff.toFixed(2)}` : row.diff < 0 ? `-₹${Math.abs(row.diff).toFixed(2)}` : '₹0.00'}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Audit Match Status',
      render: (row) => <StatusBadge status={row.status} size="sm" />,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-xl font-bold font-outfit text-navy">Bank Settlement Reconciliation</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Side-by-side audit of expected daily gateway nodal clearing vs. actual statement deposits.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          title="Bank Credited Total"
          value={`₹${totalActual.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`}
          subtitle="Direct bank statement deposits"
          icon={Building2}
          accentColor="emerald"
        />
        <MetricCard
          title="Expected Settlement Total"
          value={`₹${totalExpected.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`}
          subtitle="Net nodal batch expectations"
          icon={Building2}
          accentColor="primary"
        />
        <MetricCard
          title="Settlement Exceptions"
          value={totalDiscrepancies}
          subtitle="Missing deposits or amount offsets"
          icon={AlertTriangle}
          accentColor="rose"
        />
      </div>

      {/* Bank Reconciliation Table */}
      <DataTable
        columns={columns}
        data={bankRecords}
        loading={loading}
        searchPlaceholder="Search settlement date or UTR..."
      />
    </div>
  );
}
