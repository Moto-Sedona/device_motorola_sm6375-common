/*
 * SPDX-FileCopyrightText: The LineageOS Project
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Legacy ION entry points for stock blobs built for the 5.4 kernel, such as
 * fingerprint TA clients and the audio calibration loader (libacdbloader.so).
 * GKI 6.1 has no /dev/ion, so allocations go to the
 * matching Qualcomm DMA-BUF heaps instead; the returned fds are dma-bufs,
 * which QSEECom and the audio calibration driver accept as before.
 */

#include <BufferAllocator/BufferAllocator.h>
#include <log/log.h>
#include <unistd.h>

#include <mutex>
#include <string>

#undef LOG_TAG
#define LOG_TAG "ion_qsecom_shim"

namespace {

// msm_ion_ids.h bit numbers used by the 5.4 vendor blobs.
constexpr unsigned int kIonQsecomTaHeap = 1u << 1;
constexpr unsigned int kIonQsecomHeap = 1u << 7;
constexpr unsigned int kIonSystemHeap = 1u << 25;
// ION buffers are uncached unless ION_FLAG_CACHED is set.
constexpr unsigned int kIonFlagCached = 1u << 0;

// Any non-negative value works as the "ion client": it is only passed back.
constexpr int kIonClientFd = 0x10e0;

BufferAllocator& Allocator() {
    static BufferAllocator allocator;
    return allocator;
}

std::string HeapForMask(unsigned int heap_mask, unsigned int flags) {
    if (heap_mask & kIonQsecomHeap) return "qcom,qseecom";
    if (heap_mask & kIonQsecomTaHeap) return "qcom,qseecom-ta";
    // libacdbloader shares this calibration buffer with the ADSP without any
    // cache maintenance, so keep the uncached semantics it asked for.
    if (heap_mask & kIonSystemHeap)
        return (flags & kIonFlagCached) ? "qcom,system" : "qcom,system-uncached";
    return "system";
}

}  // namespace

extern "C" int ion_open() {
    return kIonClientFd;
}

extern "C" int ion_close(int fd) {
    return fd == kIonClientFd ? 0 : -EINVAL;
}

extern "C" int ion_alloc_fd(int fd, size_t len, size_t align, unsigned int heap_mask,
                            unsigned int flags, int* handle_fd) {
    (void)align;
    if (fd != kIonClientFd || handle_fd == nullptr) return -EINVAL;

    static std::mutex lock;
    std::lock_guard<std::mutex> guard(lock);
    const std::string heap = HeapForMask(heap_mask, flags);
    int buf = Allocator().Alloc(heap, len);
    if (buf < 0) {
        ALOGE("%s: %zu bytes from %s (mask 0x%x) failed: %d", __func__, len, heap.c_str(),
              heap_mask, buf);
        return buf;
    }
    *handle_fd = buf;
    return 0;
}
