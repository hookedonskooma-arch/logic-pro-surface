#include "PluginEditor.h"
#include "BinaryData.h"

static std::vector<std::byte> toBytes (const char* data, int size)
{
    auto* p = reinterpret_cast<const std::byte*> (data);
    return { p, p + size };
}

std::optional<juce::WebBrowserComponent::Resource>
MelegiEditor::provideResource (const juce::String& url)
{
    if (url == "/" || url == "/index.html")
        return juce::WebBrowserComponent::Resource {
            toBytes (BinaryData::plugin_ui_html, BinaryData::plugin_ui_htmlSize),
            "text/html" };
    return std::nullopt;
}

MelegiEditor::MelegiEditor (MelegiProcessor& p)
    : AudioProcessorEditor (p), processor (p)
{
    auto options =
        juce::WebBrowserComponent::Options{}
            .withNativeIntegrationEnabled()
            .withResourceProvider ([] (const auto& url) { return provideResource (url); })
            .withNativeFunction ("queuePhrase",
                [this] (const juce::Array<juce::var>& args,
                        juce::WebBrowserComponent::NativeFunctionCompletion complete)
                {
                    // args[0]: [{pitch, startBeats, durBeats, vel}, ...]
                    const bool ok = args.size() == 1 && processor.queuePhraseBeats (args[0]);
                    complete (juce::var (ok));
                })
            .withNativeFunction ("getAgent",
                [this] (const juce::Array<juce::var>&,
                        juce::WebBrowserComponent::NativeFunctionCompletion complete)
                {
                    complete (juce::var (processor.selectedAgent));
                })
            .withNativeFunction ("setAgent",
                [this] (const juce::Array<juce::var>& args,
                        juce::WebBrowserComponent::NativeFunctionCompletion complete)
                {
                    if (args.size() == 1)
                        processor.selectedAgent = args[0].toString();
                    complete (juce::var (true));
                })
            .withNativeFunction ("getHostContext",
                [this] (const juce::Array<juce::var>&,
                        juce::WebBrowserComponent::NativeFunctionCompletion complete)
                {
                    auto* obj = new juce::DynamicObject();
                    obj->setProperty ("bpm",     processor.hostBpm.load());
                    obj->setProperty ("playing", processor.hostPlaying.load());
                    obj->setProperty ("ppq",     processor.hostPpq.load());
                    obj->setProperty ("loop",    processor.loopMode.load());
                    complete (juce::var (obj));
                })
            .withNativeFunction ("setLoop",
                [this] (const juce::Array<juce::var>& args,
                        juce::WebBrowserComponent::NativeFunctionCompletion complete)
                {
                    if (args.size() == 1)
                        processor.loopMode.store ((bool) args[0]);
                    complete (juce::var (processor.loopMode.load()));
                })
            .withNativeFunction ("setVozParam",
                [this] (const juce::Array<juce::var>& args,
                        juce::WebBrowserComponent::NativeFunctionCompletion complete)
                {
                    if (args.size() == 1)
                        processor.vozParam.store ((float) args[0]);
                    complete (juce::var (true));
                });

    web = std::make_unique<juce::WebBrowserComponent> (options);
    addAndMakeVisible (*web);
    web->goToURL (juce::WebBrowserComponent::getResourceProviderRoot());

    setResizable (true, true);
    setSize (1100, 760);
}

void MelegiEditor::resized()
{
    if (web != nullptr)
        web->setBounds (getLocalBounds());
}
