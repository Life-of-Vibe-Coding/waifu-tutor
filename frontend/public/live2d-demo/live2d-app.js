(function () {
  var statusEl = document.getElementById('status');
  var mount = document.getElementById('app');
  var model = null;
  var app = null;
  var mood = 'neutral';
  var idleTimer = null;
  var moodResetTimer = null;
  var floatTick = 0;
  var baseX = 0;
  var baseY = 0;
  var currentMoodBoost = false;
  var motionHistory = {
    Idle: -1,
    Use: -1,
  };

  var moodMotionMap = {
    neutral: { group: 'Idle', indices: [0, 1, 2, 3, 4, 5], priority: 1 },
    happy: { group: 'Use', indices: [4, 5, 6, 7, 10, 11, 13, 14], priority: 10 },
    encouraging: { group: 'Use', indices: [4, 6, 8, 10, 11, 12, 14], priority: 8 },
    sad: { group: 'Use', indices: [0, 1, 2, 9], priority: 6 },
    excited: { group: 'Use', indices: [4, 5, 8, 10, 11, 12, 13, 14], priority: 10 },
  };

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
      baseX = model.x;
      baseY = model.y;
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
    baseX = model.x;
    baseY = model.y;
  }

  function pickMotionIndex(group, indices) {
    if (!indices || !indices.length) {
      return 0;
    }

    if (indices.length === 1) {
      return indices[0];
    }

    var last = motionHistory[group];
    var candidate = indices[Math.floor(Math.random() * indices.length)];
    var tries = 0;
    while (candidate === last && tries < 4) {
      candidate = indices[Math.floor(Math.random() * indices.length)];
      tries += 1;
    }
    motionHistory[group] = candidate;
    return candidate;
  }

  function playMotion(group, indices, priority) {
    if (!model || typeof model.motion !== 'function') {
      return false;
    }

    try {
      var index = pickMotionIndex(group, indices);
      model.motion(group, index, priority || 1);
      return true;
    } catch (error) {
      return false;
    }
  }

  function playIdleMotion() {
    return playMotion('Idle', moodMotionMap.neutral.indices, moodMotionMap.neutral.priority);
  }

  function scheduleIdleRoutine() {
    if (idleTimer) {
      window.clearTimeout(idleTimer);
    }

    var delay = 5200 + Math.random() * 4200;
    idleTimer = window.setTimeout(function () {
      if (!model) {
        return;
      }

      if (mood === 'neutral' || mood === 'encouraging') {
        playIdleMotion();
      } else if (!currentMoodBoost) {
        var moodSpec = moodMotionMap[mood] || moodMotionMap.neutral;
        playMotion(moodSpec.group, moodSpec.indices, moodSpec.priority);
      }

      scheduleIdleRoutine();
    }, delay);
  }

  function startFloatMotion() {
    if (!app || !model) {
      return;
    }

    app.ticker.add(function (delta) {
      if (!model) {
        return;
      }

      floatTick += 0.017 * delta;
      var moodScale = currentMoodBoost ? 1.25 : 1;
      var vertical = Math.sin(floatTick) * 2.4 * moodScale;
      var tilt = Math.sin(floatTick * 0.75) * 0.0048 * moodScale;

      model.x = baseX;
      model.y = baseY + vertical;
      model.rotation = tilt;
    });
  }

  function moodToMotion(targetMood) {
    if (!model) {
      return;
    }

    try {
      var moodSpec = moodMotionMap[targetMood] || moodMotionMap.neutral;
      currentMoodBoost = targetMood === 'excited' || targetMood === 'happy';

      if (typeof model.motion === 'function') {
        playMotion(moodSpec.group, moodSpec.indices, moodSpec.priority);

        if (moodResetTimer) {
          window.clearTimeout(moodResetTimer);
        }

        if (targetMood !== 'neutral') {
          moodResetTimer = window.setTimeout(function () {
            currentMoodBoost = false;
            playIdleMotion();
          }, 3600);
        }
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
      backgroundColor: 0xffc4e0,
      backgroundAlpha: 1,
      antialias: true,
    });

    mount.appendChild(app.view);

    try {
      model = await Live2DModelCtor.from('/live2d-demo/models/haru/haru_greeter_t03.model3.json');
      app.stage.addChild(model);
      fitModel();
      startFloatMotion();
      setupBridge();
      moodToMotion(mood);
      scheduleIdleRoutine();
      setStatus('model loaded');
    } catch (error) {
      console.error(error);
      setStatus('failed to load model');
    }

    window.addEventListener('resize', fitModel);
  }

  init();
})();
