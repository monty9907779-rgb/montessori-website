/* Routes every WhatsApp link on the site through the contact page /wa/?src=site
   (injected into every page by nginx: sub_filter in ops/nginx/montessori-ksa.conf).
   /wa/ itself is the page that opens WhatsApp, so it is skipped: rewriting its
   own wa.me buttons sent visitors back to /wa/ in a loop and WhatsApp never opened.
   Shipped to the server by ops/server/seo/self-update.sh (public list). */
(function () {
  if (window.NS_waFix) return;
  window.NS_waFix = true;
  var path = (location.pathname || '/').replace(/\/+$/, '');
  if (path === '/wa') return;
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
})();
