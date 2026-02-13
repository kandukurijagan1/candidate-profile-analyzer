const radar = document.getElementById('radar');
if (radar) {
  new Chart(radar, {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        label: 'Score (0–100)',
        data: values,
        fill: true,
        backgroundColor: 'rgba(129,140,248,.25)',
        borderColor: 'rgba(129,140,248,1)',
        pointBackgroundColor: '#fff',
      }]
    },
    options: {
      animation: { duration: 900, easing: 'easeOutQuart' },
      scales: {
        r: {
          suggestedMin: 0, suggestedMax: 100,
          grid: { color: 'rgba(255,255,255,.2)' },
          angleLines: { color: 'rgba(255,255,255,.2)' },
          pointLabels: { color: '#e5e7eb' },
          ticks: { display: false }
        }
      },
      plugins: { legend: { labels: { color: '#e5e7eb' } } }
    }
  });
}
