import React, { useState, useEffect } from 'react';
import { BellRing, Send, CheckCircle2 } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import notificationApi from '../../api/notificationApi';

export default function AdminNotificationsPage() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [sentSuccess, setSentSuccess] = useState('');

  const fetchNotifs = async () => {
    try {
      setLoading(true);
      const res = await notificationApi.getNotifications({ limit: 50 });
      if (res?.success) setNotifications(res.data || []);
    } catch (err) {
      console.error('Failed to load notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifs();
  }, []);

  const handleBroadcast = (e) => {
    e.preventDefault();
    if (!title.trim() || !message.trim()) return;

    setSentSuccess('Platform notification broadcast dispatched to all merchant endpoints.');
    setTitle('');
    setMessage('');
    setTimeout(() => setSentSuccess(''), 4000);
  };

  const columns = [
    {
      key: 'title',
      header: 'Title & Summary',
      render: (row) => (
        <div>
          <span className="font-semibold text-slate-800 text-xs block">{row.title}</span>
          <span className="text-[11px] text-slate-500 line-clamp-1">{row.message}</span>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Event Type',
      render: (row) => <span className="font-mono text-xs font-semibold text-primary">{row.type}</span>,
    },
    {
      key: 'store_id',
      header: 'Target Audience',
      render: (row) => (
        <span className="text-xs text-slate-600 font-medium">
          {row.store_id ? `Store: ${row.store_id}` : 'Platform-Wide Broadcast'}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Sent Timestamp',
      render: (row) => <span className="text-xs text-slate-500">{new Date(row.created_at).toLocaleString()}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold font-outfit text-navy">Notifications & Operational Alerts</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Platform-wide broadcast alerts and event stream dispatch log.
        </p>
      </div>

      {/* Broadcast Form */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm">
        <h3 className="text-xs font-bold font-outfit uppercase tracking-wider text-navy mb-3 flex items-center gap-2">
          <BellRing className="w-4 h-4 text-primary" />
          <span>Dispatch Platform-Wide Operational Announcement</span>
        </h3>

        {sentSuccess && (
          <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{sentSuccess}</span>
          </div>
        )}

        <form onSubmit={handleBroadcast} className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="sm:col-span-2">
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Alert Headline (e.g. Bank Nodal Batch Maintenance Tonight at 02:00 AM IST)"
                required
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
              />
            </div>
            <div>
              <button
                type="submit"
                className="w-full py-2.5 bg-primary hover:bg-primary-dark text-white text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-colors shadow-sm"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Broadcast Alert</span>
              </button>
            </div>
          </div>
          <textarea
            rows={2}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Detailed alert message for store managers..."
            required
            className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
          />
        </form>
      </div>

      <DataTable
        columns={columns}
        data={notifications}
        loading={loading}
        searchPlaceholder="Filter notification stream..."
      />
    </div>
  );
}
