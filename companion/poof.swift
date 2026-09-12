import CoreGraphics
import AppKit
import Foundation

/// PoofOverlay: the teleport VFX. A pixel-poof cloud rendered on a borderless
/// transparent panel at the destination, timed to the gnome's appear/vanish.
/// No sprites needed — the poof is procedural (CoreAnimation particle-ish rings),
/// so it works before any AE render lands.

final class PoofOverlay: NSWindow {
    private let imageView: NSImageView

    init() {
        imageView = NSImageView()
        let screen = NSScreen.main?.frame ?? NSRect(x: 0, y: 0, width: 1680, height: 1050)
        super.init(contentRect: screen,
                   styleMask: [.borderless],
                   backing: .buffered,
                   defer: false)
        isOpaque = false
        backgroundColor = .clear
        level = .floating
        ignoresMouseEvents = true
        collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        contentView = imageView
    }

    /// A procedural poof: expanding rings + puff circles at the point, ~0.6s.
    func poof(at screenPoint: NSPoint, color: NSColor = NSColor(white: 0.9, alpha: 0.85)) {
        // screenPoint is in global screen coords (origin bottom-left) — convert to this
        // window's top-left based coordinate space.
        let screenH = NSScreen.main?.frame.height ?? 1050
        let local = NSPoint(x: screenPoint.x, y: screenH - screenPoint.y)

        let host = NSView(frame: NSRect(x: 0, y: 0, width: frame.width, height: frame.height))
        host.wantsLayer = true
        contentView = host

        let rings = 3
        let puffs = 6
        for i in 0..<(rings + puffs) {
            let isRing = i < rings
            let size: CGFloat = isRing ? CGFloat(30 + i * 45) : CGFloat(14 + i * 3)
            let layer = CALayer()
            layer.frame = NSRect(x: local.x - size / 2, y: local.y - size / 2, width: size, height: size)
            if isRing {
                layer.cornerRadius = size / 2
                layer.borderWidth = 3
                layer.borderColor = color.cgColor
                layer.backgroundColor = NSColor.clear.cgColor
            } else {
                layer.cornerRadius = size / 2
                layer.backgroundColor = color.withAlphaComponent(0.5).cgColor
                // puffs scatter outward
                let angle = CGFloat(i - rings) / CGFloat(puffs) * 2 * .pi
                let drift: CGFloat = 60
                layer.position = NSPoint(x: local.x + cos(angle) * drift * 0.4,
                                         y: local.y + sin(angle) * drift * 0.4)
            }
            host.layer?.addSublayer(layer)

            let pop = CABasicAnimation(keyPath: "transform.scale")
            pop.fromValue = 0.2
            pop.toValue = 1.6
            pop.duration = 0.5
            pop.fillMode = .forwards
            pop.isRemovedOnCompletion = false

            let fade = CABasicAnimation(keyPath: "opacity")
            fade.fromValue = 0.9
            fade.toValue = 0.0
            fade.duration = 0.6
            fade.fillMode = .forwards
            fade.isRemovedOnCompletion = false

            layer.add(pop, forKey: "pop")
            layer.add(fade, forKey: "fade")
        }

        orderFrontRegardless()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.75) { [weak self] in
            self?.orderOut(nil)
        }
    }
}