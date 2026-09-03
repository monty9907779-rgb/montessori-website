(function () {
  if (window.NS_waFix) return;
  window.NS_waFix = true;
  var target = '/wa/?src=site';
  function rewrite() {
    var links = document.getElementsByTagName('a');
    for (var i = 0; i < links.length; i += 1) {
      var href = links[i].getAttribute('href') || '';
      if (href.indexOf('wa.me') > -1 || href.indexOf('api.whatsapp.com') > -1) {
        links[i].setAttribute('href', target);
      }
    }
  }
  if (document.readyState !== 'loading') rewrite();
  else document.addEventListener('DOMContentLoaded', rewrite);
  setTimeout(rewrite, 1200);
  setTimeout(rewrite, 3500);
}());
