/**
 * ROI (Region of Interest) Selector - Improved Implementation
 * 
 * Based on standard image processing practices:
 * - Click-and-drag for primary selection (intuitive, standard approach)
 * - Numeric inputs for fine-tuning (not sliders - more precise)
 * - Proper coordinate handling across browsers
 * - Camera constraint validation (for Mako cameras)
 * 
 * Features:
 * - Interactive click-and-drag ROI selection on image
 * - Resize by dragging corners/edges
 * - Move by dragging center
 * - Numeric input fields for precise adjustment
 * - Automatic validation against camera constraints
 * - Works consistently across Pi browser and Mac browser
 */

class ROISelectorImproved {
    constructor(imageElement, canvasElement, socket, constraints = null) {
        this.img = imageElement;
        this.canvas = canvasElement;
        this.ctx = canvasElement.getContext('2d');
        this.socket = socket;
        
        // Camera constraints (from Mako camera API if available)
        this.constraints = constraints || {
            offset_x: {min: 0, max: 1920, increment: 1},
            offset_y: {min: 0, max: 1080, increment: 1},
            width: {min: 10, max: 1920, increment: 1},
            height: {min: 10, max: 1080, increment: 1}
        };
        
        // ROI state (in image coordinates, not canvas coordinates)
        this.roi = null; // {x, y, width, height}
        this.isDrawing = false;
        this.isResizing = false;
        this.isMoving = false;
        this.resizeHandle = null;
        this.startX = 0;
        this.startY = 0;
        this.startROI = null;
        
        // Image dimensions (actual image size, not displayed size)
        this.imgWidth = 0;
        this.imgHeight = 0;
        
        // Setup
        this.setupCanvas();
        this.setupEventListeners();
        this.loadROI();
    }
    
    setupCanvas() {
        // Match canvas size to displayed image size
        const updateCanvasSize = () => {
            if (this.img.complete && this.img.naturalWidth > 0) {
                // Use naturalWidth/naturalHeight for actual image dimensions
                this.imgWidth = this.img.naturalWidth;
                this.imgHeight = this.img.naturalHeight;
                
                // Set canvas size to match displayed image size
                const rect = this.img.getBoundingClientRect();
                this.canvas.width = rect.width;
                this.canvas.height = rect.height;
                this.canvas.style.width = rect.width + 'px';
                this.canvas.style.height = rect.height + 'px';
                
                this.draw();
            }
        };
        
        this.img.addEventListener('load', updateCanvasSize);
        window.addEventListener('resize', updateCanvasSize);
        updateCanvasSize();
    }
    
    setupEventListeners() {
        // Mouse events
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('mouseleave', (e) => this.onMouseUp(e));
        
        // Touch events
        this.canvas.addEventListener('touchstart', (e) => this.onTouchStart(e));
        this.canvas.addEventListener('touchmove', (e) => this.onTouchMove(e));
        this.canvas.addEventListener('touchend', (e) => this.onTouchEnd(e));
        
        // Listen for ROI updates from server
        if (this.socket) {
            this.socket.on('roi', (data) => {
                if (data.roi) {
                    // Server sends ROI in image coordinates - use directly
                    this.setROI(data.roi, false); // false = don't send back to server
                } else {
                    this.clearROI(false);
                }
            });
            
            // Request current ROI and constraints from server
            this.socket.emit('roi', {cmd: 'get'});
        }
    }
    
    getImageCoordinates(e) {
        // Get coordinates in image pixel space (not canvas pixel space)
        const rect = this.canvas.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        
        // Canvas coordinates (displayed size)
        const canvasX = clientX - rect.left;
        const canvasY = clientY - rect.top;
        
        // Convert to image coordinates (actual image size)
        const scaleX = this.imgWidth / this.canvas.width;
        const scaleY = this.imgHeight / this.canvas.height;
        
        return {
            x: canvasX * scaleX,
            y: canvasY * scaleY,
            canvasX: canvasX,
            canvasY: canvasY
        };
    }
    
    getResizeHandle(x, y) {
        if (!this.roi) return null;
        
        const HANDLE_SIZE = 10;
        const scaleX = this.canvas.width / this.imgWidth;
        const scaleY = this.canvas.height / this.imgHeight;
        
        // Handle positions in canvas coordinates
        const handles = {
            'nw': {x: this.roi.x * scaleX, y: this.roi.y * scaleY},
            'ne': {x: (this.roi.x + this.roi.width) * scaleX, y: this.roi.y * scaleY},
            'sw': {x: this.roi.x * scaleX, y: (this.roi.y + this.roi.height) * scaleY},
            'se': {x: (this.roi.x + this.roi.width) * scaleX, y: (this.roi.y + this.roi.height) * scaleY},
            'n': {x: (this.roi.x + this.roi.width / 2) * scaleX, y: this.roi.y * scaleY},
            's': {x: (this.roi.x + this.roi.width / 2) * scaleX, y: (this.roi.y + this.roi.height) * scaleY},
            'e': {x: (this.roi.x + this.roi.width) * scaleX, y: (this.roi.y + this.roi.height / 2) * scaleY},
            'w': {x: this.roi.x * scaleX, y: (this.roi.y + this.roi.height / 2) * scaleY}
        };
        
        for (const [handle, pos] of Object.entries(handles)) {
            const dist = Math.sqrt(Math.pow(x - pos.x, 2) + Math.pow(y - pos.y, 2));
            if (dist < HANDLE_SIZE) {
                return handle;
            }
        }
        
        // Check if clicking inside ROI (for moving)
        const roiX = this.roi.x * scaleX;
        const roiY = this.roi.y * scaleY;
        const roiW = this.roi.width * scaleX;
        const roiH = this.roi.height * scaleY;
        
        if (x >= roiX && x <= roiX + roiW && y >= roiY && y <= roiY + roiH) {
            return 'move';
        }
        
        return null;
    }
    
    onMouseDown(e) {
        e.preventDefault();
        const coords = this.getImageCoordinates(e);
        this.startX = coords.x;
        this.startY = coords.y;
        this.startROI = this.roi ? {...this.roi} : null;
        
        if (this.roi) {
            const handle = this.getResizeHandle(coords.canvasX, coords.canvasY);
            if (handle === 'move') {
                this.isMoving = true;
            } else if (handle) {
                this.isResizing = true;
                this.resizeHandle = handle;
            } else {
                // Start new ROI
                this.roi = {x: coords.x, y: coords.y, width: 0, height: 0};
                this.isDrawing = true;
            }
        } else {
            // Start new ROI
            this.roi = {x: coords.x, y: coords.y, width: 0, height: 0};
            this.isDrawing = true;
        }
    }
    
    onMouseMove(e) {
        e.preventDefault();
        const coords = this.getImageCoordinates(e);
        
        if (this.isDrawing) {
            this.roi.width = coords.x - this.roi.x;
            this.roi.height = coords.y - this.roi.y;
            this.draw();
        } else if (this.isResizing && this.startROI) {
            const dx = coords.x - this.startX;
            const dy = coords.y - this.startY;
            
            // Resize logic (same as before)
            switch (this.resizeHandle) {
                case 'nw':
                    this.roi.x = this.startROI.x + dx;
                    this.roi.y = this.startROI.y + dy;
                    this.roi.width = this.startROI.width - dx;
                    this.roi.height = this.startROI.height - dy;
                    break;
                case 'ne':
                    this.roi.y = this.startROI.y + dy;
                    this.roi.width = this.startROI.width + dx;
                    this.roi.height = this.startROI.height - dy;
                    break;
                case 'sw':
                    this.roi.x = this.startROI.x + dx;
                    this.roi.width = this.startROI.width - dx;
                    this.roi.height = this.startROI.height + dy;
                    break;
                case 'se':
                    this.roi.width = this.startROI.width + dx;
                    this.roi.height = this.startROI.height + dy;
                    break;
                case 'n':
                    this.roi.y = this.startROI.y + dy;
                    this.roi.height = this.startROI.height - dy;
                    break;
                case 's':
                    this.roi.height = this.startROI.height + dy;
                    break;
                case 'e':
                    this.roi.width = this.startROI.width + dx;
                    break;
                case 'w':
                    this.roi.x = this.startROI.x + dx;
                    this.roi.width = this.startROI.width - dx;
                    break;
            }
            
            this.draw();
        } else if (this.isMoving && this.startROI) {
            const dx = coords.x - this.startX;
            const dy = coords.y - this.startY;
            this.roi.x = this.startROI.x + dx;
            this.roi.y = this.startROI.y + dy;
            this.draw();
        } else if (this.roi) {
            // Update cursor
            const handle = this.getResizeHandle(coords.canvasX, coords.canvasY);
            if (handle === 'move') {
                this.canvas.style.cursor = 'move';
            } else if (handle) {
                const cursors = {
                    'nw': 'nw-resize', 'ne': 'ne-resize',
                    'sw': 'sw-resize', 'se': 'se-resize',
                    'n': 'n-resize', 's': 's-resize',
                    'e': 'e-resize', 'w': 'w-resize'
                };
                this.canvas.style.cursor = cursors[handle] || 'default';
            } else {
                this.canvas.style.cursor = 'crosshair';
            }
        }
    }
    
    onMouseUp(e) {
        e.preventDefault();
        if (this.isDrawing || this.isResizing || this.isMoving) {
            // Normalize ROI
            if (this.roi.width < 0) {
                this.roi.x += this.roi.width;
                this.roi.width = Math.abs(this.roi.width);
            }
            if (this.roi.height < 0) {
                this.roi.y += this.roi.height;
                this.roi.height = Math.abs(this.roi.height);
            }
            
            // Validate and snap to constraints
            this.validateAndSnapROI();
            
            // Clamp to image bounds
            this.roi.x = Math.max(0, Math.min(this.roi.x, this.imgWidth));
            this.roi.y = Math.max(0, Math.min(this.roi.y, this.imgHeight));
            this.roi.width = Math.min(this.roi.width, this.imgWidth - this.roi.x);
            this.roi.height = Math.min(this.roi.height, this.imgHeight - this.roi.y);
            
            this.saveROI();
            this.updateNumericInputs();
            
            this.isDrawing = false;
            this.isResizing = false;
            this.isMoving = false;
            this.resizeHandle = null;
        }
    }
    
    validateAndSnapROI() {
        if (!this.roi) return;
        
        // Snap to increments
        const snapToIncrement = (value, min, max, increment) => {
            const snapped = Math.round(value / increment) * increment;
            return Math.max(min, Math.min(max, snapped));
        };
        
        this.roi.x = snapToIncrement(
            this.roi.x,
            this.constraints.offset_x.min,
            this.constraints.offset_x.max,
            this.constraints.offset_x.increment
        );
        
        this.roi.y = snapToIncrement(
            this.roi.y,
            this.constraints.offset_y.min,
            this.constraints.offset_y.max,
            this.constraints.offset_y.increment
        );
        
        this.roi.width = snapToIncrement(
            this.roi.width,
            this.constraints.width.min,
            Math.min(this.constraints.width.max, this.imgWidth - this.roi.x),
            this.constraints.width.increment
        );
        
        this.roi.height = snapToIncrement(
            this.roi.height,
            this.constraints.height.min,
            Math.min(this.constraints.height.max, this.imgHeight - this.roi.y),
            this.constraints.height.increment
        );
    }
    
    onTouchStart(e) {
        e.preventDefault();
        this.onMouseDown(e);
    }
    
    onTouchMove(e) {
        e.preventDefault();
        this.onMouseMove(e);
    }
    
    onTouchEnd(e) {
        e.preventDefault();
        this.onMouseUp(e);
    }
    
    draw() {
        if (!this.ctx || !this.roi) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            return;
        }
        
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        if (!this.roi.width || !this.roi.height) return;
        
        // Calculate scale from image to canvas
        const scaleX = this.canvas.width / this.imgWidth;
        const scaleY = this.canvas.height / this.imgHeight;
        
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
        
        // Draw resize handles
        const HANDLE_SIZE = 8;
        this.ctx.fillStyle = '#00ff00';
        const handles = [
            {x: x, y: y}, {x: x + w, y: y},
            {x: x, y: y + h}, {x: x + w, y: y + h},
            {x: x + w/2, y: y}, {x: x + w/2, y: y + h},
            {x: x + w, y: y + h/2}, {x: x, y: y + h/2}
        ];
        handles.forEach(handle => {
            this.ctx.fillRect(handle.x - HANDLE_SIZE/2, handle.y - HANDLE_SIZE/2, HANDLE_SIZE, HANDLE_SIZE);
        });
        
        // Draw ROI info
        this.ctx.fillStyle = '#ffffff';
        this.ctx.font = '12px Arial';
        const info = `ROI: (${Math.round(this.roi.x)}, ${Math.round(this.roi.y)}) ${Math.round(this.roi.width)}×${Math.round(this.roi.height)}`;
        this.ctx.fillText(info, x + 5, y - 5);
    }
    
    setROI(roi, sendToServer = true) {
        this.roi = {
            x: roi.x,
            y: roi.y,
            width: roi.width,
            height: roi.height
        };
        this.validateAndSnapROI();
        this.draw();
        this.updateNumericInputs();
        
        if (sendToServer) {
            this.saveROI();
        }
        
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }
    
    getROI() {
        return this.roi;
    }
    
    clearROI(sendToServer = true) {
        this.roi = null;
        this.draw();
        this.updateNumericInputs();
        
        if (this.socket && sendToServer) {
            this.socket.emit('roi', {cmd: 'clear'});
        }
        
        localStorage.removeItem('camera_roi');
        
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }
    
    updateNumericInputs() {
        // Update numeric input fields if they exist
        const xInput = document.getElementById('roi_x');
        const yInput = document.getElementById('roi_y');
        const widthInput = document.getElementById('roi_width');
        const heightInput = document.getElementById('roi_height');
        
        if (this.roi) {
            if (xInput) xInput.value = Math.round(this.roi.x);
            if (yInput) yInput.value = Math.round(this.roi.y);
            if (widthInput) widthInput.value = Math.round(this.roi.width);
            if (heightInput) heightInput.value = Math.round(this.roi.height);
        } else {
            if (xInput) xInput.value = '';
            if (yInput) yInput.value = '';
            if (widthInput) widthInput.value = '';
            if (heightInput) heightInput.value = '';
        }
    }
    
    updateFromNumericInputs() {
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
        this.constraints = constraints;
        if (this.roi) {
            this.validateAndSnapROI();
            this.draw();
            this.updateNumericInputs();
        }
    }
}

