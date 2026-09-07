(function () {
  if (!('serviceWorker' in navigator)) return;

  navigator.serviceWorker
    .register('/sw.js', { updateViaCache: 'none' })
    .then(function (registration) {
      return registration.update();
    })
    .catch(function () {});
})();
