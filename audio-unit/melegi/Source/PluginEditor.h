#pragma once
#include "PluginProcessor.h"
#include <juce_gui_extra/juce_gui_extra.h>

class MelegiEditor : public juce::AudioProcessorEditor
{
public:
    explicit MelegiEditor (MelegiProcessor&);
    ~MelegiEditor() override = default;

    void resized() override;

private:
    MelegiProcessor& processor;
    std::unique_ptr<juce::WebBrowserComponent> web;

    static std::optional<juce::WebBrowserComponent::Resource> provideResource (const juce::String& url);

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (MelegiEditor)
};
