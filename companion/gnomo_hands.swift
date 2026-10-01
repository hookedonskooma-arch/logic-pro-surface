// gnomo-hands: GNOMO's eyes and hands outside his own window.
//
// A small native helper. It does not decide what is allowed: `python -m gnomo
// hands` puts every action on the ladder first and refuses tier 3. This binary
// adds the human half: every click, keystroke or key combo waits for a native
// "Do it" dialog. There is no flag that skips it.
//
//   gnomo-hands look                      labelled buttons/fields of the front window
//   gnomo-hands find  <label>             elements whose label matches
//   gnomo-hands point <label>             glide the cursor onto it; never clicks
//   gnomo-hands click <label> [--index N] asks, then AXPress (CGEvent click as fallback)
//   gnomo-hands type  <text>              asks, then CGEvent unicode keystrokes
//   gnomo-hands key   <combo>             asks, then e.g. cmd+z, return, shift+tab
//
// Kill switch: if the human touched the mouse or keyboard in the last 750 ms
// before the gnome acts, he lets go ("human_took_over").
//
// Honest contract: a posted event or AX press proves only that actuation was
// attempted. Replies say "attempted" and name the channel, never "confirmed".
//
// Build (macOS): companion/build_hands.sh
// Needs: System Settings > Privacy & Security > Accessibility for this binary.

import AppKit
import ApplicationServices
import CoreGraphics
import Foundation

// MARK: - output

func emit(_ obj: [String: Any]) -> Never {
    let data = (try? JSONSerialization.data(withJSONObject: obj, options: [.sortedKeys])) ?? Data("{}".utf8)
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data("\n".utf8))
    exit((obj["ok"] as? Bool ?? false) ? 0 : 1)
}

func fail(_ reason: String, _ extra: [String: Any] = [:]) -> Never {
    var o: [String: Any] = ["ok": false, "status": "failed", "reason": reason]
    for (k, v) in extra { o[k] = v }
    emit(o)
}

// MARK: - permission, human guard, human yes

func requireTrust() {
    let opts = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
    if !AXIsProcessTrustedWithOptions(opts) {
        fail("needs_accessibility_permission",
             ["fix": "System Settings > Privacy & Security > Accessibility: allow gnomo-hands, then retry"])
    }
}

/// The gnome posts from his own private source, never the shared HID state,
/// so his own glides are not mistaken for the human.
let gnomeSource = CGEventSource(stateID: .privateState)
let guardMs = 750.0

/// Milliseconds since the human last used real hardware.
func humanIdleMs() -> Double {
    let types: [CGEventType] = [.mouseMoved, .leftMouseDown, .rightMouseDown, .leftMouseDragged,
                                .scrollWheel, .keyDown, .flagsChanged]
    return (types.map { CGEventSource.secondsSinceLastEventType(.hidSystemState, eventType: $0) }.min() ?? .infinity) * 1000
}

/// Kill switch, checked right before acting. Actions are short (well under a second).
func checkHumanGuard() {
    let idle = humanIdleMs()
    if idle < guardMs { fail("human_took_over", ["idle_ms": Int(idle), "guard_ms": Int(guardMs)]) }
}

/// The per-action yes. A native dialog only a person can answer; then focus
/// goes back to the app the gnome is about to act on.
func askHuman(_ what: String, returnTo pid: pid_t) {
    let app = NSApplication.shared
    app.setActivationPolicy(.accessory)
    app.activate(ignoringOtherApps: true)
    let alert = NSAlert()
    alert.messageText = "GNOMO wants to do this"
    alert.informativeText = what + "\n\nNothing happens unless you press Do it."
    alert.alertStyle = .warning
    alert.addButton(withTitle: "Not now")  // first button = default (Return): the safe answer
    alert.addButton(withTitle: "Do it")
    let answer = alert.runModal()
    if answer != .alertSecondButtonReturn { fail("declined_by_human", ["asked": what]) }
    NSRunningApplication(processIdentifier: pid)?.activate(options: [])
    usleep(250_000)  // let the target window come back to the front
    // The click that answered the dialog is human input; give it time to age out of the guard.
    usleep(UInt32(guardMs * 1000))
}

// MARK: - accessibility tree

struct Element {
    let ax: AXUIElement
    let role: String
    let label: String
    let frame: CGRect?
    let actions: [String]
}

func attr<T>(_ el: AXUIElement, _ name: String) -> T? {
    var value: CFTypeRef?
    guard AXUIElementCopyAttributeValue(el, name as CFString, &value) == .success else { return nil }
    return value as? T
}

func frameOf(_ el: AXUIElement) -> CGRect? {
    var posRef: CFTypeRef?
    var sizeRef: CFTypeRef?
    guard AXUIElementCopyAttributeValue(el, kAXPositionAttribute as CFString, &posRef) == .success,
          AXUIElementCopyAttributeValue(el, kAXSizeAttribute as CFString, &sizeRef) == .success,
          let p = posRef, let s = sizeRef,
          CFGetTypeID(p) == AXValueGetTypeID(), CFGetTypeID(s) == AXValueGetTypeID() else { return nil }
    var point = CGPoint.zero
    var size = CGSize.zero
    guard AXValueGetValue(p as! AXValue, .cgPoint, &point),
          AXValueGetValue(s as! AXValue, .cgSize, &size) else { return nil }
    return CGRect(origin: point, size: size)
}

func labelOf(_ el: AXUIElement) -> String {
    for key in [kAXTitleAttribute, kAXDescriptionAttribute, kAXHelpAttribute, kAXIdentifierAttribute] {
        if let s: String = attr(el, key), !s.trimmingCharacters(in: .whitespaces).isEmpty { return s }
    }
    if let s: String = attr(el, kAXValueAttribute), s.count <= 80 { return s }
    return ""
}

func actionsOf(_ el: AXUIElement) -> [String] {
    var names: CFArray?
    guard AXUIElementCopyActionNames(el, &names) == .success, let list = names as? [String] else { return [] }
    return list
}

let maxNodes = 600
let maxDepth = 14

func frontmost() -> (pid: pid_t, name: String) {
    guard let app = NSWorkspace.shared.frontmostApplication else { fail("no_frontmost_app") }
    return (app.processIdentifier, app.localizedName ?? "?")
}

/// Labelled, actionable elements of the frontmost app's focused window and menu bar.
func collect() -> (pid: pid_t, app: String, elements: [Element], truncated: Bool) {
    let front = frontmost()
    let appEl = AXUIElementCreateApplication(front.pid)
    var roots: [AXUIElement] = []
    if let win: AXUIElement = attr(appEl, kAXFocusedWindowAttribute) {
        roots.append(win)
    } else if let wins: [AXUIElement] = attr(appEl, kAXWindowsAttribute), let first = wins.first {
        roots.append(first)
    }
    if let bar: AXUIElement = attr(appEl, kAXMenuBarAttribute) { roots.append(bar) }

    var out: [Element] = []
    var visited = 0
    var stack: [(AXUIElement, Int)] = roots.map { ($0, 0) }
    while let item = stack.popLast() {
        let (el, depth) = item
        visited += 1
        if visited > maxNodes { return (front.pid, front.name, out, true) }
        let role: String = attr(el, kAXRoleAttribute) ?? ""
        let label = labelOf(el)
        let actions = actionsOf(el)
        let isField = role == kAXTextFieldRole || role == kAXTextAreaRole
        if !label.isEmpty && (!actions.isEmpty || isField) {
            out.append(Element(ax: el, role: role, label: label, frame: frameOf(el), actions: actions))
        }
        // Closed menus are huge; list the menu bar items but not every menu entry.
        if role == kAXMenuRole && depth > 1 { continue }
        if depth < maxDepth, let kids: [AXUIElement] = attr(el, kAXChildrenAttribute) {
            for kid in kids.reversed() { stack.append((kid, depth + 1)) }
        }
    }
    return (front.pid, front.name, out, false)
}

func describe(_ e: Element, _ index: Int) -> [String: Any] {
    var d: [String: Any] = ["index": index, "role": e.role, "label": e.label, "actions": e.actions]
    if let f = e.frame {
        d["frame"] = ["x": Int(f.minX), "y": Int(f.minY), "w": Int(f.width), "h": Int(f.height)]
    }
    return d
}

/// Exact (case-insensitive) label matches win; otherwise substring matches.
func match(_ query: String) -> (pid: pid_t, app: String, hits: [Element]) {
    let q = query.lowercased().trimmingCharacters(in: .whitespaces)
    let all = collect()
    let exact = all.elements.filter { $0.label.lowercased() == q }
    if !exact.isEmpty { return (all.pid, all.app, exact) }
    return (all.pid, all.app, all.elements.filter { $0.label.lowercased().contains(q) })
}

/// One target or a refusal. Ambiguity fails closed unless the caller picks an index.
func resolve(_ query: String, index: Int?) -> (pid: pid_t, app: String, el: Element) {
    let found = match(query)
    if found.hits.isEmpty { fail("not_found", ["app": found.app, "query": query]) }
    if let i = index {
        guard found.hits.indices.contains(i) else { fail("bad_index", ["app": found.app, "count": found.hits.count]) }
        return (found.pid, found.app, found.hits[i])
    }
    if found.hits.count > 1 {
        fail("ambiguous", ["app": found.app, "query": query,
                           "candidates": found.hits.prefix(12).enumerated().map { describe($0.element, $0.offset) },
                           "fix": "repeat with --index N"])
    }
    return (found.pid, found.app, found.hits[0])
}

// MARK: - actuation (CGEvent)

func center(_ r: CGRect) -> CGPoint { CGPoint(x: r.midX, y: r.midY) }

func glide(to target: CGPoint) {
    let start = CGEvent(source: nil)?.location ?? target
    let steps = 24
    for i in 1...steps {
        let t = Double(i) / Double(steps)
        let ease = t * t * (3 - 2 * t)
        let p = CGPoint(x: start.x + (target.x - start.x) * ease, y: start.y + (target.y - start.y) * ease)
        CGEvent(mouseEventSource: gnomeSource, mouseType: .mouseMoved, mouseCursorPosition: p, mouseButton: .left)?
            .post(tap: .cghidEventTap)
        usleep(12_000)
    }
}

func clickAt(_ p: CGPoint) {
    glide(to: p)
    CGEvent(mouseEventSource: gnomeSource, mouseType: .leftMouseDown, mouseCursorPosition: p, mouseButton: .left)?
        .post(tap: .cghidEventTap)
    usleep(40_000)
    CGEvent(mouseEventSource: gnomeSource, mouseType: .leftMouseUp, mouseCursorPosition: p, mouseButton: .left)?
        .post(tap: .cghidEventTap)
}

func typeText(_ text: String) {
    var chunk: [UInt16] = []
    func flush() {
        guard !chunk.isEmpty else { return }
        for down in [true, false] {
            let ev = CGEvent(keyboardEventSource: gnomeSource, virtualKey: 0, keyDown: down)
            ev?.keyboardSetUnicodeString(stringLength: chunk.count, unicodeString: chunk)
            ev?.post(tap: .cghidEventTap)
        }
        chunk.removeAll()
        usleep(15_000)
    }
    for ch in text {
        let units = Array(String(ch).utf16)
        if chunk.count + units.count > 16 { flush() }
        chunk.append(contentsOf: units)
    }
    flush()
}

let keyCodes: [String: CGKeyCode] = [
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12,
    "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23,
    "9": 25, "7": 26, "8": 28, "0": 29, "o": 31, "u": 32, "i": 34, "p": 35, "l": 37, "j": 38, "k": 40,
    "n": 45, "m": 46, "return": 36, "enter": 36, "tab": 48, "space": 49, "delete": 51, "escape": 53,
    "esc": 53, "left": 123, "right": 124, "down": 125, "up": 126, ",": 43, ".": 47, "/": 44,
]

func parseCombo(_ combo: String) -> (CGKeyCode, CGEventFlags) {
    var flags: CGEventFlags = []
    var key: CGKeyCode?
    for part in combo.lowercased().split(separator: "+").map(String.init) {
        switch part {
        case "cmd", "command": flags.insert(.maskCommand)
        case "shift": flags.insert(.maskShift)
        case "alt", "opt", "option": flags.insert(.maskAlternate)
        case "ctrl", "control": flags.insert(.maskControl)
        default:
            guard let code = keyCodes[part] else { fail("unknown_key", ["key": part]) }
            key = code
        }
    }
    guard let code = key else { fail("no_key_in_combo", ["combo": combo]) }
    return (code, flags)
}

func pressCombo(_ code: CGKeyCode, _ flags: CGEventFlags) {
    for down in [true, false] {
        let ev = CGEvent(keyboardEventSource: gnomeSource, virtualKey: code, keyDown: down)
        ev?.flags = flags
        ev?.post(tap: .cghidEventTap)
    }
}

// MARK: - main

var args = Array(CommandLine.arguments.dropFirst())
var index: Int?
if let i = args.firstIndex(of: "--index"), i + 1 < args.count {
    index = Int(args[i + 1])
    args.removeSubrange(i...(i + 1))
}
guard let verb = args.first else { fail("usage", ["verbs": ["look", "find", "point", "click", "type", "key"]]) }
let joined = args.dropFirst().joined(separator: " ")
requireTrust()

switch verb {
case "look":
    let all = collect()
    emit(["ok": true, "status": "observed", "channel": "ax", "app": all.app, "truncated": all.truncated,
          "elements": all.elements.prefix(200).enumerated().map { describe($0.element, $0.offset) }])

case "find":
    let found = match(joined)
    emit(["ok": true, "status": "observed", "channel": "ax", "app": found.app,
          "elements": found.hits.prefix(50).enumerated().map { describe($0.element, $0.offset) }])

case "point":
    let t = resolve(joined, index: index)
    guard let f = t.el.frame else { fail("no_frame", ["label": t.el.label]) }
    checkHumanGuard()
    glide(to: center(f))
    emit(["ok": true, "status": "attempted", "channel": "cgevent_move", "app": t.app,
          "target": describe(t.el, index ?? 0)])

case "click":
    let t = resolve(joined, index: index)
    askHuman("Click \u{201C}\(t.el.label)\u{201D} (\(t.el.role)) in \(t.app)?", returnTo: t.pid)
    checkHumanGuard()
    if t.el.actions.contains(kAXPressAction),
       AXUIElementPerformAction(t.el.ax, kAXPressAction as CFString) == .success {
        emit(["ok": true, "status": "attempted", "channel": "ax_press", "app": t.app,
              "target": describe(t.el, index ?? 0)])
    }
    guard let f = t.el.frame else { fail("no_frame_and_no_press", ["label": t.el.label]) }
    clickAt(center(f))
    emit(["ok": true, "status": "attempted", "channel": "cgevent_click", "app": t.app,
          "target": describe(t.el, index ?? 0)])

case "type":
    guard !joined.isEmpty else { fail("nothing_to_type") }
    let front = frontmost()
    let preview = joined.count > 120 ? String(joined.prefix(120)) + "\u{2026}" : joined
    askHuman("Type into \(front.name):\n\u{201C}\(preview)\u{201D} (\(joined.count) characters)", returnTo: front.pid)
    checkHumanGuard()
    typeText(joined)
    emit(["ok": true, "status": "attempted", "channel": "cgevent_keys", "app": front.name, "chars": joined.count])

case "key":
    guard !joined.isEmpty else { fail("usage", ["example": "key cmd+z"]) }
    let (code, flags) = parseCombo(joined)
    let front = frontmost()
    askHuman("Press \(joined) in \(front.name)?", returnTo: front.pid)
    checkHumanGuard()
    pressCombo(code, flags)
    emit(["ok": true, "status": "attempted", "channel": "cgevent_keys", "app": front.name, "combo": joined])

default:
    fail("unknown_verb", ["verb": verb])
}
