/**
 * ROI (Region of Interest) Selector - Refactored Version
 * 
 * Interactive rectangle selection on camera image with proper separation of concerns.
 * 
 * Architecture:
 * - View: DOM manipulation and rendering
 * - Model: ROI state management
 * - Controller: Event handling and WebSocket communication
 * 
 * Features:
 * - Draw ROI by clicking and dragging
 * - Resize ROI by dragging corners/edges
 * - Move ROI by dragging center
 * - Redraw ROI multiple times
 * - Send ROI coordinates to backend via WebSocket
 * - Load/save ROI from localStorage
 * 
 * @class ROISelector
 */
class ROISelector {
    /**
     * Create a new ROI selector instance.
     * 
     * @param {HTMLImageElement} imageElement - The image element to overlay
     * @param {HTMLCanvasElement} canvasElement - The canvas element for drawing
     * @param {Socket} socket - WebSocket connection for server communication
     */
    constructor(imageElement, canvasElement, socket) {
        // Validate inputs
        if (!imageElement || !canvasElement) {
            throw new Error('ROISelector requires both image and canvas elements');
        }
        
        // View elements
        this.img = imageElement;
        this.canvas = canvasElement;
        this.ctx = canvasElement.getContext('2d');
        if (!this.ctx) {
            throw new Error('Could not get 2D context from canvas');
        }
        
        // Controller: WebSocket connection
        this.socket = socket;
        
        // Model: ROI state
        this.roi = null; // {x, y, width, height} in image coordinates
        this.isDrawing = false;
        this.isResizing = false;
        this.isMoving = false;
        this.resizeHandle = null; // 'nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w', 'move'
        this.startX = 0;
        this.startY = 0;
        this.startROI = null;
        
        // View: Image dimensions (updated when image loads)
        this.imgWidth = 0;
        this.imgHeight = 0;
        
        // Constants
        this.MIN_ROI_SIZE = 10; // Minimum ROI size in pixels
        this.HANDLE_SIZE = 10; // Resize handle size in pixels
        this.STROKE_COLOR = '#00ff00'; // Green stroke
        this.FILL_COLOR = 'rgba(0, 255, 0, 0.1)'; // Semi-transparent green fill
        this.HANDLE_COLOR = '#ffff00'; // Yellow handles
        
        // Initialize
        this.setupCanvas();
        this.setupEventListeners();
        this.loadROI(); // Load saved ROI if available
    }
    
    /**
     * Setup canvas to match image size and handle resizing.
     * View layer: DOM manipulation
     */
    setupCanvas() {
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
    
    /**
     * Setup event listeners for mouse and touch events.
     * Controller layer: Event handling
     */
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
    
    /**
     * Convert event coordinates to canvas and image coordinates.
     * View layer: Coordinate transformation
     * 
     * @param {MouseEvent|TouchEvent} e - Mouse or touch event
     * @returns {Object} Coordinates in both canvas and image space
     */
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
    
    /**
     * Get resize handle at given coordinates.
     * Model layer: State query
     * 
     * @param {number} x - X coordinate in canvas space
     * @param {number} y - Y coordinate in canvas space
     * @returns {string|null} Handle name or null
     */
    getResizeHandle(x, y) {
        if (!this.roi) return null;
        
        const scaleX = this.canvas.width / this.imgWidth;
        const scaleY = this.canvas.height / this.imgHeight;
        const roiX = this.roi.x * scaleX;
        const roiY = this.roi.y * scaleY;
        const roiW = this.roi.width * scaleX;
        const roiH = this.roi.height * scaleY;
        
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
        
        // Check if clicking inside ROI (for moving)
        if (x >= roiX && x <= roiX + roiW && y >= roiY && y <= roiY + roiH) {
            // Check if near center (for moving)
            const centerX = roiX + roiW / 2;
            const centerY = roiY + roiH / 2;
            const distFromCenter = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2);
            const minDist = Math.min(roiW, roiH) / 4;
            
            if (distFromCenter < minDist) {
                return 'move';
            }
        }
        
        // Check each handle
        for (const [name, pos] of Object.entries(handles)) {
            const dist = Math.sqrt((x - pos.x) ** 2 + (y - pos.y) ** 2);
            if (dist < this.HANDLE_SIZE) {
                return name;
            }
        }
        
        return null;
    }
    
    /**
     * Handle mouse down event.
     * Controller layer: Event handling
     * 
     * @param {MouseEvent} e - Mouse event
     */
    onMouseDown(e) {
        e.preventDefault();
        const coords = this.getCanvasCoordinates(e);
        const handle = this.getResizeHandle(coords.canvasX, coords.canvasY);
        
        this.startX = coords.x;
        this.startY = coords.y;
        this.startROI = this.roi ? {...this.roi} : null;
        
        if (handle === 'move' && this.roi) {
            this.isMoving = true;
        } else if (handle) {
            this.isResizing = true;
            this.resizeHandle = handle;
        } else {
            this.isDrawing = true;
            this.roi = {
                x: coords.x,
                y: coords.y,
                width: 0,
                height: 0
            };
        }
    }
    
    /**
     * Handle mouse move event.
     * Controller layer: Event handling
     * 
     * @param {MouseEvent} e - Mouse event
     */
    onMouseMove(e) {
        const coords = this.getCanvasCoordinates(e);
        
        if (this.isDrawing) {
            // Update ROI while drawing
            this.roi.width = coords.x - this.roi.x;
            this.roi.height = coords.y - this.roi.y;
            this.draw();
        } else if (this.isResizing && this.startROI) {
            // Resize ROI
            const dx = coords.x - this.startX;
            const dy = coords.y - this.startY;
            this.resizeROI(dx, dy);
            this.draw();
        } else if (this.isMoving && this.startROI) {
            // Move ROI
            const dx = coords.x - this.startX;
            const dy = coords.y - this.startY;
            this.roi.x = this.startROI.x + dx;
            this.roi.y = this.startROI.y + dy;
            this.draw();
        } else if (this.roi) {
            // Update cursor based on handle
            const handle = this.getResizeHandle(coords.canvasX, coords.canvasY);
            this.updateCursor(handle);
        }
    }
    
    /**
     * Handle mouse up event.
     * Controller layer: Event handling
     * 
     * @param {MouseEvent} e - Mouse event
     */
    onMouseUp(e) {
        if (this.isDrawing || this.isResizing || this.isMoving) {
            // Normalize ROI (ensure positive width/height)
            if (this.roi) {
                if (this.roi.width < 0) {
                    this.roi.x += this.roi.width;
                    this.roi.width = -this.roi.width;
                }
                if (this.roi.height < 0) {
                    this.roi.y += this.roi.height;
                    this.roi.height = -this.roi.height;
                }
                
                // Enforce minimum size
                if (this.roi.width < this.MIN_ROI_SIZE) {
                    this.roi.width = this.MIN_ROI_SIZE;
                }
                if (this.roi.height < this.MIN_ROI_SIZE) {
                    this.roi.height = this.MIN_ROI_SIZE;
                }
                
                // Clamp to image bounds
                this.clampROIToBounds();
                
                // Save ROI
                this.saveROI();
            }
        }
        
        this.isDrawing = false;
        this.isResizing = false;
        this.isMoving = false;
        this.resizeHandle = null;
        this.canvas.style.cursor = 'crosshair';
    }
    
    /**
     * Resize ROI based on handle and delta.
     * Model layer: State modification
     * 
     * @param {number} dx - Delta X
     * @param {number} dy - Delta Y
     */
    resizeROI(dx, dy) {
        if (!this.roi || !this.startROI) return;
        
        const scaleX = this.canvas.width / this.imgWidth;
        const scaleY = this.canvas.height / this.imgHeight;
        const scaledDx = dx;
        const scaledDy = dy;
        
        switch (this.resizeHandle) {
            case 'nw':
                this.roi.x = this.startROI.x + scaledDx;
                this.roi.y = this.startROI.y + scaledDy;
                this.roi.width = this.startROI.width - scaledDx;
                this.roi.height = this.startROI.height - scaledDy;
                break;
            case 'ne':
                this.roi.y = this.startROI.y + scaledDy;
                this.roi.width = this.startROI.width + scaledDx;
                this.roi.height = this.startROI.height - scaledDy;
                break;
            case 'sw':
                this.roi.x = this.startROI.x + scaledDx;
                this.roi.width = this.startROI.width - scaledDx;
                this.roi.height = this.startROI.height + scaledDy;
                break;
            case 'se':
                this.roi.width = this.startROI.width + scaledDx;
                this.roi.height = this.startROI.height + scaledDy;
                break;
            case 'n':
                this.roi.y = this.startROI.y + scaledDy;
                this.roi.height = this.startROI.height - scaledDy;
                break;
            case 's':
                this.roi.height = this.startROI.height + scaledDy;
                break;
            case 'e':
                this.roi.width = this.startROI.width + scaledDx;
                break;
            case 'w':
                this.roi.x = this.startROI.x + scaledDx;
                this.roi.width = this.startROI.width - scaledDx;
                break;
        }
        
        // Enforce minimum size
        if (this.roi.width < this.MIN_ROI_SIZE) {
            this.roi.width = this.MIN_ROI_SIZE;
            if (this.resizeHandle && this.resizeHandle.includes('w')) {
                this.roi.x = this.startROI.x + this.startROI.width - this.MIN_ROI_SIZE;
            }
        }
        if (this.roi.height < this.MIN_ROI_SIZE) {
            this.roi.height = this.MIN_ROI_SIZE;
            if (this.resizeHandle && this.resizeHandle.includes('n')) {
                this.roi.y = this.startROI.y + this.startROI.height - this.MIN_ROI_SIZE;
            }
        }
    }
    
    /**
     * Clamp ROI to image bounds.
     * Model layer: State validation
     */
    clampROIToBounds() {
        if (!this.roi) return;
        
        if (this.roi.x < 0) {
            this.roi.width += this.roi.x;
            this.roi.x = 0;
        }
        if (this.roi.y < 0) {
            this.roi.height += this.roi.y;
            this.roi.y = 0;
        }
        if (this.roi.x + this.roi.width > this.imgWidth) {
            this.roi.width = this.imgWidth - this.roi.x;
        }
        if (this.roi.y + this.roi.height > this.imgHeight) {
            this.roi.height = this.imgHeight - this.roi.y;
        }
    }
    
    /**
     * Update cursor based on resize handle.
     * View layer: UI feedback
     * 
     * @param {string|null} handle - Handle name or null
     */
    updateCursor(handle) {
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
    
    /**
     * Draw ROI and handles on canvas.
     * View layer: Rendering
     */
    draw() {
        if (!this.roi || this.roi.width <= 0 || this.roi.height <= 0) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            return;
        }
        
        const scaleX = this.canvas.width / this.imgWidth;
        const scaleY = this.canvas.height / this.imgHeight;
        const x = this.roi.x * scaleX;
        const y = this.roi.y * scaleY;
        const w = this.roi.width * scaleX;
        const h = this.roi.height * scaleY;
        
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw ROI rectangle
        this.ctx.strokeStyle = this.STROKE_COLOR;
        this.ctx.lineWidth = 2;
        this.ctx.fillStyle = this.FILL_COLOR;
        this.ctx.fillRect(x, y, w, h);
        this.ctx.strokeRect(x, y, w, h);
        
        // Draw resize handles
        this.ctx.fillStyle = this.HANDLE_COLOR;
        const handles = [
            {x: x, y: y}, // nw
            {x: x + w, y: y}, // ne
            {x: x, y: y + h}, // sw
            {x: x + w, y: y + h}, // se
            {x: x + w / 2, y: y}, // n
            {x: x + w / 2, y: y + h}, // s
            {x: x + w, y: y + h / 2}, // e
            {x: x, y: y + h / 2} // w
        ];
        
        handles.forEach(handle => {
            this.ctx.fillRect(handle.x - this.HANDLE_SIZE / 2, handle.y - this.HANDLE_SIZE / 2,
                            this.HANDLE_SIZE, this.HANDLE_SIZE);
        });
    }
    
    /**
     * Save ROI to server and localStorage.
     * Controller layer: Data persistence
     */
    saveROI() {
        if (this.roi && this.roi.width > 0 && this.roi.height > 0) {
            // Send to backend via WebSocket
            if (this.socket) {
                this.socket.emit('roi', {
                    cmd: 'set',
                    parameters: {
                        x: Math.round(this.roi.x),
                        y: Math.round(this.roi.y),
                        width: Math.round(this.roi.width),
                        height: Math.round(this.roi.height)
                    }
                });
            }
            
            // Also save to localStorage
            try {
                localStorage.setItem('camera_roi', JSON.stringify(this.roi));
            } catch (e) {
                console.warn('Failed to save ROI to localStorage:', e);
            }
        }
    }
    
    /**
     * Load ROI from localStorage.
     * Controller layer: Data loading
     */
    loadROI() {
        try {
            const saved = localStorage.getItem('camera_roi');
            if (saved) {
                this.roi = JSON.parse(saved);
                this.draw();
            }
        } catch (e) {
            console.error('Failed to load ROI from localStorage:', e);
        }
    }
    
    /**
     * Clear ROI selection.
     * Model layer: State modification
     * 
     * @param {boolean} sendToServer - If true, send clear command to server
     */
    clearROI(sendToServer = true) {
        this.roi = null;
        this.draw();
        
        if (this.socket && sendToServer) {
            this.socket.emit('roi', {cmd: 'clear'});
        }
        
        try {
            localStorage.removeItem('camera_roi');
        } catch (e) {
            console.warn('Failed to remove ROI from localStorage:', e);
        }
    }
    
    /**
     * Get current ROI.
     * Model layer: State query
     * 
     * @returns {Object|null} ROI object or null
     */
    getROI() {
        return this.roi;
    }
    
    /**
     * Set ROI from external source (e.g., server).
     * Model layer: State modification
     * 
     * @param {Object} roi - ROI object {x, y, width, height}
     */
    setROI(roi) {
        if (roi && roi.width > 0 && roi.height > 0) {
            this.roi = roi;
            this.clampROIToBounds();
            this.draw();
        } else {
            this.roi = null;
            this.draw();
        }
    }
    
    /**
     * Handle touch start event.
     * Controller layer: Event handling
     * 
     * @param {TouchEvent} e - Touch event
     */
    onTouchStart(e) {
        e.preventDefault();
        this.onMouseDown(e.touches[0]);
    }
    
    /**
     * Handle touch move event.
     * Controller layer: Event handling
     * 
     * @param {TouchEvent} e - Touch event
     */
    onTouchMove(e) {
        e.preventDefault();
        this.onMouseMove(e.touches[0]);
    }
    
    /**
     * Handle touch end event.
     * Controller layer: Event handling
     * 
     * @param {TouchEvent} e - Touch event
     */
    onTouchEnd(e) {
        e.preventDefault();
        this.onMouseUp(e.changedTouches[0]);
    }
}

