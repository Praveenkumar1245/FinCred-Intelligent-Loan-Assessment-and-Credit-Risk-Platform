// FinCred AI — Chart.js Visualizations

function renderDashboardStatusChart(elementId, dataObj) {
    const ctx = document.getElementById(elementId);
    if (!ctx || typeof Chart === 'undefined') return;

    const labels = Object.keys(dataObj);
    const values = Object.values(dataObj);

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#15803d', // Meets Requirements (Green)
                    '#b91c1c', // Does Not Meet (Red)
                    '#b45309', // Pending Verification (Amber)
                    '#1d4ed8'  // Manual Review (Blue)
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        font: { size: 11 }
                    }
                }
            },
            cutout: '68%'
        }
    });
}

function renderDashboardSalaryChart(elementId, dataObj) {
    const ctx = document.getElementById(elementId);
    if (!ctx || typeof Chart === 'undefined') return;

    const labels = Object.keys(dataObj);
    const values = Object.values(dataObj);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Applications',
                data: values,
                backgroundColor: '#194a7a',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0 }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function renderSalaryComparisonChart(elementId, prevSal, currSal, avgSal) {
    const ctx = document.getElementById(elementId);
    if (!ctx || typeof Chart === 'undefined') return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Previous Monthly Salary', 'Current Verified Salary', 'Avg Verified (Selected Period)'],
            datasets: [{
                label: 'Monthly Amount (₹)',
                data: [prevSal, currSal, avgSal],
                backgroundColor: [
                    '#64748b', // Previous
                    '#0f2942', // Current
                    '#007788'  // Average
                ],
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function (val) {
                            return '₹' + val.toLocaleString('en-IN');
                        }
                    }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return ' Amount: ₹' + context.raw.toLocaleString('en-IN');
                        }
                    }
                }
            }
        }
    });
}

function renderDtiGaugeChart(elementId, projectedDti, maxDti) {
    const ctx = document.getElementById(elementId);
    if (!ctx || typeof Chart === 'undefined') return;

    const remaining = Math.max(0, 100 - projectedDti);
    const isExceeded = projectedDti > maxDti;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Projected Debt Burden', 'Available Debt Capacity'],
            datasets: [{
                data: [projectedDti, remaining],
                backgroundColor: [
                    isExceeded ? '#b91c1c' : (projectedDti > maxDti - 10 ? '#b45309' : '#15803d'),
                    '#e2e8f0'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            circumference: 180,
            rotation: 270,
            cutout: '75%',
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            return ` ${ctx.label}: ${ctx.raw.toFixed(1)}%`;
                        }
                    }
                }
            }
        }
    });
}

function renderLoanTypeDistributionChart(elementId, dataObj) {
    const ctx = document.getElementById(elementId);
    if (!ctx || typeof Chart === 'undefined') return;

    const labels = Object.keys(dataObj);
    const values = Object.values(dataObj);
    const colors = [
        '#0f2942', // Navy
        '#007788', // Teal
        '#d97706', // Amber / Gold
        '#2563eb', // Blue
        '#059669', // Emerald
        '#7c3aed', // Purple
        '#ea580c', // Orange
        '#475569'  // Slate
    ];

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Applications',
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: { precision: 0 }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            return ` ${ctx.raw} Applications`;
                        }
                    }
                }
            }
        }
    });
}

