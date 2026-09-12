// GNOMO — the desk companion window.
//
// Rules this file obeys (studio/GNOMO.md, docs/HONEST_CONTRACT.md):
//   - ONE ladder, ONE mouth. This window owns neither. Every decision and
//     every spoken word is delegated to `python -m gnomo --json ...`.
//   - The window adds a face, a bubble, a tier badge, and a place to type.
//     It never decides, never speaks on its own, never invents state.
//   - Body verbs (walk / zoom / point / come) move the window's own body.
//     They never reach the ladder and never ledger. Closed sets, fail
//     closed: an unknown target is a rejection, never a guess.
//   - Hearing is push-to-talk: the ears open only while the mic button is
//     held on, and every transcript goes through the same routing table
//     as typed text. The window adds no new paths.
//   - If the CLI is missing or fails, the bubble says so. It never pretends.
//
// Build: swiftc -o companion/build/Gnomo companion/main.swift
// Run:   companion/build/Gnomo

import AppKit
import AVFoundation
import Speech

// MARK: - The CLI record we parse (mirror of logic-probe/gnomo/cli.py)

struct CLIError: Error, CustomStringConvertible {
    let message: String
    var description: String { message }
}

struct Decision: Codable {
    let companion: String?
    let command: String?
    let hat: String?
    let tier: Int?
    let authority: String?
    let mode: String?
    let action: String?
    let spoken: String?
    let voice: Voice?
    struct Voice: Codable {
        let spoke: Bool?
        let reason: String?
    }
}

// MARK: - Repo discovery + CLI bridge

enum Gnomo {
    /// Walk up from the executable until we find a dir holding
    /// logic-probe/ and companion/assets/gnome-face.png. GNOMO_REPO wins.
    static let repoRoot: String = {
        if let env = ProcessInfo.processInfo.environment["GNOMO_REPO"] {
            return env
        }
        var url = URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent()
        for _ in 0..<8 {
            let candidate = url.path
            let hasProbe = FileManager.default.fileExists(
                atPath: candidate + "/logic-probe/gnomo/cli.py")
            let hasFace = FileManager.default.fileExists(
                atPath: candidate + "/companion/assets/gnome-face.png")
            if hasProbe && hasFace {
                return candidate
            }
            url = url.deletingLastPathComponent()
        }
        return FileManager.default.currentDirectoryPath
    }()

    static var assetsDir: String { repoRoot + "/companion/assets" }

    /// Python that can run the gnomo package. GNOMO_PYTHON wins; then the
    /// hermes venv; then system python3. Proven once, cached.
    static let python: String = {
        if let env = ProcessInfo.processInfo.environment["GNOMO_PYTHON"] {
            return env
        }
        for candidate in [
            "/Users/christian.grau/.hermes/hermes-agent/venv/bin/python",
            "/usr/bin/python3",
        ] {
            if FileManager.default.isExecutableFile(atPath: candidate) {
                return candidate
            }
        }
        return "python3"
    }()

    /// Run `python -m gnomo --json <args>`; return (stdout, stderr, code).
    static func run(_ args: String..., timeout: TimeInterval = 60) -> (out: String, err: String, code: Int32) {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: python)
        task.currentDirectoryURL = URL(fileURLWithPath: repoRoot)
        task.arguments = ["-m", "gnomo", "--json"] + args
        var env = ProcessInfo.processInfo.environment
        env["PYTHONPATH"] = repoRoot + "/logic-probe"
        task.environment = env
        let outPipe = Pipe()
        let errPipe = Pipe()
        task.standardOutput = outPipe
        task.standardError = errPipe
        do {
            try task.run()
        } catch {
            return ("", "cannot launch \(python): \(error.localizedDescription)", -1)
        }
        let watchdog = DispatchWorkItem { if task.isRunning { task.terminate() } }
        DispatchQueue.global().asyncAfter(deadline: .now() + timeout, execute: watchdog)
        task.waitUntilExit()
        watchdog.cancel()
        let out = String(data: outPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        let err = String(data: errPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        return (out, err, task.terminationStatus)
    }

    static func decide(_ action: String) -> Result<Decision, CLIError> {
        finish(run("decide", action))
    }

    static func park(_ idea: String) -> Result<Decision, CLIError> {
        finish(run("park", idea))
    }

    static func next() -> Result<Decision, CLIError> {
        finish(run("next"))
    }

    private static func finish(_ r: (out: String, err: String, code: Int32)) -> Result<Decision, CLIError> {
        if r.code == 0, let d = parse(r.out) {
            return .success(d)
        }
        if r.code == 2, !r.err.isEmpty {
            return .failure(CLIError(message: r.err.trimmingCharacters(in: .whitespacesAndNewlines)))
        }
        if let d = parse(r.out) {
            return .success(d)
        }
        let why = r.err.isEmpty ? "exit \(r.code)" : r.err
        return .failure(CLIError(message: "the ladder did not answer: \(why)"))
    }

    static func parse(_ blob: String) -> Decision? {
        try? JSONDecoder().decode(Decision.self, from: Data(blob.utf8))
    }
}

// MARK: - Screen facts (CGWindowList is public; no pixel reading)

enum ScreenFacts {
    /// Other apps' on-screen windows: (owner, title, bounds). Window titles
    /// need screen-recording permission the user may not have granted, so
    /// a missing title is honest and normal — matching is by owner first.
    static func otherWindows(excluding pid: Int32) -> [(owner: String, title: String, frame: NSRect)] {
        guard let info = CGWindowListCopyWindowInfo(
            [.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID)
            as? [[String: Any]] else { return [] }
        var out: [(String, String, NSRect)] = []
        for w in info {
            let ownerPID = w[kCGWindowOwnerPID as String] as? Int32 ?? -1
            if ownerPID == pid { continue }
            let owner = w[kCGWindowOwnerName as String] as? String ?? ""
            let title = w[kCGWindowName as String] as? String ?? ""
            let layer = w[kCGWindowLayer as String] as? Int ?? 0
            if layer != 0 { continue } // skip menus, overlays
            if let b = w[kCGWindowBounds as String] as? [String: Any],
               let x = b["X"] as? CGFloat, let y = b["Y"] as? CGFloat,
               let w2 = b["Width"] as? CGFloat, let h = b["Height"] as? CGFloat {
                if w2 < 60 || h < 60 { continue } // skip scraps
                out.append((owner, title, NSRect(x: x, y: y, width: w2, height: h)))
            }
        }
        return out
    }
}

// MARK: - Drag anywhere (gnome, bubble, badge all forward)

class DragView: NSView {
    var onDragStart: ((NSPoint) -> Void)?
    var onDragMove: ((NSPoint) -> Void)?

    override func mouseDown(with event: NSEvent) {
        window?.makeKey()
        onDragStart?(NSEvent.mouseLocation)
    }

    override func mouseDragged(with event: NSEvent) {
        onDragMove?(NSEvent.mouseLocation)
    }
}

// MARK: - Speech bubble

final class BubbleView: DragView {
    var text: String = "" {
        didSet {
            needsDisplay = true
            popIn()
        }
    }
    var subtext: String = "" {
        didSet { needsDisplay = true }
    }

    override var isOpaque: Bool { false }

    /// A new answer pops the bubble in — a quarter-second scale-up.
    private func popIn() {
        guard let layer = layer else {
            wantsLayer = true
            return
        }
        let pop = CAKeyframeAnimation(keyPath: "transform.scale")
        pop.values = [0.92, 1.03, 1.0]
        pop.keyTimes = [0, 0.6, 1]
        pop.duration = 0.28
        pop.timingFunction = CAMediaTimingFunction(name: .easeOut)
        layer.add(pop, forKey: "popin")
    }

    override func draw(_ dirtyRect: NSRect) {
        let path = NSBezierPath(roundedRect: bounds, xRadius: 14, yRadius: 14)
        NSColor(calibratedWhite: 0.07, alpha: 0.94).setFill()
        path.fill()

        let body = NSMutableParagraphStyle()
        body.lineBreakMode = .byWordWrapping

        var attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 12, weight: .medium),
            .foregroundColor: NSColor.white,
            .paragraphStyle: body,
        ]
        let textRect = bounds.insetBy(dx: 12, dy: 10)

        if !text.isEmpty {
            let measured = (text as NSString).size(withAttributes: attrs)
            (text as NSString).draw(in: textRect, withAttributes: attrs)
            var rest = textRect
            rest.origin.y = textRect.minY + measured.height + 4
            rest.size.height = max(0, textRect.maxY - rest.origin.y)
            if !subtext.isEmpty {
                attrs[.font] = NSFont.systemFont(ofSize: 10, weight: .regular)
                attrs[.foregroundColor] = NSColor(calibratedWhite: 0.62, alpha: 1)
                (subtext as NSString).draw(in: rest, withAttributes: attrs)
            }
            return
        }

        if !subtext.isEmpty {
            attrs[.font] = NSFont.systemFont(ofSize: 10, weight: .regular)
            attrs[.foregroundColor] = NSColor(calibratedWhite: 0.62, alpha: 1)
            (subtext as NSString).draw(in: textRect, withAttributes: attrs)
        }
    }
}

// MARK: - The gnome's movements (CoreAnimation, layer-backed)
//
// One photo, honest motion. Every move is a transform on the same single
// image. The gestures are the ladder made visible; the body verbs add
// walking, waddling, leaning, and listening pose. The animation reacts to
// the CLI's record and to explicit body commands, and to nothing else.

final class GnomeAnimator {
    private weak var view: NSView?
    private var waddleTimer: Timer?

    init(view: NSView) {
        self.view = view
        view.wantsLayer = true
        view.layer?.anchorPoint = CGPoint(x: 0.5, y: 0.0)
        startBreathing()
        dropIn()
    }

    /// Idle breathing — always on, gentle, a small stubborn sway.
    private func startBreathing() {
        guard let layer = view?.layer else { return }
        let breathe = CAKeyframeAnimation(keyPath: "transform.scale.y")
        breathe.values = [1.0, 0.985, 1.0]
        breathe.keyTimes = [0, 0.5, 1]
        breathe.duration = 4.0
        breathe.repeatCount = .infinity
        breathe.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(breathe, forKey: "breathe")

        let sway = CAKeyframeAnimation(keyPath: "transform.rotation")
        sway.values = [0.0, 0.015, 0.0, -0.015, 0.0]
        sway.keyTimes = [0, 0.25, 0.5, 0.75, 1]
        sway.duration = 9.0
        sway.repeatCount = .infinity
        sway.isAdditive = true
        sway.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(sway, forKey: "sway")

        lookAroundLoop()
    }

    private func lookAroundLoop() {
        DispatchQueue.main.asyncAfter(deadline: .now() + Double.random(in: 12...22)) { [weak self] in
            self?.lookAround()
            self?.lookAroundLoop()
        }
    }

    /// A slow glance left then right, as if checking the faders.
    private func lookAround() {
        guard let layer = view?.layer else { return }
        let look = CAKeyframeAnimation(keyPath: "transform.rotation.z")
        look.values = [0, 0.03, 0.03, -0.02, 0]
        look.keyTimes = [0, 0.25, 0.5, 0.75, 1]
        look.duration = 2.6
        look.isAdditive = true
        look.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(look, forKey: "lookaround")
    }

    /// Entrance: the gnome drops onto the desk when the app launches.
    func dropIn() {
        guard let layer = view?.layer else { return }
        let drop = CAKeyframeAnimation(keyPath: "position.y")
        drop.values = [220, 0, -8, 0]
        drop.keyTimes = [0, 0.55, 0.75, 1]
        drop.duration = 0.8
        drop.isAdditive = true
        drop.timingFunction = CAMediaTimingFunction(name: .easeIn)
        layer.add(drop, forKey: "dropin")
    }

    /// The human focused the input: the gnome straightens to attention.
    func attention() {
        guard let layer = view?.layer else { return }
        let straighten = CAKeyframeAnimation(keyPath: "transform.scale")
        straighten.values = [1.0, 1.04, 1.02, 1.0]
        straighten.keyTimes = [0, 0.3, 0.6, 1]
        straighten.duration = 0.5
        straighten.isAdditive = true
        straighten.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(straighten, forKey: "attention")
    }

    // MARK: body verbs

    /// Walking: a waddle — side-to-side roll with a step bob, for the
    /// whole trip. Started before the frame moves, stopped on arrival.
    func startWaddle(seconds: Double) {
        guard let layer = view?.layer else { return }
        let waddle = CAKeyframeAnimation(keyPath: "transform.rotation.z")
        waddle.values = [0, 0.06, 0, -0.06, 0]
        waddle.keyTimes = [0, 0.25, 0.5, 0.75, 1]
        waddle.duration = 0.55
        waddle.repeatCount = .infinity
        waddle.isAdditive = true
        waddle.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(waddle, forKey: "waddle")

        let step = CAKeyframeAnimation(keyPath: "position.y")
        step.values = [0, -5, 0]
        step.keyTimes = [0, 0.5, 1]
        step.duration = 0.275
        step.repeatCount = .infinity
        step.isAdditive = true
        step.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(step, forKey: "step")

        waddleTimer?.invalidate()
        waddleTimer = Timer.scheduledTimer(withTimeInterval: seconds, repeats: false) { [weak self] _ in
            self?.stopWaddle()
        }
    }

    func stopWaddle() {
        view?.layer?.removeAnimation(forKey: "waddle")
        view?.layer?.removeAnimation(forKey: "step")
    }

    /// Leaning toward a point on the screen while it points at it.
    func leanToward(screenPoint: NSPoint, from gnomeCenter: NSPoint) {
        guard let layer = view?.layer else { return }
        let dx = screenPoint.x - gnomeCenter.x
        let lean = CGFloat(max(-0.18, min(0.18, dx / 600.0)))
        let l = CAKeyframeAnimation(keyPath: "transform.rotation.z")
        l.values = [0, lean, lean, 0]
        l.keyTimes = [0, 0.2, 0.8, 1]
        l.duration = 3.2
        l.isAdditive = true
        l.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(l, forKey: "lean")
    }

    /// Ears open: the gnome perks up while the mic is listening.
    func listening() {
        guard let layer = view?.layer else { return }
        let perk = CAKeyframeAnimation(keyPath: "transform.scale")
        perk.values = [1.0, 1.06, 1.04, 1.04]
        perk.keyTimes = [0, 0.25, 0.5, 1]
        perk.duration = 0.6
        perk.isAdditive = true
        perk.timingFunction = CAMediaTimingFunction(name: .easeOut)
        layer.add(perk, forKey: "perk")
    }

    /// Teleport vanish: shrink + fade to ghost in the given time.
    func vanish(seconds: Double) {
        guard let layer = view?.layer else { return }
        let s = CAKeyframeAnimation(keyPath: "transform.scale")
        s.values = [1.0, 1.08, 0.6, 0.0]
        s.keyTimes = [0, 0.25, 0.7, 1]
        s.duration = seconds
        s.fillMode = .forwards
        s.isRemovedOnCompletion = false
        layer.add(s, forKey: "vanish")
    }

    /// Teleport appear: from ghost back to full, with a settle bounce.
    func appear() {
        guard let layer = view?.layer else { return }
        let s = CAKeyframeAnimation(keyPath: "transform.scale")
        s.values = [0.0, 1.15, 0.92, 1.0]
        s.keyTimes = [0, 0.5, 0.75, 1]
        s.duration = 0.5
        s.isAdditive = false
        layer.removeAnimation(forKey: "vanish")
        layer.add(s, forKey: "appear")
    }

    // MARK: tier gestures

    /// T0 — it acts: one small hop off the desk.
    func hop() {
        guard let layer = view?.layer else { return }
        let up = CAKeyframeAnimation(keyPath: "position.y")
        up.values = [0, -16, 0, -5, 0]
        up.keyTimes = [0, 0.35, 0.6, 0.8, 1]
        up.duration = 0.9
        up.isAdditive = true
        up.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(up, forKey: "hop")
    }

    /// T1 — it proposes: one slow nod, gnome-paced.
    func nod() {
        guard let layer = view?.layer else { return }
        let nod = CAKeyframeAnimation(keyPath: "transform.rotation.x")
        nod.values = [0, 0.10, 0, 0.05, 0]
        nod.keyTimes = [0, 0.3, 0.55, 0.75, 1]
        nod.duration = 1.1
        nod.isAdditive = true
        nod.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(nod, forKey: "nod")
    }

    /// T2 — your call: a shrug, the whole gnome squashes and settles.
    func shrug() {
        guard let layer = view?.layer else { return }
        let s = CAKeyframeAnimation(keyPath: "transform.scale")
        s.values = [1.0, 0.96, 1.02, 0.98, 1.0]
        s.keyTimes = [0, 0.3, 0.55, 0.8, 1]
        s.duration = 1.1
        s.isAdditive = true
        s.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(s, forKey: "shrug")
    }

    /// T3 — never: a firm head shake.
    func shakeHead() {
        guard let layer = view?.layer else { return }
        let h = CAKeyframeAnimation(keyPath: "transform.rotation.z")
        h.values = [0, 0.05, -0.05, 0.04, -0.04, 0]
        h.keyTimes = [0, 0.15, 0.35, 0.55, 0.75, 1]
        h.duration = 1.0
        h.isAdditive = true
        h.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(h, forKey: "shake")
    }

    /// The mouth is talking (spoke=true): a quick bounce while it says it.
    func talkBounce() {
        guard let layer = view?.layer else { return }
        let talk = CAKeyframeAnimation(keyPath: "position.y")
        talk.values = [0, -4, 0, -4, 0]
        talk.keyTimes = [0, 0.25, 0.5, 0.75, 1]
        talk.duration = 0.5
        talk.repeatCount = 4
        talk.isAdditive = true
        talk.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(talk, forKey: "talk")
    }

    /// The one entry the panel calls when a decision lands.
    /// Fail-closed: no tier in the record → the shrug, never a bold move.
    func react(to decision: Decision) {
        if decision.voice?.spoke == true {
            talkBounce()
        }
        switch decision.tier ?? 2 {
        case 0: hop()
        case 1: nod()
        case 2: shrug()
        case 3: shakeHead()
        default: shrug()
        }
    }

    /// A CLI failure is not a decision; the gnome slumps, it does not act.
    func slump() {
        guard let layer = view?.layer else { return }
        let s = CAKeyframeAnimation(keyPath: "transform.scale.y")
        s.values = [1.0, 0.94, 0.97, 0.94, 1.0]
        s.keyTimes = [0, 0.3, 0.5, 0.7, 1]
        s.duration = 1.2
        s.isAdditive = true
        s.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        layer.add(s, forKey: "slump")
    }
}

// MARK: - Pointing overlay (a clear fullscreen window, ignores clicks)

final class PointOverlay: NSWindow {
    private let arrowLayer = CAShapeLayer()
    private let targetLayer = CAShapeLayer()

    init() {
        let screen = NSScreen.main?.frame ?? NSRect(x: 0, y: 0, width: 1680, height: 1050)
        super.init(contentRect: screen, styleMask: [.borderless, .nonactivatingPanel],
                   backing: .buffered, defer: false)
        isOpaque = false
        backgroundColor = .clear
        level = .floating
        collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        ignoresMouseEvents = true
        orderOut(nil) // hidden until a point happens

        let root = NSView()
        root.wantsLayer = true
        contentView = root

        arrowLayer.strokeColor = NSColor.systemYellow.withAlphaComponent(0.95).cgColor
        arrowLayer.fillColor = NSColor.systemYellow.cgColor
        arrowLayer.lineWidth = 6
        arrowLayer.lineCap = .round
        arrowLayer.opacity = 0.0
        root.layer?.addSublayer(arrowLayer)

        targetLayer.strokeColor = NSColor.systemYellow.withAlphaComponent(0.95).cgColor
        targetLayer.fillColor = NSColor.clear.cgColor
        targetLayer.lineWidth = 5
        targetLayer.opacity = 0.0
        root.layer?.addSublayer(targetLayer)
    }

    /// Draw an arrow from the gnome to the target, hold, then fade out.
    func point(from gnome: NSPoint, to targetCenter: NSPoint, targetFrame: NSRect) {
        guard let root = contentView else { return }
        let size = root.bounds.size
        // CG coordinates (origin bottom-left) match NSWindow coordinates.
        func flip(_ p: NSPoint) -> CGPoint {
            CGPoint(x: p.x, y: size.height - p.y)
        }
        let g = flip(gnome)
        let t = flip(targetCenter)

        // Arrow line: stop short of the target circle.
        let dx = t.x - g.x, dy = t.y - g.y
        let len = sqrt(dx * dx + dy * dy)
        let short = max(0, len - 90)
        let end = CGPoint(x: g.x + dx / len * short, y: g.y + dy / len * short)

        let path = CGMutablePath()
        path.move(to: g)
        path.addLine(to: end)
        arrowLayer.path = path

        // Arrowhead at `end`, oriented along the line.
        let head = CGMutablePath()
        let ang = atan2(dy, dx)
        let hl: CGFloat = 26
        for spread in [CGFloat.pi * 0.82, -CGFloat.pi * 0.82] {
            let a = ang + spread
            let p = CGPoint(x: end.x + cos(a) * hl, y: end.y + sin(a) * hl)
            if spread > 0 {
                head.move(to: end)
                head.addLine(to: p)
            } else {
                head.addLine(to: p)
                head.closeSubpath()
            }
        }
        let headLayer = CAShapeLayer()
        headLayer.path = head
        headLayer.fillColor = NSColor.systemYellow.cgColor
        headLayer.opacity = 1.0
        headLayer.name = "head"
        root.layer?.addSublayer(headLayer)

        // Target ring around the window's frame.
        let tl = flip(NSPoint(x: targetFrame.minX, y: targetFrame.maxY))
        let br = flip(NSPoint(x: targetFrame.maxX, y: targetFrame.minY))
        let rectPath = CGMutablePath()
        rectPath.addRoundedRect(in: CGRect(x: tl.x - 8, y: br.y - 8,
                                           width: (br.x - tl.x) + 16, height: (tl.y - br.y) + 16),
                                cornerWidth: 14, cornerHeight: 14)
        targetLayer.path = rectPath

        arrowLayer.opacity = 1.0
        targetLayer.opacity = 1.0

        // Fade everything out after a hold, then hide and clean up.
        let fade = CABasicAnimation(keyPath: "opacity")
        fade.fromValue = 1.0
        fade.toValue = 0.0
        fade.beginTime = 3.0
        fade.duration = 0.6
        fade.fillMode = .forwards
        fade.isRemovedOnCompletion = false
        arrowLayer.add(fade, forKey: "fade")
        targetLayer.add(fade, forKey: "fade")
        headLayer.add(fade, forKey: "fade")

        DispatchQueue.main.asyncAfter(deadline: .now() + 3.7) { [weak self] in
            self?.orderOut(nil)
            self?.arrowLayer.opacity = 0.0
            self?.targetLayer.opacity = 0.0
            headLayer.removeFromSuperlayer()
        }
    }

    func show() {
        setFrame(NSScreen.main?.frame ?? frame, display: false)
        orderFrontRegardless()
        contentView?.layer?.opacity = 1.0
    }
}

// MARK: - The ears (macOS Speech, on-device when available, push-to-talk)

final class Ears {
    private let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private let audioEngine = AVAudioEngine()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?

    var onPartial: ((String) -> Void)?
    var onFinal: ((String) -> Void)?
    var onError: ((String) -> Void)?

    private(set) var listening = false

    func toggle() {
        listening ? stop() : start()
    }

    func start() {
        guard !listening else { return }
        SFSpeechRecognizer.requestAuthorization { [weak self] status in
            DispatchQueue.main.async {
                switch status {
                case .authorized:
                    self?.requestMicThenStart()
                case .denied:
                    self?.onError?("the Mac says no: speech recognition is denied in Settings")
                case .restricted:
                    self?.onError?("speech recognition is restricted on this Mac")
                default:
                    self?.onError?("speech recognition is not authorized")
                }
            }
        }
    }

    private func requestMicThenStart() {
        // macOS 14+ API; older systems fail honestly below if unavailable.
        AVAudioApplication.requestRecordPermission { [weak self] granted in
            DispatchQueue.main.async {
                if granted {
                    self?.beginListening()
                } else {
                    self?.onError?("the Mac says no: microphone is denied in Settings")
                }
            }
        }
    }

    private func beginListening() {
        guard let recognizer = recognizer, recognizer.isAvailable else {
            onError?("no speech recognizer available on this Mac")
            return
        }

        let node = audioEngine.inputNode
        let format = node.outputFormat(forBus: 0)
        guard format.channelCount > 0, format.sampleRate > 0 else {
            onError?("no microphone on this Mac — no ears, and no pretending")
            return
        }

        let req = SFSpeechAudioBufferRecognitionRequest()
        req.shouldReportPartialResults = true
        if recognizer.supportsOnDeviceRecognition {
            req.requiresOnDeviceRecognition = true // honest: on-device when possible
        }
        request = req

        node.removeTap(onBus: 0)
        node.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
            req.append(buffer)
        }

        audioEngine.prepare()
        do {
            try audioEngine.start()
        } catch {
            onError?("could not open the mic: \(error.localizedDescription)")
            return
        }
        listening = true

        task = recognizer.recognitionTask(with: req) { [weak self] result, error in
            DispatchQueue.main.async {
                if let result = result {
                    let text = result.bestTranscription.formattedString
                    if result.isFinal {
                        self?.stop()
                        if !text.isEmpty {
                            self?.onFinal?(text)
                        }
                    } else {
                        self?.onPartial?(text)
                    }
                } else if let error = error {
                    self?.stop()
                    self?.onError?("ears failed: \(error.localizedDescription)")
                }
            }
        }
    }

    func stop() {
        guard listening || task != nil || audioEngine.isRunning else { return }
        request?.endAudio()
        task?.cancel()
        task = nil
        request = nil
        audioEngine.inputNode.removeTap(onBus: 0)
        audioEngine.stop()
        listening = false
    }
}

// MARK: - The panel

final class GnomoPanel: NSPanel {
    private var gnome = NSImageView()
    private var bubble = BubbleView()
    private var input = NSTextField()
    private var micButton = NSButton()
    private var badge = NSTextField(labelWithString: "GNOMO · waiting")
    private var dragAnchor: NSPoint = .zero
    private var busy = false
    private var animator: GnomeAnimator?
    private var ears: Ears?
    private var pointOverlay: PointOverlay?
    private var poofOverlay: PoofOverlay?
    private var gnomeHeight: NSLayoutConstraint?
    private var zoomScale: CGFloat = 1.0

    private let baseGnomeHeight: CGFloat = 250
    private let zoomedIn: CGFloat = 2.4   // "bigger to the screen": real takeover size
    private let zoomMax: CGFloat = 3.2    // full takeover ceiling

    private let tierLabels: [Int: String] = [
        0: "T0 · DOING IT — for you",
        1: "T1 · SAY THE WORD — with you",
        2: "T2 · YOUR CALL",
        3: "T3 · NO — never",
    ]
    private let tierColors: [Int: NSColor] = [
        0: NSColor.systemGreen,
        1: NSColor.systemYellow,
        2: NSColor.systemOrange,
        3: NSColor.systemRed,
    ]

    init() {
        super.init(contentRect: .zero, styleMask: [.borderless, .nonactivatingPanel],
                   backing: .buffered, defer: false)
        styleMask.insert(.resizable)
        isFloatingPanel = true
        level = .floating
        collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        isOpaque = false
        backgroundColor = .clear
        setFrameAutosaveName("GnomoPanelFrame")
        if !setFrameUsingName("GnomoPanelFrame") {
            setFrame(NSRect(x: 0, y: 0, width: 260, height: 430), display: true)
        }

        buildUI()
    }

    override var canBecomeKey: Bool { true }

    private func buildUI() {
        let root = DragView()
        root.onDragStart = { [weak self] p in self?.dragAnchor = p }
        root.onDragMove = { [weak self] p in self?.windowDragged(to: p) }

        gnome.imageScaling = .scaleProportionallyUpOrDown
        gnome.image = NSImage(contentsOf: URL(fileURLWithPath: Gnomo.assetsDir + "/gnome-face.png"))
        gnome.translatesAutoresizingMaskIntoConstraints = false

        bubble.text = "One thing at a time. Click me or type below."
        bubble.translatesAutoresizingMaskIntoConstraints = false

        input.placeholderString = "a decision · park: … · next"
        input.bezelStyle = .roundedBezel
        input.font = .systemFont(ofSize: 12)
        input.delegate = self
        input.target = self
        input.action = #selector(submit(_:))
        input.translatesAutoresizingMaskIntoConstraints = false

        micButton.bezelStyle = .texturedRounded
        micButton.font = NSFont.systemFont(ofSize: 13)
        micButton.title = "🎙"
        micButton.controlSize = .small
        micButton.toolTip = "Hold a conversation: click, speak, and the transcript routes like typed text"
        micButton.target = self
        micButton.action = #selector(toggleEars(_:))
        micButton.translatesAutoresizingMaskIntoConstraints = false

        badge.font = .monospacedSystemFont(ofSize: 10, weight: .medium)
        badge.textColor = .secondaryLabelColor
        badge.alignment = .center
        badge.translatesAutoresizingMaskIntoConstraints = false

        root.addSubview(gnome)
        root.addSubview(bubble)
        root.addSubview(input)
        root.addSubview(micButton)
        root.addSubview(badge)
        contentView = root

        let gh = gnome.heightAnchor.constraint(equalToConstant: baseGnomeHeight)
        gnomeHeight = gh

        NSLayoutConstraint.activate([
            root.widthAnchor.constraint(equalToConstant: 260),

            gnome.topAnchor.constraint(equalTo: root.topAnchor, constant: 10),
            gnome.centerXAnchor.constraint(equalTo: root.centerXAnchor),
            gh,

            bubble.topAnchor.constraint(equalTo: gnome.bottomAnchor, constant: 6),
            bubble.leadingAnchor.constraint(equalTo: root.leadingAnchor, constant: 2),
            bubble.trailingAnchor.constraint(equalTo: root.trailingAnchor, constant: -2),
            bubble.heightAnchor.constraint(greaterThanOrEqualToConstant: 58),

            input.topAnchor.constraint(equalTo: bubble.bottomAnchor, constant: 8),
            input.leadingAnchor.constraint(equalTo: root.leadingAnchor, constant: 8),
            input.trailingAnchor.constraint(equalTo: micButton.leadingAnchor, constant: -6),

            micButton.centerYAnchor.constraint(equalTo: input.centerYAnchor),
            micButton.trailingAnchor.constraint(equalTo: root.trailingAnchor, constant: -8),
            micButton.widthAnchor.constraint(equalToConstant: 34),

            badge.topAnchor.constraint(equalTo: input.bottomAnchor, constant: 6),
            badge.centerXAnchor.constraint(equalTo: root.centerXAnchor),
            badge.bottomAnchor.constraint(equalTo: root.bottomAnchor, constant: -6),
        ])

        animator = GnomeAnimator(view: gnome)

        ears = Ears()
        ears?.onPartial = { [weak self] text in
            self?.input.stringValue = text // live transcript in the field
        }
        ears?.onFinal = { [weak self] text in
            guard let self else { return }
            self.micButton.title = "🎙"
            self.badge.stringValue = "heard: \(text)"
            self.submitTyped(text) // same routing as typed text
        }
        ears?.onError = { [weak self] reason in
            self?.micButton.title = "🎙"
            self?.bubble.text = reason
            self?.bubble.subtext = "no ears is no ears; the hands still work"
            self?.badge.stringValue = "GNOMO · no ears"
            self?.badge.textColor = NSColor.systemRed
        }

        pointOverlay = PointOverlay()
    }

    private func windowDragged(to screenPoint: NSPoint) {
        let dx = screenPoint.x - dragAnchor.x
        let dy = screenPoint.y - dragAnchor.y
        var f = frame
        f.origin.x += dx
        f.origin.y += dy
        setFrame(f, display: true)
        dragAnchor = screenPoint
    }

    // MARK: routing — mirrors logic-probe/gnomo/companion_router.py `route()`
    //
    // The tested source of truth. Ladder verbs (next/park/decide) reach
    // the CLI and ledger. Body verbs (walk/come/zoom/point) move the
    // window's own body and never ledger. Empty and unknown fail closed to
    // reject. If the table changes in Python, change it here in the same
    // commit.

    private func route(_ typed: String) -> (verb: String, arg: String?) {
        let raw = typed.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty else { return ("reject", nil) }
        let lower = raw.lowercased()
        if lower == "next" { return ("next", nil) }
        if lower == "park" || lower.hasPrefix("park:") || lower.hasPrefix("park ") {
            let idea = String(raw.dropFirst(4)).trimmingCharacters(in: .whitespaces)
                .trimmingCharacters(in: CharacterSet(charactersIn: ":"))
                .trimmingCharacters(in: .whitespaces)
            guard !idea.isEmpty else { return ("reject", nil) }
            return ("park", idea)
        }
        if lower == "come" || lower == "come here" || lower == "comehere" {
            return ("walk", "here")
        }
        if lower == "walk" { return ("walk", "random") }
        if lower.hasPrefix("walk ") {
            let target = String(raw.dropFirst(5)).trimmingCharacters(in: .whitespaces).lowercased()
            let targets = ["here", "left", "right", "center", "random"]
            if targets.contains(target) { return ("walk", target) }
            return ("reject", nil)
        }
        if lower == "point" { return ("reject", nil) }
        if lower.hasPrefix("point ") {
            let what = String(raw.dropFirst(6)).trimmingCharacters(in: .whitespaces)
            guard !what.isEmpty else { return ("reject", nil) }
            return ("point", what)
        }
        if lower == "zoom" { return ("zoom", "toggle") }
        if lower.hasPrefix("zoom ") {
            let arg = String(raw.dropFirst(5)).trimmingCharacters(in: .whitespaces).lowercased()
            let args = ["in", "out", "normal", "toggle"]
            if args.contains(arg) { return ("zoom", arg) }
            return ("reject", nil)
        }
        if lower == "plan" || lower.hasPrefix("plan ") || lower.hasPrefix("plan:") {
            let path = String(raw.dropFirst(5)).trimmingCharacters(in: .whitespaces)
            guard !path.isEmpty else { return ("reject", nil) }
            return ("plan", path)
        }
        if lower.hasPrefix("poof") {
            let target = String(raw.dropFirst(4)).trimmingCharacters(in: .whitespaces)
            return ("poof", target.isEmpty ? "center" : target)
        }
        return ("decide", raw)
    }

    @objc private func toggleEars(_ sender: NSButton) {
        guard let ears else { return }
        if ears.listening {
            ears.stop()
            micButton.title = "🎙"
            badge.stringValue = "ears closed"
            badge.textColor = .secondaryLabelColor
            setListeningFace(false)
        } else {
            ears.start()
            micButton.title = "🔴"
            badge.stringValue = "listening…"
            badge.textColor = NSColor.systemRed
            animator?.listening()
            setListeningFace(true)
        }
    }

    @objc private func submit(_ sender: NSTextField) {
        let (verb, arg) = route(sender.stringValue)
        switch verb {
        case "reject":
            if !sender.stringValue.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                bubble.text = "I do not know that move. walk left/right/center/here/random · zoom in/out · point at <app>."
                bubble.subtext = ""
                badge.stringValue = "GNOMO · no such move"
                badge.textColor = NSColor.systemRed
                animator?.shakeHead()
            }
            return
        case "walk":
            walk(to: arg ?? "random")
            sender.stringValue = ""
            return
        case "zoom":
            zoom(arg ?? "toggle")
            sender.stringValue = ""
            return
        case "point":
            point(at: arg ?? "")
            sender.stringValue = ""
            return
        case "plan":
            planVerb(path: arg ?? "")
            sender.stringValue = ""
            return
        case "poof":
            teleport(to: arg ?? "center")
            sender.stringValue = ""
            return
        default:
            break
        }

        guard !busy else { return }
        sender.stringValue = ""
        busy = true
        badge.stringValue = "asking the ladder…"
        badge.textColor = .secondaryLabelColor

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let result: Result<Decision, CLIError>
            switch verb {
            case "next":
                result = Gnomo.next()
            case "park":
                result = Gnomo.park(arg ?? "")
            default:
                result = Gnomo.decide(arg ?? "")
            }
            DispatchQueue.main.async { [weak self] in
                self?.busy = false
                self?.show(result)
            }
        }
    }

    private func show(_ result: Result<Decision, CLIError>) {
        switch result {
        case .failure(let err):
            bubble.text = err.message
            bubble.subtext = "the window did not invent an answer"
            badge.stringValue = "GNOMO · no answer"
            badge.textColor = NSColor.systemRed
            animator?.slump()
        case .success(let d):
            bubble.text = d.spoken ?? "(the ladder printed no line)"
            var subs: [String] = []
            if let hat = d.hat { subs.append(hat + " hat") }
            if let authority = d.authority { subs.append("authority: " + authority) }
            if let v = d.voice {
                subs.append(v.spoke == true ? "spoken" : "not spoken: \(v.reason ?? "?")")
            }
            bubble.subtext = subs.joined(separator: " · ")
            let tier = d.tier ?? 2
            badge.stringValue = tierLabels[tier] ?? "T\(tier)"
            badge.textColor = tierColors[tier] ?? NSColor.systemOrange
            animator?.react(to: d)
            // Expression swap: the face matches the ladder rung.
            setFace(forTier: tier)
        }
    }

    /// Face per ladder rung, from the mockup character set:
    ///   T0 act -> happy · T1 propose -> thinking · T2 ask -> confused
    ///   T3 never -> error · listening -> emote-listening · failure -> error
    private func setFace(forTier tier: Int) {
        let name: String
        switch tier {
        case 0: name = "happy"
        case 1: name = "thinking"
        case 2: name = "confused"
        default: name = "error"
        }
        setFaceState(name)
    }

    private func faceName(forTier tier: Int) -> String {
        switch tier {
        case 0: return "gnomo-happy"
        case 1: return "gnomo-thinking"
        case 2: return "gnomo-confused"
        default: return "gnomo-error"
        }
    }

    private func setListeningFace(_ listening: Bool) {
        setFaceState(listening ? "listening" : "idle")
    }

    /// Frame player: if a rendered alpha sequence exists for the state
    /// (companion/assets/sequences/<state>/*.png), loop it; otherwise fall
    /// back to the static bust. Sequences come from the CA export (Stage 3).
    private func setFaceState(_ state: String) {
        seqTimer?.invalidate()
        seqTimer = nil
        let dir = Gnomo.assetsDir + "/sequences/" + state
        let files = (try? FileManager.default.contentsOfDirectory(
            atPath: dir))?.filter { $0.hasSuffix(".png") }.sorted() ?? []
        guard files.count > 1 else {
            if files.count == 1 { setFaceImage("sequences/\(state)/\(files[0])") }
            else { setFaceImage(state == "listening" ? "mockup/emote-listening.png" : "mockup/gnomo-idle.png") }
            return
        }
        playSequence(state: state, files: files)
    }

    private var seqTimer: Timer?
    private var seqIndex = 0
    private var seqFiles: [String] = []
    private var seqState = ""

    private func playSequence(state: String, files: [String]) {
        seqState = state
        seqFiles = files
        seqIndex = 0
        seqTimer = Timer.scheduledTimer(withTimeInterval: 0.18, repeats: true) { [weak self] t in
            guard let self, self.seqState == state else { t.invalidate(); return }
            let f = self.seqFiles[self.seqIndex % self.seqFiles.count]
            self.setFaceImage("sequences/\(state)/\(f)")
            self.seqIndex += 1
        }
    }

    private func setFaceImage(_ relPath: String) {
        let path = Gnomo.assetsDir + "/" + relPath
        if let img = NSImage(contentsOf: URL(fileURLWithPath: path)) {
            gnome.image = img
        }
    }

    // MARK: body verbs — the window's own body, never ledgered

    /// Teleport: vanish with a poof, appear at the designated spot with a poof.
    /// No walking — the gnome materializes near the topic. The destination is
    /// either a named area or the center of a pointed-at window.
    private func teleport(to target: String) {
        let oldCenter = NSPoint(x: frame.midX, y: frame.minY + 30)

        // vanish: poof at the old spot, fade the gnome out
        poofOverlay = poofOverlay ?? PoofOverlay()
        poofOverlay?.poof(at: oldCenter)
        animator?.vanish(seconds: 0.35)
        badge.stringValue = "poof…"
        badge.textColor = .secondaryLabelColor

        let dest = designatedArea(for: target)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) { [weak self] in
            guard let self else { return }
            var f = self.frame
            f.origin = dest
            self.setFrame(f, display: false)
            // appear: poof at the new spot, fade the gnome in, drop-in bounce
            self.poofOverlay?.poof(at: NSPoint(x: f.midX, y: f.minY + 30))
            self.animator?.appear()
            self.badge.stringValue = "GNOMO · here"
            self.badge.textColor = .secondaryLabelColor
        }
    }

    /// Designated areas: gnome-sized spots tied to screen geography.
    private func designatedArea(for target: String) -> NSPoint {
        guard let screen = NSScreen.main else { return .zero }
        let visible = screen.visibleFrame
        let margin: CGFloat = 40
        switch target {
        case "left":
            return NSPoint(x: visible.minX + margin, y: visible.minY + 30)
        case "right":
            return NSPoint(x: visible.maxX - frame.width - margin, y: visible.minY + 30)
        case "center", "here":
            return NSPoint(x: visible.midX - frame.width / 2, y: visible.minY + 30)
        default:
            // a topic word: teleport NEAR the window that matches it, lower-center
            let words = target.lowercased()
                .components(separatedBy: CharacterSet.alphanumerics.inverted)
                .filter { !$0.isEmpty }
            let candidates = ScreenFacts.otherWindows(excluding: ProcessInfo.processInfo.processIdentifier)
            var best: (owner: String, frame: NSRect)? = nil
            var bestScore = 0
            for c in candidates {
                var score = 0
                for w in words {
                    if c.owner.lowercased().contains(w) { score += 2 }
                    if c.title.lowercased().contains(w) { score += 3 }
                }
                if score > bestScore { bestScore = score; best = (c.owner, c.frame) }
            }
            guard let hit = best else {
                return NSPoint(x: visible.midX - frame.width / 2, y: visible.minY + 30)
            }
            // land beside the topic's window: near its lower-center, clamped on-screen
            let x = max(visible.minX + margin,
                        min(hit.frame.midX - frame.width / 2,
                            visible.maxX - frame.width - margin))
            let y = max(visible.minY + 30, hit.frame.minY - frame.height + 120)
            bubble.text = "Poofed to \(hit.owner)."
            return NSPoint(x: x, y: y)
        }
    }

    /// Walk: animate the panel across the bottom of the screen, waddling
    /// for the whole trip. "here" is the honest default: screen center.
    private func walk(to target: String) {
        guard let screen = NSScreen.main else { return }
        let visible = screen.visibleFrame
        let margin: CGFloat = 40
        let x: CGFloat
        switch target {
        case "here", "center":
            x = visible.midX - frame.width / 2
        case "left":
            x = visible.minX + margin
        case "right":
            x = visible.maxX - frame.width - margin
        default: // random
            x = CGFloat.random(in: visible.minX + margin...(visible.maxX - frame.width - margin))
        }

        var dest = frame
        dest.origin.x = x
        dest.origin.y = visible.minY + 30

        let distance = hypot(dest.midX - frame.midX, dest.midY - frame.midY)
        let duration = max(0.8, min(6.0, distance / 180.0))

        badge.stringValue = "walking…"
        badge.textColor = .secondaryLabelColor
        animator?.startWaddle(seconds: duration)

        NSAnimationContext.runAnimationGroup({ ctx in
            ctx.duration = duration
            ctx.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
            self.animator().setFrame(dest, display: true)
        }, completionHandler: { [weak self] in
            self?.animator?.stopWaddle()
            self?.badge.stringValue = "GNOMO · here"
            self?.badge.textColor = .secondaryLabelColor
        })
    }

    /// Zoom: scale the gnome toward screen takeover. The window is a
    /// fullscreen transparent stage; the UI block floats inside it, so
    /// "bigger" = grow the gnome + re-anchor the block (window never resizes).
    private func zoom(_ arg: String) {
        switch arg {
        case "in":
            zoomScale = zoomScale >= zoomMax - 0.01 ? 1.0 : min(zoomMax, max(zoomedIn, zoomScale * 1.6))
        case "out", "normal":
            zoomScale = 1.0
        default: // toggle
            zoomScale = zoomScale > 1.05 ? 1.0 : zoomedIn
        }
        applyZoom(animated: true)
    }

    private func applyZoom(animated: Bool) {
        guard let constraint = gnomeHeight, let root = contentView else { return }
        let newHeight = baseGnomeHeight * zoomScale

        // Feet planted: the window's BOTTOM stays put, the top grows upward.
        constraint.constant = newHeight
        root.layoutSubtreeIfNeeded()

        var fit = root.fittingSize
        fit.width = max(260, fit.width)
        var f = frame
        f.origin.y = f.maxY - fit.height          // bottom fixed (flip coords: minY is bottom)
        f.size = fit
        // clamp on-screen
        if let screen = NSScreen.main {
            let v = screen.visibleFrame
            f.origin.y = max(v.minY, min(f.origin.y, screen.frame.maxY - f.height))
        }
        let apply = {
            constraint.constant = newHeight
            self.setFrame(f, display: true)
            root.layoutSubtreeIfNeeded()
        }

        if animated {
            NSAnimationContext.runAnimationGroup({ ctx in
                ctx.duration = 0.45
                ctx.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
                ctx.allowsImplicitAnimation = true
                apply()
            }, completionHandler: nil)
        } else {
            apply()
        }

        badge.stringValue = zoomScale > 1.05 ? "GNOMO · zoomed \(Int(zoomScale * 100))%" : "GNOMO · normal"
        badge.textColor = .secondaryLabelColor
    }

    /// The size the window needs for the current gnome height.
    private func windowLayoutSize() -> NSSize? {
        guard let root = contentView else { return nil }
        root.layoutSubtreeIfNeeded()
        return root.fittingSize
    }

    /// Point: find the app window on screen by owner/title words, draw an
    /// honest arrow at it, lean toward it. No match → say so, no fake.
    private func point(at query: String) {
        let words = query.lowercased()
            .components(separatedBy: CharacterSet.alphanumerics.inverted)
            .filter { !$0.isEmpty }
        let candidates = ScreenFacts.otherWindows(excluding: ProcessInfo.processInfo.processIdentifier)

        var best: (owner: String, title: String, frame: NSRect)? = nil
        var bestScore = 0
        for c in candidates {
            var score = 0
            for w in words {
                if c.owner.lowercased().contains(w) { score += 2 }
                if c.title.lowercased().contains(w) { score += 3 }
            }
            if score > bestScore {
                bestScore = score
                best = c
            }
        }

        guard let target = best else {
            bubble.text = "I cannot see a \(query) from here."
            bubble.subtext = "CGWindowList, owner names only — no pixel reading, no guessing"
            badge.stringValue = "GNOMO · not found"
            badge.textColor = NSColor.systemOrange
            animator?.shrug()
            return
        }

        let targetCenter = NSPoint(x: target.frame.midX, y: target.frame.midY)
        let gnomeCenter = NSPoint(x: frame.midX, y: frame.maxY - 120)

        pointOverlay?.show()
        pointOverlay?.point(from: gnomeCenter, to: targetCenter, targetFrame: target.frame)
        animator?.leanToward(screenPoint: targetCenter, from: gnomeCenter)

        bubble.text = "That one: \(target.owner)."
        bubble.subtext = target.title.isEmpty ? "owner: \(target.owner)" : "“\(target.title)”"
        badge.stringValue = "GNOMO · pointing"
        badge.textColor = NSColor.systemYellow
    }

    /// `plan <path>`: compile a MusicPlan JSON file. Tier-0 body verb of the
    /// composition engine — no ladder, no ledger, never a send. Sound is
    /// `gnomo play --go`, from the terminal, with Chris's nod.
    private func planVerb(path: String) {
        let expanded = (path as NSString).expandingTildeInPath
        guard FileManager.default.fileExists(atPath: expanded) else {
            bubble.text = "No plan file there: \(path)"
            bubble.subtext = "give me a MusicPlan JSON — tempo, length_bars, chords"
            badge.stringValue = "GNOMO · no plan"
            badge.textColor = NSColor.systemOrange
            animator?.shrug()
            return
        }
        busy = true
        badge.stringValue = "compiling…"
        badge.textColor = .secondaryLabelColor
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let r = Gnomo.run("plan", "--file", expanded)
            DispatchQueue.main.async { [weak self] in
                guard let self else { return }
                busy = false
                guard r.code == 0,
                      let data = r.out.data(using: .utf8),
                      let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
                else {
                    bubble.text = "The compile did not answer."
                    bubble.subtext = r.err.isEmpty ? "exit \(r.code)" : r.err
                    badge.stringValue = "GNOMO · compile failed"
                    badge.textColor = NSColor.systemRed
                    animator?.slump()
                    return
                }
                if obj["accepted"] as? Bool != true {
                    bubble.text = "Plan rejected: \(obj["error"] ?? "unknown reason")"
                    bubble.subtext = "nothing compiled, nothing played"
                    badge.stringValue = "GNOMO · plan rejected"
                    badge.textColor = NSColor.systemOrange
                    animator?.shakeHead()
                    return
                }
                let bars = obj["length_bars"] as? Int ?? 0
                let tempo = obj["tempo"] as? Int ?? 0
                let events = obj["event_count"] as? Int ?? 0
                let hash = obj["phrase_hash"] as? String ?? "?"
                bubble.text = "Plan compiles: \(bars) bars at \(tempo), \(events) events."
                bubble.subtext = "hash \(hash) · to hear it: gnomo play --file <plan> --out <port> --go"
                badge.stringValue = "GNOMO · plan ready"
                badge.textColor = NSColor.systemGreen
                animator?.nod()
            }
        }
    }
}

// MARK: - Menu bar presence

final class StatusMenu: NSObject, NSMenuDelegate {
    private let item: NSStatusItem
    private weak var panel: GnomoPanel?

    init(panel: GnomoPanel) {
        self.panel = panel
        item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        super.init()
        item.button?.title = "GNOMO"
        let menu = NSMenu()
        menu.delegate = self

        let next = NSMenuItem(title: "The one thing", action: #selector(runNext), keyEquivalent: "n")
        next.target = self
        menu.addItem(next)

        let park = NSMenuItem(title: "Park an idea…", action: #selector(parkIdea), keyEquivalent: "p")
        park.target = self
        menu.addItem(park)

        let walk = NSMenuItem(title: "Take a walk", action: #selector(walk), keyEquivalent: "w")
        walk.target = self
        menu.addItem(walk)

        let ledger = NSMenuItem(title: "Open the ledger", action: #selector(openLedger), keyEquivalent: "l")
        ledger.target = self
        menu.addItem(ledger)

        menu.addItem(.separator())

        let quit = NSMenuItem(title: "Dismiss the gnome", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        menu.addItem(quit)

        item.menu = menu
    }

    @objc private func runNext() {
        panel?.submitTyped("next")
    }

    @objc private func walk() {
        panel?.submitTyped("walk random")
    }

    @objc private func parkIdea() {
        let alert = NSAlert()
        alert.messageText = "Park an idea"
        alert.informativeText = "It goes to PARKING_LOT.md. Nothing here is a commitment."
        alert.addButton(withTitle: "Park it")
        alert.addButton(withTitle: "Forget it")
        let field = NSTextField(frame: NSRect(x: 0, y: 0, width: 260, height: 24))
        alert.accessoryView = field
        guard let window = panel, alert.runModal() == .alertFirstButtonReturn,
              !field.stringValue.isEmpty else { return }
        window.submitTyped("park: " + field.stringValue)
    }

    @objc private func openLedger() {
        let path = Gnomo.repoRoot + "/studio/datasets/decisions.jsonl"
        if FileManager.default.fileExists(atPath: path) {
            NSWorkspace.shared.openFile(path) // deprecated but works
        } else {
            let dir = Gnomo.repoRoot + "/studio/datasets"
            try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
            NSWorkspace.shared.openFile(dir) // deprecated but works
        }
    }
}

// MARK: - App

extension GnomoPanel {
    /// One typed entry point for the field, the menu, and the ears.
    func submitTyped(_ raw: String) {
        input.stringValue = raw
        submit(input)
    }

    /// The human is typing: the gnome straightens up. Listening pose.
    func focusReceived() {
        animator?.attention()
    }
}

extension GnomoPanel: NSTextFieldDelegate {
    /// First keystroke in the field: the gnome straightens to attention.
    func controlTextDidBeginEditing(_ obj: Notification) {
        animator?.attention()
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    var panel: GnomoPanel?
    var status: StatusMenu?

    func applicationDidFinishLaunching(_ note: Notification) {
        let p = GnomoPanel()
        panel = p
        status = StatusMenu(panel: p)
        p.orderFrontRegardless()
    }
}

// MARK: - Entry

/// `--selftest` runs the three routes against the real CLI and prints a
/// JSON verdict, no window. Body verbs are UI-only and pinned by
/// tests/test_companion_router.py against companion_router.route().
func runSelfTest() -> Int32 {
    let cases: [(String, () -> Result<Decision, CLIError>)] = [
        ("decide", { Gnomo.decide("set track 3 to -6 dB") }),
        ("park", { Gnomo.park("selftest: companion park route works") }),
        ("next", { Gnomo.next() }),
    ]
    var results: [String: String] = [:]
    var ok = true
    for (name, fn) in cases {
        switch fn() {
        case .success(let d):
            let tier = d.tier.map(String.init) ?? "?"
            let spoke = d.voice?.spoke == true ? "true" : "false"
            results[name] = "ok tier=\(tier) spoke=\(spoke)"
        case .failure(let err):
            ok = false
            results[name] = "FAIL: \(err.message)"
        }
    }
    let json = (try? JSONEncoder().encode(results)).map { String(data: $0, encoding: .utf8) ?? "{}" } ?? "{}"
    print(json)
    return ok ? 0 : 1
}

if CommandLine.arguments.contains("--selftest") {
    exit(runSelfTest())
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory) // on the desktop, not in the Dock
app.run()