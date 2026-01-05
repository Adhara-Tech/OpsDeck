/**
 * Asset Operations Dashboard - Chart.js Visualizations
 */

document.addEventListener('DOMContentLoaded', function () {
    // Check if dashboard data is available
    if (typeof window.assetsDashboardData === 'undefined') {
        console.error('Assets dashboard data not found');
        return;
    }

    const data = window.assetsDashboardData;

    // Chart 1: Status Distribution (Doughnut)
    const statusCtx = document.getElementById('statusChart');
    if (statusCtx) {
        new Chart(statusCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: data.statusLabels,
                datasets: [{
                    data: data.statusData,
                    backgroundColor: [
                        '#1cc88a', // In Use - Success green
                        '#f6c23e', // In Stock - Warning yellow
                        '#e74a3b', // Maintenance - Danger red
                        '#4e73df', // Available - Primary blue
                        '#858796'  // Other - Gray
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Chart 2: Breakdown Rate by Brand (Bar)
    const breakdownCtx = document.getElementById('breakdownChart');
    if (breakdownCtx) {
        new Chart(breakdownCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.brandLabels,
                datasets: [{
                    label: 'Breakdown Rate (%)',
                    data: data.brandBreakdownRates,
                    backgroundColor: data.brandBreakdownRates.map(rate => {
                        // Color code: Red if > 20%, Orange if > 10%, Green otherwise
                        if (rate > 20) return '#e74a3b';
                        if (rate > 10) return '#f6c23e';
                        return '#1cc88a';
                    }),
                    borderColor: data.brandBreakdownRates.map(rate => {
                        if (rate > 20) return '#c9302c';
                        if (rate > 10) return '#d39e00';
                        return '#17a673';
                    }),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const value = context.parsed.y || 0;
                                return `Breakdown Rate: ${value}%`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function (value) {
                                return value + '%';
                            }
                        },
                        title: {
                            display: true,
                            text: 'Breakdown Rate (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Brand'
                        }
                    }
                }
            }
        });
    }
});
