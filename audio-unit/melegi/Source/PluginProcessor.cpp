#include "PluginProcessor.h"
#include "PluginEditor.h"

MelegiProcessor::MelegiProcessor()
    : AudioProcessor (BusesProperties()) // MIDI FX: no audio buses required
{
    bridgeClient.connect(); // 127.0.0.1:9001, no-ops until voz-bridge/bridge.js is running
}

void MelegiProcessor::prepareToPlay (double sampleRate, int)
{
    currentSampleRate = sampleRate;
}

bool MelegiProcessor::queuePhraseBeats (const juce::var& notesArray)
{
    auto* arr = notesArray.getArray();
    if (arr == nullptr || arr->isEmpty() || arr->size() > Phrase::maxNotes)
        return false;

    const auto scope = phraseFifo.write (1);
    if (scope.blockSize1 + scope.blockSize2 < 1)
        return false; // queue full — UI shows "Riff is ahead of you"

    auto& slot = phraseSlots[scope.blockSize1 > 0 ? scope.startIndex1 : scope.startIndex2];
    slot.noteCount = 0;
    double maxEnd = 0.0;

    for (const auto& n : *arr)
    {
        auto* obj = n.getDynamicObject();
        if (obj == nullptr) return false;

        const int pitch = (int) obj->getProperty ("pitch");
        const double start = (double) obj->getProperty ("startBeats");
        const double dur = (double) obj->getProperty ("durBeats");
        const int vel = obj->hasProperty ("vel") ? (int) obj->getProperty ("vel") : 100;

        if (pitch < 0 || pitch > 127 || dur <= 0.0 || start < 0.0
            || vel < 1 || vel > 127)
            return false; // validator: musician-readable message lives UI-side

        auto& note = slot.notes[slot.noteCount++];
        note.pitch      = pitch;
        note.velocity   = vel;
        note.startBeats = start;
        note.endBeats   = start + dur;
        maxEnd = std::max (maxEnd, note.endBeats);
    }
    // round phrase length up to whole 4/4 bars so loops repeat on the grid
    slot.lengthBeats = std::max (4.0, std::ceil (maxEnd / 4.0) * 4.0);
    return true;
}

void MelegiProcessor::allNotesOff (juce::MidiBuffer& midi, int samplePos)
{
    for (int p = 0; p < 128; ++p)
        if (noteOn[p])
        {
            midi.addEvent (juce::MidiMessage::noteOff (1, p), samplePos);
            noteOn[p] = false;
        }
}

bool MelegiProcessor::adoptNextPhrase()
{
    if (phraseFifo.getNumReady() < 1)
        return false;
    const auto scope = phraseFifo.read (1);
    const int idx = scope.blockSize1 > 0 ? scope.startIndex1 : scope.startIndex2;
    active = phraseSlots[idx];
    return true;
}

void MelegiProcessor::emitRange (juce::MidiBuffer& midi, double posStart, double posEnd,
                                 double samplesPerBeat, int numSamples, double wrapLen)
{
    // wrapLen > 0: loop mode — events repeat every wrapLen beats.
    auto emitAt = [&] (double eventBeat, bool on, const PhraseNote& n)
    {
        const int offset = juce::jlimit (0, numSamples - 1,
            (int) ((eventBeat - posStart) * samplesPerBeat));
        if (on)
        {
            midi.addEvent (juce::MidiMessage::noteOn (1, n.pitch, (juce::uint8) n.velocity), offset);
            noteOn[n.pitch] = true;
        }
        else
        {
            midi.addEvent (juce::MidiMessage::noteOff (1, n.pitch), offset);
            noteOn[n.pitch] = false;
        }
    };

    for (int i = 0; i < active.noteCount; ++i)
    {
        const auto& n = active.notes[i];
        if (wrapLen <= 0.0)
        {
            if (n.startBeats >= posStart && n.startBeats < posEnd) emitAt (n.startBeats, true, n);
            if (n.endBeats   >= posStart && n.endBeats   < posEnd) emitAt (n.endBeats, false, n);
        }
        else
        {
            // find every repetition k with (note + k*wrapLen) inside the block
            for (const bool on : { true, false })
            {
                const double base = on ? n.startBeats : n.endBeats;
                double k = std::floor ((posStart - base) / wrapLen);
                for (double rep = base + k * wrapLen; rep < posEnd; rep += wrapLen)
                    if (rep >= posStart)
                        emitAt (rep, on, n);
            }
        }
    }
}

void MelegiProcessor::processBlock (juce::AudioBuffer<float>& audio,
                                    juce::MidiBuffer& midi)
{
    juce::ScopedNoDenormals noDenormals;
    audio.clear();

    // Forward parameter value via VOZ bridge (Slice 1)
    // Send the parameter value every block for real-time updates
    static int paramSendCounter = 0;
    if (++paramSendCounter >= 10) {  // Send every 10 blocks to reduce network traffic
        paramSendCounter = 0;
        bridgeClient.sendParam("vozParam", vozParam.load());
    }

    const int numSamples = audio.getNumSamples() > 0 ? audio.getNumSamples()
                                                     : getBlockSize();

    // read host transport once per block; publish for the UI up-link
    bool   isPlaying = false;
    double bpm = hostBpm.load();
    double ppq = 0.0;
    bool   havePpq = false;
    double beatsPerBar = 4.0;

    if (auto* ph = getPlayHead())
        if (auto pos = ph->getPosition())
        {
            isPlaying = pos->getIsPlaying();
            if (auto b = pos->getBpm())          { bpm = *b; hostBpm.store (*b); }
            if (auto p = pos->getPpqPosition())  { ppq = *p; havePpq = true; hostPpq.store (*p); }
            if (auto ts = pos->getTimeSignature())
                beatsPerBar = ts->numerator * (4.0 / ts->denominator);
            hostPlaying.store (isPlaying);
        }

    if (bpm <= 0.0) bpm = 120.0;
    const double samplesPerBeat = currentSampleRate * 60.0 / bpm;
    const double blockBeats     = numSamples / samplesPerBeat;

    // transport stop: flush and drop host sync (phrase stays armed for freewheel)
    if (wasPlaying && ! isPlaying)
    {
        allNotesOff (midi, 0);
        activeValid = false;
        hostSynced  = false;
    }
    wasPlaying = isPlaying;

    // playhead jump (cycle wrap, scrub): kill held notes; loop math re-maps
    if (hostSynced && isPlaying && havePpq
        && std::abs (ppq - lastBlockEndPpq) > 0.1)
        allNotesOff (midi, 0);

    // adopt a phrase when idle
    if (! activeValid && adoptNextPhrase())
    {
        activeValid = true;
        if (isPlaying && havePpq)
        {
            hostSynced = true;
            anchorPpq  = std::ceil (ppq / beatsPerBar) * beatsPerBar; // next bar line
        }
        else
        {
            hostSynced   = false;
            freewheelPos = 0;
        }
    }

    if (! activeValid)
    {
        lastBlockEndPpq = ppq + blockBeats;
        return;
    }

    const bool looping = loopMode.load();

    if (hostSynced && havePpq)
    {
        // phrase position derived FROM the host clock — tempo ramps, cycle
        // jumps and scrubs all stay locked
        const double posStart = ppq - anchorPpq;
        const double posEnd   = posStart + blockBeats;

        if (looping)
        {
            emitRange (midi, posStart, posEnd, samplesPerBeat, numSamples, active.lengthBeats);
            // boundary swap: a queued phrase takes over at the next repeat line
            if (phraseFifo.getNumReady() > 0)
            {
                const double intoPhrase = std::fmod (std::max (0.0, posEnd), active.lengthBeats);
                if (intoPhrase < blockBeats * 1.5)   // we just crossed (or are about to cross) the line
                {
                    const double oldLen = active.lengthBeats;
                    if (adoptNextPhrase())
                        anchorPpq += std::floor ((posEnd) / oldLen) * oldLen; // re-anchor at the boundary
                }
            }
        }
        else
        {
            emitRange (midi, posStart, posEnd, samplesPerBeat, numSamples, 0.0);
            if (posStart > active.lengthBeats)      // one-shot finished
                activeValid = false;
        }
    }
    else
    {
        // freewheel: transport stopped — play immediately, counted in samples
        const double posStart = freewheelPos / samplesPerBeat;
        const double posEnd   = posStart + blockBeats;
        emitRange (midi, posStart, posEnd, samplesPerBeat, numSamples, 0.0);
        freewheelPos += numSamples;
        if (posStart > active.lengthBeats)
        {
            allNotesOff (midi, numSamples - 1);
            activeValid = false;
        }
    }

    lastBlockEndPpq = ppq + blockBeats;
}

void MelegiProcessor::getStateInformation (juce::MemoryBlock& dest)
{
    juce::ValueTree state ("MELEGI");
    state.setProperty ("agent", selectedAgent, nullptr);
    state.setProperty ("loop", loopMode.load(), nullptr);
    juce::MemoryOutputStream out (dest, false);
    state.writeToStream (out);
}

void MelegiProcessor::setStateInformation (const void* data, int size)
{
    auto state = juce::ValueTree::readFromData (data, (size_t) size);
    if (state.isValid())
    {
        if (state.hasProperty ("agent")) selectedAgent = state["agent"].toString();
        if (state.hasProperty ("loop"))  loopMode.store ((bool) state["loop"]);
    }
}

juce::AudioProcessorEditor* MelegiProcessor::createEditor()
{
    return new MelegiEditor (*this);
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new MelegiProcessor();
}
