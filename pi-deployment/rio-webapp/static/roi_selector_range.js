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
        this._suppressSliderEvents = false;
        this._sliderSuppressTimer = null;
        this._dragging = false;
        this._applyOnRelease = true;
        /** Authoritative stream size from server (hardware ROI); ignores stale img.naturalWidth. */
        this._serverStreamW = 0;
        this._serverStreamH = 0;
        /** Fixed slider coordinate space (full sensor/view); survives hardware crop. */
        this._railStreamW = 0;
        this._railStreamH = 0;
        this._pendingHardwareCommit = false;
        this._lastCommitRoi = null;
        this._lastAppliedStreamW = 0;
        this._lastAppliedStreamH = 0;
        /** Cached pixel size of slider tracks (content area); stable during drag. */
        this._trackW = 0;
        this._trackH = 0;
        this._userHasAdjustedSliders = false;
        /** Set when user clicks Apply ROI; cleared on hardware_applied. */
        this._awaitingHardwareApply = false;
        /** Frozen stream + track pixels for the duration of a handle drag. */
        this._dragLayout = null;
        /** Delta-drag anchor: start mouse + edge values (stream coords). */
        this._dragState = null;
        /** When true, rail pixel size must not change (during drag). */
        this._railsLocked = false;

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
        this._setupCanvasInteraction();
        this.updateCanvasSize();
        
        const updateAll = () => {
            if (this._dragging) {
                return;
            }
            this.updateCanvasSize();
            requestAnimationFrame(() => {
                if (this._dragging) return;
                this.updateSliderDimensions();
                if (this.customHorizontalSlider) {
                    this.customHorizontalSlider.cachedRect = null;
                    this.customHorizontalSlider.updateDisplay();
                }
                if (this.customVerticalSlider) {
                    this.customVerticalSlider.cachedRect = null;
                    this.customVerticalSlider.updateDisplay();
                }
            });
        };

        this.img.addEventListener('load', () => {
            updateAll();
        });

        // Use ResizeObserver for reliable layout updates (modern browsers)
        if (window.ResizeObserver) {
            const ro = new ResizeObserver(() => updateAll());
            ro.observe(this.img);
        } else {
            window.addEventListener('resize', () => updateAll());
        }
    }
    
    /**
     * Free rectangle draw/move/resize directly on the camera image
     * (like Daheng Galaxy Viewer). Preview only — hardware applies via Apply ROI.
     */
    _setupCanvasInteraction() {
        const c = this.canvas;
        if (!c || c._roiInteractive) return;
        c._roiInteractive = true;
        c.style.pointerEvents = 'auto';
        c.style.cursor = 'crosshair';
        c.style.touchAction = 'none';

        const HIT = 8; // px hit zone for edges/corners

        const localXY = (e) => {
            const r = c.getBoundingClientRect();
            return { px: e.clientX - r.left, py: e.clientY - r.top };
        };

        const hitTest = (px, py) => {
            if (!this.roi) return { mode: 'new' };
            const r = this._roiStreamToDisplayRect(this.roi);
            const nearL = Math.abs(px - r.x) <= HIT;
            const nearR = Math.abs(px - (r.x + r.w)) <= HIT;
            const nearT = Math.abs(py - r.y) <= HIT;
            const nearB = Math.abs(py - (r.y + r.h)) <= HIT;
            const inX = px >= r.x - HIT && px <= r.x + r.w + HIT;
            const inY = py >= r.y - HIT && py <= r.y + r.h + HIT;
            if ((nearL || nearR) && (nearT || nearB)) {
                return { mode: 'resize', ex: nearL ? 'min' : 'max', ey: nearT ? 'min' : 'max' };
            }
            if ((nearL || nearR) && inY) return { mode: 'resize', ex: nearL ? 'min' : 'max', ey: null };
            if ((nearT || nearB) && inX) return { mode: 'resize', ex: null, ey: nearT ? 'min' : 'max' };
            if (px > r.x && px < r.x + r.w && py > r.y && py < r.y + r.h) return { mode: 'move' };
            return { mode: 'new' };
        };

        const cursorFor = (h) => {
            if (h.mode === 'move') return 'move';
            if (h.mode === 'resize') {
                if (h.ex && h.ey) return (h.ex === h.ey) ? 'nwse-resize' : 'nesw-resize';
                return h.ex ? 'ew-resize' : 'ns-resize';
            }
            return 'crosshair';
        };

        const clampX = (v) => Math.max(0, Math.min(Math.round(v), Math.max(1, this.streamWidth())));
        const clampY = (v) => Math.max(0, Math.min(Math.round(v), Math.max(1, this.streamHeight())));

        let drag = null;

        const syncFromRect = () => {
            if (this.customHorizontalSlider) this.customHorizontalSlider.updateDisplay();
            if (this.customVerticalSlider) this.customVerticalSlider.updateDisplay();
            this.updateFromRange(false);
        };

        const onPointerMove = (e) => {
            if (!drag) {
                const { px, py } = localXY(e);
                c.style.cursor = cursorFor(hitTest(px, py));
                return;
            }
            e.preventDefault();
            const { px, py } = localXY(e);
            const p = this._displayToAbs(px, py);
            if (drag.mode === 'new') {
                this.x_min = clampX(Math.min(drag.ax, p.x));
                this.x_max = clampX(Math.max(drag.ax, p.x));
                this.y_min = clampY(Math.min(drag.ay, p.y));
                this.y_max = clampY(Math.max(drag.ay, p.y));
            } else if (drag.mode === 'move') {
                const w = drag.x_max - drag.x_min;
                const h = drag.y_max - drag.y_min;
                let nx = clampX(drag.x_min + (p.x - drag.ax));
                let ny = clampY(drag.y_min + (p.y - drag.ay));
                nx = Math.min(nx, Math.max(0, this.streamWidth() - w));
                ny = Math.min(ny, Math.max(0, this.streamHeight() - h));
                this.x_min = nx;
                this.x_max = nx + w;
                this.y_min = ny;
                this.y_max = ny + h;
            } else {
                if (drag.ex === 'min') this.x_min = clampX(Math.min(p.x, drag.x_max));
                if (drag.ex === 'max') this.x_max = clampX(Math.max(p.x, drag.x_min));
                if (drag.ey === 'min') this.y_min = clampY(Math.min(p.y, drag.y_max));
                if (drag.ey === 'max') this.y_max = clampY(Math.max(p.y, drag.y_min));
            }
            syncFromRect();
        };

        const onPointerUp = (e) => {
            if (!drag) return;
            drag = null;
            try { c.releasePointerCapture(e.pointerId); } catch (err) { /* no-op */ }
            this._endDrag();
            this._previewFromSliders();
        };

        c.addEventListener('pointerdown', (e) => {
            if (e.button !== undefined && e.button !== 0) return;
            e.preventDefault();
            const { px, py } = localXY(e);
            const h = hitTest(px, py);
            const p = this._displayToAbs(px, py);
            this._beginDrag();
            drag = {
                mode: h.mode,
                ex: h.ex || null,
                ey: h.ey || null,
                ax: p.x,
                ay: p.y,
                x_min: this.x_min, x_max: this.x_max,
                y_min: this.y_min, y_max: this.y_max,
            };
            if (h.mode === 'new') {
                this.x_min = clampX(p.x);
                this.x_max = clampX(p.x);
                this.y_min = clampY(p.y);
                this.y_max = clampY(p.y);
            }
            try { c.setPointerCapture(e.pointerId); } catch (err) { /* no-op */ }
        });
        c.addEventListener('pointermove', onPointerMove);
        c.addEventListener('pointerup', onPointerUp);
        c.addEventListener('pointercancel', onPointerUp);
    }

    streamWidth() {
        if (this._railStreamW > 0) return this._railStreamW;
        if (this._serverStreamW > 0) return this._serverStreamW;
        return Math.max(1, this.maxWidth);
    }

    streamHeight() {
        if (this._railStreamH > 0) return this._railStreamH;
        if (this._serverStreamH > 0) return this._serverStreamH;
        return Math.max(1, this.maxHeight);
    }

    /** Current camera view size (after hardware crop) — overlay layout only. */
    viewStreamWidth() {
        if (this._serverStreamW > 0) return this._serverStreamW;
        return this.streamWidth();
    }

    viewStreamHeight() {
        if (this._serverStreamH > 0) return this._serverStreamH;
        return this.streamHeight();
    }

    /**
     * Single layout for overlay + sliders. Stream pixels map to img content via uniform scale.
     * Requires #camera_image { width:100%; height:100%; object-fit:contain; }.
     */
    _layout() {
        const streamW = Math.max(1, this.viewStreamWidth());
        const streamH = Math.max(1, this.viewStreamHeight());
        const rect = this.img.getBoundingClientRect();
        const elementW = Math.max(1, rect.width);
        const elementH = Math.max(1, rect.height);
        const scale = Math.min(elementW / streamW, elementH / streamH);
        const contentW = streamW * scale;
        const contentH = streamH * scale;
        return {
            offsetX: (elementW - contentW) / 2,
            offsetY: (elementH - contentH) / 2,
            contentW,
            contentH,
            width: contentW,
            height: contentH,
            scale,
            scaleX: scale,
            scaleY: scale,
            streamW,
            streamH,
            elementW,
            elementH,
        };
    }

    /** Rail layout uses full sensor/view coords — not cropped stream — so rails stay fixed. */
    _railLayout() {
        const streamW = Math.max(1, this.streamWidth());
        const streamH = Math.max(1, this.streamHeight());
        const rect = this.img.getBoundingClientRect();
        const elementW = Math.max(1, rect.width);
        const elementH = Math.max(1, rect.height);
        const scale = Math.min(elementW / streamW, elementH / streamH);
        const contentW = streamW * scale;
        const contentH = streamH * scale;
        return {
            offsetX: (elementW - contentW) / 2,
            offsetY: (elementH - contentH) / 2,
            contentW,
            contentH,
            width: contentW,
            height: contentH,
            scale,
            scaleX: scale,
            scaleY: scale,
            streamW,
            streamH,
            elementW,
            elementH,
        };
    }

    /** Current hardware crop offsets (absolute sensor coords of the visible view). */
    _viewOffsets() {
        const c = this.constraints || {};
        return {
            ox: (c.offset_x && c.offset_x.current) || 0,
            oy: (c.offset_y && c.offset_y.current) || 0,
        };
    }

    /** ROI is absolute sensor coords; the image shows the current (possibly cropped) view. */
    _roiStreamToDisplayRect(roi) {
        const L = this._layout();
        const o = this._viewOffsets();
        return {
            x: L.offsetX + (roi.x - o.ox) * L.scale,
            y: L.offsetY + (roi.y - o.oy) * L.scale,
            w: roi.width * L.scale,
            h: roi.height * L.scale,
        };
    }

    /** Display (canvas) pixels → absolute sensor coords. */
    _displayToAbs(px, py) {
        const L = this._layout();
        const o = this._viewOffsets();
        return {
            x: (px - L.offsetX) / L.scale + o.ox,
            y: (py - L.offsetY) / L.scale + o.oy,
        };
    }

    /** Absolute ROI → view-relative rect clamped to current stream (software ROI consumers). */
    _absRoiToView(roi) {
        if (!roi) return null;
        const o = this._viewOffsets();
        const vw = Math.max(1, this.viewStreamWidth());
        const vh = Math.max(1, this.viewStreamHeight());
        const x0 = Math.max(0, roi.x - o.ox);
        const y0 = Math.max(0, roi.y - o.oy);
        const x1 = Math.min(vw, roi.x - o.ox + roi.width);
        const y1 = Math.min(vh, roi.y - o.oy + roi.height);
        if (x1 - x0 < 1 || y1 - y0 < 1) return null;
        return {
            x: Math.round(x0),
            y: Math.round(y0),
            width: Math.round(x1 - x0),
            height: Math.round(y1 - y0),
        };
    }

    /** During drag, freeze content scale so overlay matches slider rails. */
    _layoutForDraw() {
        if (!this._dragLayout) {
            return this._layout();
        }
        const L = this._layout();
        const scaleX = this._dragLayout.trackW / this._dragLayout.streamW;
        const scaleY = this._dragLayout.trackH / this._dragLayout.streamH;
        return {
            offsetX: this._dragLayout.offsetX,
            offsetY: this._dragLayout.offsetY,
            contentW: this._dragLayout.trackW,
            contentH: this._dragLayout.trackH,
            width: this._dragLayout.trackW,
            height: this._dragLayout.trackH,
            scale: scaleX,
            scaleX,
            scaleY,
            streamW: this._dragLayout.streamW,
            streamH: this._dragLayout.streamH,
            elementW: L.elementW,
            elementH: L.elementH,
        };
    }

    _clearCanvasLogical() {
        if (!this.ctx || !this.canvas) return;
        const dpr = this.dpr || 1;
        this.ctx.clearRect(0, 0, this.canvas.width / dpr, this.canvas.height / dpr);
    }

    /** After hardware crop, view coords are 0-based; offset current must be 0 for snap. */
    _normalizeViewConstraints() {
        const c = this.constraints;
        if (!c) return;
        if (c.offset_x) c.offset_x.current = 0;
        if (c.offset_y) c.offset_y.current = 0;
        if (c.width) c.width.current = this.streamWidth();
        if (c.height) c.height.current = this.streamHeight();
        if (c.stream_width !== undefined) c.stream_width = this.streamWidth();
        if (c.stream_height !== undefined) c.stream_height = this.streamHeight();
    }

    _showRoiWarning(msg) {
        const el = document.getElementById('roi_warning');
        if (el) {
            el.textContent = msg;
            if (msg) {
                el.classList.remove('d-none');
            } else {
                el.classList.add('d-none');
            }
        } else if (msg) {
            console.warn(msg);
        }
    }

    _snapToIncrement(value, minVal, maxVal, increment) {
        const inc = Math.max(1, increment);
        const snapped = Math.floor(value / inc) * inc;
        return Math.max(minVal, Math.min(maxVal, snapped));
    }

    /** Exact port of daheng validate_and_snap_roi (absolute sensor coords). */
    _validateAndSnapAbsolute(ax, ay, aw, ah) {
        const c = this.constraints || {};
        const maxW = c.sensor_width || this.streamWidth();
        const maxH = c.sensor_height || this.streamHeight();
        const minW = c.width?.min || 8;
        const minH = c.height?.min || 8;
        const wInc = c.width?.increment || 1;
        const hInc = c.height?.increment || 1;
        const oxInc = c.offset_x?.increment || 1;
        const oyInc = c.offset_y?.increment || 1;

        let width = this._snapToIncrement(aw, minW, maxW, wInc);
        let height = this._snapToIncrement(ah, minH, maxH, hInc);
        let x = this._snapToIncrement(ax, 0, Math.max(0, maxW - width), oxInc);
        let y = this._snapToIncrement(ay, 0, Math.max(0, maxH - height), oyInc);
        if (x + width > maxW) {
            width = this._snapToIncrement(maxW - x, minW, maxW, wInc);
        }
        if (y + height > maxH) {
            height = this._snapToIncrement(maxH - y, minH, maxH, hInc);
        }
        if (x > maxW - width) {
            x = this._snapToIncrement(Math.max(0, maxW - width), 0, Math.max(0, maxW - width), oxInc);
        }
        if (y > maxH - height) {
            y = this._snapToIncrement(Math.max(0, maxH - height), 0, Math.max(0, maxH - height), oyInc);
        }
        return { x, y, width, height };
    }

    /** Match daheng snap_view_roi: view-relative → absolute snap → view coords. */
    _snapViewRoiLikeServer(viewX, viewY, viewW, viewH) {
        const c = this.constraints || {};
        const curOx = c.offset_x?.current || 0;
        const curOy = c.offset_y?.current || 0;
        const abs = this._validateAndSnapAbsolute(
            viewX + curOx, viewY + curOy, viewW, viewH
        );
        return {
            x: abs.x - curOx,
            y: abs.y - curOy,
            width: abs.width,
            height: abs.height,
        };
    }

    syncCoordSpaceFromImage() {
        /* Stream size comes only from server (_serverStreamW/H). Do not touch maxWidth here —
           that desyncs jQuery slider max from streamWidth() used by the overlay. */
    }

    _beginSliderProgrammaticUpdate() {
        this._updatingInputs = true;
        this._suppressSliderEvents = true;
        if (this._sliderSuppressTimer) {
            clearTimeout(this._sliderSuppressTimer);
        }
    }

    _endSliderProgrammaticUpdate() {
        this._sliderSuppressTimer = setTimeout(() => {
            this._updatingInputs = false;
            this._suppressSliderEvents = false;
        }, 120);
    }

    _streamScale() {
        if (this._dragLayout) {
            return this._dragLayout;
        }
        return {
            streamW: Math.max(1, this.streamWidth()),
            streamH: Math.max(1, this.streamHeight()),
            trackW: Math.max(50, this._trackWidthPx()),
            trackH: Math.max(50, this._trackHeightPx()),
        };
    }

    _pxDeltaToStream(deltaPx, trackPx, streamPx) {
        if (!trackPx || trackPx <= 0) return 0;
        return (deltaPx / trackPx) * streamPx;
    }

    _beginDragState(axis, edge, clientX, clientY) {
        this._beginDrag();
        this._dragState = {
            axis,
            edge,
            startX: clientX,
            startY: clientY,
            startXMin: this.x_min,
            startXMax: this.x_max,
            startYMin: this.y_min,
            startYMax: this.y_max,
        };
    }

    _applyHorizontalDelta(clientX) {
        if (!this._dragState || this._dragState.axis !== 'x') return;
        const S = this._streamScale();
        const deltaPx = clientX - this._dragState.startX;
        const deltaVal = this._pxDeltaToStream(deltaPx, S.trackW, S.streamW);
        const ds = this._dragState;
        if (ds.edge === 'min') {
            const v = Math.round(ds.startXMin + deltaVal);
            this.x_min = Math.max(0, Math.min(v, ds.startXMax));
            this.x_max = ds.startXMax;
        } else {
            const v = Math.round(ds.startXMax + deltaVal);
            this.x_max = Math.min(S.streamW, Math.max(v, ds.startXMin));
            this.x_min = ds.startXMin;
        }
    }

    _applyVerticalDelta(clientY) {
        if (!this._dragState || this._dragState.axis !== 'y') return;
        const S = this._streamScale();
        const deltaPx = clientY - this._dragState.startY;
        const deltaVal = this._pxDeltaToStream(deltaPx, S.trackH, S.streamH);
        const ds = this._dragState;
        if (ds.edge === 'min') {
            const v = Math.round(ds.startYMin + deltaVal);
            this.y_min = Math.max(0, Math.min(v, ds.startYMax));
            this.y_max = ds.startYMax;
        } else {
            const v = Math.round(ds.startYMax + deltaVal);
            this.y_max = Math.min(S.streamH, Math.max(v, ds.startYMin));
            this.y_min = ds.startYMin;
        }
    }

    _lockRailPixels() {
        this._railsLocked = true;
        const yEl = $('#roi_y_range_slider');
        const xEl = $('#roi_x_range_slider');
        const xInner = $('#roi_x_slider_inner');
        const h = Math.round(Math.max(50, this._trackH || yEl.height() || 100));
        const w = Math.round(Math.max(50, this._trackW || xEl.width() || 100));
        this._trackH = h;
        this._trackW = w;
        yEl.css({ height: h + 'px', minHeight: h + 'px', maxHeight: h + 'px', flexShrink: '0' });
        xEl.css({ width: w + 'px', minWidth: w + 'px', maxWidth: w + 'px', flexShrink: '0' });
        xInner.css({ width: w + 'px', minWidth: w + 'px', flexShrink: '0' });
    }

    _unlockRailPixels() {
        this._railsLocked = false;
        $('#roi_y_range_slider').css({ minHeight: '', maxHeight: '', flexShrink: '' });
        $('#roi_x_range_slider').css({ minWidth: '', maxWidth: '', flexShrink: '' });
        $('#roi_x_slider_inner').css({ minWidth: '', flexShrink: '' });
    }

    _beginDrag() {
        if (this._trackW <= 0 || this._trackH <= 0) {
            this.updateSliderDimensions();
        }
        const L = this._railLayout();
        this._trackW = Math.max(50, L.contentW);
        this._trackH = Math.max(50, L.contentH);
        this._lockRailPixels();
        this._dragLayout = {
            streamW: Math.max(1, this.streamWidth()),
            streamH: Math.max(1, this.streamHeight()),
            trackW: this._trackW,
            trackH: this._trackH,
            offsetX: L.offsetX,
            offsetY: L.offsetY,
        };
        this._dragging = true;
        this._userHasAdjustedSliders = true;
    }

    _endDrag() {
        this._dragging = false;
        this._dragLayout = null;
        this._dragState = null;
        if (this.customHorizontalSlider) {
            this.customHorizontalSlider.dragging = null;
            this.customHorizontalSlider.cachedRect = null;
        }
        if (this.customVerticalSlider) {
            this.customVerticalSlider.dragging = null;
            this.customVerticalSlider.cachedRect = null;
        }
        this._unlockRailPixels();
    }

    _clampSliderValues() {
        const maxW = Math.max(1, this.streamWidth());
        const maxH = Math.max(1, this.streamHeight());
        this.maxWidth = maxW;
        this.maxHeight = maxH;
        this.x_min = Math.max(0, Math.min(this.x_min, maxW));
        this.x_max = Math.max(this.x_min, Math.min(this.x_max, maxW));
        this.y_min = Math.max(0, Math.min(this.y_min, maxH));
        this.y_max = Math.max(this.y_min, Math.min(this.y_max, maxH));
    }

    _trackWidthPx() {
        if (this._trackW > 0) return this._trackW;
        if (this.customHorizontalSlider) return this.customHorizontalSlider.getWidth();
        return 100;
    }

    _trackHeightPx() {
        if (this._trackH > 0) return this._trackH;
        if (this.customVerticalSlider) return this.customVerticalSlider.getHeight();
        return 100;
    }

    _applyXSliderState() {
        if (this.customHorizontalSlider) {
            this.customHorizontalSlider.updateDisplay();
        }
    }

    _applyYSliderState() {
        if (this.customVerticalSlider) {
            this.customVerticalSlider.updateDisplay();
        }
    }

    updateCanvasSize() {
        if (!this.canvas || !this.img) return;
        if (this._dragging) return;

        this.syncCoordSpaceFromImage();

        const container = this.img.parentElement;
        const rect = this.img.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.dpr = dpr;

        if (container) {
            const containerRect = container.getBoundingClientRect();
            this.canvas.style.left = (rect.left - containerRect.left) + 'px';
            this.canvas.style.top = (rect.top - containerRect.top) + 'px';
        }

        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';

        if (this.ctx) {
            this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }

        if (!this._dragging) {
            this.updateSliderDimensions();
        }
        this.draw();
    }
    
    updateSliderDimensions() {
        if (!this.img || this._dragging || this._railsLocked) return;

        const layout = this._railLayout();
        const imgRect = this.img.getBoundingClientRect();
        let imgHeight = layout.contentH;
        let imgWidth = layout.contentW;

        if (imgHeight < 50) imgHeight = 50;
        if (imgWidth < 50) imgWidth = 50;

        this._trackW = imgWidth;
        this._trackH = imgHeight;

        if (this.customHorizontalSlider) {
            this.customHorizontalSlider.updateDimensions(imgWidth);
        }

        if (this.customVerticalSlider) {
            const yBarRow = $('.roi-y-bar-row');
            const yValuesCol = $('.roi-y-values-col');
            let railHeight = imgHeight;
            if (yBarRow.length) {
                const row = this.img.closest('.roi-view-row');
                let contentTop = layout.offsetY;
                let rowRect = null;
                if (row && row.length) {
                    rowRect = row[0].getBoundingClientRect();
                    contentTop = (imgRect.top - rowRect.top) + layout.offsetY;
                }
                const maxRail = rowRect
                    ? Math.max(50, rowRect.height - contentTop - 4)
                    : imgHeight;
                railHeight = Math.min(imgHeight, maxRail);
                const padTop = Math.max(0, contentTop);
                yBarRow.css({ 'padding-top': padTop + 'px', 'margin-top': '0' });
                yValuesCol.css({
                    'height': railHeight + 'px',
                    'min-height': railHeight + 'px',
                });
            }
            this._trackH = railHeight;
            this.customVerticalSlider.updateDimensions(railHeight);
        }

        const xInner = $('#roi_x_slider_inner');
        if (xInner.length) {
            const column = this.img.closest('.camera-column');
            let marginLeft = layout.offsetX;
            if (column && column.length) {
                const columnRect = column[0].getBoundingClientRect();
                marginLeft = (imgRect.left - columnRect.left) + layout.offsetX;
            }
            xInner.css({
                'width': imgWidth + 'px',
                'margin-left': marginLeft + 'px',
                'margin-right': '0',
            });
        }
    }
    
    setupCustomHorizontalSlider(maxW, initialXMin, initialXMax) {
        const sliderElement = $('#roi_x_range_slider');

        sliderElement.empty();
        sliderElement.css({
            'position': 'relative',
            'width': '100%',
            'height': '20px',
            'background': '#E0E0E0',
            'border-radius': '10px',
            'cursor': 'pointer',
            'box-sizing': 'border-box',
        });

        const track = $('<div></div>').css({
            'position': 'absolute', 'left': '0', 'top': '0',
            'width': '100%', 'height': '100%', 'background': 'transparent',
        });
        sliderElement.append(track);

        const range = $('<div></div>').css({
            'position': 'absolute', 'top': '0', 'height': '100%',
            'background': '#2196F3', 'border-radius': '10px', 'pointer-events': 'none',
        });
        sliderElement.append(range);

        const handleStyle = {
            'position': 'absolute', 'top': '-2px',
            'width': '20px', 'height': '24px',
            'background': '#2196F3', 'border': '2px solid #1565C0',
            'border-radius': '10px', 'cursor': 'ew-resize', 'z-index': '10',
            'box-shadow': '0 2px 4px rgba(0,0,0,0.2)',
        };
        const handle1 = $('<div></div>').css(handleStyle);
        const handle2 = $('<div></div>').css(handleStyle);
        sliderElement.append(handle1);
        sliderElement.append(handle2);

        this.customHorizontalSlider = {
            element: sliderElement,
            track, range, handle1, handle2,
            dragging: null,
            cachedRect: null,
            updateDimensions: (width) => {
                if (this._dragging) return;
                sliderElement.css('width', Math.max(50, width) + 'px');
                this.customHorizontalSlider.cachedRect = null;
                this.customHorizontalSlider.updateDisplay();
            },
            getWidth: () => {
                if (this._dragLayout) return this._dragLayout.trackW;
                const elem = sliderElement[0];
                if (!elem) return 100;
                const rect = elem.getBoundingClientRect();
                if (rect.width > 0) return rect.width;
                return sliderElement.width() || 100;
            },
            updateDisplay: () => {
                const S = this._streamScale();
                const max = S.streamW;
                const val1 = this.x_min;
                const val2 = this.x_max;
                const pct1 = (val1 / max) * 100;
                const pct2 = (val2 / max) * 100;
                handle1.css('left', `calc(${pct1}% - 10px)`);
                handle2.css('left', `calc(${pct2}% - 10px)`);
                range.css({ display: 'none' });
                $('#roi_x_min').val(val1).attr('max', max);
                $('#roi_x_max').val(val2).attr('max', max);
            },
            positionToValue: (pos) => {
                const S = this._streamScale();
                if (S.trackW <= 0) return 0;
                const v = (pos / S.trackW) * S.streamW;
                return Math.max(0, Math.min(S.streamW, Math.round(v)));
            },
            getBoundingRect: () => {
                if (this.customHorizontalSlider.dragging && this.customHorizontalSlider.cachedRect) {
                    return this.customHorizontalSlider.cachedRect;
                }
                const elem = sliderElement[0];
                if (!elem) return null;
                const rect = elem.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    this.customHorizontalSlider.cachedRect = rect;
                    return rect;
                }
                return null;
            },
        };

        this.x_min = initialXMin;
        this.x_max = initialXMax;
        this.customHorizontalSlider.updateDisplay();

        const onMove = (clientX) => {
            this._applyHorizontalDelta(clientX);
            this.customHorizontalSlider.updateDisplay();
            this.updateFromRange(false);
        };

        const onUp = () => {
            $(document).off('.horizSlider');
            this._endDrag();
            this._previewFromSliders();
            this.customHorizontalSlider.updateDisplay();
        };

        const onDown = (e, handle) => {
            e.preventDefault();
            e.stopPropagation();
            const edge = (handle[0] === handle1[0]) ? 'min' : 'max';
            this._beginDragState('x', edge, e.clientX, e.clientY);
            this.customHorizontalSlider.dragging = handle;
            $(document).on('mousemove.horizSlider', (ev) => onMove(ev.clientX));
            $(document).on('mouseup.horizSlider', onUp);
        };

        handle1.on('mousedown', (e) => onDown(e, handle1));
        handle2.on('mousedown', (e) => onDown(e, handle2));

        track.on('click', (e) => {
            const rect = this.customHorizontalSlider.getBoundingRect();
            if (!rect) return;
            const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
            const value = this.customHorizontalSlider.positionToValue(x);
            const dist1 = Math.abs(value - this.x_min);
            const dist2 = Math.abs(value - this.x_max);
            if (dist1 < dist2) {
                this.x_min = Math.min(value, this.x_max);
            } else {
                this.x_max = Math.max(value, this.x_min);
            }
            this.customHorizontalSlider.updateDisplay();
            this.updateFromRange(false);
            this._previewFromSliders();
        });
    }
    
    setupCustomVerticalSlider(maxH, initialYMin, initialYMax) {
        const sliderElement = $('#roi_y_range_slider');
        
        // Get initial height from image with multiple fallback methods (Chrome compatibility)
        let initialHeight = 300; // Default fallback
        if (this.img) {
            // Method 1: getBoundingClientRect (primary)
            const imgRect = this.img.getBoundingClientRect();
            if (imgRect.height > 0) {
                initialHeight = imgRect.height;
            } else {
                // Method 2: offsetHeight
                const offsetH = this.img.offsetHeight;
                if (offsetH > 0) {
                    initialHeight = offsetH;
                } else {
                    // Method 3: clientHeight
                    const clientH = this.img.clientHeight;
                    if (clientH > 0) {
                        initialHeight = clientH;
                    } else {
                        // Method 4: computed style
                        const style = window.getComputedStyle(this.img);
                        const styleH = parseFloat(style.height);
                        if (styleH > 0) {
                            initialHeight = styleH;
                        } else {
                            // Method 5: naturalHeight scaled to display
                            if (this.img.naturalHeight > 0 && this.img.naturalWidth > 0) {
                                const imgWidth = this.img.offsetWidth || this.img.clientWidth || parseFloat(window.getComputedStyle(this.img).width);
                                if (imgWidth > 0) {
                                    const scale = imgWidth / this.img.naturalWidth;
                                    initialHeight = this.img.naturalHeight * scale;
                                }
                            }
                        }
                    }
                }
            }
        }
        
        // Ensure minimum height
        if (initialHeight < 100) {
            initialHeight = 300; // Fallback to safe minimum
        }
        
        // Create custom slider structure
        sliderElement.empty();
        sliderElement.css({
            'position': 'relative',
            'width': '20px',
            'height': initialHeight + 'px',
            'margin': '0 auto',
            'background': '#E0E0E0',
            'border-radius': '10px',
            'cursor': 'pointer',
            'box-sizing': 'border-box',
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
        
        const handleStyle = {
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
        };
        const handle1 = $('<div></div>').css(handleStyle)
            .on('mouseenter', function() { $(this).css('background', '#7FD3D3'); })
            .on('mouseleave', function() { $(this).css('background', '#2196F3'); });
        const handle2 = $('<div></div>').css(handleStyle)
            .on('mouseenter', function() { $(this).css('background', '#7FD3D3'); })
            .on('mouseleave', function() { $(this).css('background', '#2196F3'); });
        sliderElement.append(handle1);
        sliderElement.append(handle2);
        
        // Store references
        this.customVerticalSlider = {
            element: sliderElement,
            track: track,
            range: range,
            handle1: handle1,
            handle2: handle2,
            dragging: null,
            cachedRect: null, // Cache getBoundingClientRect for performance
            updateDimensions: (height) => {
                if (this._dragging) return;
                const h = Math.max(50, height);
                sliderElement.css('height', h + 'px');
                const wrap = sliderElement.closest('.roi-y-track-wrap');
                if (wrap.length) {
                    wrap.css('height', h + 'px');
                }
                this.customVerticalSlider.cachedRect = null;
                this.customVerticalSlider.updateDisplay();
            },
            getHeight: () => {
                if (this._dragLayout) return this._dragLayout.trackH;
                const elem = sliderElement[0];
                if (!elem) return 100;
                const rect = elem.getBoundingClientRect();
                if (rect.height > 0) return rect.height;
                return sliderElement.height() || 100;
            },
            updateDisplay: () => {
                const S = this._streamScale();
                const max = S.streamH;
                const val1 = this.y_min;
                const val2 = this.y_max;
                const pct1 = (val1 / max) * 100;
                const pct2 = (val2 / max) * 100;
                const top1 = `calc(${pct1}% - 10px)`;
                const top2 = `calc(${pct2}% - 10px)`;
                handle1.css('top', top1);
                handle2.css('top', top2);
                range.css({ display: 'none' });
                $('#roi_y_min').val(val1).attr('max', max);
                $('#roi_y_max').val(val2).attr('max', max);
            },
            valueToPosition: (value) => {
                const S = this._streamScale();
                return (value / S.streamH) * S.trackH;
            },
            positionToValue: (position) => {
                const S = this._streamScale();
                if (S.trackH <= 0) return 0;
                const v = (position / S.trackH) * S.streamH;
                return Math.max(0, Math.min(S.streamH, Math.round(v)));
            },
            getBoundingRect: () => {
                // Cache rect during drag operations for performance
                if (this.customVerticalSlider.dragging && this.customVerticalSlider.cachedRect) {
                    return this.customVerticalSlider.cachedRect;
                }
                const elem = sliderElement[0];
                if (!elem) return null;
                const rect = elem.getBoundingClientRect();
                // Validate rect
                if (rect.height > 0 && rect.width > 0) {
                    this.customVerticalSlider.cachedRect = rect;
                    return rect;
                }
                return null;
            }
        };
        
        // Set initial values
        this.y_min = initialYMin;
        this.y_max = initialYMax;
        this.customVerticalSlider.updateDisplay();
        
        // Mouse and touch event handlers
        const handleMouseMove = (e) => {
            if (!this.customVerticalSlider.dragging) return;
            e.preventDefault();
            this._applyVerticalDelta(e.clientY);
            this.customVerticalSlider.updateDisplay();
            this.updateFromRange(false);
        };

        const handleMouseUp = () => {
            $(document).off('mousemove.verticalSlider');
            $(document).off('mouseup.verticalSlider');
            this._endDrag();
            this._previewFromSliders();
            this.customVerticalSlider.updateDisplay();
        };

        const handleMouseDown = (e, handle) => {
            e.preventDefault();
            e.stopPropagation();
            const edge = (handle[0] === handle1[0]) ? 'min' : 'max';
            this._beginDragState('y', edge, e.clientX, e.clientY);
            this.customVerticalSlider.dragging = handle;
            $(document).on('mousemove.verticalSlider', handleMouseMove);
            $(document).on('mouseup.verticalSlider', handleMouseUp);
        };
        
        // Attach event handlers
        handle1.on('mousedown', (e) => handleMouseDown(e, handle1));
        handle2.on('mousedown', (e) => handleMouseDown(e, handle2));
        
        // Touch support
        const handleTouchStart = (e, handle) => {
            e.preventDefault();
            const touch = e.originalEvent.touches[0];
            if (!touch) return;
            const edge = (handle[0] === handle1[0]) ? 'min' : 'max';
            this._beginDragState('y', edge, touch.clientX, touch.clientY);
            this.customVerticalSlider.dragging = handle;
            $(document).on('touchmove.verticalSlider', handleTouchMove);
            $(document).on('touchend.verticalSlider', handleTouchEnd);
        };

        const handleTouchMove = (e) => {
            if (!this.customVerticalSlider.dragging) return;
            e.preventDefault();
            const touch = e.originalEvent.touches[0];
            if (!touch) return;
            this._applyVerticalDelta(touch.clientY);
            this.customVerticalSlider.updateDisplay();
            this.updateFromRange(false);
        };

        const handleTouchEnd = () => {
            $(document).off('touchmove.verticalSlider');
            $(document).off('touchend.verticalSlider');
            this._endDrag();
            this._previewFromSliders();
            this.customVerticalSlider.updateDisplay();
        };
        
        handle1.on('touchstart', (e) => handleTouchStart(e, handle1));
        handle2.on('touchstart', (e) => handleTouchStart(e, handle2));
        
        // Click on track to move nearest handle
        track.on('click', (e) => {
            const rect = this.customVerticalSlider.getBoundingRect();
            if (!rect) {
                // Recalculate if needed
                this.customVerticalSlider.cachedRect = null;
                const newRect = this.customVerticalSlider.getBoundingRect();
                if (!newRect) return;
            }
            
            const rectToUse = this.customVerticalSlider.cachedRect || sliderElement[0].getBoundingClientRect();
            const y = e.clientY - rectToUse.top;
            const clampedY = Math.max(0, Math.min(rectToUse.height, y));
            const value = this.customVerticalSlider.positionToValue(clampedY);
            
            const dist1 = Math.abs(value - this.y_min);
            const dist2 = Math.abs(value - this.y_max);
            
            if (dist1 < dist2) {
                this.y_min = Math.min(value, this.y_max);
            } else {
                this.y_max = Math.max(value, this.y_min);
            }
            
            this.customVerticalSlider.updateDisplay();
            this.updateFromRange(false);
            this._previewFromSliders();
        });
    }
    
    setupRangeSliders() {
        const maxW = this.maxWidth;
        const maxH = this.maxHeight;
        
        const initialXMin = Math.max(0, Math.floor(maxW * 0.1));
        const initialXMax = Math.min(maxW, Math.floor(maxW * 0.9));
        const initialYMin = Math.max(0, Math.floor(maxH * 0.1));
        const initialYMax = Math.min(maxH, Math.floor(maxH * 0.9));
        
        this.setupCustomHorizontalSlider(maxW, initialXMin, initialXMax);
        this.setupCustomVerticalSlider(maxH, initialYMin, initialYMax);
        
        this.x_min = initialXMin;
        this.x_max = initialXMax;
        this.y_min = initialYMin;
        this.y_max = initialYMax;
        
        this._updatingInputs = true;
        $('#roi_x_min').val(this.x_min);
        $('#roi_x_max').val(this.x_max);
        $('#roi_y_min').val(this.y_min);
        $('#roi_y_max').val(this.y_max);
        setTimeout(() => { this._updatingInputs = false; }, 0);
    }
    
    updateFromRange(applyHardware = false) {
        if (this._updatingInputs) return;

        if (applyHardware) {
            if (this._pendingHardwareCommit) return;
            this._pendingHardwareCommit = true;
            const raw = this._roiFromSlidersRaw();
            if (!raw) {
                this._pendingHardwareCommit = false;
                this._clearRoiPreview();
                return;
            }
            this._lastCommitRoi = Object.assign({}, raw);
            this.roi = raw;
            this.draw();
            this.saveROI(true);
            setTimeout(() => { this._pendingHardwareCommit = false; }, 300);
        } else {
            const roi = this._roiFromSlidersRaw();
            if (!roi) {
                this._clearRoiPreview();
                return;
            }
            this.roi = roi;
            this.syncNumericInputsOnly();
            this.draw();
        }
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }

    _clearRoiPreview() {
        this.roi = null;
        this._clearCanvasLogical();
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }

    /** Raw slider rect for live overlay (matches handle positions while dragging). */
    _roiFromSlidersRaw() {
        const x0 = Math.min(this.x_min, this.x_max);
        const x1 = Math.max(this.x_min, this.x_max);
        const y0 = Math.min(this.y_min, this.y_max);
        const y1 = Math.max(this.y_min, this.y_max);
        const w = x1 - x0;
        const h = y1 - y0;
        if (w < 10 || h < 10) return null;
        return { x: x0, y: y0, width: w, height: h };
    }

    /** Preview only — do not rewrite slider positions while dragging. */
    previewRoiFromRange() {
        return this._snapRangeToRoi(
            this.x_min, this.x_max, this.y_min, this.y_max, false
        );
    }

    /** Commit snap on release; updates x_min/x_max/y_min/y_max to snapped values. */
    normalizeRangeToRoi() {
        const out = this._snapRangeToRoi(
            this.x_min, this.x_max, this.y_min, this.y_max, true
        );
        return out;
    }

    _snapRangeToRoi(xMin, xMax, yMin, yMax, mutate) {
        const x0 = Math.min(xMin, xMax);
        const x1 = Math.max(xMin, xMax);
        const y0 = Math.min(yMin, yMax);
        const y1 = Math.max(yMin, yMax);
        const w = x1 - x0;
        const h = y1 - y0;
        const minW = this.constraints.width?.min || 8;
        const minH = this.constraints.height?.min || 8;
        if (w < minW || h < minH) return null;

        // Slider space is absolute sensor coords — snap absolutely (matches server).
        const snapped = this._validateAndSnapAbsolute(x0, y0, w, h);
        if (snapped.width < minW || snapped.height < minH) return null;

        if (mutate) {
            this.x_min = snapped.x;
            this.x_max = snapped.x + snapped.width;
            this.y_min = snapped.y;
            this.y_max = snapped.y + snapped.height;
        }
        if (snapped.width < 10 || snapped.height < 10) return null;
        return snapped;
    }

    syncNumericInputsOnly() {
        this._updatingInputs = true;
        $('#roi_x_min').val(this.x_min);
        $('#roi_x_max').val(this.x_max);
        $('#roi_y_min').val(this.y_min);
        $('#roi_y_max').val(this.y_max);
        setTimeout(() => { this._updatingInputs = false; }, 0);
    }

    syncUIFromRange() {
        this._clampSliderValues();
        this._applyXSliderState();
        this._applyYSliderState();
    }
    
    setupEventListeners() {
        if (this.socket) {
            this.socket.on('roi', (data) => {
                if (this._dragging) {
                    return;
                }

                if (data.cleared) {
                    this._applyStreamSize(
                        data.stream_width, data.stream_height, data.constraints, false, true
                    );
                    this._normalizeViewConstraints();
                    this._showRoiWarning('');
                    this._userHasAdjustedSliders = false;
                    this.resetSlidersAfterClear(false);
                    if (this.img) {
                        this.updateCanvasSize();
                    }
                    return;
                }

                if (data.hardware_applied) {
                    const saved = {
                        x_min: this.x_min, x_max: this.x_max,
                        y_min: this.y_min, y_max: this.y_max,
                    };
                    this._applyStreamSize(
                        data.stream_width, data.stream_height, data.constraints, false, false
                    );
                    this.x_min = saved.x_min;
                    this.x_max = saved.x_max;
                    this.y_min = saved.y_min;
                    this.y_max = saved.y_max;
                    this._clampSliderValues();
                    this.roi = null;
                    this._pendingHardwareCommit = false;
                    this._awaitingHardwareApply = false;
                    this._lastCommitRoi = null;
                    localStorage.removeItem('camera_roi');
                    // Keep server constraints as-is: offset_x/y.current now hold the
                    // real crop offsets, needed for absolute<->view conversion.
                    this._clearCanvasLogical();
                    this.syncUIFromRange();
                    if (this.img) {
                        this.updateCanvasSize();
                    }
                    if (typeof updateROIInfo === 'function') {
                        updateROIInfo();
                    }
                    return;
                }

                if (data.stream_width && data.stream_height && !data.roi_scheduled) {
                    const sizeChanged = data.stream_width !== this._serverStreamW ||
                        data.stream_height !== this._serverStreamH;
                    if (sizeChanged || data.constraints) {
                        this._applyStreamSize(
                            data.stream_width, data.stream_height, data.constraints, false, true
                        );
                    }
                    const mayReset = !this._userHasAdjustedSliders &&
                        !data.roi && !data.snapped_roi;
                    if (mayReset) {
                        this.setSlidersToFullStream(false);
                    }
                }

                if (data.roi_apply_failed) {
                    this._pendingHardwareCommit = false;
                    this._showRoiWarning('Hardware ROI apply failed — try again or Clear ROI.');
                    if (this._lastCommitRoi) {
                        this._applySnappedRoi(this._lastCommitRoi, true);
                    }
                    return;
                }

                if (data.multi_roi_enabled) {
                    this._showRoiWarning('MultiROI mode is enabled on camera — disable it in Galaxy Viewer.');
                } else if (data.multi_roi_enabled === false) {
                    this._showRoiWarning('');
                }

                if (data.snapped_roi && !data.hardware_applied) {
                    // Hardware snap only — handles stay where the user put them.
                } else if (data.roi && !data.hardware_applied && !data.roi_scheduled) {
                    // Server software ROI is view-relative; sliders are absolute.
                    const o = this._viewOffsets();
                    this.setROI({
                        x: data.roi.x + o.ox,
                        y: data.roi.y + o.oy,
                        width: data.roi.width,
                        height: data.roi.height,
                    }, false);
                } else if (data.constraints && !data.stream_width) {
                    this.setConstraints(data.constraints, true);
                }
            });

            this.socket.emit('roi', {cmd: 'get'});
        }

        const applyFromNumericInputs = () => {
            const maxW = Math.max(1, this.streamWidth());
            let min = parseInt($('#roi_x_min').val(), 10);
            let max = parseInt($('#roi_x_max').val(), 10);
            if (isNaN(min)) min = 0;
            if (isNaN(max)) max = 0;
            min = Math.max(0, Math.min(min, maxW));
            max = Math.max(min, Math.min(max, maxW));
            if (min !== this.x_min || max !== this.x_max) {
                this.x_min = min;
                this.x_max = max;
                if (this.customHorizontalSlider) {
                    this.customHorizontalSlider.updateDisplay();
                }
                this.updateFromRange(false);
                this.saveROI(false);
            }
        };

        $('#roi_x_min, #roi_x_max').on('change blur', applyFromNumericInputs);

        const applyFromNumericInputsY = () => {
            const maxH = Math.max(1, this.streamHeight());
            let min = parseInt($('#roi_y_min').val(), 10);
            let max = parseInt($('#roi_y_max').val(), 10);
            if (isNaN(min)) min = 0;
            if (isNaN(max)) max = 0;
            min = Math.max(0, Math.min(min, maxH));
            max = Math.min(maxH, Math.max(min, max));
            if (min !== this.y_min || max !== this.y_max) {
                this.y_min = min;
                this.y_max = max;
                if (this.customVerticalSlider) {
                    this.customVerticalSlider.updateDisplay();
                }
                this.updateFromRange(false);
                this.saveROI(false);
            }
        };

        $('#roi_y_min, #roi_y_max').on('change blur', applyFromNumericInputsY);
    }
    
    _applySnappedRoi(roi, syncSliders = true) {
        this.roi = roi;
        if (syncSliders) {
            this.x_min = roi.x;
            this.x_max = roi.x + roi.width;
            this.y_min = roi.y;
            this.y_max = roi.y + roi.height;
            this.syncUIFromRange();
        }
        this.draw();
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }

    draw() {
        if (!this.ctx || !this.roi) {
            this._clearCanvasLogical();
            return;
        }

        const dpr = this.dpr || (window.devicePixelRatio || 1);
        const displayW = this.canvas.width / dpr;
        const displayH = this.canvas.height / dpr;
        this.ctx.clearRect(0, 0, displayW, displayH);

        if (!this.roi.width || !this.roi.height) return;

        const r = this._roiStreamToDisplayRect(this.roi);
        const x = r.x;
        const y = r.y;
        const w = r.w;
        const h = r.h;

        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        this.ctx.fillRect(0, 0, displayW, displayH);
        this.ctx.clearRect(x, y, w, h);

        this.ctx.strokeStyle = '#2196F3';
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x, y, w, h);
    }
    
    setROI(roi, sendToServer = true) {
        this.x_min = roi.x;
        this.x_max = roi.x + roi.width;
        this.y_min = roi.y;
        this.y_max = roi.y + roi.height;
        const normalized = this.normalizeRangeToRoi();
        if (!normalized) return;
        this.roi = normalized;
        this.syncUIFromRange();
        this.draw();
        if (sendToServer) {
            this.saveROI(true);
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
        this._lastCommitRoi = null;
        this._clearCanvasLogical();
        localStorage.removeItem('camera_roi');

        if (this.socket && sendToServer) {
            this.socket.emit('roi', {cmd: 'clear'});
        } else {
            this.resetSlidersAfterClear(false);
        }

        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }

    setSlidersToFullStream(updateCanvas) {
        const maxW = this.streamWidth();
        const maxH = this.streamHeight();
        this.x_min = 0;
        this.x_max = maxW;
        this.y_min = 0;
        this.y_max = maxH;
        this.roi = null;
        this._clearCanvasLogical();
        this.syncUIFromRange();
        if (updateCanvas && this.img) {
            this.updateCanvasSize();
        }
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }

    resetSlidersAfterClear(sendToServer) {
        this.roi = null;
        this.setSlidersToFullStream(false);
        localStorage.removeItem('camera_roi');
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }
    
    /** Preview only — updates rect/inputs/overlay. Hardware applies via Apply ROI button. */
    _previewFromSliders() {
        if (this._updatingInputs) return;
        const raw = this._roiFromSlidersRaw();
        if (!raw) {
            this._clearRoiPreview();
            return;
        }
        this.roi = raw;
        this._userHasAdjustedSliders = true;
        this.draw();
        this.syncNumericInputsOnly();
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }

    _commitHardwareFromSliders() {
        if (this._updatingInputs) return;
        const snapped = this.normalizeRangeToRoi();
        if (!snapped) return;
        this.roi = snapped;
        this._lastCommitRoi = Object.assign({}, snapped);
        this.syncUIFromRange();
        this.draw();
        this.syncNumericInputsOnly();
        this._awaitingHardwareApply = true;
        this._userHasAdjustedSliders = true;
        if (this._pendingHardwareCommit) return;
        this._pendingHardwareCommit = true;
        this.saveROI(true);
        setTimeout(() => { this._pendingHardwareCommit = false; }, 500);
        if (typeof updateROIInfo === 'function') {
            updateROIInfo();
        }
    }

    applyHardwareROI() {
        this._commitHardwareFromSliders();
    }

    saveROI(applyHardware = false) {
        // Hardware: absolute sensor coords. Software: converted to view-relative
        // so server-side consumers (droplet detection, frame crops) stay correct.
        const roiPayload = applyHardware
            ? this._lastCommitRoi
            : this._absRoiToView(this.roi);
        if (!roiPayload || roiPayload.width <= 0 || roiPayload.height <= 0) return;

        if (!applyHardware) {
            localStorage.setItem('camera_roi', JSON.stringify(this.roi));
        }

        if (this.socket) {
            this.socket.emit('roi', {
                cmd: 'set',
                parameters: Object.assign({}, roiPayload, {
                    apply_hardware: applyHardware,
                    absolute: !!applyHardware,
                })
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
                const maxW = this.streamWidth();
                const maxH = this.streamHeight();
                if (roi.x + roi.width > maxW + 4 || roi.y + roi.height > maxH + 4) {
                    localStorage.removeItem('camera_roi');
                    return;
                }
                this.setROI(roi, false);
            } catch (e) {
                console.error('Failed to load ROI:', e);
                localStorage.removeItem('camera_roi');
            }
        }
    }
    
    /**
     * Sync stream dimensions from server (Galaxy Width/Height of current view).
     * Slider values are view-relative edges — never scale them on resize; reset to full frame instead.
     */
    _applyStreamSize(width, height, constraints, resetSlidersToFull = false, updateRails = true) {
        if (width > 0 && height > 0) {
            const sameSize = width === this._lastAppliedStreamW && height === this._lastAppliedStreamH;
            if (sameSize && !resetSlidersToFull && !constraints && !updateRails) {
                return;
            }
            this.maxWidth = width;
            this.maxHeight = height;
            this._serverStreamW = width;
            this._serverStreamH = height;
            this._lastAppliedStreamW = width;
            this._lastAppliedStreamH = height;
            // Rails always live in full-sensor coords so ROI can move/expand
            // freely after a crop (no collapse to the cropped view).
            const cs = constraints || this.constraints;
            const sensorW = (cs && cs.sensor_width) || 0;
            const sensorH = (cs && cs.sensor_height) || 0;
            if (sensorW > 0 && sensorH > 0) {
                this._railStreamW = sensorW;
                this._railStreamH = sensorH;
            } else if (updateRails || this._railStreamW <= 0 || this._railStreamH <= 0) {
                this._railStreamW = width;
                this._railStreamH = height;
            }
        }
        if (constraints) {
            this.constraints = constraints;
        }
        if (resetSlidersToFull) {
            this.setSlidersToFullStream(false);
        } else if (!this._dragging && !this._railsLocked) {
            if (this.img) this.updateSliderDimensions();
            if (this.customHorizontalSlider) this.customHorizontalSlider.updateDisplay();
            if (this.customVerticalSlider) this.customVerticalSlider.updateDisplay();
        }
    }

    setConstraints(constraints, skipRoiResync) {
        this.constraints = constraints;
        if (!skipRoiResync && this.roi) {
            this.setROI(this.roi, false);
        }
    }
}
