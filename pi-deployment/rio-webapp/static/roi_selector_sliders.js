/**
 * ROI (Region of Interest) Selector - Slider-based UI
 * 
 * This implementation uses sliders and input fields instead of free-form
 * canvas selection for better reliability across browsers and reduced
 * resource usage on Raspberry Pi.
 * 
 * Features:
 * - Slider-based ROI selection (more reliable than canvas-based)
 * - Input fields for precise coordinate entry
 * - Works consistently across Pi browser and Mac browser
 * - Lower resource usage than canvas-based selection
 * - Visual preview on camera image
 */

class ROISelectorSliders {
    constructor(imageElement, socket, maxWidth, maxHeight) {
        this.img = imageElement;
        this.socket = socket;
        
        // Maximum image dimensions (from camera)
        this.maxWidth = maxWidth || 1920;
        this.maxHeight = maxHeight || 1080;
        
        // Current ROI state (in image coordinates)
        this.roi = null; // {x, y, width, height}
        
        // Canvas for visual overlay (optional, lighter than interactive canvas)
        this.canvas = null;
        this.ctx = null;
        
        // Setup
        this.setupCanvas();
        this.setupEventListeners();
        this.loadROI(); // Load saved ROI if available
    }
    
    setupCanvas() {
        // Create a lightweight canvas for visual overlay only (not interactive)
        const container = this.img.parentElement;
        if (!container) return;
        
        // Check if canvas already exists
        let existingCanvas = container.querySelector('#roi_overlay_canvas');
        if (existingCanvas) {
            this.canvas = existingCanvas;
        } else {
            this.canvas = document.createElement('canvas');
            this.canvas.id = 'roi_overlay_canvas';
            this.canvas.style.position = 'absolute';
            this.canvas.style.top = '0';
            this.canvas.style.left = '0';
            this.canvas.style.pointerEvents = 'none'; // Not interactive
            container.style.position = 'relative';
            container.appendChild(this.canvas);
        }
        
        this.ctx = this.canvas.getContext('2d');
        this.updateCanvasSize();
        
        // Update canvas size when image loads/resizes
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
                    this.setROI(data.roi);
                } else {
                    this.clearROI(false); // false = don't send to server
                }
            });
            
            // Request current ROI from server
            this.socket.emit('roi', {cmd: 'get'});
        }
    }
    
    draw() {
        if (!this.ctx || !this.roi) return;
        
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
        const info = `ROI: (${this.roi.x}, ${this.roi.y}) ${this.roi.width}×${this.roi.height}`;
        this.ctx.fillText(info, x + 5, y - 5);
    }
    
    setROI(roi) {
        // Clamp ROI to valid bounds
        this.roi = {
            x: Math.max(0, Math.min(roi.x, this.maxWidth)),
            y: Math.max(0, Math.min(roi.y, this.maxHeight)),
            width: Math.max(10, Math.min(roi.width, this.maxWidth - roi.x)),
            height: Math.max(10, Math.min(roi.height, this.maxHeight - roi.y))
        };
        
        this.draw();
        this.updateUI();
        
        // Trigger ROI info update
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }
    
    getROI() {
        return this.roi;
    }
    
    clearROI(sendToServer = true) {
        this.roi = null;
        if (this.ctx) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
        this.updateUI();
        
        if (this.socket && sendToServer) {
            this.socket.emit('roi', {cmd: 'clear'});
        }
        
        localStorage.removeItem('camera_roi');
        
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }
    
    updateUI() {
        // Update slider/input UI elements if they exist
        const xInput = document.getElementById('roi_x');
        const yInput = document.getElementById('roi_y');
        const widthInput = document.getElementById('roi_width');
        const heightInput = document.getElementById('roi_height');
        
        if (this.roi) {
            if (xInput) xInput.value = this.roi.x;
            if (yInput) yInput.value = this.roi.y;
            if (widthInput) widthInput.value = this.roi.width;
            if (heightInput) heightInput.value = this.roi.height;
        } else {
            if (xInput) xInput.value = 0;
            if (yInput) yInput.value = 0;
            if (widthInput) widthInput.value = 0;
            if (heightInput) heightInput.value = 0;
        }
    }
    
    loadROI() {
        // Try to load from localStorage
        const saved = localStorage.getItem('camera_roi');
        if (saved) {
            try {
                const roi = JSON.parse(saved);
                this.setROI(roi);
            } catch (e) {
                console.error('Failed to load ROI:', e);
            }
        }
    }
    
    saveROI() {
        if (!this.roi) return;
        
        // Save to localStorage
        localStorage.setItem('camera_roi', JSON.stringify(this.roi));
        
        // Send to server
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
    
    // Method to update ROI from slider/input values
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
            this.saveROI();
        }
    }
}

// Make updateFromInputs accessible globally for inline event handlers
if (typeof window !== 'undefined') {
    window.ROISelectorSliders = ROISelectorSliders;
}

