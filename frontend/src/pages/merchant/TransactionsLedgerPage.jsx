import React, { useState, useEffect, useCallback } from 'react';
import { Search, Filter, Download, ArrowUpDown } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import ThreeWayAuditModal from '../../components/audit/ThreeWayAuditModal';
import ResolutionSubmitModal from '../../components/audit/ResolutionSubmitModal';
import reconciliationApi from '../../api/reconciliationApi';

export default function TransactionsLedgerPage() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(25);

  const [statusFilter, setStatusFilter] = useState('All');
  const [typeFilter, setTypeFilter] = useState('All');
  const [methodFilter, setMethodFilter] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  const [selectedAuditTx, setSelectedAuditTx] = useState(null);
  const [resolveTarget, setResolveTarget] = useState(null);

  const fetchTransactions = useCallback(async () => {
    try {
      setLoading(true);
      const res = await reconciliationApi.getTransactions({
        page,
        limit,
        status: statusFilter,
        type: typeFilter,
        method: methodFilter,
        search: searchQuery,
      });
      if (res?.success) {
        setTransactions(res.data || []);
        setTotal(res.total || 0);
      }
    } catch (err) {
      console.error('Failed to fetch transactions:', err);
    } finally {
      setLoading(false);
    }
  }, [page, limit, statusFilter, typeFilter, methodFilter, searchQuery]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  const handleRowClick = async (row) => {
    try {
      const res = await reconciliationApi.getTransactionAudit(row.transaction_id);
      if (res?.success) {
        setSelectedAuditTx(res.data);
      }
    } catch (err) {
      console.error('Failed to load transaction audit:', err);
    }
  };

  const handleExportCsv = () => {
    if (!transactions.length) return;
    const headers = ['transaction_id', 'order_id', 'type', 'status', 'method', 'amount_inr', 'fee_inr', 'tax_inr', 'settled_amount_inr', 'expected_settlement_date'];
    const rows = transactions.map((t) => headers.map((h) => JSON.stringify(t[h] || '')).join(','));
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
    const link = document.createElement('a');
    link.setAttribute('href', encodeURI(csvContent));
    link.setAttribute('download', `transactions_ledger_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const columns = [
    {
      key: 'transaction_id',
      header: 'Transaction ID',
      render: (row) => <span className="font-mono font-semibold text-primary">{row.transaction_id}</span>,
    },
    {
      key: 'order_id',
      header: 'Order ID',
      render: (row) => <span className="font-mono text-slate-600">{row.order_id || '—'}</span>,
    },
    {
      key: 'type',
      header: 'Type',
      render: (row) => <span className="text-xs font-semibold uppercase">{row.type}</span>,
    },
    {
      key: 'amount_inr',
      header: 'Amount',
      render: (row) => <span className="font-mono font-medium">₹{Number(row.amount_inr).toFixed(2)}</span>,
    },
    {
      key: 'fee_inr',
      header: 'Fee (2%)',
      render: (row) => <span className="font-mono text-slate-500">₹{Number(row.fee_inr).toFixed(2)}</span>,
    },
    {
      key: 'tax_inr',
      header: 'GST (18%)',
      render: (row) => <span className="font-mono text-slate-500">₹{Number(row.tax_inr).toFixed(2)}</span>,
    },
    {
      key: 'settled_amount_inr',
      header: 'Net Settled',
      render: (row) => <span className="font-mono font-bold text-navy">₹{Number(row.settled_amount_inr).toFixed(2)}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => <StatusBadge status={row.status} size="sm" />,
    },
    {
      key: 'expected_settlement_date',
      header: 'Expected Deposit',
      render: (row) => <span className="text-xs font-mono text-slate-600">{row.expected_settlement_date || '—'}</span>,
    },
    {
      key: 'resolution_status',
      header: 'Audit Resolution',
      render: (row) => (
        <StatusBadge
          status={row.resolution_status || (row.exception_flag === 'YES' ? 'NEEDS_REVIEW' : 'AUTO_RESOLVED')}
          size="sm"
        />
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold font-outfit text-navy">Transactions Ledger</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Gateway captured payments, refunds, payouts, and fees. Click any row for visual 3-way audit.
          </p>
        </div>
        <button
          onClick={handleExportCsv}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-sm"
        >
          <Download className="w-3.5 h-3.5 text-slate-500" />
          <span>Export Ledger CSV</span>
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-sm flex flex-wrap items-center gap-3 text-xs">
        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
            placeholder="Search by Transaction ID or Order ID..."
            className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-slate-800"
          />
        </div>

        {/* Status Dropdown */}
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500 font-semibold uppercase text-[10px]">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="All">All Statuses</option>
            <option value="captured">Captured</option>
            <option value="refunded">Refunded</option>
            <option value="failed">Failed</option>
            <option value="disputed">Disputed</option>
          </select>
        </div>

        {/* Type Dropdown */}
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500 font-semibold uppercase text-[10px]">Type:</span>
          <select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setPage(1);
            }}
            className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="All">All Types</option>
            <option value="PAYMENT">PAYMENT</option>
            <option value="REFUND">REFUND</option>
            <option value="PAYOUT">PAYOUT</option>
          </select>
        </div>

        {/* Method Dropdown */}
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500 font-semibold uppercase text-[10px]">Method:</span>
          <select
            value={methodFilter}
            onChange={(e) => {
              setMethodFilter(e.target.value);
              setPage(1);
            }}
            className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="All">All Methods</option>
            <option value="card">Card</option>
            <option value="upi">UPI</option>
            <option value="netbanking">Netbanking</option>
            <option value="wallet">Wallet</option>
          </select>
        </div>
      </div>

      {/* Transactions DataGrid */}
      <DataTable
        columns={columns}
        data={transactions}
        loading={loading}
        onRowClick={handleRowClick}
        pagination={{
          page,
          limit,
          total,
          onPageChange: (newPage) => setPage(newPage),
        }}
        emptyMessage="No transactions found matching active filter criteria."
      />

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
        onSuccess={fetchTransactions}
      />
    </div>
  );
}
