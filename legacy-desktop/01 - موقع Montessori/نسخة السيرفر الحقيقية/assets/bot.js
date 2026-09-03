/* بوت الـFAQ القديم أُزيل (8/8) — ودجت دردشة الموقع (Chatwoot) المتصل بالـCRM. زر الواتساب مستقل. */
(function(){
  if(window.__CW_WIDGET) return; window.__CW_WIDGET=1;
  window.chatwootSettings = { locale:'ar', position:'left', type:'standard', launcherTitle:'محتاج مساعدة؟ 🌸', darkMode:'light' };
  var st=document.createElement('style'); st.id='cw-widget-offset';
  st.textContent='.woot-widget-bubble{bottom:20px !important; left:82px !important; right:auto !important;} .woot--bubble-holder{bottom:20px !important; left:82px !important; right:auto !important;} .woot-widget-holder{bottom:92px !important; left:20px !important; right:auto !important;} @media (max-width:600px){.woot-widget-bubble{left:70px !important; bottom:16px !important;} .woot--bubble-holder{left:70px !important; bottom:16px !important;} .woot-widget-holder{left:12px !important; bottom:84px !important;}}';
  document.head.appendChild(st);
  var BASE='https://crm.montessori-ksa.com';
  var g=document.createElement('script'), s=document.getElementsByTagName('script')[0];
  g.src=BASE+'/packs/js/sdk.js'; g.defer=true; g.async=true;
  s.parentNode.insertBefore(g,s);
  g.onload=function(){ window.chatwootSDK.run({ websiteToken:'8hXf9gepYA9hNwjKun31U7ZQ', baseUrl:BASE }); };
})();
