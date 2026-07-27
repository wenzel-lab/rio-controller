/**
 * Camera stream status bar helpers (Galaxy Viewer style):
 * cursor position + pixel value readout on hover over the camera image.
 *
 * Listens on the camera container (events bubble up from the ROI overlay
 * canvas that sits on top of the image) — ADDS listeners only, never
 * touches the ROI selector's own pointer handlers.
 */
(function () {
    'use strict';

    var THROTTLE_MS = 80; // ~12 Hz sampling, cheap on mousemove storms

    function init() {
        var img = document.getElementById('camera_image');
        var cursorEl = document.getElementById('sb_cursor');
        var pixelEl = document.getElementById('sb_pixel');
        if (!img || !img.parentElement || !cursorEl || !pixelEl) return;
        var container = img.parentElement;

        var sampler = document.createElement('canvas');
        sampler.width = 1;
        sampler.height = 1;
        var sctx = sampler.getContext('2d', { willReadFrequently: true });
        var lastSample = 0;

        /** Map client coords to natural image coords (object-fit: contain letterbox math). */
        function toImageCoords(clientX, clientY) {
            var rect = img.getBoundingClientRect();
            var nw = img.naturalWidth, nh = img.naturalHeight;
            if (nw <= 0 || nh <= 0 || rect.width <= 0 || rect.height <= 0) return null;
            var scale = Math.min(rect.width / nw, rect.height / nh);
            var offX = rect.left + (rect.width - nw * scale) / 2;
            var offY = rect.top + (rect.height - nh * scale) / 2;
            var x = (clientX - offX) / scale;
            var y = (clientY - offY) / scale;
            if (x < 0 || y < 0 || x >= nw || y >= nh) return null;
            return { x: Math.floor(x), y: Math.floor(y) };
        }

        function clear() {
            cursorEl.textContent = '(--, --)';
            pixelEl.textContent = 'Mono: --';
        }

        function onMove(e) {
            var now = Date.now();
            if (now - lastSample < THROTTLE_MS) return;
            lastSample = now;
            var p = toImageCoords(e.clientX, e.clientY);
            if (!p) {
                clear();
                return;
            }
            cursorEl.textContent = '(' + p.x + ', ' + p.y + ')';
            try {
                sctx.drawImage(img, p.x, p.y, 1, 1, 0, 0, 1, 1);
                var d = sctx.getImageData(0, 0, 1, 1).data;
                if (d[0] === d[1] && d[1] === d[2]) {
                    pixelEl.textContent = 'Mono: ' + d[0];
                } else {
                    pixelEl.textContent = 'RGB: (' + d[0] + ', ' + d[1] + ', ' + d[2] + ')';
                }
            } catch (err) {
                pixelEl.textContent = 'Mono: --';
            }
        }

        container.addEventListener('pointermove', onMove);
        container.addEventListener('pointerleave', clear);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
