import React, { useState, useEffect, useCallback } from 'react';
import { Search, Filter, Download } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import ThreeWayAuditModal from '../../components/audit/ThreeWayAuditModal';
import reconciliationApi from '../../api/reconciliationApi';
import adminApi from '../../api/adminApi';

export default function AdminTransactionsPage() {
  const [transactions, setTransactions] = useState([]);
  const [merchants, setMerchants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(25);

  const [merchantFilter, setMerchantFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAuditTx, setSelectedAuditTx] = useState(null);

  useEffect(() => {
    adminApi.getMerchants().then((res) => {
      if (res?.success) setMerchants(res.data || []);
    });
  }, []);

  const fetchTransactions = useCallback(async () => {
    try {
      setLoading(true);
      const res = await reconciliationApi.getTransactions({
        page,
        limit,
        merchant_id: merchantFilter !== 'All' ? merchantFilter : undefined,
        status: statusFilter,
        search: searchQuery,
      });
      if (res?.success) {
        setTransactions(res.data || []);
        setTotal(res.total || 0);
      }
    } catch (err) {
      console.error('Failed to load platform transactions:', err);
    } finally {
      setLoading(false);
    }
  }, [page, limit, merchantFilter, statusFilter, searchQuery]);

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

  const columns = [
    {
      key: 'transaction_id',
      header: 'Transaction ID',
      render: (row) => <span className="font-mono font-semibold text-primary">{row.transaction_id}</span>,
    },
    {
      key: 'merchant_id',
      header: 'Merchant',
      render: (row) => <span className="font-semibold uppercase text-slate-700">{row.merchant_id}</span>,
    },
    {
      key: 'store_id',
      header: 'Store',
      render: (row) => <span className="font-mono text-slate-500 text-xs">{row.store_id}</span>,
    },
    {
      key: 'type',
      header: 'Type',
      render: (row) => <span className="text-xs uppercase font-medium">{row.type}</span>,
    },
    {
      key: 'amount_inr',
      header: 'Amount',
      render: (row) => <span className="font-mono font-medium">₹{Number(row.amount_inr).toFixed(2)}</span>,
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
      key: 'resolution_status',
      header: 'Resolution',
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
      <div>
        <h2 className="text-xl font-bold font-outfit text-navy">Platform Transactions Explorer</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Multi-tenant cross-merchant transaction ledger with visual 3-way reconciliation audit.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-sm flex flex-wrap items-center gap-3 text-xs">
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
            placeholder="Search by Transaction ID or Order ID..."
            className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
          />
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-slate-500 font-semibold uppercase text-[10px]">Merchant:</span>
          <select
            value={merchantFilter}
            onChange={(e) => {
              setMerchantFilter(e.target.value);
              setPage(1);
            }}
            className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700"
          >
            <option value="All">All Merchants</option>
            {merchants.map((m) => (
              <option key={m.merchant_id} value={m.merchant_id}>
                {m.name} ({m.merchant_id.toUpperCase()})
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-slate-500 font-semibold uppercase text-[10px]">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700"
          >
            <option value="All">All Statuses</option>
            <option value="captured">Captured</option>
            <option value="refunded">Refunded</option>
            <option value="failed">Failed</option>
            <option value="disputed">Disputed</option>
          </select>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={transactions}
        loading={loading}
        onRowClick={handleRowClick}
        pagination={{
          page,
          limit,
          total,
          onPageChange: (p) => setPage(p),
        }}
        emptyMessage="No platform transactions found."
      />

      <ThreeWayAuditModal
        isOpen={Boolean(selectedAuditTx)}
        onClose={() => setSelectedAuditTx(null)}
        auditData={selectedAuditTx}
      />
    </div>
  );
}
