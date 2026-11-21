import React, { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, CheckCircle, XCircle, ShieldCheck } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import Modal from '../../components/common/Modal';
import ThreeWayAuditModal from '../../components/audit/ThreeWayAuditModal';
import exceptionApi from '../../api/exceptionApi';
import reconciliationApi from '../../api/reconciliationApi';
import { useSocket } from '../../context/SocketContext';

export default function AdminExceptionsReviewPage() {
  const [exceptions, setExceptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAuditTx, setSelectedAuditTx] = useState(null);

  // Review Modal State
  const [actionItem, setActionItem] = useState(null); // { item, action: 'APPROVE' | 'REJECT' | 'DIRECT' }
  const [adminNote, setAdminNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const { socket } = useSocket();

  const fetchExceptions = useCallback(async () => {
    try {
      setLoading(true);
      // Fetch both PENDING_ADMIN and NEEDS_REVIEW for central desk
      const res = await exceptionApi.getExceptions();
      if (res?.success) setExceptions(res.data || []);
    } catch (err) {
      console.error('Failed to load exceptions:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchExceptions();
  }, [fetchExceptions]);

  useEffect(() => {
    if (!socket) return;
    const handleSync = () => {
      fetchExceptions();
    };
    socket.on('exception_submitted', handleSync);
    socket.on('exception_resolved', handleSync);
    return () => {
      socket.off('exception_submitted', handleSync);
      socket.off('exception_resolved', handleSync);
    };
  }, [socket, fetchExceptions]);

  const handleRowAudit = async (txId) => {
    try {
      const res = await reconciliationApi.getTransactionAudit(txId);
      if (res?.success) setSelectedAuditTx(res.data);
    } catch (err) {
      console.error('Failed to load transaction audit:', err);
    }
  };

  const handleActionSubmit = async (e) => {
    e.preventDefault();
    if (!actionItem) return;

    try {
      setSubmitting(true);
      setErrorMsg('');

      if (actionItem.action === 'DIRECT') {
        await exceptionApi.directResolve(actionItem.item.resolution_id || 0, {
          transaction_id: actionItem.item.transaction_id,
          admin_note: adminNote.trim(),
        });
      } else {
        await exceptionApi.verifyResolution(actionItem.item.resolution_id, {
          action: actionItem.action,
          admin_note: adminNote.trim(),
        });
      }

      setActionItem(null);
      setAdminNote('');
      fetchExceptions();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to execute administrative action');
    } finally {
      setSubmitting(false);
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
      key: 'anomaly_type',
      header: 'Discrepancy',
      render: (row) => <span className="text-xs text-slate-800 font-medium">{row.anomaly_type}</span>,
    },
    {
      key: 'resolution_note',
      header: 'Store Submission Note',
      render: (row) => (
        <span className="text-xs text-slate-600 truncate max-w-xs block font-mono">
          {row.resolution_note || 'Awaiting store note'}
        </span>
      ),
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
    {
      key: 'actions',
      header: 'Administrative Action',
      className: 'text-right',
      render: (row) => (
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={() => handleRowAudit(row.transaction_id)}
            className="text-xs text-primary font-medium hover:underline"
          >
            Audit
          </button>
          {row.status === 'PENDING_ADMIN' ? (
            <>
              <button
                onClick={() => setActionItem({ item: row, action: 'APPROVE' })}
                className="px-2 py-1 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded transition-colors shadow-xs"
              >
                Approve
              </button>
              <button
                onClick={() => setActionItem({ item: row, action: 'REJECT' })}
                className="px-2 py-1 text-xs font-semibold text-rose-600 bg-rose-50 hover:bg-rose-100 rounded border border-rose-200 transition-colors"
              >
                Reject
              </button>
            </>
          ) : (
            <button
              onClick={() => setActionItem({ item: row, action: 'DIRECT' })}
              className="px-2 py-1 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded transition-colors"
            >
              Direct Resolve
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold font-outfit text-navy">Central Exceptions Review Desk</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Review store resolution justifications, approve clearing updates, or directly sign off discrepancies.
        </p>
      </div>

      <DataTable
        columns={columns}
        data={exceptions}
        loading={loading}
        searchPlaceholder="Filter exceptions by ID or description..."
        emptyMessage="No pending exceptions in the central review queue."
      />

      {/* Audit Modal */}
      <ThreeWayAuditModal
        isOpen={Boolean(selectedAuditTx)}
        onClose={() => setSelectedAuditTx(null)}
        auditData={selectedAuditTx}
      />

      {/* Action Modal */}
      <Modal
        isOpen={Boolean(actionItem)}
        onClose={() => setActionItem(null)}
        title={`${actionItem?.action === 'APPROVE' ? 'Approve' : actionItem?.action === 'REJECT' ? 'Reject' : 'Direct Resolve'} Exception`}
      >
        <form onSubmit={handleActionSubmit} className="space-y-4">
          {errorMsg && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
              {errorMsg}
            </div>
          )}

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
            <p>
              Target Transaction: <strong className="font-mono text-primary">{actionItem?.item?.transaction_id}</strong>
            </p>
            <p>
              Store Justification: <span className="text-slate-700 font-mono">{actionItem?.item?.resolution_note || 'None provided'}</span>
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Admin Controller Audit Comment <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={3}
              value={adminNote}
              onChange={(e) => setAdminNote(e.target.value)}
              placeholder="Document the administrative verification reason or audit sign-off..."
              required
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-slate-800"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setActionItem(null)}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className={`px-4 py-2 text-xs font-semibold text-white rounded-lg transition-colors shadow-sm disabled:opacity-50 ${
                actionItem?.action === 'APPROVE'
                  ? 'bg-emerald-600 hover:bg-emerald-700'
                  : actionItem?.action === 'REJECT'
                  ? 'bg-rose-600 hover:bg-rose-700'
                  : 'bg-primary hover:bg-primary-dark'
              }`}
            >
              {submitting ? 'Processing...' : 'Confirm Action'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
