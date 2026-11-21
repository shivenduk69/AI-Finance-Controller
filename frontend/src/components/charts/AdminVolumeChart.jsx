import React from 'react';
import Plot from 'react-plotly.js';

export default function AdminVolumeChart({
  dates = ['10-08', '12-08', '14-08', '16-08', '18-08', '20-08', '22-08'],
  flipkartVolume = [12500, 18400, 15600, 21000, 19500, 24000, 22800],
  amazonVolume = [8500, 11200, 9800, 14500, 13200, 16800, 15400],
}) {
  return (
    <div className="w-full h-72">
      <Plot
        data={[
          {
            x: dates,
            y: flipkartVolume,
            name: 'Flipkart Stores (₹)',
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#0F4C75', width: 2.5 },
            marker: { size: 5 },
          },
          {
            x: dates,
            y: amazonVolume,
            name: 'Amazon Stores (₹)',
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#F59E0B', width: 2.5 },
            marker: { size: 5 },
          },
        ]}
        layout={{
          autosize: true,
          margin: { t: 20, r: 20, l: 45, b: 40 },
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
