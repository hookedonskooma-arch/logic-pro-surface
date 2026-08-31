#pragma once

#include <cstdint>

// RENDER PATH RULES (Apple AU sample / EVALS E09):
// no heap allocation, no file I/O, no locks, no Swift, no Objective-C.
// Preallocate everything. Bounded work only.

namespace logic_surface {

inline constexpr int kMaxQueuedEvents = 64;
inline constexpr uint8_t kNoteC3 = 60;
inline constexpr uint8_t kNoteE3 = 64;
inline constexpr uint8_t kNoteG3 = 67;
inline constexpr uint8_t kNoteC4 = 72;
inline constexpr int kPhraseNoteCount = 4;
inline constexpr uint32_t kFramesBetweenNotes = 480;
inline constexpr uint32_t kNoteLengthFrames = 240;

struct MidiEvent {
    uint32_t sample_offset;
    uint8_t status;
    uint8_t data1;
    uint8_t data2;
};

class PhraseKernel {
public:
    PhraseKernel() = default;

    void reset() noexcept;
    void triggerPhrase(uint32_t startOffset, uint8_t velocity) noexcept;

    // RENDER_PATH_BEGIN
    void render(uint32_t frameCount, MidiEvent* outEvents, int* outCount, int maxOut) noexcept;
    // RENDER_PATH_END

    int queuedCount() const noexcept { return queue_count_; }

private:
    MidiEvent queue_[kMaxQueuedEvents];
    int queue_count_ = 0;
    uint8_t last_velocity_ = 100;

    void pushEvent(uint32_t offset, uint8_t status, uint8_t data1, uint8_t data2) noexcept;
};

}  // namespace logic_surface
