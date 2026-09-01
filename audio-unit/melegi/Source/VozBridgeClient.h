// VozBridgeClient.h — Slice 0
//
// Minimal TCP client that connects to the Node bridge (bridge.js) and
// sends one JSON line per parameter change:
//   {"param":"<name>","value":<float>}\n
//
// Usage in PluginProcessor:
//
//   In the header:
//     VozBridgeClient bridgeClient;
//
//   In the constructor, after apvts is set up:
//     bridgeClient.connect();
//     apvts.addParameterListener("formant", &bridgeParamForwarder);
//     // or simplest for Slice 0: call bridgeClient.sendParam() directly
//     // from your existing parameterChanged() override.
//
//   Wherever your FORMANT parameter changes (e.g. in
//   AudioProcessorValueTreeState::Listener::parameterChanged):
//     void parameterChanged(const juce::String& parameterID, float newValue) override
//     {
//         bridgeClient.sendParam(parameterID, newValue);
//     }
//
// This uses juce::StreamingSocket, which is part of juce_core — no extra
// modules or third-party libs needed. Connection is fire-and-forget:
// if the bridge isn't running, sendParam() just no-ops (checked via
// isConnected()) so the plugin never blocks or crashes without it.

#pragma once

#include <juce_core/juce_core.h>
#include <juce_events/juce_events.h>

class VozBridgeClient : private juce::Thread
{
public:
    VozBridgeClient() : juce::Thread("VozBridgeClient") {}

    ~VozBridgeClient() override
    {
        stopThread(2000);
    }

    // Call once, e.g. in the plugin constructor. Connects in the
    // background so it never blocks the audio thread or plugin load.
    void connect(const juce::String& host = "127.0.0.1", int port = 9001)
    {
        targetHost = host;
        targetPort = port;
        startThread();
    }

    // Call from the message thread whenever a tracked parameter changes.
    // Safe to call even if not connected yet — it just no-ops.
    void sendParam(const juce::String& paramId, float value)
    {
        const juce::ScopedLock lock(socketLock);

        if (socket == nullptr || !socket->isConnected())
            return;

        juce::DynamicObject::Ptr obj = new juce::DynamicObject();
        obj->setProperty("param", paramId);
        obj->setProperty("value", value);

        juce::String json = juce::JSON::toString(juce::var(obj.get()), true);
        json << "\n"; // newline-delimited, matches bridge.js parsing

        auto utf8 = json.toRawUTF8();
        socket->write(utf8, (int) strlen(utf8));
    }

    bool isConnected() const
    {
        const juce::ScopedLock lock(socketLock);
        return socket != nullptr && socket->isConnected();
    }

private:
    void run() override
    {
        // Simple retry loop: try to connect, and if the bridge isn't up
        // yet (or drops), keep trying every couple seconds rather than
        // giving up. Slice 0 doesn't need anything fancier than this.
        while (!threadShouldExit())
        {
            {
                const juce::ScopedLock lock(socketLock);
                if (socket == nullptr || !socket->isConnected())
                {
                    socket.reset(new juce::StreamingSocket());
                    bool ok = socket->connect(targetHost, targetPort, 1000);
                    if (ok)
                        juce::Logger::writeToLog("VozBridgeClient: connected to " + targetHost + ":" + juce::String(targetPort));
                }
            }

            wait(2000);
        }
    }

    juce::CriticalSection socketLock;
    std::unique_ptr<juce::StreamingSocket> socket;
    juce::String targetHost;
    int targetPort = 9001;
};
