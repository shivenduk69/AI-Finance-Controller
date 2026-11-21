import React from 'react';
import Plot from 'react-plotly.js';

export default function CashForecastChart({ forecastData = [] }) {
  const dates = forecastData.map((d) => d.date);
  const cumulative = forecastData.map((d) => d.cumulative_cash);
  const netInflow = forecastData.map((d) => d.net_inflow);

  return (
    <div className="w-full h-80">
      <Plot
        data={[
          {
            x: dates,
            y: netInflow,
            name: 'Net Daily Inflow (₹)',
            type: 'bar',
            marker: { color: '#3282B8' },
          },
          {
            x: dates,
            y: cumulative,
            name: 'Cumulative Cash (₹)',
            type: 'scatter',
            mode: 'lines+markers',
            yaxis: 'y2',
            line: { color: '#0F4C75', width: 3 },
            marker: { size: 6, color: '#0F4C75' },
          },
        ]}
        layout={{
          autosize: true,
          margin: { t: 20, r: 40, l: 45, b: 40 },
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          font: { family: 'Inter, sans-serif', size: 11, color: '#64748B' },
          legend: { orientation: 'h', x: 0, y: 1.15 },
          xaxis: { showgrid: false },
          yaxis: {
            title: 'Daily Inflow (₹)',
            gridcolor: '#F1F5F9',
          },
          yaxis2: {
            title: 'Cumulative Balance (₹)',
            overlaying: 'y',
            side: 'right',
            showgrid: false,
          },
        }}
        useResizeHandler
        className="w-full h-full"
        config={{ displayModeBar: false, responsive: true }}
      />
    </div>
  );
}
