#pragma once
#include <juce_audio_utils/juce_audio_utils.h>
#include "VozBridgeClient.h"

// One scheduled MIDI note, times in BEATS relative to phrase start —
// tempo-independent so the phrase follows the host clock exactly.
struct PhraseNote
{
    int    pitch      = 60;
    int    velocity   = 100;
    double startBeats = 0.0;
    double endBeats   = 0.0;
};

// A phrase handed over from the UI thread. Fixed capacity keeps the audio
// thread allocation-free: the UI thread fills a slot, the audio thread drains.
struct Phrase
{
    static constexpr int maxNotes = 256;
    PhraseNote notes[maxNotes];
    int    noteCount   = 0;
    double lengthBeats = 0.0;   // rounded up to whole bars at queue time
};

class MelegiProcessor : public juce::AudioProcessor
{
public:
    MelegiProcessor();
    ~MelegiProcessor() override = default;

    // -- AudioProcessor boilerplate ------------------------------------
    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override {}
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override                        { return true; }
    const juce::String getName() const override            { return "MELEGI"; }
    bool acceptsMidi() const override                      { return true; }
    bool producesMidi() const override                     { return true; }
    bool isMidiEffect() const override                     { return true; }
    double getTailLengthSeconds() const override           { return 0.0; }
    int getNumPrograms() override                          { return 1; }
    int getCurrentProgram() override                       { return 0; }
    void setCurrentProgram (int) override                  {}
    const juce::String getProgramName (int) override       { return {}; }
    void changeProgramName (int, const juce::String&) override {}
    void getStateInformation (juce::MemoryBlock&) override;
    void setStateInformation (const void*, int) override;

    // -- MELEGI ---------------------------------------------------------
    // Called from the UI (message) thread with notes in beats:
    // [{pitch, startBeats, durBeats, vel}]. Posts to the audio thread.
    bool queuePhraseBeats (const juce::var& notesArray);

    // UI-thread readable state (for the editor / JS bridge)
    juce::String selectedAgent { "riff" };

    // VOZ bridge parameter for Slice 1
    std::atomic<float> vozParam { 0.5f };  // normalized 0.0-1.0 parameter

    // host context, written by the audio thread each block, read by the UI
    std::atomic<double> hostBpm     { 120.0 };
    std::atomic<bool>   hostPlaying { false };
    std::atomic<double> hostPpq     { 0.0 };

    // loop-jam: replay the active phrase, swap to a queued one at the boundary
    std::atomic<bool> loopMode { false };

    // VOZ bridge (Slice 0): fire-and-forget TCP link to a companion process.
    // Connected but not wired to any param yet — MELEGI has no APVTS/FORMANT
    // knob for it to forward. Call bridgeClient.sendParam(id, value) from
    // wherever a future param surface makes sense.
    VozBridgeClient bridgeClient;

private:
    // slot exchange: UI writes, audio thread consumes
    static constexpr int fifoSlots = 4;
    Phrase phraseSlots[fifoSlots];
    juce::AbstractFifo phraseFifo { fifoSlots };

    // active playback state (audio thread only)
    Phrase  active;
    bool    activeValid    = false;
    double  anchorPpq      = 0.0;    // host ppq where the phrase starts (bar-locked)
    double  lastBlockEndPpq = 0.0;   // continuity check for jump detection
    bool    hostSynced     = false;  // true = clock is host ppq, false = freewheel
    int64_t freewheelPos   = 0;      // samples since phrase start (stopped-transport mode)
    bool    noteOn[128]    = {};
    bool    wasPlaying     = false;

    double  currentSampleRate = 44100.0;

    void allNotesOff (juce::MidiBuffer& midi, int samplePos);
    bool adoptNextPhrase();          // pull from FIFO into `active`; true if adopted

    // emit note on/offs whose beat positions fall in [posStart, posEnd),
    // mapping beats -> block sample offsets
    void emitRange (juce::MidiBuffer& midi, double posStart, double posEnd,
                    double samplesPerBeat, int numSamples, double wrapLen);

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (MelegiProcessor)
};
