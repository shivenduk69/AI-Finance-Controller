import React, { useState, useEffect } from 'react';
import { Receipt, AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import MetricCard from '../../components/common/MetricCard';
import aiApi from '../../api/aiApi';

export default function TaxAuditPage() {
  const [taxSummary, setTaxSummary] = useState(null);
  const [auditedRecords, setAuditedRecords] = useState([]);
  const [loading, setLoading] = useState(true);

  const runAudit = async () => {
    try {
      setLoading(true);
      const res = await aiApi.taxAudit();
      if (res?.success) {
        setTaxSummary(res.summary);
        setAuditedRecords(res.audited_records || []);
      }
    } catch (err) {
      console.error('Failed to run tax audit:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runAudit();
  }, []);

  const columns = [
    {
      key: 'transaction_id',
      header: 'Transaction ID',
      render: (row) => <span className="font-mono font-semibold text-primary">{row.transaction_id}</span>,
    },
    {
      key: 'type',
      header: 'Type',
      render: (row) => <span className="text-xs uppercase font-medium">{row.type}</span>,
    },
    {
      key: 'recipient_type',
      header: 'Recipient Entity',
      render: (row) => <span className="text-xs font-semibold text-slate-700">{row.recipient_type}</span>,
    },
    {
      key: 'amount_inr',
      header: 'Gross Amount',
      render: (row) => <span className="font-mono">₹{Number(row.amount_inr).toFixed(2)}</span>,
    },
    {
      key: 'actual_gst',
      header: 'GST on Fee (18%)',
      render: (row) => (
        <span className={`font-mono ${Math.abs(row.gst_variance || 0) > 0.05 ? 'text-rose-600 font-bold' : ''}`}>
          ₹{Number(row.actual_gst).toFixed(2)}
        </span>
      ),
    },
    {
      key: 'actual_tds',
      header: 'TDS (Sec 194-O)',
      render: (row) => (
        <span className={`font-mono ${Math.abs(row.tds_variance || 0) > 0.05 ? 'text-rose-600 font-bold' : ''}`}>
          ₹{Number(row.actual_tds).toFixed(2)}
        </span>
      ),
    },
    {
      key: 'tax_status',
      header: 'Tax Compliance',
      render: (row) => <StatusBadge status={row.tax_status === 'OK' ? 'AUTO_RESOLVED' : 'NEEDS_REVIEW'} customLabel={row.tax_status} size="sm" />,
    },
    {
      key: 'audit_comments',
      header: 'Auditor Findings',
      render: (row) => <span className="text-xs text-slate-600 truncate max-w-xs block">{row.audit_comments}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold font-outfit text-navy">Section 194-O TDS & GST Compliance Audit</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Verification of 18% GST deductions on gateway fees and statutory Section 194-O TDS withholdings.
          </p>
        </div>
        <button
          onClick={runAudit}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-primary hover:bg-primary-dark rounded-lg transition-all shadow-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Rerun Tax Audit</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <MetricCard
          title="Tax Compliance Score"
          value={taxSummary ? `${taxSummary.tax_compliance_pct}%` : '...'}
          subtitle={`${taxSummary?.total_tax_discrepancies || 0} variances flagged`}
          icon={CheckCircle2}
          accentColor="emerald"
          loading={loading}
        />
        <MetricCard
          title="Total Audited Records"
          value={taxSummary ? taxSummary.total_audited_records : '...'}
          subtitle="Gateway transactions"
          icon={Receipt}
          accentColor="primary"
          loading={loading}
        />
        <MetricCard
          title="GST Fee Variances"
          value={taxSummary ? taxSummary.gst_anomalies_count : '...'}
          subtitle="Off by > ₹0.05 on 18%"
          icon={AlertTriangle}
          accentColor="rose"
          loading={loading}
        />
        <MetricCard
          title="Section 194-O Variances"
          value={taxSummary ? taxSummary.tds_anomalies_count : '...'}
          subtitle="Under/over withholdings"
          icon={AlertTriangle}
          accentColor="amber"
          loading={loading}
        />
      </div>

      {/* Section 194-O Statutory Rates Guide */}
      <div className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-sm">
        <h3 className="text-xs font-bold font-outfit uppercase tracking-wider text-navy mb-2">
          Active Statutory Withholding Rules (CBDT Section 194-O)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="font-semibold text-slate-700">Individual E-Commerce Participant:</span>
            <p className="text-primary font-mono font-bold mt-0.5">1.0% TDS</p>
            <p className="text-[11px] text-slate-500 mt-1">Applicable on gross sale value for resident individuals.</p>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="font-semibold text-slate-700">Corporate Entity Participant:</span>
            <p className="text-primary font-mono font-bold mt-0.5">2.0% TDS</p>
            <p className="text-[11px] text-slate-500 mt-1">Applicable on corporate and institutional seller payouts.</p>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="font-semibold text-slate-700">Non-Resident Participant:</span>
            <p className="text-slate-600 font-mono font-bold mt-0.5">Exempt / Withheld Separately</p>
            <p className="text-[11px] text-slate-500 mt-1">Exempt under domestic Section 194-O provisions.</p>
          </div>
        </div>
      </div>

      {/* Audited Tax Table */}
      <DataTable
        columns={columns}
        data={auditedRecords}
        loading={loading}
        searchPlaceholder="Search by transaction ID or comments..."
        emptyMessage="No tax records audited."
      />
    </div>
  );
}
