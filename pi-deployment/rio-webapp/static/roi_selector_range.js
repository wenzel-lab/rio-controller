/**
 * ROI Selector - Dual-Handle Range Slider Implementation
 * 
 * Uses jQuery UI range sliders with dual handles (min/max) for X and Y axes.
 * More intuitive than separate x/y/width/height sliders.
 * 
 * Features:
 * - Dual-handle range sliders for X and Y axes
 * - Visual ROI preview on canvas overlay
 * - Converts min/max values to x/y/width/height for server
 * - Works reliably across browsers
 * - Supports camera hardware ROI constraints
 */

class ROISelectorRange {
    constructor(imageElement, socket, maxWidth, maxHeight, constraints = null) {
        this.img = imageElement;
        this.socket = socket;
        
        // Maximum image dimensions
        this.maxWidth = maxWidth || 1920;
        this.maxHeight = maxHeight || 1080;
        
        // Camera constraints (from Mako camera if available)
        this.constraints = constraints || {
            offset_x: {min: 0, max: maxWidth, increment: 1},
            offset_y: {min: 0, max: maxHeight, increment: 1},
            width: {min: 10, max: maxWidth, increment: 1},
            height: {min: 10, max: maxHeight, increment: 1}
        };
        
        // Current ROI (stored as x_min, x_max, y_min, y_max)
        this.x_min = 0;
        this.x_max = 0;
        this.y_min = 0;
        this.y_max = 0;
        this.roi = null; // Will be calculated from min/max
        
        // Canvas for visual preview
        this.canvas = null;
        this.ctx = null;
        
        // Flag to prevent recursive event loops
        this._updatingInputs = false;
        
        this.setupCanvas();
        this.setupRangeSliders();
        this.setupEventListeners();
        this.loadROI();
    }
    
    setupCanvas() {
        // Create read-only canvas for visual preview
        const container = this.img.parentElement;
        if (!container) return;
        
        let existingCanvas = container.querySelector('#roi_preview_canvas');
        if (existingCanvas) {
            this.canvas = existingCanvas;
        } else {
            this.canvas = document.createElement('canvas');
            this.canvas.id = 'roi_preview_canvas';
            this.canvas.style.position = 'absolute';
            this.canvas.style.top = '0';
            this.canvas.style.left = '0';
            this.canvas.style.pointerEvents = 'none'; // Read-only
            container.style.position = 'relative';
            container.appendChild(this.canvas);
        }
        
        this.ctx = this.canvas.getContext('2d');
        this.updateCanvasSize();
        
        this.img.addEventListener('load', () => this.updateCanvasSize());
        window.addEventListener('resize', () => this.updateCanvasSize());
    }
    
    updateCanvasSize() {
        if (!this.canvas || !this.img) return;
        
        const rect = this.img.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = rect.height;
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';
        
        this.draw();
    }
    
    setupRangeSliders() {
        const maxW = this.maxWidth;
        const maxH = this.maxHeight;
        
        // Initialize with visible range so sliders are visible from start
        // Use 10%-90% range so handles are clearly visible at both ends
        const initialXMin = Math.max(0, Math.floor(maxW * 0.1));
        const initialXMax = Math.min(maxW, Math.floor(maxW * 0.9));
        const initialYMin = Math.max(0, Math.floor(maxH * 0.1));
        const initialYMax = Math.min(maxH, Math.floor(maxH * 0.9));
        
        // X-axis range slider (dual handles) - visible blue line with handles
        $('#roi_x_range_slider').slider({
            range: true,
            min: 0,
            max: maxW,
            values: [initialXMin, initialXMax],
            step: this.constraints.offset_x.increment || 1,
            slide: (event, ui) => {
                this.x_min = ui.values[0];
                this.x_max = ui.values[1];
                this.updateFromRange();
            },
            change: (event, ui) => {
                this.x_min = ui.values[0];
                this.x_max = ui.values[1];
                this.updateFromRange();
            }
        });
        
        // Y-axis range slider (dual handles) - visible blue line with handles
        $('#roi_y_range_slider').slider({
            range: true,
            min: 0,
            max: maxH,
            values: [initialYMin, initialYMax],
            step: this.constraints.offset_y.increment || 1,
            slide: (event, ui) => {
                this.y_min = ui.values[0];
                this.y_max = ui.values[1];
                this.updateFromRange();
            },
            change: (event, ui) => {
                this.y_min = ui.values[0];
                this.y_max = ui.values[1];
                this.updateFromRange();
            }
        });
        
        // Set initial slider values (visible range for UI, but no ROI set yet)
        // Sliders are initialized with a visible range so handles are visible at both ends
        // ROI will only be created when user moves the sliders (via updateFromRange)
        this.x_min = initialXMin;
        this.x_max = initialXMax;
        this.y_min = initialYMin;
        this.y_max = initialYMax;
        
        // Update numeric inputs to match slider values (visual only, no ROI sent to server)
        this._updatingInputs = true;
        $('#roi_x_min').val(this.x_min);
        $('#roi_x_max').val(this.x_max);
        $('#roi_y_min').val(this.y_min);
        $('#roi_y_max').val(this.y_max);
        setTimeout(() => { this._updatingInputs = false; }, 0);
        
        // Note: CSS styling for blue slider range is in index.html <style> tag
        // ROI is null initially - user must move sliders to create ROI
    }
    
    updateFromRange() {
        if (this._updatingInputs) return;
        
        // Convert min/max to x/y/width/height
        const x = this.x_min;
        const y = this.y_min;
        const width = Math.max(10, this.x_max - this.x_min);
        const height = Math.max(10, this.y_max - this.y_min);
        
        // Update numeric inputs
        $('#roi_x_min').val(this.x_min);
        $('#roi_x_max').val(this.x_max);
        $('#roi_y_min').val(this.y_min);
        $('#roi_y_max').val(this.y_max);
        
        // Only set ROI if we have valid dimensions (width/height >= 10)
        // This prevents sending ROI on initial page load when sliders are just visible
        if (width >= 10 && height >= 10) {
            this.setROI({x, y, width, height}, true);
        } else {
            // Invalid range - clear ROI display but don't send to server
            this.roi = null;
            if (this.ctx) {
                this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            }
            if (typeof updateROIInfo === 'function') {
                updateROIInfo();
            }
        }
    }
    
    setupEventListeners() {
        // Listen for ROI updates from server
        if (this.socket) {
            this.socket.on('roi', (data) => {
                if (data.roi) {
                    this.setROI(data.roi, false); // false = don't send back
                } else {
                    this.clearROI(false);
                }
                
                // Update constraints if provided
                if (data.constraints) {
                    this.setConstraints(data.constraints);
                }
            });
            
            // Request current ROI and constraints from server
            this.socket.emit('roi', {cmd: 'get'});
        }
        
        // Sync numeric inputs with sliders
        $('#roi_x_min, #roi_x_max').on('input', () => {
            const min = parseInt($('#roi_x_min').val()) || 0;
            const max = parseInt($('#roi_x_max').val()) || 0;
            if (min !== this.x_min || max !== this.x_max) {
                this.x_min = min;
                this.x_max = max;
                $('#roi_x_range_slider').slider('values', [min, max]);
                this.updateFromRange();
            }
        });
        
        $('#roi_y_min, #roi_y_max').on('input', () => {
            const min = parseInt($('#roi_y_min').val()) || 0;
            const max = parseInt($('#roi_y_max').val()) || 0;
            if (min !== this.y_min || max !== this.y_max) {
                this.y_min = min;
                this.y_max = max;
                $('#roi_y_range_slider').slider('values', [min, max]);
                this.updateFromRange();
            }
        });
    }
    
    draw() {
        if (!this.ctx || !this.roi) {
            if (this.ctx) {
                this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            }
            return;
        }
        
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        if (!this.roi.width || !this.roi.height) return;
        
        // Calculate scale from image to canvas
        const scaleX = this.canvas.width / this.maxWidth;
        const scaleY = this.canvas.height / this.maxHeight;
        
        const x = this.roi.x * scaleX;
        const y = this.roi.y * scaleY;
        const w = this.roi.width * scaleX;
        const h = this.roi.height * scaleY;
        
        // Draw semi-transparent overlay outside ROI
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.clearRect(x, y, w, h);
        
        // Draw ROI rectangle with blue border
        this.ctx.strokeStyle = '#0099ff';
        this.ctx.lineWidth = 3;
        this.ctx.strokeRect(x, y, w, h);
        
        // Draw ROI info
        this.ctx.fillStyle = '#ffffff';
        this.ctx.font = 'bold 14px Arial';
        const info = `ROI: (${this.roi.x}, ${this.roi.y}) ${this.roi.width}×${this.roi.height} px`;
        this.ctx.fillText(info, x + 5, y - 8);
    }
    
    setROI(roi, sendToServer = true) {
        // Validate and snap to constraints
        this.roi = {
            x: this.snapToIncrement(roi.x, this.constraints.offset_x),
            y: this.snapToIncrement(roi.y, this.constraints.offset_y),
            width: this.snapToIncrement(roi.width, this.constraints.width),
            height: this.snapToIncrement(roi.height, this.constraints.height)
        };
        
        // Clamp to bounds
        this.roi.x = Math.max(this.constraints.offset_x.min, 
                            Math.min(this.constraints.offset_x.max, this.roi.x));
        this.roi.y = Math.max(this.constraints.offset_y.min, 
                            Math.min(this.constraints.offset_y.max, this.roi.y));
        this.roi.width = Math.max(this.constraints.width.min, 
                                 Math.min(this.constraints.width.max, 
                                         this.maxWidth - this.roi.x, this.roi.width));
        this.roi.height = Math.max(this.constraints.height.min, 
                                  Math.min(this.constraints.height.max, 
                                          this.maxHeight - this.roi.y, this.roi.height));
        
        // Update min/max values from ROI
        this.x_min = this.roi.x;
        this.x_max = this.roi.x + this.roi.width;
        this.y_min = this.roi.y;
        this.y_max = this.roi.y + this.roi.height;
        
        this._updatingInputs = true;
        $('#roi_x_range_slider').slider('values', [this.x_min, this.x_max]);
        $('#roi_y_range_slider').slider('values', [this.y_min, this.y_max]);
        $('#roi_x_min').val(this.x_min);
        $('#roi_x_max').val(this.x_max);
        $('#roi_y_min').val(this.y_min);
        $('#roi_y_max').val(this.y_max);
        setTimeout(() => { this._updatingInputs = false; }, 0);
        
        this.draw();
        
        if (sendToServer) {
            this.saveROI();
        }
        
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }
    
    snapToIncrement(value, constraint) {
        const increment = constraint.increment || 1;
        const snapped = Math.round(value / increment) * increment;
        return Math.max(constraint.min || 0, Math.min(constraint.max || 9999, snapped));
    }
    
    getROI() {
        return this.roi;
    }
    
    clearROI(sendToServer = true) {
        this.roi = null;
        
        // Reset to visible range (10%-90%) so sliders remain visible with blue line and handles
        const maxW = this.maxWidth;
        const maxH = this.maxHeight;
        this.x_min = Math.max(0, Math.floor(maxW * 0.1));
        this.x_max = Math.min(maxW, Math.floor(maxW * 0.9));
        this.y_min = Math.max(0, Math.floor(maxH * 0.1));
        this.y_max = Math.min(maxH, Math.floor(maxH * 0.9));
        
        if (this.ctx) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
        
        this._updatingInputs = true;
        $('#roi_x_range_slider').slider('values', [this.x_min, this.x_max]);
        $('#roi_y_range_slider').slider('values', [this.y_min, this.y_max]);
        $('#roi_x_min').val(this.x_min);
        $('#roi_x_max').val(this.x_max);
        $('#roi_y_min').val(this.y_min);
        $('#roi_y_max').val(this.y_max);
        setTimeout(() => { this._updatingInputs = false; }, 0);
        
        if (this.socket && sendToServer) {
            this.socket.emit('roi', {cmd: 'clear'});
        }
        
        localStorage.removeItem('camera_roi');
        
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }
    
    saveROI() {
        if (!this.roi || this.roi.width <= 0 || this.roi.height <= 0) return;
        
        // Save to localStorage
        localStorage.setItem('camera_roi', JSON.stringify(this.roi));
        
        // Send to server (in x/y/width/height format)
        if (this.socket) {
            this.socket.emit('roi', {
                cmd: 'set',
                parameters: this.roi
            });
        }
        
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }
    
    loadROI() {
        const saved = localStorage.getItem('camera_roi');
        if (saved) {
            try {
                const roi = JSON.parse(saved);
                this.setROI(roi, false); // Don't send to server on load
            } catch (e) {
                console.error('Failed to load ROI:', e);
            }
        } else {
            // No saved ROI - sliders are visible with default range but no ROI set
            // User can move sliders to create ROI
        }
    }
    
    setConstraints(constraints) {
        // Update constraints and slider limits
        this.constraints = constraints;
        
        // Update slider max values
        $('#roi_x_range_slider').slider('option', 'max', constraints.offset_x.max);
        $('#roi_y_range_slider').slider('option', 'max', constraints.offset_y.max);
        
        // Re-validate current ROI if set
        if (this.roi) {
            this.setROI(this.roi, false);
        }
    }
}
