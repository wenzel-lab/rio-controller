/**
 * C API for Rio Daheng native grabber (GXDQAllBufs acquisition thread).
 * Enable from Python with RIO_DAHENG_CPP=1.
 */
#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Open camera by serial number (NULL/empty → first device). Returns 0 on success. */
int daheng_grabber_open(const char* serial_number);

void daheng_grabber_close(void);

/** Sensor WidthMax/HeightMax. */
int daheng_grabber_get_sensor_size(int32_t* width, int32_t* height);

/** Current stream Width/Height (ROI). */
int daheng_grabber_get_stream_size(int32_t* width, int32_t* height);

/**
 * Set absolute ROI (OffsetX/Y, Width, Height). Stops stream if running, applies, restarts.
 * Returns 0 on success.
 */
int daheng_grabber_set_roi(int32_t offset_x, int32_t offset_y, int32_t width, int32_t height);

/** ExposureTime in microseconds. Safe while streaming on many Daheng models. */
int daheng_grabber_set_exposure_us(double exposure_us);

int daheng_grabber_get_exposure_us(double* exposure_us);

/** AcquisitionFrameRateMode ON + set AFR to range max. */
int daheng_grabber_sync_afr_max(void);

/** Start GXDQAllBufs thread. Returns 0 on success. */
int daheng_grabber_start(void);

void daheng_grabber_stop(void);

int daheng_grabber_is_running(void);

/**
 * Copy latest Mono8 frame if seq > after_seq.
 * Returns 1 if a newer frame was copied, 0 if none, -1 on error.
 */
int daheng_grabber_get_latest_mono8(
    uint8_t* out,
    int32_t out_capacity,
    int32_t* width,
    int32_t* height,
    uint64_t* frame_id,
    uint64_t* seq,
    uint64_t after_seq);

/** Host drain rate (Galaxy Acq.FPS style, ~1s window). */
double daheng_grabber_get_acq_fps(void);

/** GenICam CurrentAcquisitionFrameRate. */
double daheng_grabber_get_sdk_fps(void);

uint64_t daheng_grabber_get_frame_id(void);

#ifdef __cplusplus
}
#endif
