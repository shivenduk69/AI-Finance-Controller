import React, { useState, useEffect } from 'react';
import { Users, Plus, ShieldCheck } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import StatusBadge from '../../components/common/StatusBadge';
import Modal from '../../components/common/Modal';
import adminApi from '../../api/adminApi';

export default function AdminUserAccessPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);

  // Form State
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState('MERCHANT');
  const [merchantId, setMerchantId] = useState('flipkart');
  const [storeId, setStoreId] = useState('fk_delhi');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const res = await adminApi.getUsers();
      if (res?.success) setUsers(res.data || []);
    } catch (err) {
      console.error('Failed to load users:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password.trim() || !name.trim()) return;

    try {
      setSubmitting(true);
      setErrorMsg('');
      await adminApi.createUser({
        email: email.trim().toLowerCase(),
        password: password.trim(),
        name: name.trim(),
        role,
        merchant_id: role === 'ADMIN' ? null : merchantId,
        store_id: role === 'ADMIN' ? null : storeId,
      });
      setEmail('');
      setPassword('');
      setName('');
      setModalOpen(false);
      fetchUsers();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to create user');
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    {
      key: 'name',
      header: 'User Name',
      render: (row) => <span className="font-bold text-slate-800">{row.name}</span>,
    },
    {
      key: 'email',
      header: 'Email Address',
      render: (row) => <span className="font-mono text-slate-600">{row.email}</span>,
    },
    {
      key: 'role',
      header: 'Access Role',
      render: (row) => (
        <span
          className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
            row.role === 'ADMIN'
              ? 'bg-amber-100 text-amber-800 border border-amber-200'
              : 'bg-primary/10 text-primary border border-primary/20'
          }`}
        >
          {row.role}
        </span>
      ),
    },
    {
      key: 'merchant_id',
      header: 'Merchant Organization',
      render: (row) => (
        <span className="font-semibold uppercase text-xs text-slate-700">
          {row.merchant_id || 'Global Platform'}
        </span>
      ),
    },
    {
      key: 'store_id',
      header: 'Scoped Store ID',
      render: (row) => <span className="font-mono text-slate-500 text-xs">{row.store_id || 'All Stores'}</span>,
    },
    {
      key: 'created_at',
      header: 'Created Date',
      render: (row) => <span className="text-xs text-slate-500">{new Date(row.created_at).toLocaleDateString()}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold font-outfit text-navy">User Access & Role-Based Control</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Provision platform administrators and store managers with Argon2id password security.
          </p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-primary hover:bg-primary-dark rounded-lg transition-all shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>Provision New User</span>
        </button>
      </div>

      <DataTable
        columns={columns}
        data={users}
        loading={loading}
        searchPlaceholder="Search users by name or email..."
      />

      {/* Create User Modal */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Provision Authorized User">
        <form onSubmit={handleCreateUser} className="space-y-4">
          {errorMsg && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
              {errorMsg}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Full Legal Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Priya Sharma"
              required
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Work Email Address <span className="text-rose-500">*</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="priya@flipkart.com"
              required
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Initial Password <span className="text-rose-500">*</span>
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 characters"
              required
              minLength={6}
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
                Role Designation
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-semibold"
              >
                <option value="MERCHANT">MERCHANT (Store Manager)</option>
                <option value="ADMIN">ADMIN (Platform Controller)</option>
              </select>
            </div>

            {role === 'MERCHANT' && (
              <div>
                <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
                  Merchant
                </label>
                <select
                  value={merchantId}
                  onChange={(e) => setMerchantId(e.target.value)}
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-semibold uppercase"
                >
                  <option value="flipkart">Flipkart</option>
                  <option value="amazon">Amazon</option>
                </select>
              </div>
            )}
          </div>

          {role === 'MERCHANT' && (
            <div>
              <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
                Scoped Store Identifier
              </label>
              <input
                type="text"
                value={storeId}
                onChange={(e) => setStoreId(e.target.value)}
                placeholder="e.g. fk_delhi"
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono text-slate-800"
              />
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-xs font-semibold text-white bg-primary hover:bg-primary-dark rounded-lg shadow-sm disabled:opacity-50"
            >
              {submitting ? 'Creating...' : 'Create Account'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
