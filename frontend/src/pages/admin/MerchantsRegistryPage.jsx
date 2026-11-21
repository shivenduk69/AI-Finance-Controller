import React, { useState, useEffect } from 'react';
import { Building2, Plus } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import Modal from '../../components/common/Modal';
import adminApi from '../../api/adminApi';

export default function MerchantsRegistryPage() {
  const [merchants, setMerchants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);

  const [merchantId, setMerchantId] = useState('');
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchMerchants = async () => {
    try {
      setLoading(true);
      const res = await adminApi.getMerchants();
      if (res?.success) setMerchants(res.data || []);
    } catch (err) {
      console.error('Failed to load merchants:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMerchants();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!merchantId.trim() || !name.trim()) return;

    try {
      setSubmitting(true);
      setErrorMsg('');
      await adminApi.createMerchant({
        merchant_id: merchantId.trim().toLowerCase(),
        name: name.trim(),
        code: code.trim().toUpperCase() || merchantId.trim().toUpperCase(),
      });
      setMerchantId('');
      setName('');
      setCode('');
      setModalOpen(false);
      fetchMerchants();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to register merchant');
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    {
      key: 'merchant_id',
      header: 'Merchant ID',
      render: (row) => <span className="font-mono font-semibold text-primary">{row.merchant_id}</span>,
    },
    {
      key: 'name',
      header: 'Organization Name',
      render: (row) => <span className="font-bold text-slate-800">{row.name}</span>,
    },
    {
      key: 'code',
      header: 'Code',
      render: (row) => <span className="font-mono text-slate-600 font-semibold">{row.code}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <StatusBadge status={row.is_active ? 'completed' : 'failed'} customLabel={row.is_active ? 'ACTIVE' : 'INACTIVE'} size="sm" />
      ),
    },
    {
      key: 'created_at',
      header: 'Registered At',
      render: (row) => <span className="text-xs text-slate-500">{new Date(row.created_at).toLocaleDateString()}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold font-outfit text-navy">Merchants Registry</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Registered digital commerce merchants participating in multi-source reconciliation.
          </p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-primary hover:bg-primary-dark rounded-lg transition-all shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>Register Merchant</span>
        </button>
      </div>

      <DataTable
        columns={columns}
        data={merchants}
        loading={loading}
        searchPlaceholder="Search merchants by name or code..."
      />

      {/* Modal */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Register New Merchant">
        <form onSubmit={handleCreate} className="space-y-4">
          {errorMsg && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
              {errorMsg}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Merchant ID <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={merchantId}
              onChange={(e) => setMerchantId(e.target.value)}
              placeholder="e.g. myntra"
              required
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono text-slate-800"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Organization Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Myntra Designs Pvt Ltd"
              required
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Enterprise Short Code
            </label>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g. MYNTRA"
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono text-slate-800"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-xs font-semibold text-white bg-primary hover:bg-primary-dark rounded-lg transition-colors shadow-sm disabled:opacity-50"
            >
              {submitting ? 'Registering...' : 'Register Merchant'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
