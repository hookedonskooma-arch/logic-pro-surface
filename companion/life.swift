/// LifeLayer: the things that make a moving box feel like a creature.
///
/// Four systems, all additive to the existing GnomeAnimator:
///   1. Ground shadow — a soft ellipse under the gnome that scales/fades with
///      his height (zoom raises him, hop lifts him, drag swings him).
///   2. Idle life — a behavior loop on a 6-14s random timer: blink (quick
///      squash of the eye area via scale), weight shift (tiny x lean), ear
///      twitch (hat tilt), deep sigh (slow scale.y drop). Never repeats
///      exactly; timer re-arms with random jitter.
///   3. Squash & stretch constants — every gesture gets volume preservation:
///      up = taller+narrower, down = shorter+wider. Baked into helper.
///   4. Drag life — while dragged he dangles (gravity lean toward motion),
///      on release he settles with a springy wobble.
///
/// Nothing here touches the ladder, the ledger, or any DAW. Pure body.

import AppKit

final class LifeLayer {
    private weak var view: NSView?
    private weak var window: NSWindow?
    private var shadowLayer: CALayer?
    private var idleTimer: Timer?
    private var isDragging = false
    private var lastDragPoint: NSPoint = .zero

    /// emote sprites for blink/look variants (head-level swaps)
    private var faceURLs: [URL] = []
    private var baseFaceURL: URL?

    init(view: NSView, window: NSWindow?) {
        self.view = view
        self.window = window
        installShadow()
        scheduleIdleLife()
    }

    // MARK: 1. Ground shadow

    private func installShadow() {
        guard let v = view else { return }
        v.wantsLayer = true
        let s = CALayer()
        s.backgroundColor = NSColor.black.withAlphaComponent(0.28).cgColor
        s.cornerRadius = 14
        s.opacity = 0.55
        s.frame = NSRect(x: 0, y: 0, width: 150, height: 22)
        s.isGeometryFlipped = false
        // parent anchor is bottom-center (0.5, 0), so place the shadow at the feet
        s.position = CGPoint(x: 0, y: -6)
        s.anchorPoint = CGPoint(x: 0.5, y: 0.5)
        v.layer?.addSublayer(s)
        shadowLayer = s
        breatheShadow()
    }

    private func breatheShadow() {
        guard let s = shadowLayer else { return }
        let b = CABasicAnimation(keyPath: "opacity")
        b.fromValue = 0.45
        b.toValue = 0.62
        b.duration = 4.0
        b.autoreverses = true
        b.repeatCount = .infinity
        b.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        s.add(b, forKey: "shadowBreathe")
    }

    /// Shadow responds to vertical lift: higher = smaller + fainter.
    func updateShadow(lift: CGFloat, scale: CGFloat) {
        guard let s = shadowLayer else { return }
        let lift01 = max(0, min(1, lift / 300))
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        s.opacity = Float(0.55 - 0.4 * lift01)
        s.transform = CATransform3DMakeScale(max(0.4, scale - lift01 * 0.3), max(0.4, 1 - lift01 * 0.5), 1)
        CATransaction.commit()
    }

    // MARK: 2. Idle life — random micro-behaviors

    /// Face sources for idle blinks/looks. The window registers its face files.
    func registerFaces(base: URL?, variants: [URL]) {
        baseFaceURL = base
        faceURLs = variants
    }

    private func scheduleIdleLife() {
        let next = Double.random(in: 6...14)
        idleTimer = Timer.scheduledTimer(withTimeInterval: next, repeats: false) { [weak self] _ in
            self?.doIdleBehavior()
            self?.scheduleIdleLife()
        }
    }

    private func doIdleBehavior() {
        guard !isDragging else { return }
        let roll = Int.random(in: 0..<5)
        switch roll {
        case 0: blink()
        case 1: weightShift()
        case 2: lookAround()
        case 3: deepSigh()
        default: earTwitch()
        }
    }

    /// Blink: quick vertical squash of the whole sprite — reads as a blink at
    /// this pixel scale.
    func blink() {
        guard let layer = view?.layer else { return }
        let b = CAKeyframeAnimation(keyPath: "transform.scale.y")
        b.values = [1.0, 0.96, 1.0]
        b.keyTimes = [0, 0.5, 1]
        b.duration = 0.16
        b.isAdditive = true
        layer.add(b, forKey: "blink")
    }

    /// Weight shift: tiny x-lean, hold, return. Gnomes don't stand still.
    func weightShift() {
        guard let layer = view?.layer else { return }
        let dir = CGFloat.random(in: -1...1) >= 0 ? 1.0 : -1.0
        let lean = CAKeyframeAnimation(keyPath: "transform.rotation.z")
        lean.values = [0, dir * 0.03, dir * 0.03, 0]
        lean.keyTimes = [0, 0.4, 0.75, 1]
        lean.duration = 2.4
        lean.isAdditive = true
        layer.add(lean, forKey: "weightshift")
    }

    /// Look around: two short hat-tilts in different directions.
    func lookAround() {
        guard let layer = view?.layer else { return }
        let l = CAKeyframeAnimation(keyPath: "transform.rotation.z")
        let d1 = CGFloat.random(in: 0.04...0.08)
        let d2 = -d1 * CGFloat.random(in: 0.6...1.2)
        l.values = [0, d1, 0, d2, 0]
        l.keyTimes = [0, 0.2, 0.4, 0.7, 1]
        l.duration = 2.2
        l.isAdditive = true
        l.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(l, forKey: "look")
    }

    /// Deep sigh: slow scale.y drop then recover — the old man breathes.
    func deepSigh() {
        guard let layer = view?.layer else { return }
        let s = CAKeyframeAnimation(keyPath: "transform.scale.y")
        s.values = [1.0, 1.012, 0.982, 1.0]
        s.keyTimes = [0, 0.3, 0.75, 1]
        s.duration = 3.0
        s.isAdditive = true
        s.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(s, forKey: "sigh")
        blink()
    }

    /// Ear/hat twitch: tiny quick rotation burst.
    func earTwitch() {
        guard let layer = view?.layer else { return }
        let t = CAKeyframeAnimation(keyPath: "transform.rotation.z")
        t.values = [0, 0.02, -0.015, 0.008, 0]
        t.keyTimes = [0, 0.3, 0.55, 0.8, 1]
        t.duration = 0.45
        t.isAdditive = true
        layer.add(t, forKey: "twitch")
    }

    // MARK: 3. Squash & stretch helper — volume-preserving gesture accent

    /// Call inside any gesture: returns (sx, sy) pair for a scale keyframe.
    /// dy>0 = going up (stretch tall), dy<0 = landing (squash wide).
    static func squashStretch(_ dy: CGFloat) -> [NSPoint] {
        let stretch = NSPoint(x: 1.0 - 0.06 * dy, y: 1.0 + 0.10 * dy)
        let squash = NSPoint(x: 1.0 + 0.08 * dy, y: 1.0 - 0.12 * dy)
        return [NSPoint(x: 1, y: 1), stretch, NSPoint(x: 1, y: 1), squash, NSPoint(x: 1, y: 1)]
    }

    // MARK: 3. Drag life — dangle + springy settle

    func setDragging(_ dragging: Bool) {
        isDragging = dragging
        if dragging {
            idleTimer?.invalidate()
        } else {
            settle()
            scheduleIdleLife()
        }
    }

    /// While dragged: the sprite lags the motion — a gravity tilt toward the
    /// drag direction, like he's hanging from your cursor.
    func dragTilt(velocityX: CGFloat) {
        guard let layer = view?.layer, isDragging else { return }
        let clamped = max(-0.35, min(0.35, velocityX / 900.0))
        // transform directly while dragging (no keyframe; the next event re-sets)
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        let current = layer.transform
        layer.transform = CATransform3DRotate(current, clamped * 0.2, 0, 0, 1)
        CATransaction.commit()
    }

    /// On release: springy settle — overshoot past upright, wobble, rest.
    func settle() {
        guard let layer = view?.layer else { return }
        let rest = CATransform3DIdentity
        // animate from current (tilted) back to rest with overshoot
        let s = CASpringAnimation(keyPath: "transform")
        s.fromValue = NSValue(caTransform3D: layer.transform)
        s.toValue = NSValue(caTransform3D: rest)
        s.damping = 9
        s.mass = 1.2
        s.stiffness = 120
        s.duration = 0.9
        s.isAdditive = false
        layer.add(s, forKey: "settle")
        // reset immediately after the animation's fromValue is captured
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.02) {
            layer.transform = rest
        }
    }

    /// Lift reading for the shadow while dragging: distance from home y.
    func dragLift(currentY: CGFloat, homeY: CGFloat) -> CGFloat {
        abs(currentY - homeY)
    }

    func stopAll() {
        idleTimer?.invalidate()
        idleTimer = nil
    }
}