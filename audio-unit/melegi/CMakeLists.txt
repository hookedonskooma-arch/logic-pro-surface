cmake_minimum_required(VERSION 3.22)
project(MELEGI VERSION 0.1.0)

# AU MIDI FX only. Never VST. Never VST3. Not a synth. Not TTS.
# Not audio pass-through. Not Ollama. See docs/MELEGI-EXTRACTION.md.

set(CMAKE_OSX_ARCHITECTURES arm64)
set(CMAKE_CXX_STANDARD 17)

# JUCE is not vendored in this repo (the tree is huge). Studio MELEGI
# was built against JUCE 8.0.13. Fetch a checkout, then point here:
#   git clone --branch 8.0.13 --depth 1 https://github.com/juce-framework/JUCE.git
#   cmake -S audio-unit/melegi -B audio-unit/melegi/build -DJUCE_PATH=/path/to/JUCE
# Optional: -DMELEGI_FETCH_JUCE=ON clones 8.0.13 into the build dir only.
set(JUCE_PATH "" CACHE PATH "Path to a JUCE checkout. Do not vendor JUCE in git.")
option(MELEGI_FETCH_JUCE "Clone JUCE 8.0.13 via FetchContent into the build dir" OFF)
option(MELEGI_COPY_PLUGIN_AFTER_BUILD "Install MELEGI.component after build (Logic)" OFF)

if(MELEGI_FETCH_JUCE)
    include(FetchContent)
    FetchContent_Declare(JUCE
        GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
        GIT_TAG 8.0.13
        GIT_SHALLOW TRUE
    )
    FetchContent_MakeAvailable(JUCE)
elseif(JUCE_PATH)
    add_subdirectory("${JUCE_PATH}" JUCE)
elseif(DEFINED ENV{JUCE_PATH} AND EXISTS "$ENV{JUCE_PATH}/CMakeLists.txt")
    add_subdirectory("$ENV{JUCE_PATH}" JUCE)
elseif(EXISTS "$ENV{HOME}/JUCE/CMakeLists.txt")
    add_subdirectory("$ENV{HOME}/JUCE" JUCE)
else()
    message(FATAL_ERROR
        "JUCE not found. Clone 8.0.13 and pass -DJUCE_PATH=... "
        "or -DMELEGI_FETCH_JUCE=ON. See audio-unit/melegi/README.md. "
        "The JUCE tree is not vendored.")
endif()

juce_add_plugin(MELEGI
    COMPANY_NAME "GROUXX"
    BUNDLE_ID com.grouxx.melegi
    PLUGIN_MANUFACTURER_CODE Grxx
    PLUGIN_CODE Melr
    FORMATS AU
    PRODUCT_NAME "MELEGI"
    IS_MIDI_EFFECT TRUE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT TRUE
    IS_SYNTH FALSE
    COPY_PLUGIN_AFTER_BUILD ${MELEGI_COPY_PLUGIN_AFTER_BUILD}
    HARDENED_RUNTIME_ENABLED TRUE
    HARDENED_RUNTIME_OPTIONS com.apple.security.network.client
    NEEDS_WEB_BROWSER TRUE
)

juce_add_binary_data(MELEGIAssets SOURCES
    Resources/plugin_ui.html
)

target_sources(MELEGI PRIVATE
    Source/PluginProcessor.cpp
    Source/PluginEditor.cpp
)

target_compile_definitions(MELEGI PRIVATE
    JUCE_WEB_BROWSER=1
    JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0  # never VST; never VST3; flag stays off
)

target_link_libraries(MELEGI PRIVATE
    MELEGIAssets
    juce::juce_audio_utils
    juce::juce_gui_extra
    PUBLIC
    juce::juce_recommended_config_flags
    juce::juce_recommended_warning_flags
)
