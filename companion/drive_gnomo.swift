// Type a decision into the running Gnomo window's input field.
// Posts ALL events (click + keys) directly to the Gnomo process PID, so
// the gnome gets the input even though it's an accessory app that never
// becomes frontmost. Reads live window bounds from CGWindowList.

import CoreGraphics
import Foundation

func gnomoWindow() -> (id: Int, pid: Int, x: Double, y: Double, w: Double, h: Double)? {
    guard let info = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID)
            as? [[String: Any]] else { return nil }
    for win in info {
        let owner = win[kCGWindowOwnerName as String] as? String ?? ""
        if owner == "Gnomo" {
            let id = win[kCGWindowNumber as String] as? Int ?? 0
            let pid = win[kCGWindowOwnerPID as String] as? Int ?? 0
            if let b = win[kCGWindowBounds as String] as? [String: Any],
               let x = b["X"] as? Double, let y = b["Y"] as? Double,
               let w = b["Width"] as? Double, let h = b["Height"] as? Double {
                return (id, pid, x, y, w, h)
            }
        }
    }
    return nil
}

var targetPid: Int32 = 0

func post(_ event: CGEvent) {
    if targetPid != 0 {
        event.postToPid(targetPid)
    } else {
        event.post(tap: .cghidEventTap)
    }
}

func click(x: Double, y: Double) {
    let down = CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown,
                       mouseCursorPosition: CGPoint(x: x, y: y), mouseButton: .left)!
    let up = CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp,
                     mouseCursorPosition: CGPoint(x: x, y: y), mouseButton: .left)!
    post(down); post(up)
}

func type(_ text: String) {
    for ch in text.unicodeScalars {
        let code = UniChar(truncatingIfNeeded: ch.value)
        let e = CGEvent(keyboardEventSource: nil, virtualKey: 0, keyDown: true)!
        e.keyboardSetUnicodeString(stringLength: 1, unicodeString: [code])
        post(e)
        let up = CGEvent(keyboardEventSource: nil, virtualKey: 0, keyDown: false)!
        up.keyboardSetUnicodeString(stringLength: 1, unicodeString: [code])
        post(up)
        usleep(15000)
    }
}

func key(vk: CGKeyCode, mods: CGEventFlags = []) {
    let down = CGEvent(keyboardEventSource: nil, virtualKey: vk, keyDown: true)!
    down.flags = mods
    let up = CGEvent(keyboardEventSource: nil, virtualKey: vk, keyDown: false)!
    up.flags = mods
    post(down); post(up)
}

let args = CommandLine.arguments
guard args.count >= 2 else {
    print("usage: drive_gnomo <text...>")
    exit(1)
}
let text = args.dropFirst().joined(separator: " ")

guard let win = gnomoWindow() else {
    print("NO GNOMO WINDOW ON SCREEN")
    exit(2)
}
targetPid = Int32(win.pid)
print("window at x:\(win.x) y:\(win.y) w:\(win.w) h:\(win.h) pid:\(win.pid)")

// Input field sits below the gnome + bubble; the bubble height varies with
// the answer, so anchor to the bottom: field center ≈ height - 36.
let fx = win.x + win.w / 2
let fy = win.y + win.h - 36
print("clicking input at (\(fx), \(fy))")

click(x: fx, y: fy)
usleep(300_000)
key(vk: 0x00, mods: .maskCommand) // Cmd-A: clear any leftover text
usleep(100_000)
type(text)
usleep(150_000)
key(vk: 0x24) // Return
print("typed: \(text)")