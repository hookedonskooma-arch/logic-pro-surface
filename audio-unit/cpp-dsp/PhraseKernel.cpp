#include "PhraseKernel.h"

namespace logic_surface {

void PhraseKernel::reset() noexcept {
    queue_count_ = 0;
    last_velocity_ = 100;
}

void PhraseKernel::pushEvent(uint32_t offset, uint8_t status, uint8_t data1, uint8_t data2) noexcept {
    if (queue_count_ >= kMaxQueuedEvents) {
        return;
    }
    MidiEvent& ev = queue_[queue_count_];
    ev.sample_offset = offset;
    ev.status = status;
    ev.data1 = data1;
    ev.data2 = data2;
    queue_count_ += 1;
}

void PhraseKernel::triggerPhrase(uint32_t startOffset, uint8_t velocity) noexcept {
    last_velocity_ = velocity == 0 ? static_cast<uint8_t>(100) : velocity;
    const uint8_t notes[kPhraseNoteCount] = {kNoteC3, kNoteE3, kNoteG3, kNoteC4};
    for (int i = 0; i < kPhraseNoteCount; ++i) {
        const uint32_t onAt = startOffset + static_cast<uint32_t>(i) * kFramesBetweenNotes;
        const uint32_t offAt = onAt + kNoteLengthFrames;
        pushEvent(onAt, 0x90, notes[i], last_velocity_);
        pushEvent(offAt, 0x80, notes[i], 0);
    }
}

// RENDER_PATH_BEGIN
void PhraseKernel::render(uint32_t frameCount, MidiEvent* outEvents, int* outCount, int maxOut) noexcept {
    if (outCount == nullptr) {
        return;
    }
    *outCount = 0;
    if (outEvents == nullptr || maxOut <= 0 || frameCount == 0) {
        return;
    }

    int kept = 0;
    for (int i = 0; i < queue_count_; ++i) {
        MidiEvent ev = queue_[i];
        if (ev.sample_offset < frameCount) {
            if (*outCount < maxOut) {
                outEvents[*outCount] = ev;
                *outCount += 1;
            }
        } else {
            ev.sample_offset -= frameCount;
            queue_[kept] = ev;
            kept += 1;
        }
    }
    queue_count_ = kept;
}
// RENDER_PATH_END

}  // namespace logic_surface
