/**
 * Daheng native grabber — Galaxy GxViewer-style GXDQAllBufs drain thread.
 */

#include "daheng_grabber.h"

#include "GxIAPI.h"

#include <atomic>
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <mutex>
#include <thread>
#include <vector>

namespace {

struct QueuedFrame {
    std::vector<uint8_t> mono;
    int32_t w = 0;
    int32_t h = 0;
    uint64_t fid = 0;
    uint64_t seq = 0;
};

std::mutex g_api_mu;
GX_DEV_HANDLE g_device = nullptr;
bool g_lib_inited = false;
uint64_t g_buf_num = 5;

std::atomic<bool> g_run{false};
std::thread g_thread;

std::mutex g_frame_mu;
std::vector<uint8_t> g_latest_mono;
int32_t g_latest_w = 0;
int32_t g_latest_h = 0;
uint64_t g_latest_fid = 0;
uint64_t g_latest_seq = 0;

std::mutex g_queue_mu;
std::deque<QueuedFrame> g_record_queue;
std::atomic<bool> g_record_mode{false};
uint64_t g_record_queue_dropped = 0;
constexpr size_t kRecordQueueMax = 8192;

std::mutex g_fps_mu;
double g_acq_fps = 0.0;
uint64_t g_window_frames = 0;
std::chrono::steady_clock::time_point g_window_start;

uint64_t GalaxyBufferCount(uint32_t payload) {
    constexpr size_t kMaxMem = 8ull * 1024ull * 1024ull;
    constexpr uint64_t kMin = 5;
    constexpr uint64_t kMax = 450;
    if (payload == 0) {
        return kMin;
    }
    uint64_t n = kMaxMem / payload;
    if (n < kMin) {
        n = kMin;
    }
    if (n > kMax) {
        n = kMax;
    }
    return n;
}

bool Ok(GX_STATUS st) { return st == GX_STATUS_SUCCESS; }

template <typename Fn>
bool TryGx(Fn&& fn) {
    try {
        return Ok(fn());
    } catch (...) {
        return false;
    }
}

int ConfigureBuffersLocked() {
    if (!g_device) {
        return -1;
    }
    uint32_t ds_num = 0;
    if (!TryGx([&] { return GXGetDataStreamNumFromDev(g_device, &ds_num); }) || ds_num < 1) {
        return -1;
    }
    GX_DS_HANDLE stream = nullptr;
    if (!TryGx([&] { return GXGetDataStreamHandleFromDev(g_device, 1, &stream); })) {
        return -1;
    }
    uint32_t payload = 0;
    if (!TryGx([&] { return GXGetPayLoadSize(stream, &payload); })) {
        return -1;
    }
    g_buf_num = GalaxyBufferCount(payload);
    if (!TryGx([&] { return GXSetAcqusitionBufferNumber(g_device, g_buf_num); })) {
        return -1;
    }
    return 0;
}

int SyncAfrMaxLocked() {
    if (!g_device) {
        return -1;
    }
    // GxViewer FrameRateControl + acq_probe: Mode ON, setpoint = range max.
    // Do NOT re-write ExposureTime afterward — probe sets exposure then AFR; GenICam
    // may clamp exposure to the new frame period (Galaxy behavior).
    TryGx([&] { return GXSetEnumValue(g_device, "AcquisitionFrameRateMode", 1); });
    GX_FLOAT_VALUE afr{};
    if (TryGx([&] { return GXGetFloatValue(g_device, "AcquisitionFrameRate", &afr); })) {
        TryGx([&] { return GXSetFloatValue(g_device, "AcquisitionFrameRate", afr.dMax); });
    }
    return 0;
}

/** GxViewer ExposureGain: user selects ExposureAuto Off, then sets ExposureTime. */
int LockManualExposureGainLocked() {
    if (!g_device) {
        return -1;
    }
    TryGx([&] { return GXSetEnumValue(g_device, "ExposureAuto", 0); });  // GX_EXPOSURE_AUTO_OFF
    TryGx([&] { return GXSetEnumValue(g_device, "GainAuto", 0); });       // GX_GAIN_AUTO_OFF
    return 0;
}

void NoteFrames(uint32_t n) {
    using clock = std::chrono::steady_clock;
    const auto now = clock::now();
    std::lock_guard<std::mutex> lock(g_fps_mu);
    if (g_window_frames == 0) {
        g_window_start = now;
    }
    g_window_frames += n;
    const double dt = std::chrono::duration<double>(now - g_window_start).count();
    if (dt >= 1.0) {
        g_acq_fps = static_cast<double>(g_window_frames) / dt;
        g_window_frames = 0;
        g_window_start = now;
    }
}

void PublishFrame(PGX_FRAME_BUFFER fb) {
    const int32_t w = fb->nWidth;
    const int32_t h = fb->nHeight;
    const int32_t nbytes = w * h;
    if (nbytes <= 0 || fb->pImgBuf == nullptr) {
        return;
    }

    uint64_t seq = 0;
    {
        std::lock_guard<std::mutex> flock(g_frame_mu);
        if (static_cast<int32_t>(g_latest_mono.size()) < nbytes) {
            g_latest_mono.resize(static_cast<size_t>(nbytes));
        }
        std::memcpy(g_latest_mono.data(), fb->pImgBuf, static_cast<size_t>(nbytes));
        g_latest_w = w;
        g_latest_h = h;
        g_latest_fid = fb->nFrameID;
        g_latest_seq += 1;
        seq = g_latest_seq;
    }

    if (!g_record_mode.load(std::memory_order_acquire)) {
        return;
    }

    QueuedFrame qf;
    qf.mono.resize(static_cast<size_t>(nbytes));
    std::memcpy(qf.mono.data(), fb->pImgBuf, static_cast<size_t>(nbytes));
    qf.w = w;
    qf.h = h;
    qf.fid = fb->nFrameID;
    qf.seq = seq;

    std::lock_guard<std::mutex> qlock(g_queue_mu);
    if (g_record_queue.size() >= kRecordQueueMax) {
        g_record_queue.pop_front();
        ++g_record_queue_dropped;
    }
    g_record_queue.push_back(std::move(qf));
}

void AcqLoop() {
    std::vector<PGX_FRAME_BUFFER> frames;
    {
        std::lock_guard<std::mutex> lock(g_api_mu);
        frames.resize(static_cast<size_t>(g_buf_num));
    }

    while (g_run.load(std::memory_order_acquire)) {
        GX_DEV_HANDLE dev = nullptr;
        uint64_t buf_num = 0;
        {
            std::lock_guard<std::mutex> lock(g_api_mu);
            dev = g_device;
            buf_num = g_buf_num;
        }
        if (!dev) {
            break;
        }
        if (frames.size() != buf_num) {
            frames.resize(static_cast<size_t>(buf_num));
        }

        uint32_t n = 0;
        GX_STATUS st =
            GXDQAllBufs(dev, frames.data(), static_cast<uint32_t>(buf_num), &n, 1000);
        if (st == GX_STATUS_TIMEOUT) {
            continue;
        }
        if (st != GX_STATUS_SUCCESS || n == 0) {
            continue;
        }

        NoteFrames(n);

        bool any_ok = false;
        for (uint32_t i = 0; i < n; ++i) {
            if (frames[i]->nStatus != GX_FRAME_STATUS_SUCCESS) {
                continue;
            }
            PublishFrame(frames[i]);
            any_ok = true;
        }
        if (!any_ok) {
            GXQAllBufs(dev);
            continue;
        }

        GXQAllBufs(dev);
    }
}

int StartLocked() {
    if (!g_device || g_run.load()) {
        return g_run.load() ? 0 : -1;
    }
    if (ConfigureBuffersLocked() != 0) {
        return -1;
    }
    if (!Ok(GXStreamOn(g_device))) {
        return -1;
    }
    {
        std::lock_guard<std::mutex> flock(g_fps_mu);
        g_acq_fps = 0.0;
        g_window_frames = 0;
    }
    g_run.store(true, std::memory_order_release);
    g_thread = std::thread(AcqLoop);
    return 0;
}

}  // namespace

extern "C" int daheng_grabber_open(const char* serial_number) {
    std::lock_guard<std::mutex> lock(g_api_mu);
    if (g_device) {
        return 0;
    }
    if (!g_lib_inited) {
        if (!Ok(GXInitLib())) {
            return -1;
        }
        g_lib_inited = true;
    }
    uint32_t device_num = 0;
    if (!Ok(GXUpdateAllDeviceList(&device_num, 1000)) || device_num < 1) {
        return -1;
    }

    GX_STATUS st = GX_STATUS_ERROR;
    if (serial_number && serial_number[0] != '\0') {
        GX_OPEN_PARAM open_param{};
        open_param.openMode = GX_OPEN_SN;
        open_param.accessMode = GX_ACCESS_EXCLUSIVE;
        open_param.pszContent = const_cast<char*>(serial_number);
        st = GXOpenDevice(&open_param, &g_device);
    }
    if (!Ok(st) || !g_device) {
        st = GXOpenDeviceByIndex(1, &g_device);
    }
    if (!Ok(st) || !g_device) {
        g_device = nullptr;
        return -1;
    }

    // Match daheng_acq_probe open path; avoid optional GenICam nodes that may
    // throw GXTLClass::CNotImplementedError across DSO boundaries.
    GX_INT_VALUE wmax{};
    GX_INT_VALUE hmax{};
    if (!Ok(GXGetIntValue(g_device, "WidthMax", &wmax)) ||
        !Ok(GXGetIntValue(g_device, "HeightMax", &hmax))) {
        GXCloseDevice(g_device);
        g_device = nullptr;
        return -1;
    }
    GXSetIntValue(g_device, "OffsetX", 0);
    GXSetIntValue(g_device, "OffsetY", 0);
    GXSetIntValue(g_device, "Width", wmax.nCurValue);
    GXSetIntValue(g_device, "Height", hmax.nCurValue);

    // GxViewer OpenDevice does not rewrite Exposure/AE; a fresh camera connect
    // typically comes up from UserSet Default (power-on). That profile on this
    // MER2 is AE Off, ExposureTime=10000 us, Gain=0 — which is why Galaxy looks
    // stable. Rio left volatile 13552 us + Gain 24 → visible AC flicker.
    // Load Default explicitly (same as GxViewer UserSetControl → UserSetLoad).
    TryGx([&] { return GXSetEnumValue(g_device, "UserSetSelector", 0); });  // Default
    TryGx([&] { return GXSetCommandValue(g_device, "UserSetLoad"); });

    // Free-run for continuous /video (GxViewer StartAcquisition with Trigger Off).
    TryGx([&] { return GXSetEnumValue(g_device, "DeviceLinkThroughputLimitMode", 0); });
    TryGx([&] { return GXSetEnumValue(g_device, "TriggerMode", 0); });  // Off

    // Optional explicit override only (never a hidden default).
    if (const char* exp_env = std::getenv("RIO_DAHENG_EXPOSURE_US")) {
        const double v = std::atof(exp_env);
        if (v > 0.0) {
            LockManualExposureGainLocked();
            TryGx([&] { return GXSetFloatValue(g_device, "ExposureTime", v); });
        }
    }

    // GxViewer FrameRateControl is user-driven; enable AFR max only if requested.
    if (const char* afr = std::getenv("RIO_DAHENG_AFR_MAX")) {
        if (afr[0] == '1' || afr[0] == 't' || afr[0] == 'T' || afr[0] == 'y' ||
            afr[0] == 'Y') {
            SyncAfrMaxLocked();
        }
    }

    if (ConfigureBuffersLocked() != 0) {
        GXCloseDevice(g_device);
        g_device = nullptr;
        return -1;
    }
    return 0;
}

extern "C" void daheng_grabber_stop(void) {
    std::thread to_join;
    {
        std::lock_guard<std::mutex> lock(g_api_mu);
        if (g_run.load()) {
            g_run.store(false, std::memory_order_release);
            to_join = std::move(g_thread);
        }
        if (g_device) {
            GXStreamOff(g_device);
        }
    }
    if (to_join.joinable()) {
        to_join.join();
    }
}

extern "C" int daheng_grabber_start(void) {
    std::lock_guard<std::mutex> lock(g_api_mu);
    return StartLocked();
}

extern "C" void daheng_grabber_close(void) {
    daheng_grabber_stop();
    std::lock_guard<std::mutex> lock(g_api_mu);
    if (g_device) {
        GXCloseDevice(g_device);
        g_device = nullptr;
    }
    if (g_lib_inited) {
        GXCloseLib();
        g_lib_inited = false;
    }
}

extern "C" int daheng_grabber_is_running(void) {
    return g_run.load() ? 1 : 0;
}

extern "C" int daheng_grabber_get_sensor_size(int32_t* width, int32_t* height) {
    std::lock_guard<std::mutex> lock(g_api_mu);
    if (!g_device || !width || !height) {
        return -1;
    }
    GX_INT_VALUE wmax{};
    GX_INT_VALUE hmax{};
    if (!Ok(GXGetIntValue(g_device, "WidthMax", &wmax)) ||
        !Ok(GXGetIntValue(g_device, "HeightMax", &hmax))) {
        return -1;
    }
    *width = static_cast<int32_t>(wmax.nCurValue);
    *height = static_cast<int32_t>(hmax.nCurValue);
    return 0;
}

extern "C" int daheng_grabber_get_stream_size(int32_t* width, int32_t* height) {
    std::lock_guard<std::mutex> lock(g_api_mu);
    if (!g_device || !width || !height) {
        return -1;
    }
    GX_INT_VALUE w{};
    GX_INT_VALUE h{};
    if (!Ok(GXGetIntValue(g_device, "Width", &w)) || !Ok(GXGetIntValue(g_device, "Height", &h))) {
        return -1;
    }
    *width = static_cast<int32_t>(w.nCurValue);
    *height = static_cast<int32_t>(h.nCurValue);
    return 0;
}

extern "C" int daheng_grabber_set_roi(
    int32_t offset_x, int32_t offset_y, int32_t width, int32_t height) {
    const bool was_running = daheng_grabber_is_running() != 0;
    if (was_running) {
        daheng_grabber_stop();
    }
    {
        std::lock_guard<std::mutex> lock(g_api_mu);
        if (!g_device) {
            return -1;
        }
        // Probe order: full reset offsets, set size, then offsets.
        if (!TryGx([&] { return GXSetIntValue(g_device, "OffsetX", 0); }) ||
            !TryGx([&] { return GXSetIntValue(g_device, "OffsetY", 0); })) {
            return -2;
        }
        if (!TryGx([&] { return GXSetIntValue(g_device, "Width", width); }) ||
            !TryGx([&] { return GXSetIntValue(g_device, "Height", height); })) {
            return -3;
        }
        // Offsets are best-effort (some alignments return non-success; size still applied).
        TryGx([&] { return GXSetIntValue(g_device, "OffsetX", offset_x); });
        TryGx([&] { return GXSetIntValue(g_device, "OffsetY", offset_y); });
        SyncAfrMaxLocked();
        if (ConfigureBuffersLocked() != 0) {
            return -5;
        }
    }
    if (was_running) {
        return daheng_grabber_start() == 0 ? 0 : -6;
    }
    return 0;
}

extern "C" int daheng_grabber_set_exposure_us(double exposure_us) {
    std::lock_guard<std::mutex> lock(g_api_mu);
    if (!g_device) {
        return -1;
    }
    // GxViewer: ExposureAuto Off (combo), then ExposureTime spin → GXSetFloatValue only.
    TryGx([&] { return GXSetEnumValue(g_device, "ExposureAuto", 0); });
    if (!TryGx([&] { return GXSetFloatValue(g_device, "ExposureTime", exposure_us); })) {
        return -1;
    }
    return 0;
}

extern "C" int daheng_grabber_get_exposure_us(double* exposure_us) {
    std::lock_guard<std::mutex> lock(g_api_mu);
    if (!g_device || !exposure_us) {
        return -1;
    }
    GX_FLOAT_VALUE exp{};
    if (!Ok(GXGetFloatValue(g_device, "ExposureTime", &exp))) {
        return -1;
    }
    *exposure_us = exp.dCurValue;
    return 0;
}

extern "C" int daheng_grabber_get_exposure_range(double* min_us, double* max_us) {
    std::lock_guard<std::mutex> lock(g_api_mu);
    if (!g_device || !min_us || !max_us) {
        return -1;
    }
    GX_FLOAT_VALUE exp{};
    if (!Ok(GXGetFloatValue(g_device, "ExposureTime", &exp))) {
        return -1;
    }
    *min_us = exp.dMin;
    *max_us = exp.dMax;
    return 0;
}

extern "C" int daheng_grabber_sync_afr_max(void) {
    std::lock_guard<std::mutex> lock(g_api_mu);
    return SyncAfrMaxLocked();
}

extern "C" int daheng_grabber_get_latest_mono8(
    uint8_t* out,
    int32_t out_capacity,
    int32_t* width,
    int32_t* height,
    uint64_t* frame_id,
    uint64_t* seq,
    uint64_t after_seq) {
    if (!out || !width || !height || !frame_id || !seq) {
        return -1;
    }
    std::lock_guard<std::mutex> flock(g_frame_mu);
    if (g_latest_seq <= after_seq || g_latest_w <= 0 || g_latest_h <= 0) {
        return 0;
    }
    const int32_t nbytes = g_latest_w * g_latest_h;
    if (nbytes > out_capacity) {
        return -1;
    }
    std::memcpy(out, g_latest_mono.data(), static_cast<size_t>(nbytes));
    *width = g_latest_w;
    *height = g_latest_h;
    *frame_id = g_latest_fid;
    *seq = g_latest_seq;
    return 1;
}

extern "C" double daheng_grabber_get_acq_fps(void) {
    std::lock_guard<std::mutex> lock(g_fps_mu);
    return g_acq_fps;
}

extern "C" double daheng_grabber_get_sdk_fps(void) {
    std::lock_guard<std::mutex> lock(g_api_mu);
    if (!g_device) {
        return 0.0;
    }
    GX_FLOAT_VALUE fps{};
    if (!Ok(GXGetFloatValue(g_device, "CurrentAcquisitionFrameRate", &fps))) {
        return 0.0;
    }
    return fps.dCurValue;
}

extern "C" uint64_t daheng_grabber_get_frame_id(void) {
    std::lock_guard<std::mutex> flock(g_frame_mu);
    return g_latest_fid;
}

extern "C" int daheng_grabber_set_record_mode(int enabled) {
    const bool on = enabled != 0;
    g_record_mode.store(on, std::memory_order_release);
    if (on) {
        std::lock_guard<std::mutex> qlock(g_queue_mu);
        g_record_queue.clear();
        g_record_queue_dropped = 0;
    }
    return 0;
}

extern "C" int daheng_grabber_pop_record_mono8(
    uint8_t* out,
    int32_t out_capacity,
    int32_t* width,
    int32_t* height,
    uint64_t* frame_id,
    uint64_t* seq) {
    if (!out || !width || !height || !frame_id || !seq) {
        return -1;
    }
    std::lock_guard<std::mutex> qlock(g_queue_mu);
    if (g_record_queue.empty()) {
        return 0;
    }
    QueuedFrame qf = std::move(g_record_queue.front());
    g_record_queue.pop_front();
    const int32_t nbytes = qf.w * qf.h;
    if (nbytes <= 0 || nbytes > out_capacity) {
        return -1;
    }
    std::memcpy(out, qf.mono.data(), static_cast<size_t>(nbytes));
    *width = qf.w;
    *height = qf.h;
    *frame_id = qf.fid;
    *seq = qf.seq;
    return 1;
}

extern "C" uint64_t daheng_grabber_get_record_queue_drops(void) {
    std::lock_guard<std::mutex> qlock(g_queue_mu);
    return g_record_queue_dropped;
}

static int configure_strobe_line_out_on_line(int enabled, int line) {
    // GX_ENUM_LINE_MODE_OUTPUT=1, GX_ENUM_LINE_SOURCE_EXPOSURE_ACTIVE=5, OFF=0
    if (!TryGx([&] { return GXSetEnumValue(g_device, "LineSelector", line); })) {
        return -2;
    }
    if (enabled) {
        if (!TryGx([&] { return GXSetEnumValue(g_device, "LineMode", 1); })) {
            return -3;
        }
        if (!TryGx([&] { return GXSetEnumValue(g_device, "LineSource", 5); })) {
            return -4;
        }
    } else {
        TryGx([&] { return GXSetEnumValue(g_device, "LineSource", 0); });
    }
    return 0;
}

extern "C" int daheng_grabber_configure_strobe_line_out(int enabled, int line_selector) {
    std::lock_guard<std::mutex> lock(g_api_mu);
    if (!g_device) {
        return -1;
    }
    int line = line_selector;
    if (line < 0) {
        line = 2;  // MER2 opto Line2 is a common strobe/out pin
        if (const char* env = std::getenv("RIO_DAHENG_STROBE_LINE")) {
            const int v = std::atoi(env);
            if (v >= 0) {
                line = v;
            }
        }
    }
    const int rc = configure_strobe_line_out_on_line(enabled, line);
    // Prefer env/explicit line; if it cannot be OUTPUT+ExposureActive, try Line2 then Line3.
    if (rc == 0 || line_selector >= 0) {
        return rc;
    }
    if (line != 2) {
        const int rc2 = configure_strobe_line_out_on_line(enabled, 2);
        if (rc2 == 0) {
            return 0;
        }
    }
    if (line != 3) {
        const int rc3 = configure_strobe_line_out_on_line(enabled, 3);
        if (rc3 == 0) {
            return 0;
        }
    }
    return rc;
}
