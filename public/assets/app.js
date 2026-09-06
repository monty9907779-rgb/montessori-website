/* ============================================================================
   Kawkab Al-Tifl Al-Hurr Kindergarten — shared runtime (app.js) · v1
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
  var url = (path.charAt(0)==='/' ? NS.SITE + path : path);
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
/* ---- حاسبة أيام التغطية (الشهر المتفق عليه = 30 يوماً) ----
   مصدر واحد لكل التابات: الطلاب، الحسابات، الذمم، وصفحة وليّ الأمر. */
NS.DAY_BASIS = 30;
/* تغطية الدفعة = [شهور كاملة, أيام إضافية] — مطابق للسيرفر.
   الشهور تتحرّك تقويمياً (٤ سبتمبر + ٣ شهور = ٤ ديسمبر)، والباقي فقط يتحوّل
   لأيام بقاسم 30 (شهر + ١٠٠ ر.س من ألف = شهر و٣ أيام). */
NS.coverageFor = function(amount, monthlyFee){
  var a=parseFloat(amount)||0, f=parseFloat(monthlyFee)||0;
  if(a<=0) return [0,0];
  if(f<=0) return [1,0];
  var months=Math.floor(a/f), rem=a-months*f;
  var days=Math.round(rem/f*NS.DAY_BASIS);
  if(days>=NS.DAY_BASIS){ months++; days=0; }
  return [months,days];
};
/* أيام التغطية التقريبية — للعرض المختصر فقط */
NS.daysForAmount = function(amount, monthlyFee){
  var a=parseFloat(amount)||0, f=parseFloat(monthlyFee)||0;
  if(a<=0) return 0;
  if(f<=0) return NS.DAY_BASIS;
  return Math.round(a/f*NS.DAY_BASIS);
};
NS.addDaysISO = function(iso, n){
  if(!iso) return '';
  var d=new Date(String(iso).replace(' ','T')); if(isNaN(d)) return '';
  d.setDate(d.getDate()+(n||0));
  return NS.isoOf(d);
};
NS.isoOf = function(d){
  return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
};
/* + شهور تقويمية بنفس اليوم، مع تثبيت آخر الشهر (31 يناير + شهر = 28 فبراير) */
NS.addMonthsISO = function(iso, n){
  if(!iso) return '';
  var p=String(iso).slice(0,10).split('-'), y=+p[0], m=+p[1]-1+(n||0), d=+p[2];
  y += Math.floor(m/12); m=((m%12)+12)%12;
  var last=new Date(y, m+1, 0).getDate(); if(d>last) d=last;
  return y+'-'+String(m+1).padStart(2,'0')+'-'+String(d).padStart(2,'0');
};
/* الاستحقاق الجديد بعد دفعة بمبلغ amount ابتداءً من anchorISO */
NS.dueAfterPay = function(amount, monthlyFee, anchorISO){
  if(!anchorISO) return '';
  var c=NS.coverageFor(amount, monthlyFee);
  return NS.addDaysISO(NS.addMonthsISO(anchorISO, c[0]), c[1]);
};
/* وصف التغطية بالعربي: «٣ شهور» · «شهر و٣ أيام» · «١٤ يوم» */
NS.coverageLabel = function(amount, monthlyFee){
  var c=NS.coverageFor(amount, monthlyFee), m=c[0], d=c[1];
  if(!m && !d) return '—';
  var parts=[];
  if(m===1) parts.push('شهر');
  else if(m===2) parts.push('شهران');
  else if(m>=3 && m<=10) parts.push(m+' شهور');
  else if(m>10) parts.push(m+' شهراً');
  if(d===1) parts.push('يوم');
  else if(d===2) parts.push('يومان');
  else if(d>=3 && d<=10) parts.push(d+' أيام');
  else if(d>10) parts.push(d+' يوماً');
  return parts.join(' و');
};
/* بطاقة نتيجة الحسبة: التغطية + الاستحقاق الجديد */
NS.payCalc = function(amount, monthlyFee, anchorISO){
  var c=NS.coverageFor(amount, monthlyFee), m=c[0], d=c[1];
  if(!m && !d) return '<div class="paycalc__d">—</div><div class="paycalc__l">التغطية</div>';
  var due=NS.dueAfterPay(amount, monthlyFee, anchorISO);
  return '<div class="paycalc__d">'+NS.coverageLabel(amount, monthlyFee)+'</div>'+
    '<div class="paycalc__l">التغطية (الشهر = '+NS.DAY_BASIS+' يوم)</div>'+
    (due?('<div class="paycalc__due">تاريخ الاستحقاق التالي<b>'+NS.fmtDate(due)+'</b></div>'):'');
};
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
     '<img class="logo" src="/logo.png" alt="روضة كوكب الطفل الحر"/>'+
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

(function(){
  var css = ''+
'html.ns-admin-shell body{padding-inline-start:0}'+
'html.ns-admin-shell .appbar{position:sticky;top:0;z-index:80;background:rgba(251,248,242,.96);border-bottom:1px solid var(--line);box-shadow:0 2px 12px rgba(31,54,42,.06);backdrop-filter:saturate(1.4) blur(14px);-webkit-backdrop-filter:saturate(1.4) blur(14px)}'+
'html.ns-admin-shell .appbar__in{max-width:var(--maxw);margin-inline:auto;padding:11px clamp(14px,3vw,26px);display:flex;flex-direction:row;align-items:center;gap:14px}'+
'html.ns-admin-shell .brand{justify-content:flex-start;color:var(--forest);text-align:start;padding:0;border-bottom:0}'+
'html.ns-admin-shell .brand img{width:40px;height:40px;border-radius:11px;background:#fff;padding:3px;box-shadow:var(--sh-1)}'+
'html.ns-admin-shell .brand span{white-space:nowrap;line-height:1.25;font-size:inherit}'+
'html.ns-admin-shell .brand .b-sub{display:block;color:var(--muted);font-size:.72rem;margin-top:-2px}'+
'html.ns-admin-shell .spacer{display:block;flex:1}'+
'html.ns-admin-shell .navtoggle{display:inline-flex;align-items:center;justify-content:center;width:42px;height:42px;flex:none;border:0;border-radius:14px;background:var(--sand);color:var(--forest);cursor:pointer}'+
'html.ns-admin-shell .appnav{position:fixed;top:0;right:0;bottom:0;left:auto;width:min(340px,86vw);height:100dvh;max-height:100dvh;display:flex;flex-direction:column;flex-wrap:nowrap;gap:6px;overflow-y:auto;overflow-x:hidden;border-radius:0;padding:14px;background:var(--paper);box-shadow:-8px 0 28px rgba(0,0,0,.18);transform:translateX(100%);transition:transform var(--dur);z-index:120;scrollbar-width:thin;overscroll-behavior:contain;padding-top:max(14px,env(safe-area-inset-top));padding-bottom:max(14px,env(safe-area-inset-bottom))}'+
'html.ns-admin-shell .navscrim{position:fixed;inset:0;background:transparent;opacity:0;pointer-events:none;transition:opacity var(--dur);z-index:70}'+
'html.ns-admin-shell .navscrim.on{opacity:1;pointer-events:auto}'+
'html.ns-admin-shell body.nav-open .appnav{transform:none}'+
'html.ns-admin-shell .navclose{display:flex;align-items:center;justify-content:center;width:42px;height:42px;min-height:42px;margin-inline-start:auto;margin-bottom:8px;border:0;border-radius:14px;background:var(--sand);color:var(--forest);cursor:pointer;flex:none}'+
'html.ns-admin-shell .navclose svg{width:22px;height:22px}'+
'html.ns-admin-shell .appnav a{width:100%;min-height:48px;display:flex;align-items:center;justify-content:flex-start;gap:12px;padding:12px 14px;border-radius:14px;color:var(--muted);font-size:.98rem;font-weight:700;white-space:normal;text-align:start;line-height:1.35;flex:none}'+
'html.ns-admin-shell .appnav a svg{width:22px;height:22px;flex:none}'+
'html.ns-admin-shell .appnav a.on{background:var(--sand);color:var(--forest);box-shadow:none;position:relative}'+
'html.ns-admin-shell .appnav a.on:before{content:"";position:absolute;top:10px;bottom:10px;right:0;width:4px;border-radius:999px;background:var(--clay)}'+
'html.ns-admin-shell .appnav a.on svg{color:var(--clay)}'+
'html.ns-admin-shell .appnav a:not(.on):hover{background:var(--sand);color:var(--forest)}'+
'html.ns-admin-shell #ns-logout{margin-top:0;align-self:auto;width:42px;height:42px;border-radius:14px}'+
'html.ns-admin-shell body.nav-open .appbar{backdrop-filter:none;-webkit-backdrop-filter:none}'+
'@media(max-width:640px){html.ns-admin-shell .appbar__in{padding:9px 12px;gap:10px}html.ns-admin-shell .brand span{font-size:.9rem}html.ns-admin-shell .brand .b-sub{display:none}html.ns-admin-shell #ns-logout{width:40px;height:40px}html.ns-admin-shell .appnav{width:min(320px,88vw)}}';
  function inject(){
    if(document.getElementById('ns-vertical-admin-nav-style')) return;
    var s=document.createElement('style');
    s.id='ns-vertical-admin-nav-style';
    s.textContent=css;
    document.head.appendChild(s);
  }
  if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded', inject); }
  else inject();
})();

/* ---- shared app-shell (identical header across app pages) ---- */
NS.appbar = function(opts){
  opts = opts||{};
  try{ document.documentElement.classList.toggle('ns-admin-shell', !!(opts.nav && opts.nav.length)); }catch(e){}
  var nav='';
  if(opts.nav && opts.nav.length){
    nav='<nav class="appnav" id="ns-appnav">'+
      '<button class="navclose" id="ns-navclose" aria-label="إغلاق القائمة">'+NS.icon('close')+'</button>'+
      opts.nav.map(function(n){
      return '<a href="'+n.href+'"'+(n.on?' class="on"':'')+(n.ext?' target="_blank" rel="noopener"':'')+(n.sso?' data-crm-sso="1"':'')+(n.owner?' data-owner="1"':'')+(n.ssoApi?' data-sso-api="'+n.ssoApi+'"':'')+'>'+NS.icon(n.icon)+'<span>'+NS.esc(n.label)+'</span></a>';
    }).join('')+'</nav>';
  }
  var toggle = (opts.nav && opts.nav.length)
    ? '<button class="navtoggle" id="ns-navtoggle" aria-label="القائمة" aria-expanded="false" aria-controls="ns-appnav">'+
      NS.icon('menu')+'</button>'
    : '';
  return '<header class="appbar"><div class="appbar__in">'+ toggle +
    '<a class="brand" href="/"><img src="/logo.png" alt="روضة كوكب الطفل الحر"/>'+
      '<span>روضة كوكب الطفل الحر'+(opts.sub?'<small class="b-sub">'+NS.esc(opts.sub)+'</small>':'')+'</span></a>'+
    '<div class="spacer"></div>'+ nav + (opts.right||'') +
    '<button class="btn icon-btn" id="ns-logout" aria-label="تسجيل الخروج">'+NS.icon('logout')+'</button>'+
  '</div></header>';
};
/* admin nav (dashboard / roles / manage) — token persists in localStorage, so plain paths */
NS._isOwner = (function(){ try{ var v=localStorage.getItem('ns_is_owner'); return v===null ? true : v==='1'; }catch(e){ return true; } })();
NS._navHidden = (function(){ try{ return JSON.parse(localStorage.getItem('ns_nav_hidden')||'[]')||[]; }catch(e){ return []; } })();
NS.adminNav = function(active){
  return [
    {href:'/dashboard/', label:'الرئيسية', icon:'home',   on:active==='dashboard'},
    {href:'/students/',  label:'الطلاب',   icon:'user',   on:active==='students'},
    {href:'/enrollments/', label:'طلبات السنة الجديدة', icon:'calendar', on:active==='enrollments'},
    {href:'/classes/',   label:'الفصول',   icon:'book',   on:active==='classes'},
    {href:'/books/',     label:'الكتب',    icon:'ledger', on:active==='books'},
    {href:'/salaries/',  label:'المرتبات', icon:'wallet', on:active==='salaries'},
    {href:'/accounts/',  label:'الحسابات', icon:'ledger', on:active==='accounts'},
    {href:'/albums/',    label:'الألبومات',icon:'camera', on:active==='albums'},
    {href:'/cameras/',   label:'الكاميرات',icon:'video',  on:active==='cameras'},
    {href:'/roles/',     label:'الأدوار',  icon:'users',  on:active==='roles'},
    {href:'/permissions/', label:'الصلاحيات', icon:'shield', on:active==='permissions'},
    {href:'/manage/',    label:'الطلبات',  icon:'bell',   on:active==='manage'},
    {href:'/visits/',    label:'مواعيد الزيارات', icon:'calendar', on:active==='visits'},
    {href:'/funnel/',    label:'قمع المبيعات', icon:'users',  on:active==='funnel'},
    {href:'/social/',    label:'ردود السوشيال ميديا', icon:'chat', on:active==='social'},
    {href:'/mail/',       label:'بريد الفريق', icon:'chat', on:active==='mail', owner:true},
    {href:'/google/',     label:'منتجات جوجل', icon:'chart', on:active==='google', owner:true},
    {href:'/meta/',       label:'منتجات ميتا', icon:'chat', on:active==='meta', owner:true},
    {href:'/security/',   label:'الحماية', icon:'shield', on:active==='security', owner:true},
    {href:'/server/',     label:'حالة السيرفر', icon:'wifi', on:active==='server', owner:true},
    {href:'https://crm.montessori-ksa.com/', label:'الرسائل', icon:'chat', ext:true, sso:true}
  ].filter(function(n){ if(n.owner && !NS._isOwner) return false; return NS._navHidden.indexOf(n.href.replace(/\//g,''))<0; });
};
/* المديرة: نخفي بنود القائمة اللي الأونر قفلها. الأونر = لا شيء مخفي. */
NS.refreshNav = function(){
  var mt=null; try{ mt=localStorage.getItem('nursery_mt'); }catch(e){}
  if(!mt || !NS.api) return;
  NS.api('/api/perms/nav',{mt:mt}).then(function(r){
    if(!r || !r.ok) return;
    var h=r.hidden||[];
    try{ localStorage.setItem('ns_nav_hidden', JSON.stringify(h)); }catch(e){}
    NS._navHidden=h;
    var nav=document.querySelector('.appnav');
    if(nav){ nav.querySelectorAll('a').forEach(function(a){
      var key=(a.getAttribute('href')||'').replace(/\//g,'');
      a.style.display = h.indexOf(key)>=0 ? 'none' : '';
    }); }
    var isOwner = (r.is_stats !== undefined) ? !!r.is_stats : !!r.is_owner;
    try{ localStorage.setItem('ns_is_owner', isOwner?'1':'0'); }catch(e){}
    NS._isOwner = isOwner;
    document.querySelectorAll('[data-owner]').forEach(function(el){ el.style.display = isOwner ? '' : 'none'; });
  }).catch(function(){});
};
/* ---- درج القائمة على الموبايل ----
   بـ21 تاب كانت القائمة بتاكل 620px من 812px على الموبايل — المحتوى كله
   تحت الطيّة. بقت درج بزرار، وعلى الشاشات الكبيرة صف واحد بيتمرّر أفقياً.

   بنستخدم تفويض الأحداث على document عمداً: كل صفحة بتحقن الهيدر بنفسها
   وفي توقيت مختلف، فأي محاولة نمسك العناصر وقت التحميل بتفشل أحياناً. */
(function(){
  function nav(){ return document.getElementById('ns-appnav'); }
  function isDrawer(){ return window.matchMedia('(max-width:640px)').matches; }
  function scrim(make){
    var s = document.querySelector('.navscrim');
    if(!s && make){
      s = document.createElement('div');
      s.className = 'navscrim';
      document.body.appendChild(s);
    }
    return s;
  }
  function close(){
    var n = nav(); if(n) n.classList.remove('open');
    document.body.classList.remove('nav-open');
    var s = scrim(false); if(s) s.classList.remove('on');
    var b = document.getElementById('ns-navtoggle');
    if(b) b.setAttribute('aria-expanded','false');
    document.body.style.overflow='';
  }
  function open(){
    var n = nav(); if(n) n.classList.add('open');
    document.body.classList.add('nav-open');
    scrim(true).classList.add('on');
    var b = document.getElementById('ns-navtoggle');
    if(b) b.setAttribute('aria-expanded','true');
    document.body.style.overflow='hidden';
  }
  NS.closeNav = close;

  document.addEventListener('click', function(e){
    if(e.target.closest && e.target.closest('#ns-navclose')){
      e.preventDefault(); e.stopPropagation(); close(); return;
    }
    if(e.target.closest && e.target.closest('#ns-navtoggle')){
      e.preventDefault(); e.stopPropagation();
      var n = nav();
      if(document.body.classList.contains('nav-open')) close(); else open();
      return;
    }
    if(e.target.closest && e.target.closest('.navscrim')){ close(); return; }
    // الضغط على بند بينقل الصفحة — نقفل الدرج برضه
    if(e.target.closest && e.target.closest('.appnav a')) close();
  });

  document.addEventListener('keydown', function(e){
    var n = nav();
    if(e.key==='Escape' && document.body.classList.contains('nav-open')) close();
  });
  window.addEventListener('resize', function(){
    var n = nav();
    if(!isDrawer() && document.body.classList.contains('nav-open')) close();
  });

  /* الصف الأفقي: نودّي التاب النشط للمنظر عشان ما يفضلش مخفي في آخر التمرير.
     بنستنّى شوية لأن الهيدر بيتحقن بعد التحميل. */
  function centerActive(){
    var n = nav(); if(!n || isDrawer()) return;
    var on = n.querySelector('a.on');
    if(on){ try{ on.scrollIntoView({block:'nearest', inline:'center'}); }catch(e){} }
  }
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', function(){ setTimeout(centerActive,60); });
  }else{ setTimeout(centerActive,60); }
})();

/* شاشات الخطأ كانت بتمسح الهيدر والقائمة، فأول ما الشبكة تتعثّر تفضل حابس
   في صفحة فيها زرار «إعادة المحاولة» بس. الدالة دي بترجّع الهيدر الموجود،
   ولو الخطأ حصل قبل ما يترسم أصلاً بتبنيه من المسار. */
NS.ensureShell = function(app){
  var bar = app.querySelector('.appbar');
  if(bar) return bar;
  var key = (location.pathname.split('/').filter(Boolean)[0] || '');
  var box = document.createElement('div');
  box.innerHTML = NS.appbar({ nav: NS.adminNav(key) });
  return box.firstChild;
};

NS.wireLogout = function(kind){
  var b=document.getElementById('ns-logout'); if(!b) return;
  b.addEventListener('click',function(){
    NS.confirm({title:'تسجيل الخروج؟',body:'ستحتاج لتسجيل الدخول من جديد.',okText:'خروج',danger:true})
      .then(function(ok){ if(ok){ NS.clearToken(kind); location.href='/login/'; } });
  });
};

/* ---- 🔔 جرس التنبيهات الموحّد: عدّاد لكل ما يهم المدير/الأونر (يظهر فقط مع توكن mt صالح) ---- */
NS.notifBell = function(){
  return;

  var mt=null; try{ mt=localStorage.getItem('nursery_mt'); }catch(e){}
  if(!mt || document.getElementById('ns-bell')) return;
  // يظهر فقط في صفحات الإدارة — لا يظهر إطلاقاً على الصفحات العامة أو المدوّنة
  // (حتى لو كانت المديرة مسجّلة دخول ومارّة على الموقع العام)
  /* كل تابات الإدارة — لازم تفضل متطابقة مع NS.adminNav.
     كانت 11 مسار بس، فالجرس كان بيختفي في السيرفر والحماية وجوجل وميتا
     والسوشيال والزيارات والقمع والبريد. */
  if(!/^\/(dashboard|students|enrollments|classes|books|salaries|accounts|albums|cameras|roles|permissions|manage|visits|funnel|social|mail|google|meta|security|server)(\/|$)/.test(location.pathname)) return;
  var css=document.createElement('style');
  css.textContent='#ns-bell{position:fixed;bottom:18px;left:18px;z-index:9000;width:52px;height:52px;border-radius:50%;'+
    'border:0;background:var(--forest,#184e3e);color:#fff;box-shadow:0 4px 16px rgba(0,0,0,.25);cursor:pointer;'+
    'display:flex;align-items:center;justify-content:center}'+
    '#ns-bell svg{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}'+
    '#ns-bell .cnt{position:absolute;top:-4px;right:-4px;min-width:21px;height:21px;border-radius:999px;background:#dc2626;'+
    'color:#fff;font-size:.72rem;font-weight:800;display:flex;align-items:center;justify-content:center;padding:0 5px;font-family:inherit}'+
    '#ns-bell.zero .cnt{display:none}'+
    '#ns-notif-panel{position:fixed;bottom:80px;left:18px;z-index:9001;width:min(340px,calc(100vw - 36px));max-height:60vh;overflow:auto;'+
    'background:#fff;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,.28);padding:10px;direction:rtl}'+
    '#ns-notif-panel .nrow{display:flex;align-items:flex-start;gap:10px;padding:11px 10px;border-radius:12px;cursor:pointer;text-decoration:none;color:inherit}'+
    '#ns-notif-panel .nrow:hover{background:rgba(0,0,0,.05)}'+
    '#ns-notif-panel .ncnt{flex:none;min-width:26px;height:26px;border-radius:999px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.8rem;color:#fff}'+
    '#ns-notif-panel .t-danger{background:#dc2626}#ns-notif-panel .t-warn{background:#b45309}#ns-notif-panel .t-info{background:#184e3e}'+
    '#ns-notif-panel .nlbl{font-weight:700;font-size:.9rem}#ns-notif-panel .nnames{font-size:.76rem;color:#777;margin-top:2px;line-height:1.5}'+
    '#ns-notif-panel .nempty{padding:18px;text-align:center;color:#777;font-size:.9rem}';
  document.head.appendChild(css);
  var b=document.createElement('button');
  b.id='ns-bell'; b.className='zero'; b.title='التنبيهات';
  b.innerHTML=NS.icon('bell')+'<span class="cnt">0</span>';
  document.body.appendChild(b);
  var items=[], total=0;
  function refresh(){
    NS.api('/api/manager/notifications',{mt:mt}).then(function(d){
      if(!d||!d.ok) return;
      items=d.items||[]; total=d.total||0;
      b.querySelector('.cnt').textContent=total>99?'99+':total;
      b.classList.toggle('zero', !total);
    }).catch(function(err){ if(err&&err.type==='auth'){ b.remove(); var p=document.getElementById('ns-notif-panel'); if(p)p.remove(); } });
  }
  function closePanel(){ var p=document.getElementById('ns-notif-panel'); if(p) p.remove(); }
  b.addEventListener('click',function(e){
    e.stopPropagation();
    if(document.getElementById('ns-notif-panel')){ closePanel(); return; }
    var p=document.createElement('div'); p.id='ns-notif-panel';
    if(!items.length){ p.innerHTML='<div class="nempty">لا توجد تنبيهات — كل شيء تمام ✓</div>'; }
    else{
      p.innerHTML=items.map(function(it){
        var names=(it.names&&it.names.length)?('<div class="nnames">'+it.names.map(NS.esc).join('، ')+(it.count>it.names.length?' …':'')+'</div>'):'';
        return '<a class="nrow" href="'+NS.attr(it.url)+'"><span class="ncnt t-'+NS.attr(it.tone||'info')+'">'+it.count+'</span>'+
          '<span><div class="nlbl">'+NS.esc(it.label)+'</div>'+names+'</span></a>';
      }).join('');
    }
    p.addEventListener('click',function(ev){ ev.stopPropagation(); });
    document.body.appendChild(p);
    setTimeout(function(){ document.addEventListener('click', closePanel, {once:true}); },0);
  });
  refresh(); setInterval(refresh, 180000);
};

/* auto-init reveal immediately; push non-critical refresh work to idle */
/* التطبيق المثبَّت (PWA standalone) لا يملك تبويبات يفتح فيها نافذة جديدة —
   window.open() فيه يرجع فارغاً بصمت فلا يحدث شيء عند الضغط. في هذا الوضع
   ننتقل بنفس الصفحة بدل محاولة فتح تبويب. */
NS.isStandalone = function(){
  try{ return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true; }
  catch(e){ return false; }
};
/* ---- دخول تلقائي للـCRM بدون كلمة سر: اعتراض زرار «الرسائل» → رابط دخول لحظي ---- */
NS.wireCrmSso = function(){
  if(NS._crmSsoWired) return; NS._crmSsoWired=true;
  document.addEventListener('click', function(ev){
    var st = ev.target && ev.target.closest ? ev.target.closest('a[data-sso-api]') : null;
    if(st){
      ev.preventDefault();
      var mts=null; try{ mts=localStorage.getItem('nursery_mt'); }catch(e){}
      var fb = st.getAttribute('href') || '/';
      if(!mts){ if(NS.isStandalone()) location.href=fb; else window.open(fb,'_blank','noopener'); return; }
      var standalone = NS.isStandalone();
      var ws = standalone ? null : window.open('about:blank','_blank');
      st.style.opacity='.5';
      NS.api(st.getAttribute('data-sso-api'),{mt:mts}).then(function(r){
        st.style.opacity='';
        var dest=(r && r.ok && r.url) ? r.url : fb;
        if(standalone) location.href=dest;
        else if(ws) ws.location.href=dest; else window.open(dest,'_blank','noopener');
      }).catch(function(){
        st.style.opacity='';
        if(standalone) location.href=fb;
        else if(ws) ws.location.href=fb; else window.open(fb,'_blank','noopener');
      });
      return;
    }
    var a = ev.target && ev.target.closest ? ev.target.closest('a[data-crm-sso]') : null;
    if(!a) return;
    ev.preventDefault();
    var mt=null; try{ mt=localStorage.getItem('nursery_mt'); }catch(e){}
    var fallback = a.getAttribute('href') || 'https://crm.montessori-ksa.com/';
    var standalone2 = NS.isStandalone();
    if(!mt){ if(standalone2) location.href=fallback; else window.open(fallback,'_blank','noopener'); return; }
    // نفتح نافذة فوراً (قبل الـawait) حتى لا يحجبها المتصفح، ثم نوجّهها للرابط اللحظي
    // — إلا في التطبيق المثبَّت (standalone): لا تبويبات هناك، فننتقل بنفس الصفحة
    var w = standalone2 ? null : window.open('about:blank','_blank');
    a.style.opacity='.5';
    NS.api('/api/manager/crm_sso',{mt:mt}).then(function(r){
      a.style.opacity='';
      var dest2=(r && r.ok && r.url) ? r.url : fallback;
      if(standalone2) location.href=dest2;
      else if(r && r.ok && r.url){ if(w) w.location.href=r.url; else window.open(r.url,'_blank','noopener'); }
      else { if(w) w.location.href=fallback; else window.open(fallback,'_blank','noopener'); NS.toast((r&&r.error)||'يُفتح تسجيل الدخول العادي','err'); }
    }, function(){ a.style.opacity=''; if(standalone2) location.href=fallback; else if(w) w.location.href=fallback; else window.open(fallback,'_blank','noopener'); });
  }, false);
};

function lateInit(){
  var run=function(){ NS.refreshNav(); NS.notifBell(); NS.wireCrmSso(); };
  if('requestIdleCallback' in window) requestIdleCallback(run,{timeout:2000});
  else setTimeout(run,0);
}
if(document.readyState!=='loading'){ NS.reveal(); lateInit(); }
else document.addEventListener('DOMContentLoaded', function(){ NS.reveal(); lateInit(); });
})();
