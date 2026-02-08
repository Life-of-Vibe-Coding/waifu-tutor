(function () {
  var statusEl = document.getElementById('status');
  var mount = document.getElementById('app');
  var model = null;
  var app = null;
  var mood = 'neutral';

  function setStatus(text) {
    if (statusEl) {
      statusEl.textContent = text;
    }
  }

  function fitModel() {
    if (!model || !app) {
      return;
    }

    var width = app.renderer.width;
    var height = app.renderer.height;
    var bounds = typeof model.getLocalBounds === 'function' ? model.getLocalBounds() : null;

    if (!bounds || !bounds.width || !bounds.height) {
      var fallbackScale = Math.min(width / 900, height / 1200);
      model.scale.set(fallbackScale * 0.82);
      model.x = width * 0.5;
      model.y = height * 0.68;
      if (model.anchor && typeof model.anchor.set === 'function') {
        model.anchor.set(0.5, 0.5);
      }
      return;
    }

    var targetWidth = width * 0.84;
    var targetHeight = height * 0.92;
    var scaleX = targetWidth / bounds.width;
    var scaleY = targetHeight / bounds.height;
    var scale = Math.min(scaleX, scaleY);

    model.scale.set(scale);
    if (model.pivot && typeof model.pivot.set === 'function') {
      // Center horizontally and bias vertically to include face/torso instead of only legs.
      model.pivot.set(bounds.x + bounds.width * 0.5, bounds.y + bounds.height * 0.54);
      model.position.set(width * 0.5, height * 0.56);
    } else {
      model.x = width * 0.5;
      model.y = height * 0.56;
    }
  }

  function moodToMotion(targetMood) {
    if (!model) {
      return;
    }

    try {
      if (typeof model.motion === 'function') {
        if (targetMood === 'excited' || targetMood === 'happy') {
          model.motion('Use', 10);
          return;
        }
        if (targetMood === 'sad') {
          model.motion('Use', 1);
          return;
        }
        if (targetMood === 'encouraging') {
          model.motion('Use', 6);
          return;
        }
        model.motion('Idle', 0);
        return;
      }

      if (typeof model.tap === 'function') {
        if (targetMood === 'excited' || targetMood === 'happy') {
          model.tap('Body');
        } else if (targetMood === 'sad') {
          model.tap('Head');
        }
      }
    } catch (error) {
      setStatus('model loaded (motion fallback)');
    }
  }

  function setupBridge() {
    if (!window.WaifuTutorBridge || typeof window.WaifuTutorBridge.onMood !== 'function') {
      return;
    }

    window.WaifuTutorBridge.onMood(function (event) {
      mood = event.mood || 'neutral';
      setStatus('mood: ' + mood);
      moodToMotion(mood);
    });
  }

  async function init() {
    var live2dNs = (window.PIXI && window.PIXI.live2d) || window.live2d || null;
    var Live2DModelCtor =
      (live2dNs && live2dNs.Live2DModel) ||
      (window.PIXI && window.PIXI.Live2DModel) ||
      window.Live2DModel ||
      null;

    if (!window.PIXI || !Live2DModelCtor || typeof Live2DModelCtor.from !== 'function') {
      var debug = [];
      debug.push('PIXI=' + Boolean(window.PIXI));
      debug.push('PIXI.live2d=' + Boolean(window.PIXI && window.PIXI.live2d));
      debug.push('window.live2d=' + Boolean(window.live2d));
      debug.push('Live2DModel.from=' + Boolean(Live2DModelCtor && Live2DModelCtor.from));
      setStatus('live2d runtime not available (' + debug.join(', ') + ')');
      return;
    }

    app = new window.PIXI.Application({
      resizeTo: mount,
      backgroundAlpha: 0,
      antialias: true,
    });

    mount.appendChild(app.view);

    try {
      model = await Live2DModelCtor.from('/live2d-demo/models/haru/haru_greeter_t03.model3.json');
      app.stage.addChild(model);
      fitModel();
      setupBridge();
      moodToMotion(mood);
      setStatus('model loaded');
    } catch (error) {
      console.error(error);
      setStatus('failed to load model');
    }

    window.addEventListener('resize', fitModel);
  }

  init();
})();
