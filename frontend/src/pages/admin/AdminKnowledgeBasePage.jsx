import React, { useState } from 'react';
import { BookOpen, FileText, Search } from 'lucide-react';
import DataTable from '../../components/common/DataTable';

export default function AdminKnowledgeBasePage() {
  const [documents] = useState([
    {
      file_name: '01_three_way_reconciliation_rules.md',
      chunks_count: 6,
      category: 'Reconciliation Policy',
      last_indexed: '14-11-2026',
      sample_text: 'Rule 1: Duplicate transaction ID rejection. Rule 4: Dynamic 2% fee benchmark and 18% GST audit.',
    },
    {
      file_name: '02_section_194o_tds_guidelines.md',
      chunks_count: 4,
      category: 'Tax Compliance',
      last_indexed: '14-11-2026',
      sample_text: 'CBDT Section 194-O mandates 1% TDS on resident individuals and 2% on corporate digital sellers.',
    },
    {
      file_name: '03_razorpay_settlement_schedules.md',
      chunks_count: 5,
      category: 'Settlement SLA',
      last_indexed: '14-11-2026',
      sample_text: 'Standard captured transactions settle T+2 business days into designated nodal clearing accounts.',
    },
    {
      file_name: '04_dispute_resolution_sop.md',
      chunks_count: 3,
      category: 'Dispute SOP',
      last_indexed: '14-11-2026',
      sample_text: 'Chargebacks and customer disputes transition status to disputed with immediate fee review.',
    },
  ]);

  const columns = [
    {
      key: 'file_name',
      header: 'Policy Document',
      render: (row) => (
        <span className="font-mono font-semibold text-primary flex items-center gap-2">
          <FileText className="w-4 h-4 text-slate-400 shrink-0" />
          <span>{row.file_name}</span>
        </span>
      ),
    },
    {
      key: 'category',
      header: 'Domain Category',
      render: (row) => <span className="text-xs font-semibold text-slate-700">{row.category}</span>,
    },
    {
      key: 'chunks_count',
      header: 'Indexed Chunks',
      render: (row) => <span className="font-mono">{row.chunks_count} chunks</span>,
    },
    {
      key: 'sample_text',
      header: 'Vector Excerpt Preview',
      render: (row) => <span className="text-xs text-slate-500 line-clamp-1 max-w-md">{row.sample_text}</span>,
    },
    {
      key: 'last_indexed',
      header: 'Last Synchronized',
      render: (row) => <span className="text-xs text-slate-500 font-mono">{row.last_indexed}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold font-outfit text-navy">Knowledge Base Document Hub</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Indexed policy documentation and SOP chunks powering semantic search in PostgreSQL <code>document_chunks</code>.
        </p>
      </div>

      <DataTable
        columns={columns}
        data={documents}
        searchPlaceholder="Filter policy documents..."
      />
    </div>
  );
}
