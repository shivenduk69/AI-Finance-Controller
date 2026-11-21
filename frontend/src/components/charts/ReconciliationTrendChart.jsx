import React from 'react';
import Plot from 'react-plotly.js';

export default function ReconciliationTrendChart({
  dates = ['10-08', '11-08', '12-08', '13-08', '14-08', '15-08', '16-08', '17-08', '18-08', '19-08', '20-08', '21-08'],
  autoResolved = [8, 9, 7, 10, 8, 9, 6, 8, 7, 9, 10, 8],
  exceptions = [1, 0, 1, 0, 2, 0, 1, 0, 2, 1, 0, 1],
}) {
  return (
    <div className="w-full h-72">
      <Plot
        data={[
          {
            x: dates,
            y: autoResolved,
            name: 'Auto-Resolved',
            type: 'bar',
            marker: { color: '#0F4C75' },
          },
          {
            x: dates,
            y: exceptions,
            name: 'Exceptions (Needs Review)',
            type: 'bar',
            marker: { color: '#E53E3E' },
          },
        ]}
        layout={{
          barmode: 'stack',
          autosize: true,
          margin: { t: 20, r: 20, l: 35, b: 40 },
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          font: { family: 'Inter, sans-serif', size: 11, color: '#64748B' },
          legend: { orientation: 'h', x: 0, y: 1.15 },
          xaxis: { showgrid: false },
          yaxis: { gridcolor: '#F1F5F9' },
        }}
        useResizeHandler
        className="w-full h-full"
        config={{ displayModeBar: false, responsive: true }}
      />
    </div>
  );
}
