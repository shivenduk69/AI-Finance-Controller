import React, { useState, useEffect } from 'react';
import { HelpCircle, MessageSquare } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import Modal from '../../components/common/Modal';
import ticketApi from '../../api/ticketApi';

export default function AdminTicketsPage() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);

  // Reply Modal
  const [replyTarget, setReplyTarget] = useState(null);
  const [replyText, setReplyText] = useState('');
  const [statusUpdate, setStatusUpdate] = useState('RESOLVED');
  const [submitting, setSubmitting] = useState(false);

  const fetchTickets = async () => {
    try {
      setLoading(true);
      const res = await ticketApi.getTickets();
      if (res?.success) setTickets(res.data || []);
    } catch (err) {
      console.error('Failed to load tickets:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, []);

  const handleReplySubmit = async (e) => {
    e.preventDefault();
    if (!replyTarget || !replyText.trim()) return;

    try {
      setSubmitting(true);
      await ticketApi.replyTicket(replyTarget.ticket_id, {
        comment: replyText.trim(),
        status: statusUpdate,
      });
      setReplyTarget(null);
      setReplyText('');
      fetchTickets();
    } catch (err) {
      console.error('Failed to reply to ticket:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    {
      key: 'ticket_id',
      header: 'Ticket ID',
      render: (row) => <span className="font-mono font-semibold text-primary">{row.ticket_id}</span>,
    },
    {
      key: 'merchant_id',
      header: 'Merchant / Store',
      render: (row) => (
        <span className="text-xs font-semibold uppercase text-slate-700">
          {row.merchant_id} ({row.store_id || 'Global'})
        </span>
      ),
    },
    {
      key: 'subject',
      header: 'Subject & Description',
      render: (row) => (
        <div>
          <span className="font-semibold text-slate-800 text-xs block">{row.subject}</span>
          <span className="text-[11px] text-slate-500 line-clamp-1">{row.description}</span>
        </div>
      ),
    },
    {
      key: 'priority',
      header: 'Priority',
      render: (row) => <StatusBadge status={row.priority} size="sm" />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => <StatusBadge status={row.status} size="sm" />,
    },
    {
      key: 'actions',
      header: 'Action',
      className: 'text-right',
      render: (row) => (
        <button
          onClick={() => {
            setReplyTarget(row);
            setReplyText('');
          }}
          className="px-2.5 py-1 text-xs font-semibold text-white bg-primary hover:bg-primary-dark rounded shadow-xs"
        >
          Reply & Resolve
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold font-outfit text-navy">Central Ticket Helpdesk Center</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Review and respond to merchant inquiries, nodal discrepancies, and integration disputes.
        </p>
      </div>

      <DataTable
        columns={columns}
        data={tickets}
        loading={loading}
        searchPlaceholder="Search tickets by subject, store, or ID..."
      />

      {/* Reply Modal */}
      <Modal isOpen={Boolean(replyTarget)} onClose={() => setReplyTarget(null)} title="Reply to Support Ticket">
        <form onSubmit={handleReplySubmit} className="space-y-4">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
            <p>Ticket: <strong className="font-mono text-primary">{replyTarget?.ticket_id}</strong></p>
            <p>Subject: <span className="font-semibold text-slate-800">{replyTarget?.subject}</span></p>
            <p className="text-slate-600 mt-1">{replyTarget?.description}</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Update Ticket Status
            </label>
            <select
              value={statusUpdate}
              onChange={(e) => setStatusUpdate(e.target.value)}
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-semibold"
            >
              <option value="RESOLVED">Mark as RESOLVED</option>
              <option value="PENDING">Keep PENDING</option>
              <option value="CLOSED">CLOSE Ticket</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Controller Response & Resolution Comment <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={4}
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder="Enter explanation, bank statement trace confirmation, or corrective steps..."
              required
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-slate-800"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setReplyTarget(null)}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-xs font-semibold text-white bg-primary hover:bg-primary-dark rounded-lg shadow-sm disabled:opacity-50"
            >
              {submitting ? 'Sending...' : 'Send Response'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
