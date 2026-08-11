/**
 * Daheng C++ acquisition FPS probe (Galaxy GxViewer-style).
 *
 * Goal: measure sustained host Acq.FPS with GXDQAllBufs + large buffer pool,
 * without RGB convert / JPEG — to see if native drain can hold ~SDK rate
 * (e.g. ~1050 @ 200x200 / 20 us) where Python/gxipy sits ~960.
 *
 * Close Rio / Galaxy Viewer before running (exclusive USB device).
 *
 * Usage:
 *   ./daheng_acq_probe [--sn FDQ23120254] [--width 200] [--height 200]
 *                      [--exposure-us 20] [--seconds 15]
 */

#include "GxIAPI.h"

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

namespace {

void PrintError(GX_STATUS status) {
    size_t size = 0;
    GXGetLastError(&status, nullptr, &size);
    if (size == 0) {
        std::fprintf(stderr, "GX error %d\n", static_cast<int>(status));
        return;
    }
    std::vector<char> buf(size);
    GXGetLastError(&status, buf.data(), &size);
    std::fprintf(stderr, "GX error %d: %s\n", static_cast<int>(status), buf.data());
}

bool Ok(GX_STATUS status, const char* what) {
    if (status == GX_STATUS_SUCCESS) {
        return true;
    }
    std::fprintf(stderr, "%s failed: ", what);
    PrintError(status);
    return false;
}

struct Args {
    std::string sn = "FDQ23120254";
    int64_t width = 200;
    int64_t height = 200;
    double exposure_us = 20.0;
    double seconds = 15.0;
};

Args ParseArgs(int argc, char** argv) {
    Args a;
    for (int i = 1; i < argc; ++i) {
        const std::string k = argv[i];
        auto need = [&](const char* name) -> const char* {
            if (i + 1 >= argc) {
                std::fprintf(stderr, "missing value for %s\n", name);
                std::exit(2);
            }
            return argv[++i];
        };
        if (k == "--sn") {
            a.sn = need("--sn");
        } else if (k == "--width") {
            a.width = std::strtoll(need("--width"), nullptr, 10);
        } else if (k == "--height") {
            a.height = std::strtoll(need("--height"), nullptr, 10);
        } else if (k == "--exposure-us") {
            a.exposure_us = std::strtod(need("--exposure-us"), nullptr);
        } else if (k == "--seconds") {
            a.seconds = std::strtod(need("--seconds"), nullptr);
        } else if (k == "--help" || k == "-h") {
            std::printf(
                "Usage: %s [--sn SN] [--width W] [--height H] "
                "[--exposure-us US] [--seconds S]\n",
                argv[0]);
            std::exit(0);
        } else {
            std::fprintf(stderr, "unknown arg: %s\n", k.c_str());
            std::exit(2);
        }
    }
    return a;
}

uint64_t GalaxyBufferCount(uint32_t payload) {
    // GxViewer.cpp SetAcquisitionBufferNum
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

}  // namespace

int main(int argc, char** argv) {
    const Args args = ParseArgs(argc, argv);

    if (!Ok(GXInitLib(), "GXInitLib")) {
        return 1;
    }

    uint32_t device_num = 0;
    if (!Ok(GXUpdateAllDeviceList(&device_num, 1000), "GXUpdateAllDeviceList")) {
        GXCloseLib();
        return 1;
    }
    if (device_num == 0) {
        std::fprintf(stderr, "No Daheng devices found\n");
        GXCloseLib();
        return 1;
    }

    GX_OPEN_PARAM open_param{};
    open_param.openMode = GX_OPEN_SN;
    open_param.accessMode = GX_ACCESS_EXCLUSIVE;
    open_param.pszContent = const_cast<char*>(args.sn.c_str());

    GX_DEV_HANDLE device = nullptr;
    if (!Ok(GXOpenDevice(&open_param, &device), "GXOpenDevice(SN)")) {
        // Fallback: first device
        std::fprintf(stderr, "Open by SN failed; trying index 1\n");
        if (!Ok(GXOpenDeviceByIndex(1, &device), "GXOpenDeviceByIndex")) {
            GXCloseLib();
            return 1;
        }
    }

    // Throughput uncapped (same intent as Rio DeviceLinkThroughputLimitMode=0).
    GXSetEnumValue(device, "DeviceLinkThroughputLimitMode", 0);

    // Full sensor then crop (Galaxy ROI order: offsets after size shrink carefully).
    GX_INT_VALUE wmax{};
    GX_INT_VALUE hmax{};
    if (!Ok(GXGetIntValue(device, "WidthMax", &wmax), "WidthMax") ||
        !Ok(GXGetIntValue(device, "HeightMax", &hmax), "HeightMax")) {
        GXCloseDevice(device);
        GXCloseLib();
        return 1;
    }
    GXSetIntValue(device, "OffsetX", 0);
    GXSetIntValue(device, "OffsetY", 0);
    GXSetIntValue(device, "Width", wmax.nCurValue);
    GXSetIntValue(device, "Height", hmax.nCurValue);

    const int64_t width = args.width;
    const int64_t height = args.height;
    if (!Ok(GXSetIntValue(device, "Width", width), "Width") ||
        !Ok(GXSetIntValue(device, "Height", height), "Height")) {
        GXCloseDevice(device);
        GXCloseLib();
        return 1;
    }
    // Center ROI when possible
    GX_INT_VALUE wcur{};
    GX_INT_VALUE hcur{};
    GXGetIntValue(device, "Width", &wcur);
    GXGetIntValue(device, "Height", &hcur);
    const int64_t ox = ((wmax.nCurValue - wcur.nCurValue) / 2) & ~1;
    const int64_t oy = ((hmax.nCurValue - hcur.nCurValue) / 2) & ~1;
    GXSetIntValue(device, "OffsetX", ox);
    GXSetIntValue(device, "OffsetY", oy);

    GXSetEnumValue(device, "ExposureAuto", 0);
    GXSetEnumValue(device, "GainAuto", 0);
    if (!Ok(GXSetFloatValue(device, "ExposureTime", args.exposure_us), "ExposureTime")) {
        GXCloseDevice(device);
        GXCloseLib();
        return 1;
    }

    // AFR Mode ON → max (Rio _sync_acquisition_framerate_to_max)
    GXSetEnumValue(device, "AcquisitionFrameRateMode", 1);
    GX_FLOAT_VALUE afr{};
    if (Ok(GXGetFloatValue(device, "AcquisitionFrameRate", &afr), "AcquisitionFrameRate get")) {
        GXSetFloatValue(device, "AcquisitionFrameRate", afr.dMax);
    }

    uint32_t ds_num = 0;
    if (!Ok(GXGetDataStreamNumFromDev(device, &ds_num), "GXGetDataStreamNumFromDev") || ds_num < 1) {
        GXCloseDevice(device);
        GXCloseLib();
        return 1;
    }
    GX_DS_HANDLE stream = nullptr;
    if (!Ok(GXGetDataStreamHandleFromDev(device, 1, &stream), "GXGetDataStreamHandleFromDev")) {
        GXCloseDevice(device);
        GXCloseLib();
        return 1;
    }
    uint32_t payload = 0;
    if (!Ok(GXGetPayLoadSize(stream, &payload), "GXGetPayLoadSize")) {
        GXCloseDevice(device);
        GXCloseLib();
        return 1;
    }
    const uint64_t buf_num = GalaxyBufferCount(payload);
    if (!Ok(GXSetAcqusitionBufferNumber(device, buf_num), "GXSetAcqusitionBufferNumber")) {
        GXCloseDevice(device);
        GXCloseLib();
        return 1;
    }

    GX_FLOAT_VALUE exp{};
    GXGetFloatValue(device, "ExposureTime", &exp);
    GX_FLOAT_VALUE sdk_fps{};
    GXGetFloatValue(device, "CurrentAcquisitionFrameRate", &sdk_fps);
    GXGetFloatValue(device, "AcquisitionFrameRate", &afr);

    std::printf("=== daheng_acq_probe (C++ / GXDQAllBufs) ===\n");
    std::printf("SN=%s ROI=%ldx%ld @ offset(%ld,%ld) exposure=%.1f us\n",
                args.sn.c_str(),
                static_cast<long>(wcur.nCurValue),
                static_cast<long>(hcur.nCurValue),
                static_cast<long>(ox),
                static_cast<long>(oy),
                exp.dCurValue);
    std::printf("payload=%u B  buffers=%llu  AFR_set=%.2f  SDK_now=%.2f\n",
                payload,
                static_cast<unsigned long long>(buf_num),
                afr.dCurValue,
                sdk_fps.dCurValue);
    std::printf("Running %.1f s (no RGB convert)...\n", args.seconds);

    std::vector<PGX_FRAME_BUFFER> frames(static_cast<size_t>(buf_num));
    if (!Ok(GXStreamOn(device), "GXStreamOn")) {
        GXCloseDevice(device);
        GXCloseLib();
        return 1;
    }

    using clock = std::chrono::steady_clock;
    const auto t0 = clock::now();
    auto window_start = t0;
    uint64_t window_frames = 0;
    uint64_t total_frames = 0;
    uint64_t incomplete = 0;
    double last_fps = 0.0;

    while (true) {
        const auto now = clock::now();
        const double elapsed =
            std::chrono::duration<double>(now - t0).count();
        if (elapsed >= args.seconds) {
            break;
        }

        uint32_t n = 0;
        GX_STATUS st = GXDQAllBufs(
            device, frames.data(), static_cast<uint32_t>(buf_num), &n, 1000);
        if (st == GX_STATUS_TIMEOUT) {
            continue;
        }
        if (st != GX_STATUS_SUCCESS) {
            PrintError(st);
            break;
        }
        if (n == 0) {
            continue;
        }
        if (frames[n - 1]->nStatus != GX_FRAME_STATUS_SUCCESS) {
            ++incomplete;
            GXQAllBufs(device);
            continue;
        }

        // Count every buffer (Galaxy Acq.FPS); do not convert/process pixels.
        window_frames += n;
        total_frames += n;
        GXQAllBufs(device);

        const double wdt =
            std::chrono::duration<double>(now - window_start).count();
        if (wdt >= 1.0) {
            last_fps = static_cast<double>(window_frames) / wdt;
            GXGetFloatValue(device, "CurrentAcquisitionFrameRate", &sdk_fps);
            std::printf("Acq.FPS=%.2f  SDK=%.2f  (batch_last=%u incomplete=%llu)\n",
                        last_fps,
                        sdk_fps.dCurValue,
                        n,
                        static_cast<unsigned long long>(incomplete));
            window_frames = 0;
            window_start = now;
        }
    }

    GXStreamOff(device);

    const double total_s =
        std::chrono::duration<double>(clock::now() - t0).count();
    const double mean_fps =
        total_s > 0.0 ? static_cast<double>(total_frames) / total_s : 0.0;
    GXGetFloatValue(device, "CurrentAcquisitionFrameRate", &sdk_fps);

    std::printf("--- summary ---\n");
    std::printf("mean Acq.FPS=%.2f  last_window=%.2f  SDK=%.2f  frames=%llu  incomplete=%llu\n",
                mean_fps,
                last_fps,
                sdk_fps.dCurValue,
                static_cast<unsigned long long>(total_frames),
                static_cast<unsigned long long>(incomplete));
    if (sdk_fps.dCurValue > 1.0) {
        std::printf("Acq/SDK ratio=%.3f\n", mean_fps / sdk_fps.dCurValue);
    }

    GXCloseDevice(device);
    GXCloseLib();
    return 0;
}
