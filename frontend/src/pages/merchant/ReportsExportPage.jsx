import React, { useState } from 'react';
import { Download, FileSpreadsheet, AlertTriangle, Receipt, Building2, CheckCircle2 } from 'lucide-react';
import reconciliationApi from '../../api/reconciliationApi';
import exceptionApi from '../../api/exceptionApi';
import aiApi from '../../api/aiApi';

export default function ReportsExportPage() {
  const [downloading, setDownloading] = useState(null);
  const [downloadSuccess, setDownloadSuccess] = useState('');

  const triggerDownload = (filename, content, type = 'text/csv') => {
    const blob = new Blob([content], { type: `${type};charset=utf-8;` });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportTransactionsLedger = async () => {
    try {
      setDownloading('tx');
      const res = await reconciliationApi.getTransactions({ limit: 1000 });
      if (res?.data) {
        const headers = ['transaction_id', 'order_id', 'type', 'status', 'method', 'amount_inr', 'fee_inr', 'tax_inr', 'settled_amount_inr', 'expected_settlement_date'];
        const csv = [headers.join(','), ...res.data.map((r) => headers.map((h) => JSON.stringify(r[h] || '')).join(','))].join('\n');
        triggerDownload(`transactions_ledger_${Date.now()}.csv`, csv);
        setDownloadSuccess('Transactions ledger exported successfully.');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setDownloading(null);
    }
  };

  const exportExceptionsReport = async () => {
    try {
      setDownloading('exc');
      const res = await exceptionApi.getExceptions();
      if (res?.data) {
        const headers = ['transaction_id', 'order_id', 'amount_inr', 'anomaly_type', 'severity', 'status', 'resolution_note'];
        const csv = [headers.join(','), ...res.data.map((r) => headers.map((h) => JSON.stringify(r[h] || '')).join(','))].join('\n');
        triggerDownload(`exceptions_audit_${Date.now()}.csv`, csv);
        setDownloadSuccess('Exceptions audit report exported successfully.');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setDownloading(null);
    }
  };

  const exportTaxAudit = async () => {
    try {
      setDownloading('tax');
      const res = await aiApi.taxAudit();
      if (res?.audited_records) {
        const headers = ['transaction_id', 'type', 'recipient_type', 'amount_inr', 'actual_gst', 'expected_gst', 'actual_tds', 'expected_tds', 'tax_status', 'audit_comments'];
        const csv = [headers.join(','), ...res.audited_records.map((r) => headers.map((h) => JSON.stringify(r[h] || '')).join(','))].join('\n');
        triggerDownload(`section_194o_tax_audit_${Date.now()}.csv`, csv);
        setDownloadSuccess('Tax & Section 194-O audit report exported.');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-xl font-bold font-outfit text-navy">Financial Reports & Export Center</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Generate production audit CSV & JSON files for treasury records, accounting systems, and compliance.
        </p>
      </div>

      {downloadSuccess && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{downloadSuccess}</span>
        </div>
      )}

      {/* Export Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: Transactions Ledger */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-3">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold font-outfit text-navy">Reconciled Transactions Ledger</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Complete historical dataset of captured payments, refunds, payouts, gateway fees, and expected nodal settlement dates.
            </p>
          </div>
          <button
            onClick={exportTransactionsLedger}
            disabled={downloading === 'tx'}
            className="mt-6 w-full py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{downloading === 'tx' ? 'Exporting...' : 'Download CSV Ledger'}</span>
          </button>
        </div>

        {/* Card 2: Exceptions Audit Report */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mb-3 border border-rose-100">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold font-outfit text-navy">Audit Exceptions & Resolution Log</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Itemized report of all flagged anomalies, missing order orphans, severity scores, and store justification notes.
            </p>
          </div>
          <button
            onClick={exportExceptionsReport}
            disabled={downloading === 'exc'}
            className="mt-6 w-full py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{downloading === 'exc' ? 'Exporting...' : 'Download Exceptions CSV'}</span>
          </button>
        </div>

        {/* Card 3: Tax Compliance & Section 194-O */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mb-3 border border-amber-100">
              <Receipt className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold font-outfit text-navy">Tax & Section 194-O Audit Report</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Compliance report detailing 18% GST fee verifications and Section 194-O statutory TDS calculations by recipient type.
            </p>
          </div>
          <button
            onClick={exportTaxAudit}
            disabled={downloading === 'tax'}
            className="mt-6 w-full py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{downloading === 'tax' ? 'Exporting...' : 'Download Tax CSV'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
