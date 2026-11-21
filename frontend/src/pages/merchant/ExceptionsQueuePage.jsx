import React, { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, Clock, CheckCircle2, Search, Filter } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import ThreeWayAuditModal from '../../components/audit/ThreeWayAuditModal';
import ResolutionSubmitModal from '../../components/audit/ResolutionSubmitModal';
import exceptionApi from '../../api/exceptionApi';
import reconciliationApi from '../../api/reconciliationApi';
import { useSocket } from '../../context/SocketContext';

export default function ExceptionsQueuePage() {
  const [activeTab, setActiveTab] = useState('ACTIVE'); // 'ACTIVE', 'PENDING', 'RESOLVED'
  const [exceptions, setExceptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState('All');

  const [selectedAuditTx, setSelectedAuditTx] = useState(null);
  const [resolveTarget, setResolveTarget] = useState(null);

  const { socket } = useSocket();

  const statusMap = {
    ACTIVE: 'NEEDS_REVIEW',
    PENDING: 'PENDING_ADMIN',
    RESOLVED: 'RESOLVED',
  };

  const fetchExceptions = useCallback(async () => {
    try {
      setLoading(true);
      const res = await exceptionApi.getExceptions({
        status: statusMap[activeTab],
        severity: severityFilter,
      });
      if (res?.success) {
        setExceptions(res.data || []);
      }
    } catch (err) {
      console.error('Failed to fetch exceptions queue:', err);
    } finally {
      setLoading(false);
    }
  }, [activeTab, severityFilter]);

  useEffect(() => {
    fetchExceptions();
  }, [fetchExceptions]);

  useEffect(() => {
    if (!socket) return;
    const handleSync = () => {
      fetchExceptions();
    };
    socket.on('exception_resolved', handleSync);
    socket.on('exception_submitted', handleSync);
    return () => {
      socket.off('exception_resolved', handleSync);
      socket.off('exception_submitted', handleSync);
    };
  }, [socket, fetchExceptions]);

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
      key: 'amount_inr',
      header: 'Amount',
      render: (row) => <span className="font-mono font-medium">₹{Number(row.amount_inr).toFixed(2)}</span>,
    },
    {
      key: 'anomaly_type',
      header: 'Discrepancy Description',
      render: (row) => <span className="text-xs text-slate-700 font-medium">{row.anomaly_type}</span>,
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (row) => <StatusBadge status={row.severity} size="sm" />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => <StatusBadge status={row.status} size="sm" />,
    },
    ...(activeTab !== 'ACTIVE'
      ? [
          {
            key: 'resolution_note',
            header: 'Resolution Note',
            render: (row) => (
              <span className="text-xs text-slate-600 truncate max-w-xs block">
                {row.resolution_note || '—'}
              </span>
            ),
          },
        ]
      : []),
    {
      key: 'actions',
      header: 'Actions',
      className: 'text-right',
      render: (row) => (
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={() => handleRowAudit(row.transaction_id)}
            className="text-xs text-primary font-medium hover:underline"
          >
            Audit
          </button>
          {activeTab === 'ACTIVE' && (
            <button
              onClick={() => setResolveTarget(row)}
              className="text-xs text-white bg-primary hover:bg-primary-dark px-2.5 py-1 rounded font-semibold transition-colors shadow-xs"
            >
              Resolve
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-xl font-bold font-outfit text-navy">Exception Resolution Queue</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Workflow for investigating and resolving reconciliation discrepancies across 3 tabs.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-6 text-sm">
        <button
          onClick={() => setActiveTab('ACTIVE')}
          className={`pb-3 font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'ACTIVE'
              ? 'border-primary text-primary font-bold'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <AlertTriangle className="w-4 h-4 text-rose-500" />
          <span>Active Exceptions</span>
        </button>

        <button
          onClick={() => setActiveTab('PENDING')}
          className={`pb-3 font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'PENDING'
              ? 'border-primary text-primary font-bold'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Clock className="w-4 h-4 text-amber-500" />
          <span>Pending Admin Verification</span>
        </button>

        <button
          onClick={() => setActiveTab('RESOLVED')}
          className={`pb-3 font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'RESOLVED'
              ? 'border-primary text-primary font-bold'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          <span>Resolution History</span>
        </button>
      </div>

      {/* Severity Filter */}
      <div className="flex items-center gap-2 text-xs">
        <span className="text-slate-500 font-semibold uppercase text-[10px]">Filter Severity:</span>
        <div className="flex gap-1.5">
          {['All', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-3 py-1 rounded-lg border font-medium transition-all ${
                severityFilter === sev
                  ? 'bg-slate-800 text-white border-slate-800 shadow-xs'
                  : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {/* Exceptions Grid */}
      <DataTable
        columns={columns}
        data={exceptions}
        loading={loading}
        searchPlaceholder="Filter exceptions by ID or note..."
        emptyMessage={`No exceptions found in ${activeTab.toLowerCase()} status.`}
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
        onSuccess={fetchExceptions}
      />
    </div>
  );
}
