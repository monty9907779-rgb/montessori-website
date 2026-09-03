/* ============================================================================
   Montessori Nursery — shared runtime (app.js) · v1
   Token handling · JSON-RPC api() with typed errors · toast · modal/confirm
   · geolocation · SVG icons · formatters · scroll reveal · lightbox
   ========================================================================== */
(function(){
'use strict';
var NS = window.NS = {};

/* ---- endpoints ---- */
NS.ODOO  = 'https://odoo.montessori-ksa.com';
NS.LOGIN = NS.ODOO + '/portal-login';                 /* invisible 303 -> Google */
NS.SWITCH = NS.ODOO + '/web/session/logout?redirect=%2Fportal-login'; /* logout then Google chooser */
NS.SITE  = '';                                        /* same-origin site root */
NS.WA_MANAGER = '966541558173';                       /* nursery admin whatsapp */

/* ---- escaping ---- */
NS.esc = function(s){ var d=document.createElement('div'); d.textContent = s==null?'':String(s); return d.innerHTML; };
NS.attr = function(s){ return String(s==null?'':s).replace(/"/g,'&quot;').replace(/</g,'&lt;'); };

/* ---- token: hash(kind) -> localStorage(store) -> strip url ---- */
var STORES = { t:'nursery_token', mt:'nursery_mt', st:'nursery_staff' };
NS.token = function(kind){
  var store = STORES[kind]; if(!store) return null;
  var h = new URLSearchParams(location.hash.slice(1));
  var tok = h.get(kind);
  if(tok){ try{ localStorage.setItem(store, tok); }catch(e){} }
  else { try{ tok = localStorage.getItem(store); }catch(e){ tok=null; } }
  // also honour a `pending` email marker on hash (parent not-yet-linked)
  NS.pending = h.get('pending') || null;
  if(location.hash){ history.replaceState(null,'',location.pathname + location.search); }
  return tok || null;
};
NS.clearToken = function(kind){ try{ localStorage.removeItem(STORES[kind]); }catch(e){} };

/* ---- typed API errors ---- */
function ApiError(type,message){ this.type=type; this.message=message; } // type: 'auth' | 'net' | 'app'
NS.ApiError = ApiError;

/* JSON-RPC call to Odoo json route. Resolves with result object.
   Throws ApiError('net') on network fail, ('app') on rpc error,
   ('auth') when result signals unauthorized. */
NS.api = function(path, params){
  var url = (path.charAt(0)==='/' ? NS.ODOO + path : path);
  return fetch(url, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ jsonrpc:'2.0', method:'call', params: params||{} })
  }).then(function(r){
    if(r.status===401||r.status===403||r.status===404){ throw new ApiError('auth','انتهت الجلسة'); }
    if(r.status>=500){ throw new ApiError('net','الخادم مشغول مؤقتاً، حاول مجدداً'); }  // transient, retryable — never log the user out
    return r.json().catch(function(){ throw new ApiError('app','رد غير صالح من الخادم'); });
  }, function(){ throw new ApiError('net','تعذّر الاتصال بالخادم'); })
  .then(function(d){
    if(d.error){ throw new ApiError('app', (d.error.data&&d.error.data.message)||d.error.message||'خطأ'); }
    var res = d.result;
    if(res && (res.error==='unauthorized' || res.ok===false && res.auth==='unauthorized')){
      throw new ApiError('auth','انتهت الجلسة');
    }
    return res;
  });
};

/* ---- toast ---- */
function toastWrap(){ var w=document.getElementById('toast-wrap');
  if(!w){ w=document.createElement('div'); w.id='toast-wrap'; document.body.appendChild(w);} return w; }
NS.toast = function(msg, kind){
  var t=document.createElement('div');
  t.className='toast toast--'+(kind==='err'?'err':'ok');
  t.innerHTML = NS.icon(kind==='err'?'alert':'check') + '<span>'+NS.esc(msg)+'</span>';
  toastWrap().appendChild(t);
  requestAnimationFrame(function(){ t.classList.add('show'); });
  setTimeout(function(){ t.classList.remove('show'); setTimeout(function(){ t.remove(); },400); }, kind==='err'?4200:2800);
};

/* ---- modal / confirm ---- */
NS.modal = function(html){
  var back=document.createElement('div'); back.className='modal-back';
  back.innerHTML='<div class="modal" role="dialog" aria-modal="true">'+html+'</div>';
  document.body.appendChild(back);
  requestAnimationFrame(function(){ back.classList.add('show'); });
  function close(){ back.classList.remove('show'); setTimeout(function(){ back.remove(); },300); }
  back.addEventListener('click', function(e){ if(e.target===back) close(); });
  return { el:back, close:close };
};
NS.confirm = function(opt){
  opt = opt||{};
  return new Promise(function(resolve){
    var danger = !!opt.danger;
    var m = NS.modal(
      '<div class="modal__icon '+(danger?'danger':'')+'">'+NS.icon(opt.icon||(danger?'alert':'help'))+'</div>'+
      '<h3>'+NS.esc(opt.title||'تأكيد')+'</h3>'+
      (opt.body?'<p>'+NS.esc(opt.body)+'</p>':'')+
      '<div class="actions">'+
        '<button class="btn '+(danger?'btn--danger':'btn--primary')+'" data-ok>'+NS.esc(opt.okText||'تأكيد')+'</button>'+
        '<button class="btn btn--ghost" data-cancel>'+NS.esc(opt.cancelText||'إلغاء')+'</button>'+
      '</div>');
    m.el.querySelector('[data-ok]').addEventListener('click', function(){ m.close(); resolve(true); });
    m.el.querySelector('[data-cancel]').addEventListener('click', function(){ m.close(); resolve(false); });
  });
};

/* ---- geolocation (typed) ---- */
NS.geo = function(opt){
  opt = opt||{};
  return new Promise(function(resolve,reject){
    if(!navigator.geolocation){ reject(new ApiError('app','المتصفح لا يدعم تحديد الموقع')); return; }
    navigator.geolocation.getCurrentPosition(
      function(p){ resolve({ latitude:p.coords.latitude, longitude:p.coords.longitude, accuracy:p.coords.accuracy }); },
      function(err){
        var msg = err.code===1 ? 'لازم تسمح بالوصول للموقع من إعدادات المتصفح' :
                  err.code===3 ? 'انتهت مهلة تحديد الموقع، حاول مرة أخرى' : 'تعذّر تحديد موقعك';
        reject(new ApiError('geo',msg));
      },
      { enableHighAccuracy:true, timeout:opt.timeout||15000, maximumAge:0 }
    );
  });
};

/* ---- formatters (Arabic, Riyadh) ---- */
NS.fmtMoney = function(n){ n=Number(n||0); return n.toLocaleString('en-US',{maximumFractionDigits:0}); };
NS.riyal = function(n){ return NS.fmtMoney(n)+' ر.س'; };
/* ميلادي دائماً (ca-gregory) — ar-SA وحدها تعرض هجري */
NS.fmtDate = function(s){ if(!s) return '—'; try{ var d=new Date(s.replace(' ','T'));
  if(isNaN(d)) return '—';
  return d.toLocaleDateString('ar-SA-u-ca-gregory-nu-latn',{day:'numeric',month:'long',year:'numeric'}); }catch(e){ return '—'; } };
NS.fmtShort = function(s){ if(!s) return '—'; try{ var d=new Date(s.replace(' ','T'));
  if(isNaN(d)) return '—';
  return d.toLocaleDateString('ar-SA-u-ca-gregory-nu-latn',{day:'numeric',month:'short'}); }catch(e){ return '—'; } };
NS.wa = function(phone,text){ var p=String(phone||'').replace(/[^0-9]/g,'');
  if(p.indexOf('0')===0) p='966'+p.slice(1); if(p.indexOf('966')!==0 && p.length===9) p='966'+p;
  return 'https://wa.me/'+p+(text?('?text='+encodeURIComponent(text)):''); };

/* ---- skeleton helpers ---- */
NS.skelLines = function(n){ var h=''; for(var i=0;i<(n||3);i++){ h+='<div class="skel skel-line" style="width:'+(60+Math.round((i*37)%38))+'%"></div>'; } return h; };
NS.skelCard = function(){ return '<div class="card card--pad"><div class="skel skel-line" style="width:40%;height:20px"></div>'+NS.skelLines(3)+'</div>'; };

/* ---- empty state ---- */
NS.empty = function(icon,title,hint){
  return '<div class="empty"><div class="empty__icon">'+NS.icon(icon||'leaf')+'</div>'+
    '<h4>'+NS.esc(title||'لا يوجد شيء بعد')+'</h4>'+(hint?'<p>'+NS.esc(hint)+'</p>':'')+'</div>';
};

/* ---- on-site auth gate (never shows Odoo UI) ---- */
NS.gate = function(mount, opt){
  opt = opt||{};
  var el = typeof mount==='string'?document.getElementById(mount):mount;
  el.className='gate';
  el.innerHTML =
   '<div class="gate__card">'+
     '<img class="logo" src="/logo.png" alt="حضانة مونتيسوري"/>'+
     '<h2>'+NS.esc(opt.title||'مرحباً بك')+'</h2>'+
     '<p>'+NS.esc(opt.body||'سجّل دخولك للمتابعة')+'</p>'+
     '<a class="btn btn--primary btn--block btn--lg" href="/login/">'+NS.icon('google')+' '+NS.esc(opt.cta||'الدخول عبر Google')+'</a>'+
     (opt.altHtml||'')+
     '<div style="margin-top:14px"><a class="btn btn--ghost btn--block" href="/">'+NS.icon('home')+' رجوع للموقع</a></div>'+
   '</div>';
};

/* ---- scroll reveal ---- */
NS.reveal = function(){
  var els=[].slice.call(document.querySelectorAll('.rev'));
  if(!('IntersectionObserver' in window)){ els.forEach(function(e){e.classList.add('in');}); return; }
  var io=new IntersectionObserver(function(es){ es.forEach(function(x){ if(x.isIntersecting){ x.target.classList.add('in'); io.unobserve(x.target);} }); },{threshold:.12,rootMargin:'0px 0px -8% 0px'});
  els.forEach(function(e){ io.observe(e); });
};

/* ---- lightbox for photo galleries ---- */
NS.lightbox = function(urls, start){
  var i = start||0;
  var opener = document.activeElement;
  var lb=document.createElement('div'); lb.className='lightbox'; lb.setAttribute('role','dialog');
  lb.setAttribute('aria-modal','true'); lb.setAttribute('aria-label','معرض الصور');
  lb.innerHTML='<button class="lb-close" aria-label="إغلاق">'+NS.icon('close')+'</button>'+
    (urls.length>1?'<button class="lb-nav lb-prev" aria-label="السابق">'+NS.icon('chevRight')+'</button><button class="lb-nav lb-next" aria-label="التالي">'+NS.icon('chevLeft')+'</button>':'')+
    '<img alt="صورة من الحضانة"/>';
  document.body.appendChild(lb);
  var img=lb.querySelector('img');
  var focusables=[].slice.call(lb.querySelectorAll('button'));
  function show(){ img.src=urls[i]; }
  function close(){ lb.classList.remove('show'); setTimeout(function(){ lb.remove(); document.removeEventListener('keydown',key);
    if(opener && opener.focus) try{ opener.focus(); }catch(e){} },300); }
  function next(d){ i=(i+d+urls.length)%urls.length; show(); }
  function key(e){
    if(e.key==='Escape'){ close(); }
    else if(e.key==='ArrowLeft'){ next(1); }
    else if(e.key==='ArrowRight'){ next(-1); }
    else if(e.key==='Tab'){ // trap focus within the dialog
      var first=focusables[0], last=focusables[focusables.length-1];
      if(e.shiftKey && document.activeElement===first){ e.preventDefault(); last.focus(); }
      else if(!e.shiftKey && document.activeElement===last){ e.preventDefault(); first.focus(); }
    }
  }
  lb.querySelector('.lb-close').addEventListener('click',close);
  lb.addEventListener('click',function(e){ if(e.target===lb) close(); });
  var pv=lb.querySelector('.lb-prev'), nx=lb.querySelector('.lb-next');
  if(pv) pv.addEventListener('click',function(){next(1);}); if(nx) nx.addEventListener('click',function(){next(-1);});
  document.addEventListener('keydown',key);
  show(); requestAnimationFrame(function(){ lb.classList.add('show'); focusables[0].focus(); });
};
NS.driveThumb = function(id,w){ return 'https://lh3.googleusercontent.com/d/'+encodeURIComponent(id)+'=w'+(w||800); };

/* ---- SVG icon registry (24x24, stroke, currentColor) ---- */
var P='<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">';
var ICONS = {
  menu:'<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>',
  close:'<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  check:'<polyline points="20 6 9 17 4 12"/>',
  checkCircle:'<circle cx="12" cy="12" r="9"/><polyline points="16 9.5 11 15 8 12"/>',
  alert:'<path d="M12 3l9 16H3z"/><line x1="12" y1="10" x2="12" y2="14"/><circle cx="12" cy="17" r=".6" fill="currentColor"/>',
  help:'<circle cx="12" cy="12" r="9"/><path d="M9.2 9.3a2.8 2.8 0 0 1 5.3 1c0 1.9-2.5 2.2-2.5 3.7"/><circle cx="12" cy="17" r=".6" fill="currentColor"/>',
  x:'<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  clock:'<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/>',
  wallet:'<rect x="3" y="6" width="18" height="13" rx="3"/><path d="M3 10h18"/><circle cx="16.5" cy="13.5" r="1.2" fill="currentColor"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="3"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="8" y1="3" x2="8" y2="7"/><line x1="16" y1="3" x2="16" y2="7"/>',
  chat:'<path d="M21 12a8 8 0 0 1-11.3 7.3L4 21l1.7-5.7A8 8 0 1 1 21 12z"/>',
  camera:'<path d="M4 8a2 2 0 0 1 2-2h1.5l1-1.6a1 1 0 0 1 .9-.5h5.2a1 1 0 0 1 .9.5l1 1.6H18a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><circle cx="12" cy="12.5" r="3.3"/>',
  users:'<circle cx="9" cy="8" r="3.2"/><path d="M3.5 19a5.5 5.5 0 0 1 11 0"/><path d="M16 5.2a3.2 3.2 0 0 1 0 6.1"/><path d="M17 13.5a5.5 5.5 0 0 1 3.5 5.5"/>',
  user:'<circle cx="12" cy="8" r="3.6"/><path d="M5 20a7 7 0 0 1 14 0"/>',
  trash:'<path d="M4 7h16"/><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/><path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12"/><path d="M10 11v6"/><path d="M14 11v6"/>',
  ledger:'<rect x="4" y="3" width="16" height="18" rx="3"/><path d="M8 8h8"/><path d="M8 12h8"/><path d="M8 16h5"/>',
  cap:'<path d="M12 4 2 9l10 5 10-5-10-5z"/><path d="M6 11v4c0 1.2 2.7 2.5 6 2.5s6-1.3 6-2.5v-4"/>',
  chart:'<path d="M4 20V4"/><path d="M4 20h16"/><rect x="7" y="11" width="3" height="6" rx="1" fill="currentColor" stroke="none"/><rect x="12" y="7" width="3" height="10" rx="1" fill="currentColor" stroke="none"/><rect x="17" y="13" width="3" height="4" rx="1" fill="currentColor" stroke="none"/>',
  logout:'<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3"/><polyline points="10 8 14 12 10 16"/><line x1="14" y1="12" x2="4" y2="12"/>',
  pin:'<path d="M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11z"/><circle cx="12" cy="10" r="2.6"/>',
  phone:'<path d="M5 4h3l2 5-2.5 1.5a11 11 0 0 0 5 5L14 12l5 2v3a2 2 0 0 1-2.2 2A16 16 0 0 1 3 6.2 2 2 0 0 1 5 4z"/>',
  whatsapp:'<path d="M12 3a9 9 0 0 0-7.7 13.6L3 21l4.5-1.3A9 9 0 1 0 12 3z"/><path d="M8.8 8.4c.8 2.6 2.2 4 4.8 4.8.6-.9 1-.9 2-.4l1 .8-.4 1.3c-2.6.7-6.6-2.8-6.9-5.9l1.3-.5z" fill="currentColor" stroke="none"/>',
  star:'<path d="M12 4l2.3 4.7 5.2.8-3.8 3.7.9 5.2L12 16.9 7.4 18l.9-5.2L4.5 9.5l5.2-.8z"/>',
  leaf:'<path d="M5 19c0-8 5-13 14-13 0 9-5 14-13 14"/><path d="M5 19c3-4 6-6 9-7"/>',
  shield:'<path d="M12 3l7 3v5c0 5-3.5 8.5-7 10-3.5-1.5-7-5-7-10V6z"/><polyline points="9 12 11 14 15 10"/>',
  refresh:'<path d="M4 12a8 8 0 0 1 13.5-5.8L20 8"/><polyline points="20 3 20 8 15 8"/><path d="M20 12a8 8 0 0 1-13.5 5.8L4 16"/><polyline points="4 21 4 16 9 16"/>',
  search:'<circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/>',
  home:'<path d="M4 11l8-7 8 7"/><path d="M6 10v9a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-9"/>',
  bell:'<path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
  plus:'<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  send:'<path d="M4 12L20 4l-5 16-4-6z"/><path d="M11 14l4-6"/>',
  chevLeft:'<polyline points="15 6 9 12 15 18"/>',
  chevRight:'<polyline points="9 6 15 12 9 18"/>',
  chevDown:'<polyline points="6 9 12 15 18 9"/>',
  arrowLeft:'<line x1="20" y1="12" x2="4" y2="12"/><polyline points="10 6 4 12 10 18"/>',
  arrowUp:'<line x1="12" y1="20" x2="12" y2="4"/><polyline points="6 10 12 4 18 10"/>',
  google:'<path d="M21 12.2c0-.7-.06-1.2-.18-1.8H12v3.4h5.1c-.1.9-.66 2.2-1.9 3.1l-.02.15 2.8 2.14.2.02A8.7 8.7 0 0 0 21 12.2z" fill="#4285F4" stroke="none"/><path d="M12 21c2.5 0 4.6-.82 6.14-2.24l-2.93-2.27c-.78.54-1.83.92-3.2.92a5.55 5.55 0 0 1-5.25-3.83l-.14.01-2.9 2.25-.05.14A9 9 0 0 0 12 21z" fill="#34A853" stroke="none"/><path d="M6.76 13.58A5.4 5.4 0 0 1 6.46 12c0-.55.1-1.08.28-1.58l-.01-.16-2.94-2.28-.1.05A9 9 0 0 0 3 12c0 1.45.35 2.82.96 4.03z" fill="#FBBC05" stroke="none"/><path d="M12 6.58c1.72 0 2.88.74 3.54 1.36l2.58-2.52C16.6 3.9 14.5 3 12 3a9 9 0 0 0-8.04 4.97l2.93 2.28A5.55 5.55 0 0 1 12 6.58z" fill="#EA4335" stroke="none"/>',
  heart:'<path d="M12 20s-7-4.5-7-9.5A3.5 3.5 0 0 1 12 8a3.5 3.5 0 0 1 7 2.5C19 15.5 12 20 12 20z"/>',
  book:'<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19a2 2 0 0 1 2-2h13"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19"/>',
  sparkle:'<path d="M12 3l1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6z"/>',
  info:'<circle cx="12" cy="12" r="9"/><line x1="12" y1="11" x2="12" y2="16"/><circle cx="12" cy="8" r=".6" fill="currentColor"/>',
  wifi:'<path d="M2 8.8a15 15 0 0 1 20 0"/><path d="M5 12.2a10 10 0 0 1 14 0"/><path d="M8.5 15.6a5 5 0 0 1 7 0"/><circle cx="12" cy="19" r=".8" fill="currentColor"/>',
  video:'<rect x="3" y="6" width="13" height="12" rx="2"/><path d="M16 10l5-3v10l-5-3z"/>',
  eye:'<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
  eyeOff:'<path d="M9.5 5.4A9.6 9.6 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3.3 4M6 6.5A17 17 0 0 0 2 12s3.5 7 10 7a9.5 9.5 0 0 0 4-.85"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/><line x1="3" y1="3" x2="21" y2="21"/>'
};
NS.icon = function(name, attrs){
  var body = ICONS[name]; if(!body) return '';
  return P.replace('<svg ', '<svg '+(attrs?attrs+' ':'')) + body + '</svg>';
};

/* ---- shared app-shell (identical header across app pages) ---- */
NS.appbar = function(opts){
  opts = opts||{};
  var nav='';
  if(opts.nav && opts.nav.length){
    nav='<nav class="appnav">'+opts.nav.map(function(n){
      return '<a href="'+n.href+'"'+(n.on?' class="on"':'')+'>'+NS.icon(n.icon)+'<span>'+NS.esc(n.label)+'</span></a>';
    }).join('')+'</nav>';
  }
  return '<header class="appbar"><div class="appbar__in">'+
    '<a class="brand" href="/"><img src="/logo.png" alt="حضانة مونتيسوري"/>'+
      '<span>حضانة مونتيسوري'+(opts.sub?'<small class="b-sub">'+NS.esc(opts.sub)+'</small>':'')+'</span></a>'+
    '<div class="spacer"></div>'+ nav + (opts.right||'') +
    '<button class="btn icon-btn" id="ns-logout" aria-label="تسجيل الخروج">'+NS.icon('logout')+'</button>'+
  '</div></header>';
};
/* admin nav (dashboard / roles / manage) — token persists in localStorage, so plain paths */
NS.adminNav = function(active){
  return [
    {href:'/dashboard/', label:'الرئيسية', icon:'chart',  on:active==='dashboard'},
    {href:'/students/',  label:'الطلاب',   icon:'user',   on:active==='students'},
    {href:'/classes/',   label:'الفصول',   icon:'book',   on:active==='classes'},
    {href:'/salaries/',  label:'المرتبات', icon:'wallet', on:active==='salaries'},
    {href:'/accounts/',  label:'الحسابات', icon:'ledger', on:active==='accounts'},
    {href:'/albums/',    label:'الألبومات',icon:'camera', on:active==='albums'},
    {href:'/cameras/',   label:'الكاميرات',icon:'video',  on:active==='cameras'},
    {href:'/roles/',     label:'الأدوار',  icon:'users',  on:active==='roles'},
    {href:'/manage/',    label:'الطلبات',  icon:'bell',   on:active==='manage'}
  ];
};
NS.wireLogout = function(kind){
  var b=document.getElementById('ns-logout'); if(!b) return;
  b.addEventListener('click',function(){
    NS.confirm({title:'تسجيل الخروج؟',body:'ستحتاج لتسجيل الدخول من جديد.',okText:'خروج',danger:true})
      .then(function(ok){ if(ok){ NS.clearToken(kind); location.href='/login/'; } });
  });
};

/* auto-init reveal on DOM ready */
if(document.readyState!=='loading') NS.reveal();
else document.addEventListener('DOMContentLoaded', NS.reveal);
})();
