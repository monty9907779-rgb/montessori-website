(function(){
  var I=NS.icon;
  /* ---------- ثنائي اللغة ---------- */
  var LG={
    ar:{title:'تسجيل الدخول',sub:'اختر طريقة الدخول المناسبة لك.',brand:'روضة كوكب الطفل الحر',
        brandp:'بوابةٌ واحدة للأهالي والفريق — ندخلك تلقائياً لصفحتك المناسبة.',
        p1:'للأهالي: حضور طفلك ورسومه وصوره',p2:'للمعلّمات: الحضور والراتب والفصول',p3:'للإدارة: لوحة تحكم كاملة',
        google:'الدخول عبر Google',div:'أو بالبريد وكلمة المرور',lem:'البريد الإلكتروني',lpw:'كلمة المرور',
        btn:'دخول',reg:'جديد؟ سجّل طفلك الآن',sw:'تغيير حساب Google / دخول بإيميل آخر',
        assure:'دخولٌ آمن — بياناتك محمية',toggle:'English',
        eEmpty:'اكتب البريد وكلمة المرور',eBad:'بيانات الدخول غير صحيحة',eNet:'تعذّر الاتصال، حاول مجدداً',
        dir:'rtl',lang:'ar',regHref:'/#register'},
    en:{title:'Sign in',sub:'Choose how you want to sign in.',brand:'Kawkab Al-Tifl Al-Hurr Kindergarten',
        brandp:'One gateway for parents and staff — we route you to your page automatically.',
        p1:'Parents: attendance, fees & photos',p2:'Teachers: attendance, salary & classes',p3:'Management: full dashboard',
        google:'Sign in with Google',div:'or with email & password',lem:'Email',lpw:'Password',
        btn:'Sign in',reg:'New? Register your child',sw:'Switch Google account / another email',
        assure:'Secure sign-in — your data is protected',toggle:'عربي',
        eEmpty:'Enter your email and password',eBad:'Incorrect email or password',eNet:'Connection failed, try again',
        dir:'ltr',lang:'en',regHref:'/en/#register'}
  };
  var cur='ar';
  try{ var sv=localStorage.getItem('ns.lang'); if(sv==='en') cur='en'; }catch(e){}
  function T(){ return LG[cur]; }
  function setTxt(id,v){ var el=document.getElementById(id); if(el) el.textContent=v; }
  function applyLang(){
    var t=T();
    document.documentElement.lang=t.lang; document.documentElement.dir=t.dir;
    document.title = cur==='en' ? 'Login | Kawkab Al-Tifl Al-Hurr Kindergarten' : 'الدخول | روضة كوكب الطفل الحر';
    setTxt('t-title',t.title); setTxt('t-sub',t.sub); setTxt('t-brand',t.brand); setTxt('t-brandp',t.brandp);
    setTxt('t-div',t.div); setTxt('t-lem',t.lem); setTxt('t-lpw',t.lpw); setTxt('lang-btn',t.toggle);
    document.getElementById('gb').innerHTML=I('google')+' <span>'+t.google+'</span>';
    document.getElementById('p1').innerHTML=I('user')+' '+t.p1;
    document.getElementById('p2').innerHTML=I('users')+' '+t.p2;
    document.getElementById('p3').innerHTML=I('chart')+' '+t.p3;
    document.getElementById('login-btn').innerHTML=I('logout')+' '+t.btn;
    var rg=document.getElementById('reg'); rg.innerHTML=I('plus')+' '+t.reg; rg.href=t.regHref;
    document.getElementById('switch').innerHTML=I('refresh')+' '+t.sw;
    document.getElementById('assure').innerHTML=I('shield')+' <span>'+t.assure+'</span>';
  }
  applyLang();
  document.getElementById('lang-btn').addEventListener('click',function(){
    cur = cur==='ar' ? 'en' : 'ar';
    try{ localStorage.setItem('ns.lang',cur); }catch(e){}
    applyLang();
  });

  var g=document.getElementById('google-btn');
  g.addEventListener('click',function(e){ e.preventDefault(); g.classList.add('is-loading'); location.href=NS.LOGIN; });
  document.getElementById('switch').addEventListener('click',function(e){ e.preventDefault(); location.href=NS.SWITCH; });

  var form=document.getElementById('login-form'), btn=document.getElementById('login-btn'), msg=document.getElementById('login-msg');
  form.addEventListener('submit',function(ev){
    if(btn.classList.contains('is-loading')) return;
    ev.preventDefault();
    var email=form.email.value.trim(), pass=form.password.value;
    if(!email||!pass){ msg.textContent=T().eEmpty; return; }
    msg.textContent=''; btn.classList.add('is-loading');
    NS.api('/api/login',{email:email,password:pass}).then(function(d){
      if(d&&d.ok&&d.redirect){ location.href=d.redirect; }
      else { btn.classList.remove('is-loading'); msg.textContent=(d&&d.error)||T().eBad; }
    }).catch(function(err){
      btn.classList.remove('is-loading');
      msg.textContent = err&&err.type==='net' ? T().eNet : T().eBad;
    });
  });

  if("serviceWorker" in navigator){
    navigator.serviceWorker.register("/sw.js").catch(function(){});
  }
})();
