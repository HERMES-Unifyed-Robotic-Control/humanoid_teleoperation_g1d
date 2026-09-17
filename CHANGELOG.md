# Changelog

## 2026-09-17

- Added G1-D internal Dex1 control through low-level motor slots 31 and 33.
- Added the official G1-D controller layout for chassis, lift and waist pitch.
- Added Pico controller shortcuts: right A starts teleoperation, left Y toggles recording and right B exits.
- Added selectable Mandarin, English and bilingual G1 voice announcements.
- Made Mandarin the default announcement language.
- Fixed the second left-Y press so it stops and saves the active episode without exiting teleoperation.
- Added post-save JSON verification with episode path, frame count and file size feedback.
- Routed headset WebRTC through the robot Wi-Fi address and made immersive stereo video the default.
- Added XR, camera-service and duplicate-port startup checks.
- Extended recording with normalized XR input and operator action fields.
