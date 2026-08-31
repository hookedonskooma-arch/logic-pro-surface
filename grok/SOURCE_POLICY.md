# Source policy

Apple is highest authority. Community MCP repos are evidence, not spec.

1. Current Apple Developer documentation (AUAudioUnit, CoreMIDI, AXUIElement, AVFAudio samples).
2. Current Apple Logic Pro User Guide and Control Surfaces Support Guide.
3. Apple sample code (Swift AUAudioUnit → Objective-C++ → C++ kernel).
4. Reproducible tests against the target Logic Pro (cite version, date, eval id).
5. This repository's evals and capability matrix.
6. Mature open-source implementations (MongLong, koltyj, rubenknol, qinnovates) as comparative specimens.
7. GitHub issues / ADRs from those specimens.
8. Forums and hearsay.
9. Model memory — lowest. Memory does not create TESTED.

Mandatory: architecture claims about Logic support, AU behavior, permissions, CoreMIDI, or Accessibility need a citation or an EXPERIMENTAL/UNKNOWN tag.

Forbidden promotions: "koltyj stars ⇒ VERIFIED", "CGEvent returned ⇒ confirmed", "AX node flipped ⇒ musical truth", "JUCE can VST ⇒ Logic native VST".
