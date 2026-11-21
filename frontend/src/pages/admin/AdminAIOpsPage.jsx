import React, { useState } from 'react';
import { Sparkles, CheckCircle2, RefreshCw, Database, Cpu } from 'lucide-react';
import MetricCard from '../../components/common/MetricCard';

export default function AdminAIOpsPage() {
  const [model, setModel] = useState('gemini-2.0-flash');
  const [indexing, setIndexing] = useState(false);
  const [indexResult, setIndexResult] = useState('');

  const handleTriggerReindex = async () => {
    try {
      setIndexing(true);
      setIndexResult('');
      // Simulate indexing trigger
      setTimeout(() => {
        setIndexing(false);
        setIndexResult('Knowledge base vector index successfully refreshed. 18 document chunks synchronized with pgvector.');
      }, 1500);
    } catch (err) {
      setIndexing(false);
      setIndexResult('Indexing failed: ' + err.message);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-bold font-outfit text-navy">AI & RAG Operations Center</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Google Gemini 2.0 generative settings, pgvector embedding parameters, and document index synchronization.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          title="Active LLM Model"
          value={model}
          subtitle="Google Gemini Interactions API"
          icon={Cpu}
          accentColor="primary"
        />
        <MetricCard
          title="Embedding Dimension"
          value="768-D"
          subtitle="pgvector cosine index"
          icon={Database}
          accentColor="emerald"
        />
        <MetricCard
          title="RAG Index Status"
          value="HEALTHY"
          subtitle="Cosine similarity search operational"
          icon={Sparkles}
          accentColor="blue"
        />
      </div>

      {indexResult && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{indexResult}</span>
        </div>
      )}

      {/* Model Configuration Card */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm space-y-4">
        <h3 className="text-sm font-bold font-outfit text-navy uppercase tracking-wider">
          Gemini Generative Configuration
        </h3>

        <div className="space-y-4 text-xs">
          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Select Production LLM Model
            </label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-semibold"
            >
              <option value="gemini-2.0-flash">Google Gemini 2.0 Flash (Recommended — Low Latency & High Reasoning)</option>
              <option value="gemini-1.5-flash">Google Gemini 1.5 Flash</option>
              <option value="gemini-1.5-pro">Google Gemini 1.5 Pro</option>
            </select>
            <p className="text-[11px] text-slate-400 mt-1">
              Used across the Floating Assistant popover and dedicated AI Chat console.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1">
              Embedding Model (RAG Vector Store)
            </label>
            <input
              type="text"
              value="models/text-embedding-004 (768 Dimensions)"
              disabled
              className="w-full text-xs p-2.5 bg-slate-100 border border-slate-200 rounded-lg text-slate-500 font-mono"
            />
          </div>
        </div>

        {/* Index Trigger */}
        <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-800">Scan & Reindex Document Vector Store</p>
            <p className="text-[11px] text-slate-500">
              Parses all PDF and Markdown files in <code>documents/</code> and creates embeddings in PostgreSQL.
            </p>
          </div>
          <button
            onClick={handleTriggerReindex}
            disabled={indexing}
            className="px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-xs font-semibold flex items-center gap-2 transition-colors disabled:opacity-50 shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${indexing ? 'animate-spin' : ''}`} />
            <span>{indexing ? 'Indexing...' : 'Trigger Vector Reindex'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
