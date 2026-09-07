(function () {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js", { updateViaCache: 'none' }).then(function (registration) { return registration.update(); }).catch(function () {});
  }
})();
