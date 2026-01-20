# Changelog — Gesture Mouse Control

All notable changes to this project are documented in this file.

This project evolved iteratively through experimentation, debugging, and usability improvements, with a strong focus on human–computer interaction (HCI), robustness, and real-world usability.

---

## [v6.1] — Reliable Click Pinch (Current)
### Added
- Pinch **tap click no longer depends on confidence**
- Click detection based purely on:
  - Pinch distance
  - Pinch timing
- Ensures consistent and predictable clicking behavior

### Changed
- Gesture confidence still applies to:
  - Cursor movement
  - Scroll
  - Drag
- Drag remains **pinch + hold**

### Fixed
- Missed or inconsistent click events
- Clicks being overridden by drag or intent confidence

---

## [v6.0] — Adaptive Speed + Intent Detection
### Added
- **Adaptive cursor speed**
  - Fast hand movement → faster cursor
  - Slow hand movement → precision
- **Slowdown zones**
  - Automatic precision near screen edges
  - Steady-hand precision mode
- **Gesture confidence scoring**
  - Probabilistic gesture intent selection
- **Intent detection with hysteresis**
  - Prevents rapid gesture flickering
  - Requires stability before switching intents
- Expanded HUD diagnostics:
  - Confidence bar
  - Velocity
  - Gain values

### Changed
- Gesture logic transitioned from rule-only to confidence-based intent selection
- Cursor movement logic rewritten to support adaptive gain

---

## [v5.3] — Virtual FOV Expansion
### Added
- **Virtual control margin**
  - Maps a smaller camera region to full screen
  - Makes narrow laptop webcams feel wider
- Improved edge tracking stability
- 720p camera capture for better landmark detection

### Changed
- Cursor mapping now uses normalized coordinates with margin correction

---

## [v5.2] — Scroll Improvements
### Added
- Scroll accumulator
  - Small hand movements now produce smooth scrolling
- Scroll deadzone to eliminate jitter

### Fixed
- Ineffective or unresponsive scroll behavior
- Scroll jitter caused by noisy hand motion

---

## [v5.1] — Pause & Drag Stability
### Added
- Spacebar pause / unpause
- Drag-and-drop via pinch + hold
- On-screen HUD showing:
  - Gesture state
  - FPS
  - Drag status

### Removed
- Fist gesture for pause (replaced with keyboard control)

---

## [v5.0] — Full Mouse Control
### Added
- Cursor movement using index finger
- Left click via pinch
- Scroll via index + middle finger
- Basic gesture HUD
- Frame-rate monitoring

---

## [v4.x] — Gesture Logic Refinement
### Improved
- Finger-up detection logic
- Pinch distance calibration
- Reduced false positives
- Improved smoothing for cursor movement

---

## [v3.x] — MediaPipe Integration
### Added
- MediaPipe Hands integration
- 21-point hand landmark tracking
- Visual hand skeleton overlay

### Fixed
- Camera coordinate mapping issues
- Landmark jitter

---

## [v2.x] — OpenCV Camera Pipeline
### Added
- Webcam capture using OpenCV
- Frame flipping for mirror control
- RGB/BGR color conversion
- Basic visual debugging overlays

---

## [v1.0] — Initial Prototype
### Added
- Proof-of-concept hand tracking
- Cursor movement mapped directly to hand position
- Early experimentation with gesture-based input

---

## 🧭 Notes
- Version numbers reflect **behavioral milestones**, not just code changes
- This project emphasizes **robust interaction design**, not just gesture detection
- Future versions may include:
  - Machine learning gesture classifiers
  - Auto-calibration
  - Context-aware gestures
  - Analytics and performance logging
