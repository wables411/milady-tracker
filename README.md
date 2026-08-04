# Milady Tracker

Stream as a Pockit Milady VRM avatar straight from your browser. Webcam
face, arm, and torso tracking.

## Quick start

**No install:** open **https://miladyvrm.lawb.xyz** and **Allow** the
camera. (HTTPS, so it works on phones too. The mic is not needed — the
camera tracks your jaw.)

**Run it locally:**

1. Install [Node.js](https://nodejs.org).
2. Run `tracker\Start Avatar Tracker.bat`.
3. Open `http://127.0.0.1:8787` and **Allow** the camera.

Windows: run `tracker\Create Desktop Icon.bat` once to get a **Milady
Tracker** desktop icon that starts everything in its own window.

## Pick your Milady

Enter a token # (1–1111) in the **milady #** box — or the 🤍 Milady #
button (with 🎲 Random), or `?milady=777` in the URL. That Pockit Milady's
VRM loads straight from `prnth.com/Pockit`. Blank = the bundled
`AlienMilady.vrm`. Your choice persists.

## OBS

**Browser Source (transparent):** append ` --enable-media-stream` to your
OBS shortcut's Target (one time, then restart OBS) so browser sources can
use the webcam. Add a Browser source with URL `http://127.0.0.1:8787/?ui=0`
— the background is transparent, layer it over anything.

**Window Capture:** open `http://127.0.0.1:8787/?bg=green` in a browser,
then Window Capture that window in OBS and add a **Chroma Key** filter.

## Controls

🤍 Milady # · 🔄 Mirror · 🎯 Fix Head · 🖼 BG · ⏺ Record · ✨ FX ·
⚙ · ☁️ Hide. Press **H** to hide/show the buttons; everything persists.
**⚙** opens the advanced settings panel (axis flips, mic mouth, tracking
toggles).

- **Mouse wheel / pinch** — zoom between full body and face close-up.
- **🎯 Fix Head** — re-zero your neutral head pose.
- **🖼 BG** — green → white → black → cult → image → transparent
  (drag & drop any picture to use it as the background).
- **⏺ Record** — capture avatar + background to a `.webm` download
  (2 min max; first click asks for the mic so clips have voice).
- **✨ FX** — ✨ sparkles · 💕 hearts · 🌈 multicolor · 📺 crt · 🐟 fisheye.
- `?demo=1` self-test (no camera) · `?mouthsens=1.3` mouth sensitivity.

## Credits

- [three.js](https://threejs.org) + [@pixiv/three-vrm](https://github.com/pixiv/three-vrm) (MIT)
- [MediaPipe Tasks Vision](https://developers.google.com/mediapipe) (Apache-2.0)
- Pockit Milady VRMs from [prnth.com/Pockit](https://prnth.com/Pockit/) ([moviemaker](https://github.com/prnthh/moviemaker), Viral Public License)
- Interface styled after [RemiliaNET's Beetleboy](https://wiki.remilia.org/Beetleboy) console; [Silkscreen](https://fontsource.org/fonts/silkscreen) font
- Sp00bs — `AlienMilady.vrm` 3D model
- for Zodomo

License: [Viral Public License](https://viralpubliclicense.org/)
