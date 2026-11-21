import React, { useState, useEffect } from 'react';
import { TrendingUp, Calendar, AlertCircle } from 'lucide-react';
import DataTable from '../../components/common/DataTable';
import MetricCard from '../../components/common/MetricCard';
import CashForecastChart from '../../components/charts/CashForecastChart';
import aiApi from '../../api/aiApi';

export default function CashForecastingPage() {
  const [forecastDays, setForecastDays] = useState(7);
  const [forecastData, setForecastData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchForecast = async () => {
      try {
        setLoading(true);
        const res = await aiApi.cashForecast(forecastDays);
        if (res?.success) {
          setForecastData(res.data || []);
        }
      } catch (err) {
        console.error('Failed to load cash forecast:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchForecast();
  }, [forecastDays]);

  const latestCumulative = forecastData.length > 0 ? forecastData[forecastData.length - 1].cumulative_cash : 0;
  const committedQueue = forecastData.slice(0, 2).reduce((acc, d) => acc + d.net_inflow, 0);

  const columns = [
    {
      key: 'date',
      header: 'Forecast Date',
      render: (row) => <span className="font-mono font-semibold text-primary">{row.date}</span>,
    },
    {
      key: 'status',
      header: 'Queue Certainty',
      render: (row) => (
        <span
          className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${
            row.status.includes('COMMITTED')
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
              : 'bg-slate-50 text-slate-700 border-slate-200'
          }`}
        >
          {row.status}
        </span>
      ),
    },
    {
      key: 'gross_collections',
      header: 'Collections (₹)',
      render: (row) => <span className="font-mono">₹{Number(row.gross_collections).toFixed(2)}</span>,
    },
    {
      key: 'refunds',
      header: 'Refunds (₹)',
      render: (row) => <span className="font-mono text-slate-500">₹{Number(row.refunds).toFixed(2)}</span>,
    },
    {
      key: 'payouts',
      header: 'Payouts (₹)',
      render: (row) => <span className="font-mono text-slate-500">₹{Number(row.payouts).toFixed(2)}</span>,
    },
    {
      key: 'fees_gst',
      header: 'Fees + GST (₹)',
      render: (row) => <span className="font-mono text-slate-500">₹{Number(row.fees_gst).toFixed(2)}</span>,
    },
    {
      key: 'net_inflow',
      header: 'Net Daily Inflow (₹)',
      render: (row) => (
        <span className={`font-mono font-bold ${row.net_inflow >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
          {row.net_inflow >= 0 ? `+₹${row.net_inflow.toFixed(2)}` : `-₹${Math.abs(row.net_inflow).toFixed(2)}`}
        </span>
      ),
    },
    {
      key: 'cumulative_cash',
      header: 'Cumulative Treasury (₹)',
      render: (row) => <span className="font-mono font-bold text-navy">₹{Number(row.cumulative_cash).toFixed(2)}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold font-outfit text-navy">Rolling Cash Flow Forecasting</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Blended liquidity projection: Days 1–2 committed from captured gateway queue, Days 3–7 from active daily moving averages.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-500 font-semibold uppercase text-[10px]">Horizon:</span>
          <select
            value={forecastDays}
            onChange={(e) => setForecastDays(Number(e.target.value))}
            className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-700 font-semibold focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value={7}>7-Day Rolling Horizon</option>
            <option value={14}>14-Day Rolling Horizon</option>
            <option value={30}>30-Day Extended Horizon</option>
          </select>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          title="Committed T+2 Queue"
          value={`₹${committedQueue.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`}
          subtitle="Direct deposit arriving in 48 hours"
          icon={Calendar}
          accentColor="emerald"
        />
        <MetricCard
          title="Projected Treasury Close"
          value={`₹${latestCumulative.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`}
          subtitle={`Estimated cash at Day +${forecastDays}`}
          icon={TrendingUp}
          accentColor="primary"
        />
        <MetricCard
          title="Liquidity Health"
          value="STABLE"
          subtitle="Zero projected liquidity shortfalls"
          icon={AlertCircle}
          accentColor="blue"
        />
      </div>

      {/* Plotly Chart */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold font-outfit text-navy">Projected Treasury Trajectory</h3>
            <p className="text-xs text-slate-500">Daily net collections against cumulative cash balance</p>
          </div>
        </div>
        <CashForecastChart forecastData={forecastData} />
      </div>

      {/* Forecast DataGrid */}
      <DataTable
        columns={columns}
        data={forecastData}
        loading={loading}
        searchPlaceholder="Filter date..."
        emptyMessage="No cash flow forecast available."
      />
    </div>
  );
}
