# Live2D Sample Build Drop-In

This directory now includes a runnable Live2D demo setup with Haru model assets.
You can replace it with your own official Cubism sample build if preferred.

Expected file for app auto-detection:
- `frontend/public/live2d-demo/index.html`

Current bundled runtime files:
- `vendor/pixi.min.js`
- `vendor/live2dcubismcore.min.js`
- `vendor/live2d.min.js`
- `vendor/live2d-pixi.min.js`
- `models/haru/*`
- `index.html`
- `live2d-app.js`
- `waifu-bridge.js`

If you want to swap in your own official sample build:
1. Follow the tutorial: https://docs.live2d.com/en/cubism-sdk-tutorials/sample-build-web/
2. Build and copy its `dist` output into this directory.
3. Keep `waifu-bridge.js` (or re-add it) for mood messaging.

The app will automatically render the Live2D sample in the character panel when `index.html` exists.

## Mood bridge (postMessage)

Waifu Tutor sends mood updates to the Live2D iframe:
- message type: `WAIFU_TUTOR_MOOD`
- payload shape:
  - `source: "waifu-tutor"`
  - `type: "WAIFU_TUTOR_MOOD"`
  - `mood: "happy" | "encouraging" | "sad" | "neutral" | "excited"`
  - `timestamp: ISO-8601 string`

Add this in your `live2d-demo/index.html`:

```html
<script src="/live2d-demo/waifu-bridge.js"></script>
<script>
  window.WaifuTutorBridge.onMood(function (event) {
    console.log("mood update", event.mood);
    // TODO: map mood to Cubism motion/expression in your sample runtime.
  });
</script>
```
