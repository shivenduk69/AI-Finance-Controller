import React, { useState, useEffect } from 'react';
import { History, ShieldCheck, Download } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import adminApi from '../../api/adminApi';

export default function AdminAuditTrailPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setLoading(true);
        const res = await adminApi.getAuditLogs({ limit: 100 });
        if (res?.success) setLogs(res.data || []);
      } catch (err) {
        console.error('Failed to load audit logs:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchLogs();
  }, []);

  const columns = [
    {
      key: 'action',
      header: 'Audit Action',
      render: (row) => (
        <span className="font-mono font-bold text-xs text-primary bg-primary/10 px-2 py-0.5 rounded">
          {row.action}
        </span>
      ),
    },
    {
      key: 'entity_type',
      header: 'Target Entity',
      render: (row) => (
        <span className="text-xs font-semibold uppercase text-slate-700">
          {row.entity_type} {row.entity_id ? `(${row.entity_id})` : ''}
        </span>
      ),
    },
    {
      key: 'user_id',
      header: 'Actor ID',
      render: (row) => <span className="font-mono text-xs text-slate-600">{row.user_id || 'SYSTEM'}</span>,
    },
    {
      key: 'ip_address',
      header: 'Origin IP',
      render: (row) => <span className="font-mono text-xs text-slate-500">{row.ip_address || '127.0.0.1'}</span>,
    },
    {
      key: 'created_at',
      header: 'Timestamp',
      render: (row) => (
        <span className="font-mono text-xs text-slate-500">
          {new Date(row.created_at).toLocaleString()}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold font-outfit text-navy">Immutable Administrative Audit Trail</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Tamper-evident system activity log recording authentication, exception resolutions, and configuration updates.
        </p>
      </div>

      <DataTable
        columns={columns}
        data={logs}
        loading={loading}
        searchPlaceholder="Filter audit trail by action or user..."
        emptyMessage="No audit logs recorded."
      />
    </div>
  );
}
