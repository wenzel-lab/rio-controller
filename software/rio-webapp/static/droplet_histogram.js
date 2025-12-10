/**
 * Droplet Histogram Visualization
 * 
 * Real-time histogram display for droplet detection metrics.
 * Based on structure from droplet_AInalysis repository.
 * 
 * Features:
 * - Width, Height, Area, and Diameter histograms
 * - Real-time updates via WebSocket
 * - Statistics display (mean, std, mode, count)
 * - Chart.js-based visualization
 */

class DropletHistogramVisualizer {
    constructor(containerId, socket) {
        this.container = document.getElementById(containerId);
        this.socket = socket;
        this.charts = {};
        this.statistics = {};
        
        // Chart.js configuration
        this.chartConfig = {
            type: 'bar',
            options: {
                responsive: true,
                maintainAspectRatio: true,  // Fixed aspect ratio
                aspectRatio: 2,  // Width:Height = 2:1 (height:width = 1:2)
                scales: {
                    y: {
                        beginAtZero: true,
                        min: 0,  // Ensure origin at 0
                        title: {
                            display: true,
                            text: 'Count'
                        }
                    },
                    x: {
                        beginAtZero: true,
                        min: 0,  // Ensure origin at 0
                        title: {
                            display: true,
                            text: 'Size (um)'  // Will be updated based on unit
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        };
        
        // Store pixel ratio and unit from server
        this.pixelRatio = 1.0;
        this.unit = 'px';
        
        this.setupWebSocket();
        this.createCharts();
    }
    
    setupWebSocket() {
        // Listen for histogram updates
        this.socket.on('droplet:histogram', (data) => {
            this.updateHistograms(data);
        });
        
        // Listen for statistics updates
        this.socket.on('droplet:statistics', (data) => {
            this.updateStatistics(data);
        });
        
        // Listen for status updates
        this.socket.on('droplet:status', (data) => {
            this.updateStatus(data);
        });
    }
    
    createCharts() {
        const metrics = ['width', 'height', 'area', 'diameter'];
        const titles = {
            'width': 'Droplet Width (Major Axis)',
            'height': 'Droplet Height (Minor Axis)',
            'area': 'Droplet Area',
            'diameter': 'Equivalent Diameter'
        };
        
        metrics.forEach(metric => {
            const chartId = `droplet_${metric}_chart`;
            const canvas = document.createElement('canvas');
            canvas.id = chartId;
            // Fixed height to maintain aspect ratio
            canvas.style.height = '300px';
            canvas.style.width = '100%';
            
            // Create responsive card with dynamic sizing
            // Use Bootstrap grid: 2 columns on large screens, 1 on small
            const col = document.createElement('div');
            col.className = 'col-lg-6 col-md-12 mb-3';
            
            const card = document.createElement('div');
            card.className = 'card h-100';
            card.innerHTML = `
                <div class="card-header">
                    <h6 class="mb-0">${titles[metric]}</h6>
                </div>
                <div class="card-body" style="position: relative; padding-bottom: 60px; min-height: 300px;">
                    <canvas id="${chartId}" style="max-height: 400px; width: 100% !important;"></canvas>
                    <div id="${chartId}_stats" class="mt-2 small text-muted" style="position: absolute; bottom: 10px; left: 15px; right: 15px;"></div>
                </div>
            `;
            
            col.appendChild(card);
            this.container.appendChild(col);
            
            const ctx = document.getElementById(chartId).getContext('2d');
            const config = {
                ...this.chartConfig,
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Count',
                        data: [],
                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    aspectRatio: 2,  // Width:Height = 2:1 (height:width = 1:2)
                    layout: {
                        padding: {
                            bottom: 50  // Space for statistics at bottom
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            min: 0,  // Ensure origin at 0
                            title: {
                                display: true,
                                text: 'Count'
                            }
                        },
                        x: {
                            beginAtZero: true,
                            min: 0,  // Ensure origin at 0
                            title: {
                                display: true,
                                text: `Size (${this.unit})`  // Will be updated dynamically
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        title: {
                            display: true,
                            position: 'top',
                            text: titles[metric]
                        },
                        tooltip: {
                            enabled: true
                        }
                    }
                }
            };
            
            this.charts[metric] = new Chart(ctx, config);
        });
    }
    
    updateHistograms(data) {
        if (!data || !data.histograms) {
            return;
        }
        
        // Update pixel ratio and unit if provided
        if (data.pixel_ratio !== undefined && data.pixel_ratio !== null) {
            const newRatio = parseFloat(data.pixel_ratio);
            if (!isNaN(newRatio) && newRatio > 0) {
                this.pixelRatio = newRatio;
                // Only log in debug mode to avoid console spam
                if (console && console.debug) {
                    console.debug(`Updated pixel ratio to: ${this.pixelRatio}`);
                }
            }
        }
        if (data.unit && typeof data.unit === 'string') {
            this.unit = data.unit;
        }
        
        let hasUpdates = false;
        
        Object.keys(this.charts).forEach(metric => {
            const histData = data.histograms[metric];
            if (histData && histData.bins && histData.counts) {
                // Convert bin edges to bin centers for display
                // Convert from pixels to micrometers if needed
                const binCenters = [];
                for (let i = 0; i < histData.bins.length - 1; i++) {
                    const centerPx = (histData.bins[i] + histData.bins[i + 1]) / 2;
                    // Convert to um using pixel_ratio and round to integer
                    // If pixel_ratio is 1.0, values stay in px; otherwise convert to um
                    const centerUm = Math.round(centerPx * this.pixelRatio);
                    binCenters.push(centerUm);
                }
                
                // Ensure counts are integers
                const counts = histData.counts.map(c => Math.round(c));
                
                // Check if data actually changed
                const labelsChanged = JSON.stringify(this.charts[metric].data.labels) !== JSON.stringify(binCenters);
                const dataChanged = JSON.stringify(this.charts[metric].data.datasets[0].data) !== JSON.stringify(counts);
                
                if (labelsChanged || dataChanged) {
                    this.charts[metric].data.labels = binCenters;
                    this.charts[metric].data.datasets[0].data = counts;
                    hasUpdates = true;
                }
                
                // Update x-axis label with unit (always update to reflect current unit)
                if (this.charts[metric].options.scales && this.charts[metric].options.scales.x) {
                    this.charts[metric].options.scales.x.title.text = `Size (${this.unit})`;
                }
                
                // Ensure origin is at 0
                if (this.charts[metric].options.scales) {
                    if (this.charts[metric].options.scales.x) {
                        this.charts[metric].options.scales.x.min = 0;
                    }
                    if (this.charts[metric].options.scales.y) {
                        this.charts[metric].options.scales.y.min = 0;
                    }
                }
            }
        });
        
        // Always update charts if we have data (even if unchanged, to refresh display)
        // This ensures charts update even if data hasn't changed but we want to refresh
        if (hasUpdates || (data.histograms && Object.keys(data.histograms).length > 0)) {
            Object.keys(this.charts).forEach(metric => {
                try {
                    // Force update to ensure display refreshes
                    this.charts[metric].update('none'); // Smooth update without animation
                } catch (e) {
                    console.error(`Error updating chart ${metric}:`, e);
                }
            });
        }
    }
    
    updateStatistics(data) {
        this.statistics = data;
        
        // Update unit and pixel ratio if provided
        if (data.unit) {
            this.unit = data.unit;
        }
        if (data.pixel_ratio !== undefined && data.pixel_ratio !== null) {
            this.pixelRatio = parseFloat(data.pixel_ratio);
        }
        
        // Update statistics display for each chart
        Object.keys(this.charts).forEach(metric => {
            const statsDiv = document.getElementById(`droplet_${metric}_chart_stats`);
            if (statsDiv && data[metric]) {
                const stats = data[metric];
                const count = data.count || 0;
                // All values are already integers from backend
                statsDiv.innerHTML = `
                    Count: ${count} | 
                    Mean: ${stats.mean} ${this.unit} | 
                    Std: ${stats.std} ${this.unit} | 
                    Mode: ${stats.mode} ${this.unit} | 
                    Range: ${stats.min} - ${stats.max} ${this.unit}
                `;
            }
        });
    }
    
    updateStatus(data) {
        // Update status display (e.g., running indicator, frame count)
        const statusDiv = document.getElementById('droplet_status');
        if (statusDiv) {
            statusDiv.innerHTML = `
                <div class="alert ${data.running ? 'alert-success' : 'alert-secondary'}">
                    <strong>Status:</strong> ${data.running ? 'Running' : 'Stopped'} | 
                    <strong>Frames:</strong> ${data.frame_count} | 
                    <strong>Droplets:</strong> ${data.droplet_count_total}
                </div>
            `;
        }
    }
}

// Control functions for droplet detection
class DropletDetectionControls {
    constructor(socket) {
        this.socket = socket;
        this.setupControls();
    }
    
    setupControls() {
        // Start button
        const startBtn = document.getElementById('droplet_start_btn');
        if (startBtn) {
            startBtn.addEventListener('click', () => {
                this.socket.emit('droplet', { cmd: 'start' });
            });
        }
        
        // Stop button
        const stopBtn = document.getElementById('droplet_stop_btn');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => {
                this.socket.emit('droplet', { cmd: 'stop' });
            });
        }
        
        // Reset button
        const resetBtn = document.getElementById('droplet_reset_btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.socket.emit('droplet', { cmd: 'reset' });
            });
        }
        
        // Get status button
        const statusBtn = document.getElementById('droplet_status_btn');
        if (statusBtn) {
            statusBtn.addEventListener('click', () => {
                this.socket.emit('droplet', { cmd: 'get_status' });
            });
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDropletVisualization);
} else {
    initDropletVisualization();
}

function initDropletVisualization() {
    // Check if socket is available (from main.js)
    if (typeof socket !== 'undefined') {
        // Create histogram visualizer
        const histogramContainer = document.getElementById('droplet_histogram_container');
        if (histogramContainer) {
            window.dropletHistogram = new DropletHistogramVisualizer('droplet_histogram_container', socket);
        } else {
            console.warn('Droplet histogram container not found');
        }
        
        // Create controls
        window.dropletControls = new DropletDetectionControls(socket);
    } else {
        console.warn('Socket not available for droplet visualization');
    }
}
