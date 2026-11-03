/* Floating WhatsApp button for public pages.
   Usage: <script src="/assets/wa-fab.js?v=924a8be511" defer></script>
   Calm by design: no fake unread badge, no looping animation. The link goes to
   /wa/?src=fab (the contact page that opens WhatsApp), like the rest of the site.
   Labels follow the page language (<html lang>). */
(function () {
  if (document.getElementById('mk-wa')) return;
  var en = (document.documentElement.lang || '').toLowerCase().indexOf('en') === 0;
  var label = en ? 'Message us on WhatsApp' : 'راسلنا على واتساب';
  var href = '/wa/?src=fab';

  /* Styles live in app.css and home.css (#mk-wa block): the site CSP blocks injected <style>. */

  var path = 'M16 3C9 3 3.5 8.5 3.5 15.5c0 2.4.7 4.6 1.8 6.5L3 29l7.2-2.2c1.8 1 3.9 1.6 6 1.6 7 0 12.5-5.5 12.5-12.5S23 3 16 3zm0 22.7c-1.9 0-3.7-.5-5.2-1.4l-.4-.2-4.3 1.3 1.3-4.2-.2-.4c-1-1.6-1.5-3.4-1.5-5.3 0-5.6 4.6-10.2 10.3-10.2S26.3 9.9 26.3 15.5 21.7 25.7 16 25.7zm5.7-7.7c-.3-.2-1.8-.9-2.1-1s-.5-.2-.7.2-.8 1-.9 1.2-.3.2-.6.1c-1.7-.8-2.8-1.5-3.9-3.4-.3-.5.3-.5.8-1.5.1-.2 0-.4 0-.5s-.7-1.7-1-2.3c-.3-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.2.2 2.1 3.3 5.2 4.6 2.9 1.2 2.9.8 3.5.8.5-.1 1.8-.7 2-1.4.2-.7.2-1.3.2-1.4-.1-.2-.3-.2-.6-.4z';
  var wrap = document.createElement('div');
  wrap.id = 'mk-wa';
  wrap.innerHTML =
    '<a id="mk-wa-fab" href="' + href + '" data-cta="fab" aria-label="' + label + '" title="' + label + '">' +
      '<svg viewBox="0 0 32 32" aria-hidden="true" focusable="false"><path d="' + path + '"/></svg>' +
    '</a>';
  document.body.appendChild(wrap);
  var fab = document.getElementById('mk-wa-fab');
  requestAnimationFrame(function () { requestAnimationFrame(function () { fab.classList.add('in'); }); });

  /* Pages without their own click tracking still report the click.
     (The home page tracks every /wa/ link itself, so skip it there.) */
  if (!document.body.classList.contains('k-page')) {
    fab.addEventListener('click', function () {
      try { if (window.gtag) gtag('event', 'whatsapp_click', { link_location: 'fab', link_url: href, transport_type: 'beacon' }); } catch (e) {}
    });
  }
})();
