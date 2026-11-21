import React, { useState, useEffect } from 'react';
import { HelpCircle, Plus, MessageSquare } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import Modal from '../../components/common/Modal';
import ticketApi from '../../api/ticketApi';

export default function HelpdeskTicketsPage() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  // Form State
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('MEDIUM');
  const [category, setCategory] = useState('RECONCILIATION_DISCREPANCY');
  const [txId, setTxId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

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

  const handleCreateTicket = async (e) => {
    e.preventDefault();
    if (!subject.trim() || !description.trim()) return;

    try {
      setSubmitting(true);
      setErrorMsg('');
      await ticketApi.createTicket({
        subject: subject.trim(),
        description: description.trim(),
        priority,
        category,
        transaction_id: txId.trim() || null,
      });
      setSubject('');
      setDescription('');
      setTxId('');
      setCreateModalOpen(false);
      fetchTickets();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to submit ticket.');
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
      key: 'subject',
      header: 'Subject & Inquiry',
      render: (row) => (
        <div>
          <span className="font-semibold text-slate-800 text-xs block">{row.subject}</span>
          <span className="text-[11px] text-slate-500 line-clamp-1">{row.description}</span>
        </div>
      ),
    },
    {
      key: 'category',
      header: 'Category',
      render: (row) => <span className="text-xs text-slate-600 font-medium">{row.category}</span>,
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
      key: 'created_at',
      header: 'Created Date',
      render: (row) => <span className="text-xs text-slate-500">{new Date(row.created_at).toLocaleDateString()}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold font-outfit text-navy">Store Support Helpdesk</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Submit reconciliation disputes, nodal inquiry tickets, and gateway technical requests.
          </p>
        </div>
        <button
          onClick={() => setCreateModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-primary hover:bg-primary-dark rounded-lg transition-all shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>New Support Ticket</span>
        </button>
      </div>

      {/* Tickets Table */}
      <DataTable
        columns={columns}
        data={tickets}
        loading={loading}
        searchPlaceholder="Search tickets by subject or ID..."
        emptyMessage="No tickets in queue. Use 'New Support Ticket' to open an inquiry."
      />

      {/* Create Ticket Modal */}
      <Modal isOpen={createModalOpen} onClose={() => setCreateModalOpen(false)} title="Open Support Ticket">
        <form onSubmit={handleCreateTicket} className="space-y-4">
          {errorMsg && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
              {errorMsg}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Subject <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="e.g. Bank credit discrepancy on 10-08-2026"
              required
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-slate-800"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
              >
                <option value="RECONCILIATION_DISCREPANCY">Reconciliation Discrepancy</option>
                <option value="FEE_TAX_DISPUTE">Fee / GST Tax Dispute</option>
                <option value="BANK_SETTLEMENT">Bank Nodal Settlement Issue</option>
                <option value="TECHNICAL_SUPPORT">Technical / Integration Help</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
                Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
              >
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
                <option value="URGENT">URGENT</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Linked Transaction ID (Optional)
            </label>
            <input
              type="text"
              value={txId}
              onChange={(e) => setTxId(e.target.value)}
              placeholder="e.g. pay_95822412"
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono text-slate-800"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Description <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Provide full context, bank statement dates, customer details, or dispute explanation..."
              required
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-slate-800"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setCreateModalOpen(false)}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-xs font-semibold text-white bg-primary hover:bg-primary-dark rounded-lg transition-colors shadow-sm disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : 'Submit Ticket'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
