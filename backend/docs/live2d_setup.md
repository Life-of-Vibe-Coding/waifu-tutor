# Live2D Cubism Web Integration

This project uses the official Live2D Cubism Web sample build output as the runtime character renderer.

## Source tutorials
- Sample build (Web): https://docs.live2d.com/en/cubism-sdk-tutorials/sample-build-web/
- JavaScript + Vite usage notes: https://docs.live2d.com/en/cubism-sdk-tutorials/use-sdk-for-web-in-javascript/

## Setup steps
Default in this repo:
1. A runnable Live2D Haru demo is already placed under:
   - `frontend/public/live2d-demo/`
2. Run frontend and open the app; character should render immediately.

Optional custom sample flow:
1. Download Cubism SDK for Web from Live2D.
2. Build the sample project according to the sample-build tutorial.
3. Copy generated `dist` files into:
   - `frontend/public/live2d-demo/`
4. Ensure this file exists:
   - `frontend/public/live2d-demo/index.html`

## Runtime behavior in Waifu Tutor
- If `live2d-demo/index.html` is available, the character panel loads it in an iframe.
- If not available, app falls back to the built-in animated placeholder renderer.

## Mood bridge contract (parent -> iframe)
Waifu Tutor posts mood updates into the iframe using `postMessage`.

- `origin`: same-origin (`window.location.origin`)
- message payload:
  - `source: "waifu-tutor"`
  - `type: "WAIFU_TUTOR_MOOD"`
  - `mood: "happy" | "encouraging" | "sad" | "neutral" | "excited"`
  - `timestamp: ISO-8601 string`

This repo provides a helper script at:
- `frontend/public/live2d-demo/waifu-bridge.js`

Add to your Live2D sample `index.html`:

```html
<script src="/live2d-demo/waifu-bridge.js"></script>
<script>
  window.WaifuTutorBridge.onMood(function (event) {
    // event.mood -> map into Cubism expression/motion playback
    // e.g. happy -> tap body motion, sad -> idle expression set
  });
</script>
```

## Notes
- Live2D assets are not committed in this repo.
- Keep model/license files in your local/private deployment according to Live2D terms.
