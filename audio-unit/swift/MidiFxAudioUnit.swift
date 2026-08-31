import AudioToolbox
import Foundation

// Swift AUAudioUnit layer. Apple sample shape:
//   Swift AUAudioUnit  ->  Objective-C++ adapter  ->  C++ kernel
//
// Apple: do not allocate, perform file I/O, take locks, or interact with the
// Swift or Objective-C runtimes in the real-time render path.
// This file sets up the unit and parameters. It does not emit MIDI.
// internalRenderBlock is the adapter's C++ hop — never a Swift loop.

@objc(LogicSurfaceMidiFxAudioUnit)
public class MidiFxAudioUnit: AUAudioUnit {
    private let adapter = KernelAdapter()
    private var _parameterTree: AUParameterTree?
    private let triggerParam: AUParameter

    public override init(componentDescription: AudioComponentDescription,
                         options: AudioComponentInstantiationOptions = []) throws {
        triggerParam = AUParameterTree.createParameter(
            withIdentifier: "triggerPhrase",
            name: "Trigger Phrase",
            address: 0,
            min: 0,
            max: 1,
            unit: .boolean,
            unitName: nil,
            flags: [.flag_IsWritable, .flag_IsReadable],
            valueStrings: nil,
            dependentParameters: nil
        )
        _parameterTree = AUParameterTree.createTree(withChildren: [triggerParam])
        try super.init(componentDescription: componentDescription, options: options)

        // Parameter observer runs on the UI / parameter thread, not render.
        triggerParam.valueObserver = { [weak self] value, _ in
            if value >= 0.5 {
                self?.adapter.triggerPhrase(withOffset: 0, velocity: 100)
            }
        }
    }

    public override var parameterTree: AUParameterTree? {
        return _parameterTree
    }

    public override var internalRenderBlock: AUInternalRenderBlock {
        return adapter.internalRenderBlock()
    }
}
