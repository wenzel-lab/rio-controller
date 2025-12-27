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
        const self = this;
        const updateCanvasSize = function() {
            // Get displayed size first
            const rect = self.img.getBoundingClientRect();
            const displayW = rect.width || self.img.offsetWidth || 640;
            const displayH = rect.height || self.img.offsetHeight || 480;
            
            // For MJPEG streams, naturalWidth/Height may not be set
            // Use a standard camera resolution (640x480 is common default)
            // But try to get actual dimensions if available
            let imgW = 0;
            let imgH = 0;
            
            if (self.img.naturalWidth > 0 && self.img.naturalHeight > 0) {
                // Standard method - works in most browsers when image loads
                imgW = self.img.naturalWidth;
                imgH = self.img.naturalHeight;
            }
            
            // IMPORTANT: For ROI coordinate consistency, always use the actual camera resolution
            // This ensures ROI coordinates are the same across all browsers
            // Try to get resolution from global cameraResolution if available
            if (typeof window.cameraResolution !== 'undefined' && 
                window.cameraResolution.width > 0 && window.cameraResolution.height > 0) {
                self.imgWidth = window.cameraResolution.width;
                self.imgHeight = window.cameraResolution.height;
            } else if (imgW > 0 && imgH > 0) {
                // Use natural dimensions if available
                self.imgWidth = imgW;
                self.imgHeight = imgH;
            } else {
                // Fallback to standard camera resolution
                self.imgWidth = 640;
                self.imgHeight = 480;
            }
            
            // Set canvas size to match displayed image size (for drawing overlay)
            self.canvas.width = displayW;
            self.canvas.height = displayH;
            self.canvas.style.width = displayW + 'px';
            self.canvas.style.height = displayH + 'px';
            
            self.draw();
        };
        
        // Update on image load
        this.img.addEventListener('load', updateCanvasSize);
        // Also try on image error or when image is already loaded
        if (this.img.complete) {
            updateCanvasSize();
        }
        
        // Update on window resize
        window.addEventListener('resize', updateCanvasSize);
        
        // Initial update with retry
        updateCanvasSize();
        // Retry after a short delay in case image is still loading
        setTimeout(updateCanvasSize, 100);
        setTimeout(updateCanvasSize, 500);
        setTimeout(updateCanvasSize, 1000);
    }
    
    setupEventListeners() {
        // Use bind for better browser compatibility (instead of arrow functions)
        const self = this;
        // Mouse events
        this.canvas.addEventListener('mousedown', function(e) { self.onMouseDown(e); });
        this.canvas.addEventListener('mousemove', function(e) { self.onMouseMove(e); });
        this.canvas.addEventListener('mouseup', function(e) { self.onMouseUp(e); });
        this.canvas.addEventListener('mouseleave', function(e) { self.onMouseUp(e); });
        
        // Touch events (for mobile)
        this.canvas.addEventListener('touchstart', function(e) { self.onTouchStart(e); });
        this.canvas.addEventListener('touchmove', function(e) { self.onTouchMove(e); });
        this.canvas.addEventListener('touchend', function(e) { self.onTouchEnd(e); });
    }
    
    getCanvasCoordinates(e) {
        const rect = this.canvas.getBoundingClientRect();
        // CRITICAL: Use canvas.width/height (internal resolution) for scaling, not rect.width/height (CSS size)
        // This ensures consistent coordinate conversion across all browsers and CSS scaling scenarios
        const canvasW = this.canvas.width || 640;
        const canvasH = this.canvas.height || 480;
        
        // Get mouse position relative to canvas element (using rect for positioning)
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        
        // Calculate canvas coordinates (0 to canvas.width/height)
        // Account for CSS scaling: if CSS size differs from internal size, we need to scale
        const cssW = rect.width || canvasW;
        const cssH = rect.height || canvasH;
        const cssScaleX = (cssW > 0 && canvasW > 0) ? canvasW / cssW : 1;
        const cssScaleY = (cssH > 0 && canvasH > 0) ? canvasH / cssH : 1;
        
        const canvasX = (clientX - rect.left) * cssScaleX;
        const canvasY = (clientY - rect.top) * cssScaleY;
        
        // Convert canvas coordinates to image coordinates
        const scaleX = (this.imgWidth > 0 && canvasW > 0) ? this.imgWidth / canvasW : 1;
        const scaleY = (this.imgHeight > 0 && canvasH > 0) ? this.imgHeight / canvasH : 1;
        
        return {
            x: canvasX * scaleX,  // Image coordinate X
            y: canvasY * scaleY,  // Image coordinate Y
            canvasX: canvasX,     // Canvas coordinate X
            canvasY: canvasY      // Canvas coordinate Y
        };
    }
    
    getResizeHandle(x, y) {
        // x, y are in canvas coordinates (0 to canvas.width/height)
        if (!this.roi) return null;
        
        const HANDLE_SIZE = 10;
        
        // Convert ROI from image coordinates to canvas coordinates
        const canvasW = this.canvas.width || 640;
        const canvasH = this.canvas.height || 480;
        const inverseScaleX = (canvasW > 0 && this.imgWidth > 0) ? canvasW / this.imgWidth : 1;
        const inverseScaleY = (canvasH > 0 && this.imgHeight > 0) ? canvasH / this.imgHeight : 1;
        
        // ROI in canvas coordinates
        const roiX = this.roi.x * inverseScaleX;
        const roiY = this.roi.y * inverseScaleY;
        const roiW = this.roi.width * inverseScaleX;
        const roiH = this.roi.height * inverseScaleY;
        
        // Define handles in canvas coordinates
        const handles = {
            'nw': {x: roiX, y: roiY},
            'ne': {x: roiX + roiW, y: roiY},
            'sw': {x: roiX, y: roiY + roiH},
            'se': {x: roiX + roiW, y: roiY + roiH},
            'n': {x: roiX + roiW / 2, y: roiY},
            's': {x: roiX + roiW / 2, y: roiY + roiH},
            'e': {x: roiX + roiW, y: roiY + roiH / 2},
            'w': {x: roiX, y: roiY + roiH / 2}
        };
        
        // Check distance to each handle
        for (const [handle, pos] of Object.entries(handles)) {
            const dist = Math.sqrt(Math.pow(x - pos.x, 2) + Math.pow(y - pos.y, 2));
            if (dist < HANDLE_SIZE) {
                return handle;
            }
        }
        
        // Check if clicking inside ROI (for moving)
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
        
        // ROI is already stored in image coordinates, so send directly
        const imageROI = {
            x: Math.round(this.roi.x),
            y: Math.round(this.roi.y),
            width: Math.round(this.roi.width),
            height: Math.round(this.roi.height)
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
    
    updateCanvasSize() {
        /**
         * Force update of canvas size to match current image display size.
         * Call this when image size changes or after image loads.
         */
        const rect = this.img.getBoundingClientRect();
        const displayW = rect.width || this.img.offsetWidth || 640;
        const displayH = rect.height || this.img.offsetHeight || 480;
        
        // Set canvas size to match displayed image size (for drawing overlay)
        this.canvas.width = displayW;
        this.canvas.height = displayH;
        this.canvas.style.width = displayW + 'px';
        this.canvas.style.height = displayH + 'px';
        
        // Update image dimensions from cameraResolution if available
        if (typeof window.cameraResolution !== 'undefined' && 
            window.cameraResolution.width > 0 && window.cameraResolution.height > 0) {
            this.imgWidth = window.cameraResolution.width;
            this.imgHeight = window.cameraResolution.height;
        } else if (this.img.naturalWidth > 0 && this.img.naturalHeight > 0) {
            this.imgWidth = this.img.naturalWidth;
            this.imgHeight = this.img.naturalHeight;
        }
        
        this.draw();
    }
}

