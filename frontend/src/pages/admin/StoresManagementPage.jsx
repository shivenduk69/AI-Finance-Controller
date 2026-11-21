import React, { useState, useEffect } from 'react';
import { FolderGit2, Plus } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import Modal from '../../components/common/Modal';
import adminApi from '../../api/adminApi';

export default function StoresManagementPage() {
  const [stores, setStores] = useState([]);
  const [merchants, setMerchants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);

  const [storeId, setStoreId] = useState('');
  const [merchantId, setMerchantId] = useState('flipkart');
  const [name, setName] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchStoresData = async () => {
    try {
      setLoading(true);
      const [storesRes, merchantsRes] = await Promise.all([
        adminApi.getStores(),
        adminApi.getMerchants(),
      ]);
      if (storesRes?.success) setStores(storesRes.data || []);
      if (merchantsRes?.success) setMerchants(merchantsRes.data || []);
    } catch (err) {
      console.error('Failed to load stores:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStoresData();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!storeId.trim() || !name.trim()) return;

    try {
      setSubmitting(true);
      setErrorMsg('');
      await adminApi.createStore({
        store_id: storeId.trim().toLowerCase(),
        merchant_id: merchantId,
        name: name.trim(),
        city: city.trim(),
        state: state.trim(),
      });
      setStoreId('');
      setName('');
      setCity('');
      setState('');
      setModalOpen(false);
      fetchStoresData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to add store');
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    {
      key: 'store_id',
      header: 'Store ID',
      render: (row) => <span className="font-mono font-semibold text-primary">{row.store_id}</span>,
    },
    {
      key: 'name',
      header: 'Store Location Name',
      render: (row) => <span className="font-bold text-slate-800">{row.name}</span>,
    },
    {
      key: 'merchant_id',
      header: 'Merchant Owner',
      render: (row) => <span className="font-semibold uppercase text-slate-600">{row.merchant_id}</span>,
    },
    {
      key: 'city',
      header: 'City',
      render: (row) => <span className="text-slate-600">{row.city || '—'}</span>,
    },
    {
      key: 'state',
      header: 'State',
      render: (row) => <span className="text-slate-500">{row.state || '—'}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <StatusBadge status={row.is_active ? 'completed' : 'failed'} customLabel={row.is_active ? 'ACTIVE' : 'INACTIVE'} size="sm" />
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold font-outfit text-navy">Stores & Locations Management</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Operational merchant stores and fulfillment hub hierarchies.
          </p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-primary hover:bg-primary-dark rounded-lg transition-all shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>Add New Store</span>
        </button>
      </div>

      <DataTable
        columns={columns}
        data={stores}
        loading={loading}
        searchPlaceholder="Search stores by location or ID..."
      />

      {/* Modal */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Add Store Location">
        <form onSubmit={handleCreate} className="space-y-4">
          {errorMsg && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
              {errorMsg}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Store Identifier <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={storeId}
              onChange={(e) => setStoreId(e.target.value)}
              placeholder="e.g. fk_chennai"
              required
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono text-slate-800"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Parent Merchant <span className="text-rose-500">*</span>
            </label>
            <select
              value={merchantId}
              onChange={(e) => setMerchantId(e.target.value)}
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-semibold uppercase text-slate-800"
            >
              {merchants.map((m) => (
                <option key={m.merchant_id} value={m.merchant_id}>
                  {m.name} ({m.merchant_id.toUpperCase()})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Store Location Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Flipkart Chennai Hub"
              required
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
                City
              </label>
              <input
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="e.g. Chennai"
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
                State
              </label>
              <input
                type="text"
                value={state}
                onChange={(e) => setState(e.target.value)}
                placeholder="e.g. Tamil Nadu"
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
              />
            </div>
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
              {submitting ? 'Adding...' : 'Add Store'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
