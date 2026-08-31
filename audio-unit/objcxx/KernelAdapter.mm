#import "KernelAdapter.h"
#include "PhraseKernel.h"

// Objective-C++ adapter. Construction and parameter hops may use ObjC.
// The block returned by -internalRenderBlock calls C++ only: stack buffers,
// no alloc, no I/O, no locks, no Swift, no ObjC messages inside the block.

@implementation KernelAdapter {
    logic_surface::PhraseKernel _kernel;
}

- (instancetype)init {
    self = [super init];
    return self;
}

- (void)reset {
    _kernel.reset();
}

- (void)triggerPhraseWithOffset:(uint32_t)offset velocity:(uint8_t)velocity {
    _kernel.triggerPhrase(offset, velocity);
}

- (AUInternalRenderBlock)internalRenderBlock {
    logic_surface::PhraseKernel* kernel = &_kernel;
    return ^AUAudioUnitStatus(AudioUnitRenderActionFlags* actionFlags,
                              const AudioTimeStamp* timestamp,
                              AUAudioFrameCount frameCount,
                              NSInteger outputBusNumber,
                              AudioBufferList* outputData,
                              const AURenderEvent* realtimeEventListHead,
                              AURenderPullInputBlock pullInputBlock) {
        // RENDER_PATH_BEGIN
        logic_surface::MidiEvent stackEvents[logic_surface::kMaxQueuedEvents];
        int count = 0;
        kernel->render(static_cast<uint32_t>(frameCount),
                       stackEvents,
                       &count,
                       logic_surface::kMaxQueuedEvents);
        (void)actionFlags;
        (void)timestamp;
        (void)outputBusNumber;
        (void)outputData;
        (void)realtimeEventListHead;
        (void)pullInputBlock;
        (void)count;
        return noErr;
        // RENDER_PATH_END
    };
}

@end
