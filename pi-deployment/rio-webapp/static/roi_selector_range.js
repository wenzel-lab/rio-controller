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
        
        this.img.addEventListener('load', () => {
            this.updateCanvasSize();
            // Delay slider update to ensure image is fully rendered
            setTimeout(() => {
                this.updateSliderDimensions();
                // Force update of custom vertical slider display
                if (this.customVerticalSlider) {
                    this.customVerticalSlider.updateDisplay();
                }
            }, 100);
        });
        window.addEventListener('resize', () => {
            this.updateCanvasSize();
            setTimeout(() => {
                this.updateSliderDimensions();
                // Force update of custom vertical slider display
                if (this.customVerticalSlider) {
                    this.customVerticalSlider.updateDisplay();
                }
            }, 100);
        });
    }
    
    updateCanvasSize() {
        if (!this.canvas || !this.img) return;
        
        const rect = this.img.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = rect.height;
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';
        
        // Update slider dimensions to match image
        this.updateSliderDimensions();
        
        this.draw();
    }
    
    updateSliderDimensions() {
        if (!this.img) return;
        
        const rect = this.img.getBoundingClientRect();
        const imgHeight = rect.height;
        const imgWidth = rect.width;
        
        // Update custom vertical Y-axis slider to match image height
        if (this.customVerticalSlider) {
            this.customVerticalSlider.updateDimensions(imgHeight);
        }
        
        // Update X-axis slider (horizontal) to match image width
        const xSlider = $('#roi_x_range_slider');
        if (xSlider.length && xSlider.slider('instance')) {
            xSlider.css({
                'width': imgWidth + 'px',
                'height': '20px'
            });
            // Recalculate slider dimensions
            setTimeout(() => {
                try {
                    xSlider.slider('refresh');
                } catch (e) {
                    console.warn('Could not refresh X slider:', e);
                }
            }, 50);
        }
    }
    
    setupCustomVerticalSlider(maxH, initialYMin, initialYMax) {
        // Create custom vertical slider that works reliably on all platforms
        const sliderContainer = $('#roi_y_range_slider').parent();
        const sliderElement = $('#roi_y_range_slider');
        
        // Clear any existing jQuery UI slider
        if (sliderElement.slider('instance')) {
            sliderElement.slider('destroy');
        }
        
        // Get initial height from image if available
        let initialHeight = 300; // Default fallback
        if (this.img) {
            const imgRect = this.img.getBoundingClientRect();
            if (imgRect.height > 0) {
                initialHeight = imgRect.height;
            }
        }
        
        // Create custom slider structure
        sliderElement.empty();
        sliderElement.css({
            'position': 'relative',
            'width': '20px',
            'height': initialHeight + 'px', // Match image height
            'margin': '0 auto',
            'background': '#E0E0E0',
            'border-radius': '10px',
            'cursor': 'pointer'
        });
        
        // Create slider track
        const track = $('<div></div>').css({
            'position': 'absolute',
            'left': '0',
            'top': '0',
            'width': '100%',
            'height': '100%',
            'background': 'transparent'
        });
        sliderElement.append(track);
        
        // Create range highlight
        const range = $('<div></div>').css({
            'position': 'absolute',
            'left': '0',
            'width': '100%',
            'background': '#2196F3',
            'border-radius': '10px',
            'pointer-events': 'none'
        });
        sliderElement.append(range);
        
        // Create handles
        const handle1 = $('<div></div>').css({
            'position': 'absolute',
            'left': '-5px',
            'width': '30px',
            'height': '20px',
            'background': '#2196F3',
            'border': '2px solid #1565C0',
            'border-radius': '10px',
            'cursor': 'ns-resize',
            'z-index': '10',
            'box-shadow': '0 2px 4px rgba(0,0,0,0.2)',
            'transition': 'background 0.2s ease'
        }).on('mouseenter', function() {
            $(this).css('background', '#7FD3D3');
        }).on('mouseleave', function() {
            $(this).css('background', '#2196F3');
        });
        const handle2 = $('<div></div>').css({
            'position': 'absolute',
            'left': '-5px',
            'width': '30px',
            'height': '20px',
            'background': '#2196F3',
            'border': '2px solid #1565C0',
            'border-radius': '10px',
            'cursor': 'ns-resize',
            'z-index': '10',
            'box-shadow': '0 2px 4px rgba(0,0,0,0.2)',
            'transition': 'background 0.2s ease'
        }).on('mouseenter', function() {
            $(this).css('background', '#7FD3D3');
        }).on('mouseleave', function() {
            $(this).css('background', '#2196F3');
        });
        sliderElement.append(handle1);
        sliderElement.append(handle2);
        
        // Store references
        this.customVerticalSlider = {
            element: sliderElement,
            track: track,
            range: range,
            handle1: handle1,
            handle2: handle2,
            maxValue: maxH,
            minValue: 0,
            value1: initialYMin,
            value2: initialYMax,
            dragging: null,
            updateDimensions: (height) => {
                sliderElement.css('height', height + 'px');
                this.customVerticalSlider.updateDisplay();
            },
            updateDisplay: () => {
                const height = sliderElement.height();
                const max = this.customVerticalSlider.maxValue;
                const val1 = this.customVerticalSlider.value1;
                const val2 = this.customVerticalSlider.value2;
                
                // Convert values to positions (top = 0, bottom = max)
                const pos1 = (val1 / max) * height;
                const pos2 = (val2 / max) * height;
                
                // Update handles
                handle1.css('top', (pos1 - 10) + 'px');
                handle2.css('top', (pos2 - 10) + 'px');
                
                // Update range highlight
                const topPos = Math.min(pos1, pos2);
                const rangeHeight = Math.abs(pos2 - pos1);
                range.css({
                    'top': topPos + 'px',
                    'height': rangeHeight + 'px'
                });
            },
            valueToPosition: (value) => {
                const height = sliderElement.height();
                return (value / this.customVerticalSlider.maxValue) * height;
            },
            positionToValue: (position) => {
                const height = sliderElement.height();
                const value = (position / height) * this.customVerticalSlider.maxValue;
                return Math.max(0, Math.min(this.customVerticalSlider.maxValue, Math.round(value)));
            }
        };
        
        // Set initial values
        this.y_min = initialYMin;
        this.y_max = initialYMax;
        this.customVerticalSlider.updateDisplay();
        
        // Mouse and touch event handlers
        const handleMouseDown = (e, handle) => {
            e.preventDefault();
            e.stopPropagation();
            this.customVerticalSlider.dragging = handle;
            $(document).on('mousemove.verticalSlider', handleMouseMove);
            $(document).on('mouseup.verticalSlider', handleMouseUp);
        };
        
        const handleMouseMove = (e) => {
            if (!this.customVerticalSlider.dragging) return;
            e.preventDefault();
            
            const rect = sliderElement[0].getBoundingClientRect();
            const y = e.clientY - rect.top;
            const value = this.customVerticalSlider.positionToValue(y);
            
            if (this.customVerticalSlider.dragging === handle1) {
                this.customVerticalSlider.value1 = Math.min(value, this.customVerticalSlider.value2);
            } else {
                this.customVerticalSlider.value2 = Math.max(value, this.customVerticalSlider.value1);
            }
            
            this.y_min = Math.min(this.customVerticalSlider.value1, this.customVerticalSlider.value2);
            this.y_max = Math.max(this.customVerticalSlider.value1, this.customVerticalSlider.value2);
            
            this.customVerticalSlider.updateDisplay();
            this.updateFromRange();
        };
        
        const handleMouseUp = (e) => {
            this.customVerticalSlider.dragging = null;
            $(document).off('mousemove.verticalSlider');
            $(document).off('mouseup.verticalSlider');
        };
        
        // Attach event handlers
        handle1.on('mousedown', (e) => handleMouseDown(e, handle1));
        handle2.on('mousedown', (e) => handleMouseDown(e, handle2));
        
        // Touch support
        const handleTouchStart = (e, handle) => {
            e.preventDefault();
            this.customVerticalSlider.dragging = handle;
            const touch = e.originalEvent.touches[0];
            $(document).on('touchmove.verticalSlider', handleTouchMove);
            $(document).on('touchend.verticalSlider', handleTouchEnd);
        };
        
        const handleTouchMove = (e) => {
            if (!this.customVerticalSlider.dragging) return;
            e.preventDefault();
            const touch = e.originalEvent.touches[0];
            const rect = sliderElement[0].getBoundingClientRect();
            const y = touch.clientY - rect.top;
            const value = this.customVerticalSlider.positionToValue(y);
            
            if (this.customVerticalSlider.dragging === handle1) {
                this.customVerticalSlider.value1 = Math.min(value, this.customVerticalSlider.value2);
            } else {
                this.customVerticalSlider.value2 = Math.max(value, this.customVerticalSlider.value1);
            }
            
            this.y_min = Math.min(this.customVerticalSlider.value1, this.customVerticalSlider.value2);
            this.y_max = Math.max(this.customVerticalSlider.value1, this.customVerticalSlider.value2);
            
            this.customVerticalSlider.updateDisplay();
            this.updateFromRange();
        };
        
        const handleTouchEnd = (e) => {
            this.customVerticalSlider.dragging = null;
            $(document).off('touchmove.verticalSlider');
            $(document).off('touchend.verticalSlider');
        };
        
        handle1.on('touchstart', (e) => handleTouchStart(e, handle1));
        handle2.on('touchstart', (e) => handleTouchStart(e, handle2));
        
        // Click on track to move nearest handle
        track.on('click', (e) => {
            const rect = sliderElement[0].getBoundingClientRect();
            const y = e.clientY - rect.top;
            const value = this.customVerticalSlider.positionToValue(y);
            
            const dist1 = Math.abs(value - this.customVerticalSlider.value1);
            const dist2 = Math.abs(value - this.customVerticalSlider.value2);
            
            // In vertical slider: top handle (handle1) = y_min, bottom handle (handle2) = y_max
            if (dist1 < dist2) {
                // Top handle controls y_min
                this.customVerticalSlider.value1 = Math.min(value, this.customVerticalSlider.value2);
                this.y_min = this.customVerticalSlider.value1;
            } else {
                // Bottom handle controls y_max
                this.customVerticalSlider.value2 = Math.max(value, this.customVerticalSlider.value1);
                this.y_max = this.customVerticalSlider.value2;
            }
            
            this.customVerticalSlider.updateDisplay();
            this.updateFromRange();
        });
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
        
        // Y-axis range slider - CUSTOM VERTICAL IMPLEMENTATION
        // jQuery UI vertical orientation is unreliable, so we use a custom implementation
        this.setupCustomVerticalSlider(maxH, initialYMin, initialYMax);
        
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
                // Update custom vertical slider
                if (this.customVerticalSlider) {
                    this.customVerticalSlider.value1 = min;
                    this.customVerticalSlider.value2 = max;
                    this.customVerticalSlider.updateDisplay();
                }
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
        
        // Draw ROI rectangle with Ocean Breeze Royal Blue border
        this.ctx.strokeStyle = '#2196F3'; // Royal Blue
        this.ctx.lineWidth = 3;
        this.ctx.strokeRect(x, y, w, h);
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
        // Update custom vertical slider
        if (this.customVerticalSlider) {
            this.customVerticalSlider.value1 = this.y_min;
            this.customVerticalSlider.value2 = this.y_max;
            this.customVerticalSlider.updateDisplay();
        }
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
        // Update custom vertical slider
        if (this.customVerticalSlider) {
            this.customVerticalSlider.value1 = this.y_min;
            this.customVerticalSlider.value2 = this.y_max;
            this.customVerticalSlider.updateDisplay();
        }
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
