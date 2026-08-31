cmake_minimum_required(VERSION 3.22)
project(LogicSurfaceMidiFx VERSION 0.0.1 LANGUAGES C CXX)

# AU MIDI Processor stub. FORMATS AU only. Never VST. Never VST3.
# MIDI effect (kAudioUnitType_MIDIProcessor / aumi), not a synth.
# MELEGI source is not in this drop. See docs/MELEGI-EXTRACTION.md.

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(LogicSurfaceKernel STATIC
    cpp-dsp/PhraseKernel.cpp
)
target_include_directories(LogicSurfaceKernel PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/cpp-dsp
)

# On macOS + Xcode the MODULE target below plus swift/ and objcxx/ produce
# an AU component. Linux CI only needs the kernel static lib / source scans.
if(APPLE)
    enable_language(OBJC OBJCXX)
    add_library(LogicSurfaceMidiFx MODULE
        cpp-dsp/PhraseKernel.cpp
        objcxx/KernelAdapter.mm
    )
    target_include_directories(LogicSurfaceMidiFx PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/cpp-dsp
        ${CMAKE_CURRENT_SOURCE_DIR}/objcxx
    )
    set_target_properties(LogicSurfaceMidiFx PROPERTIES
        BUNDLE TRUE
        BUNDLE_EXTENSION component
        MACOSX_BUNDLE_INFO_PLIST ${CMAKE_CURRENT_SOURCE_DIR}/Info.plist.in
        OUTPUT_NAME "LogicSurfaceMidiFx"
        PREFIX ""
        XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER "com.grouxx.logicsurface.midifx"
    )
endif()
