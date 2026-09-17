# Changelog

## 2026-09-17

- Added G1-D internal Dex1 control through low-level motor slots 31 and 33.
- Added the official G1-D controller layout for chassis, lift and waist pitch.
- Added Pico controller shortcuts: right A starts teleoperation, left Y toggles recording and right B exits.
- Added selectable Mandarin, English and bilingual G1 voice announcements.
- Made Mandarin the default announcement language.
- Fixed the second left-Y press so it stops and saves the active episode without exiting teleoperation.
- Added post-save JSON verification with episode path, frame count and file size feedback.
- Fixed G1-D exit homing to include motor 12 waist yaw as well as motor 14 waist pitch.
- Matched the official G1-D waist-yaw gains and added a 0.5 rad/s homing limit.
- Added a read-only monitor for integrated and external Dex1 state topics and endpoint calibration checks.
- Routed headset WebRTC through the robot Wi-Fi address and made immersive stereo video the default.
- Added XR, camera-service and duplicate-port startup checks.
- Extended recording with normalized XR input and operator action fields.
