/**
 * ROI Selector - Simple Slider-Based Implementation
 * 
 * Uses sliders with numeric display for reliable ROI selection.
 * Avoids canvas coordinate issues by working directly with image pixel coordinates.
 * 
 * Features:
 * - Sliders for X, Y, Width, Height
 * - Numeric input fields for precise values
 * - Read-only visual preview (no interaction)
 * - Works reliably across browsers
 * - Supports Mako camera hardware ROI constraints
 */

class ROISelectorSimple {
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
        
        // Current ROI (in image pixel coordinates)
        this.roi = null;
        
        // Canvas for visual preview (read-only, no interaction)
        this.canvas = null;
        this.ctx = null;
        
        this.setupCanvas();
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
            this.canvas.style.pointerEvents = 'none'; // Read-only, no interaction
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
        
        // Set up slider and input synchronization
        this.setupSliderInputSync();
    }
    
    setupSliderInputSync() {
        // Sync sliders with inputs and vice versa
        const syncPair = (sliderId, inputId, updateCallback) => {
            const slider = document.getElementById(sliderId);
            const input = document.getElementById(inputId);
            
            if (slider && input) {
                // Slider -> Input -> ROI update
                slider.addEventListener('input', () => {
                    input.value = slider.value;
                    updateCallback();
                });
                
                // Input -> Slider -> ROI update
                input.addEventListener('input', () => {
                    const value = parseInt(input.value) || 0;
                    slider.value = value;
                    updateCallback();
                });
            }
        };
        
        // Set up sync for all ROI parameters
        syncPair('roi_x_slider', 'roi_x', () => this.updateFromInputs());
        syncPair('roi_y_slider', 'roi_y', () => this.updateFromInputs());
        syncPair('roi_width_slider', 'roi_width', () => this.updateFromInputs());
        syncPair('roi_height_slider', 'roi_height', () => this.updateFromInputs());
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
        
        // Draw ROI rectangle
        this.ctx.strokeStyle = '#00ff00';
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x, y, w, h);
        
        // Draw ROI info
        this.ctx.fillStyle = '#ffffff';
        this.ctx.font = '12px Arial';
        const info = `ROI: (${this.roi.x}, ${this.roi.y}) ${this.roi.width}×${this.roi.height} px`;
        this.ctx.fillText(info, x + 5, y - 5);
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
        
        this.draw();
        this.updateInputs();
        
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
        if (this.ctx) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
        this.updateInputs();
        
        if (this.socket && sendToServer) {
            this.socket.emit('roi', {cmd: 'clear'});
        }
        
        localStorage.removeItem('camera_roi');
        
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }
    
    updateInputs() {
        // Update both sliders and numeric inputs
        const updatePair = (sliderId, inputId, value) => {
            const slider = document.getElementById(sliderId);
            const input = document.getElementById(inputId);
            if (slider) slider.value = value;
            if (input) input.value = value;
        };
        
        if (this.roi) {
            updatePair('roi_x_slider', 'roi_x', this.roi.x);
            updatePair('roi_y_slider', 'roi_y', this.roi.y);
            updatePair('roi_width_slider', 'roi_width', this.roi.width);
            updatePair('roi_height_slider', 'roi_height', this.roi.height);
        } else {
            updatePair('roi_x_slider', 'roi_x', 0);
            updatePair('roi_y_slider', 'roi_y', 0);
            updatePair('roi_width_slider', 'roi_width', 0);
            updatePair('roi_height_slider', 'roi_height', 0);
        }
    }
    
    updateFromInputs() {
        const xInput = document.getElementById('roi_x');
        const yInput = document.getElementById('roi_y');
        const widthInput = document.getElementById('roi_width');
        const heightInput = document.getElementById('roi_height');
        
        if (!xInput || !yInput || !widthInput || !heightInput) return;
        
        const x = parseInt(xInput.value) || 0;
        const y = parseInt(yInput.value) || 0;
        const width = parseInt(widthInput.value) || 0;
        const height = parseInt(heightInput.value) || 0;
        
        if (width > 0 && height > 0) {
            this.setROI({x, y, width, height});
        }
    }
    
    saveROI() {
        if (!this.roi || this.roi.width <= 0 || this.roi.height <= 0) return;
        
        // Save to localStorage
        localStorage.setItem('camera_roi', JSON.stringify(this.roi));
        
        // Send to server (in image coordinates)
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
        }
    }
    
    setConstraints(constraints) {
        // Update constraints and slider limits
        this.constraints = constraints;
        
        // Update slider max values
        const updateSliderMax = (sliderId, max) => {
            const slider = document.getElementById(sliderId);
            if (slider) slider.max = max;
        };
        
        updateSliderMax('roi_x_slider', constraints.offset_x.max);
        updateSliderMax('roi_y_slider', constraints.offset_y.max);
        updateSliderMax('roi_width_slider', constraints.width.max);
        updateSliderMax('roi_height_slider', constraints.height.max);
        
        // Re-validate current ROI if set
        if (this.roi) {
            this.setROI(this.roi, false);
        }
    }
}

