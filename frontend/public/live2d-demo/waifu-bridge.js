(function () {
  const MESSAGE_TYPE = "WAIFU_TUTOR_MOOD";
  const ALLOWED_SOURCE = "waifu-tutor";

  function isValidMessage(data) {
    return (
      data &&
      typeof data === "object" &&
      data.source === ALLOWED_SOURCE &&
      data.type === MESSAGE_TYPE &&
      typeof data.mood === "string"
    );
  }

  window.addEventListener("message", function (event) {
    if (event.origin !== window.location.origin) {
      return;
    }

    if (!isValidMessage(event.data)) {
      return;
    }

    var detail = {
      mood: event.data.mood,
      timestamp: event.data.timestamp || new Date().toISOString(),
    };

    window.dispatchEvent(new CustomEvent("waifu-tutor:mood", { detail: detail }));
  });

  window.WaifuTutorBridge = {
    onMood: function (handler) {
      if (typeof handler !== "function") {
        return function () {};
      }
      var listener = function (event) {
        handler(event.detail);
      };
      window.addEventListener("waifu-tutor:mood", listener);
      return function () {
        window.removeEventListener("waifu-tutor:mood", listener);
      };
    },
  };
})();
