import React, { useState } from 'react';
import Modal from '../common/Modal';
import exceptionApi from '../../api/exceptionApi';

export default function ResolutionSubmitModal({ isOpen, onClose, exceptionItem, onSuccess }) {
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  if (!exceptionItem) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!note.trim()) {
      setError('Please provide a resolution justification or audit reference note.');
      return;
    }

    try {
      setSubmitting(true);
      setError('');
      await exceptionApi.submitResolution({
        transaction_id: exceptionItem.transaction_id,
        order_id: exceptionItem.order_id,
        resolution_note: note.trim(),
      });
      setNote('');
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to submit resolution note');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Submit Exception Resolution">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Transaction Summary */}
        <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
          <p className="font-semibold text-slate-800">
            Target Transaction: <span className="font-mono text-primary">{exceptionItem.transaction_id}</span>
          </p>
          {exceptionItem.order_id && (
            <p className="text-slate-600">
              Linked Order ID: <span className="font-mono">{exceptionItem.order_id}</span>
            </p>
          )}
          <p className="text-slate-600">
            Discrepancy: <span className="text-rose-600 font-medium">{String(exceptionItem.anomaly_type || exceptionItem.calculated_exceptions || 'Exception')}</span>
          </p>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
            {error}
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1.5">
            Store Resolution Justification Note <span className="text-rose-500">*</span>
          </label>
          <textarea
            rows={4}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Document the corrective action, bank UTR reference, customer email confirmation, or reason for discrepancy..."
            className="w-full text-xs p-3 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-slate-800"
            required
          />
          <p className="text-[11px] text-slate-400 mt-1">
            Submitting this will transition status to <strong>PENDING_ADMIN</strong> for central controller sign-off.
          </p>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 text-xs font-semibold text-white bg-primary hover:bg-primary-dark rounded-lg shadow-sm transition-colors disabled:opacity-50"
          >
            {submitting ? 'Submitting...' : 'Submit for Admin Approval'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
