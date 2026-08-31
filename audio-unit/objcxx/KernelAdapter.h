#pragma once

#include <stdint.h>

#ifdef __OBJC__
#import <Foundation/Foundation.h>
#import <AudioToolbox/AudioToolbox.h>

@interface KernelAdapter : NSObject
- (instancetype)init;
- (void)reset;
- (void)triggerPhraseWithOffset:(uint32_t)offset velocity:(uint8_t)velocity;
- (AUInternalRenderBlock)internalRenderBlock;
@end
#endif
