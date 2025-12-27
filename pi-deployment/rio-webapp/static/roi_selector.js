/**
 * ROI (Region of Interest) Selector
 * Interactive rectangle selection on camera image
 * 
 * Features:
 * - Draw ROI by clicking and dragging
 * - Resize ROI by dragging corners/edges
 * - Move ROI by dragging center
 * - Redraw ROI multiple times
 * - Send ROI coordinates to backend via WebSocket
 */

class ROISelector {
    constructor(imageElement, canvasElement, socket) {
        this.img = imageElement;
        this.canvas = canvasElement;
        this.ctx = canvasElement.getContext('2d');
        this.socket = socket;
        
        // ROI state
        this.roi = null; // {x, y, width, height} in image coordinates
        this.isDrawing = false;
        this.isResizing = false;
        this.isMoving = false;
        this.resizeHandle = null; // 'nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'
        this.startX = 0;
        this.startY = 0;
        this.startROI = null;
        
        // Image dimensions (updated when image loads)
        this.imgWidth = 0;
        this.imgHeight = 0;
        
        // Setup
        this.setupCanvas();
        this.setupEventListeners();
        this.loadROI(); // Load saved ROI if available
    }
    
    setupCanvas() {
        // Match canvas size to image
        const updateCanvasSize = () => {
            if (this.img.complete && this.img.naturalWidth > 0) {
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
        
        // Update on image load
        this.img.addEventListener('load', updateCanvasSize);
        
        // Update on window resize
        window.addEventListener('resize', updateCanvasSize);
        
        // Initial update
        updateCanvasSize();
    }
    
    setupEventListeners() {
        // Mouse events
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('mouseleave', (e) => this.onMouseUp(e));
        
        // Touch events (for mobile)
        this.canvas.addEventListener('touchstart', (e) => this.onTouchStart(e));
        this.canvas.addEventListener('touchmove', (e) => this.onTouchMove(e));
        this.canvas.addEventListener('touchend', (e) => this.onTouchEnd(e));
    }
    
    getCanvasCoordinates(e) {
        const rect = this.canvas.getBoundingClientRect();
        const scaleX = this.imgWidth / rect.width;
        const scaleY = this.imgHeight / rect.height;
        
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        
        return {
            x: (clientX - rect.left) * scaleX,
            y: (clientY - rect.top) * scaleY,
            canvasX: clientX - rect.left,
            canvasY: clientY - rect.top
        };
    }
    
    getResizeHandle(x, y) {
        if (!this.roi) return null;
        
        const HANDLE_SIZE = 10;
        const handles = {
            'nw': {x: this.roi.x, y: this.roi.y},
            'ne': {x: this.roi.x + this.roi.width, y: this.roi.y},
            'sw': {x: this.roi.x, y: this.roi.y + this.roi.height},
            'se': {x: this.roi.x + this.roi.width, y: this.roi.y + this.roi.height},
            'n': {x: this.roi.x + this.roi.width / 2, y: this.roi.y},
            's': {x: this.roi.x + this.roi.width / 2, y: this.roi.y + this.roi.height},
            'e': {x: this.roi.x + this.roi.width, y: this.roi.y + this.roi.height / 2},
            'w': {x: this.roi.x, y: this.roi.y + this.roi.height / 2}
        };
        
        const scaleX = this.imgWidth / this.canvas.width;
        const scaleY = this.imgHeight / this.canvas.height;
        
        for (const [handle, pos] of Object.entries(handles)) {
            const handleX = pos.x / scaleX;
            const handleY = pos.y / scaleY;
            const dist = Math.sqrt(Math.pow(x - handleX, 2) + Math.pow(y - handleY, 2));
            if (dist < HANDLE_SIZE) {
                return handle;
            }
        }
        
        // Check if clicking inside ROI (for moving)
        const roiX = this.roi.x / scaleX;
        const roiY = this.roi.y / scaleY;
        const roiW = this.roi.width / scaleX;
        const roiH = this.roi.height / scaleY;
        
        if (x >= roiX && x <= roiX + roiW && y >= roiY && y <= roiY + roiH) {
            return 'move';
        }
        
        return null;
    }
    
    onMouseDown(e) {
        e.preventDefault();
        const coords = this.getCanvasCoordinates(e);
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
        const coords = this.getCanvasCoordinates(e);
        
        if (this.isDrawing) {
            // Draw new ROI
            this.roi.width = coords.x - this.roi.x;
            this.roi.height = coords.y - this.roi.y;
            this.draw();
        } else if (this.isResizing && this.startROI) {
            // Resize existing ROI
            const dx = coords.x - this.startX;
            const dy = coords.y - this.startY;
            
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
            
            // Ensure minimum size
            if (this.roi.width < 10) {
                this.roi.width = 10;
                if (this.resizeHandle.includes('w')) {
                    this.roi.x = this.startROI.x + this.startROI.width - 10;
                }
            }
            if (this.roi.height < 10) {
                this.roi.height = 10;
                if (this.resizeHandle.includes('n')) {
                    this.roi.y = this.startROI.y + this.startROI.height - 10;
                }
            }
            
            this.draw();
        } else if (this.isMoving && this.startROI) {
            // Move ROI
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
            // Normalize ROI (ensure positive width/height)
            if (this.roi.width < 0) {
                this.roi.x += this.roi.width;
                this.roi.width = Math.abs(this.roi.width);
            }
            if (this.roi.height < 0) {
                this.roi.y += this.roi.height;
                this.roi.height = Math.abs(this.roi.height);
            }
            
            // Clamp to image bounds
            this.roi.x = Math.max(0, Math.min(this.roi.x, this.imgWidth));
            this.roi.y = Math.max(0, Math.min(this.roi.y, this.imgHeight));
            this.roi.width = Math.min(this.roi.width, this.imgWidth - this.roi.x);
            this.roi.height = Math.min(this.roi.height, this.imgHeight - this.roi.y);
            
            // Save ROI
            this.saveROI();
            
            this.isDrawing = false;
            this.isResizing = false;
            this.isMoving = false;
            this.resizeHandle = null;
        }
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
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        if (!this.roi || this.roi.width === 0 || this.roi.height === 0) {
            return;
        }
        
        // Calculate scale
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
            {x: x, y: y}, // nw
            {x: x + w, y: y}, // ne
            {x: x, y: y + h}, // sw
            {x: x + w, y: y + h}, // se
            {x: x + w/2, y: y}, // n
            {x: x + w/2, y: y + h}, // s
            {x: x + w, y: y + h/2}, // e
            {x: x, y: y + h/2} // w
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
    
    saveROI() {
        if (!this.roi || this.roi.width <= 0 || this.roi.height <= 0) return;
        
        // Convert from canvas coordinates to image coordinates
        const scaleX = this.imgWidth / this.canvas.width;
        const scaleY = this.imgHeight / this.canvas.height;
        
        const imageROI = {
            x: Math.round(this.roi.x * scaleX),
            y: Math.round(this.roi.y * scaleY),
            width: Math.round(this.roi.width * scaleX),
            height: Math.round(this.roi.height * scaleY)
        };
        
        // Save to localStorage
        localStorage.setItem('camera_roi', JSON.stringify(imageROI));
        
        // Send to server (in image coordinates)
        if (this.socket) {
            this.socket.emit('roi', {
                cmd: 'set',
                parameters: imageROI
            });
        }
        
        // Trigger ROI info update
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }
    
    loadROI() {
        // Try to load from backend first (via WebSocket response)
        // For now, load from localStorage
        const saved = localStorage.getItem('camera_roi');
        if (saved) {
            try {
                this.roi = JSON.parse(saved);
                this.draw();
            } catch (e) {
                console.error('Failed to load ROI:', e);
            }
        }
    }
    
    clearROI(sendToServer = true) {
        /**
         * Clear the ROI selection.
         * 
         * @param {boolean} sendToServer - If true, send clear command to server.
         *                                  If false, only clear locally (used when
         *                                  receiving clear notification from server).
         */
        this.roi = null;
        this.draw();
        if (this.socket && sendToServer) {
            this.socket.emit('roi', {cmd: 'clear'});
        }
        localStorage.removeItem('camera_roi');
        // Trigger ROI info update
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }
    
    getROI() {
        return this.roi;
    }
    
    setROI(roi) {
        this.roi = roi;
        this.draw();
        // Trigger ROI info update when ROI is set from server
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }
}

