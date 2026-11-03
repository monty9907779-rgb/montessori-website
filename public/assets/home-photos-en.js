(function(){
  var I = NS.icon;
  NS._setIc=function(id,html){var e=document.getElementById(id); if(e) e.innerHTML=html;};
  function whenIdle(fn){
    var done=false;
    function run(){ if(done) return; done=true; fn(); }
    if(document.readyState==='complete'){
      if('requestIdleCallback' in window) requestIdleCallback(run,{timeout:2500});
      else setTimeout(run,1200);
      return;
    }
    window.addEventListener('load',function(){
      if('requestIdleCallback' in window) requestIdleCallback(run,{timeout:2500});
      else setTimeout(run,1200);
    },{once:true});
  }
  // ---- inject icons ----
  document.getElementById('burger').innerHTML = I('menu');
  document.getElementById('drawer-close').innerHTML = I('close');
  document.getElementById('totop').innerHTML = I('arrowUp');
  var strip=[['shield','Safe, trusted environment'],['home','Carefully prepared environment'],['users','Qualified teachers'],['heart','Loving, safe care']];
  strip.forEach(function(s,i){ NS._setIc('strip-'+(i+1), I(s[0])+'<span>'+s[1]+'</span>'); });
  ['home','star','user','clock'].forEach(function(n,i){ NS._setIc('pr-'+(i+1), I(n)); });
  ['shield','leaf','sparkle','check','book','chat'].forEach(function(n,i){ NS._setIc('pi-'+(i+1), I(n)); });
  ['sun','chat','sparkle','heart','star','users'].forEach(function(n,i){ NS._setIc('d-'+(i+1), I(n)); });
  ['sparkle','book','sun'].forEach(function(n,i){ NS._setIc('pg-'+(i+2), I(n)); });
  ['whatsapp','pin','clock','chat'].forEach(function(n,i){ NS._setIc('c-'+(i+1), I(n)); });
  NS._setIc('f-ig', I('camera'));
  NS._setIc('f-fb', I('users'));
  NS._setIc('f-wa', I('whatsapp'));
  function initReviews(){
    var badge=document.getElementById('g-rating'), grid=document.getElementById('reviews-grid'), sec=document.getElementById('reviews-sec');
    if(!badge||!grid||!sec) return;
    function stars(){ var h=''; for(var i=0;i<5;i++) h+=I('star'); return h; }
    fetch('/assets/reviews.json').then(function(r){ return r.json(); }).then(function(d){
      // all reviews are shown as published (no rating filter)
      if(!d||!d.reviews||!d.reviews.length){ sec.style.display='none'; return; }
      badge.innerHTML=
        '<div class="g-score">'+NS.esc(String(d.rating||''))+'</div>'+
        '<div class="g-mid"><div class="g-stars" role="img" aria-label="'+NS.attr(d.rating)+' out of 5">'+stars()+'</div>'+
        '<div class="g-sub">'+I('google','class="gmark"')+' '+NS.esc(String(d.count||''))+' Google reviews</div></div>'+
        '<a class="btn btn--ghost btn--sm" href="'+NS.attr(d.url||'#')+'" target="_blank" rel="noopener">'+I('star')+' Read all</a>';
      grid.innerHTML=d.reviews.map(function(rv){
        var initial=(rv.name||'?').trim().charAt(0);
        return '<div class="quote rev in"><div class="q-top">'+
          '<div class="stars" role="img" aria-label="'+NS.attr(rv.rating||5)+' stars">'+stars()+'</div>'+
          I('google','class="gmark"')+'</div>'+
          '<p>'+NS.esc(rv.text)+'</p>'+
          '<div class="who"><span class="avatar">'+NS.esc(initial)+'</span>'+
          '<div><b>'+NS.esc(rv.name)+'</b><span>'+NS.esc(rv.when)+' · Google review</span></div></div></div>';
      }).join('');
    }).catch(function(){ sec.style.display='none'; });
  }

  // ---- drawer ----
  var drawer=document.getElementById('drawer'), burger=document.getElementById('burger'),
      drawerClose=document.getElementById('drawer-close');
  function openD(){ drawer.classList.add('open'); document.body.style.overflow='hidden'; burger.setAttribute('aria-expanded','true'); drawerClose.focus(); }
  function closeD(){ drawer.classList.remove('open'); document.body.style.overflow=''; burger.setAttribute('aria-expanded','false'); burger.focus(); }
  burger.addEventListener('click',openD);
  drawerClose.addEventListener('click',closeD);
  drawer.querySelectorAll('[data-close]').forEach(function(a){ a.addEventListener('click',closeD); });
  document.addEventListener('keydown',function(ev){ if(ev.key==='Escape' && drawer.classList.contains('open')) closeD(); });

  // ---- back to top ----
  var totop=document.getElementById('totop');
  window.addEventListener('scroll',function(){ totop.classList.toggle('show', window.scrollY>600); },{passive:true});
  totop.addEventListener('click',function(){ var reduce = matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches; window.scrollTo({top:0, behavior: reduce ? 'auto' : 'smooth'}); });

  function initGallery(){
    var gal=document.getElementById('gal');
    if(!gal) return;
    gal.innerHTML=''; for(var i=0;i<8;i++){ gal.innerHTML+='<div class="cell"><div class="skel" style="width:100%;height:100%"></div></div>'; }
    // hero collage: swap the illustration for REAL nursery photos once they load
    function heroPhotos(ids){
      if(ids.length<3) return;
      var art=document.getElementById('hero-art');
      var slots=[['hc-arch',900],['hc-b',700],['hc-a',500]];
      var loads=slots.map(function(s,i){
        return new Promise(function(res,rej){
          var el=document.getElementById(s[0]);
          el.onload=function(){ res(); }; el.onerror=function(){ rej(); };
          el.loading='eager';
          el.src=NS.driveThumb(ids[i], s[1]);
        });
      });
      Promise.all(loads).then(function(){
        document.getElementById('hc-badge').insertAdjacentHTML('afterbegin', I('camera'));
        art.classList.add('has-photos');
        var full=ids.slice(0,3).map(function(id){ return NS.driveThumb(id,1400); });
        slots.forEach(function(s,i){
          var el=document.getElementById(s[0]); el.style.cursor='zoom-in';
          var idx = i===0?0:(i===1?1:2);
          el.setAttribute('role','button'); el.setAttribute('tabindex','0');
          el.addEventListener('click',function(){ NS.lightbox(full, idx); });
          el.addEventListener('keydown',function(ev){ if(ev.key==='Enter'||ev.key===' '){ ev.preventDefault(); NS.lightbox(full, idx); } });
        });
      }).catch(function(){}); // any failure -> keep the illustration
    }

    fetch(NS.ODOO+'/site/photos?limit=12').then(function(r){return r.json();}).then(function(d){
      var all=(d&&d.photos||[]);
      heroPhotos(all.slice(0,3));
      var ids = all.length>=11 ? all.slice(3,11) : all.slice(0,8);   // avoid repeating hero shots when we have enough
      if(!ids.length){
        gal.className=''; gal.innerHTML=NS.empty('camera','Coming soon — photos from our day','Follow us on Instagram, or visit us to see our environment yourself.');
        return;
      }
      var full=ids.map(function(id){ return NS.driveThumb(id,1200); });
      gal.innerHTML=''; gal.className='gal rev in';
      var galAlts=['Children playing at the nursery','A sensory activity for children','The reading corner','A child working with focus','Outdoor play','A creative art moment','Morning circle time','The prepared nursery environment'];
      ids.forEach(function(id,idx){
        var cell=document.createElement('div'); cell.className='cell';
        cell.setAttribute('role','button'); cell.setAttribute('tabindex','0');
        cell.innerHTML='<img loading="lazy" width="400" height="400" alt="'+NS.attr(galAlts[idx%galAlts.length])+'" src="'+NS.driveThumb(id,600)+'"/><span class="z">'+I('search')+'</span>';
        cell.addEventListener('click',function(){ NS.lightbox(full, idx); });
        cell.addEventListener('keydown',function(ev){ if(ev.key==='Enter'||ev.key===' '){ ev.preventDefault(); NS.lightbox(full, idx); } });
        gal.appendChild(cell);
      });
    }).catch(function(){
      gal.className=''; gal.innerHTML=NS.empty('camera','Coming soon — photos from our day','Follow us on Instagram or visit us to see it yourself.');
    });
  }

  whenIdle(function(){
    initReviews();
    initGallery();
  });

  // ---- register form ----
  var form=document.getElementById('regform'), msg=document.getElementById('reg-msg'),
      done=document.getElementById('reg-done'), btn=document.getElementById('reg-submit');
  function fieldOf(name){ return form.querySelector('[name="'+name+'"]').closest('.field'); }
  function setErr(name,on){ fieldOf(name).classList.toggle('err',!!on); var input=form.querySelector('[name="'+name+'"]'); if(input) input.setAttribute('aria-invalid', on?'true':'false'); }
  form.addEventListener('submit',function(ev){
    if(btn.classList.contains('is-loading')) return;
    ev.preventDefault();
    var child=form.child_name.value.trim(), email=form.parent_email.value.trim(),
        phone=form.parent_phone.value.trim(), name=form.parent_name.value.trim();
    var ok=true;
    setErr('child_name', !child); if(!child) ok=false;
    var emailOk=/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email); setErr('parent_email', !emailOk); if(!emailOk) ok=false;
    var phoneOk = !phone || /^0?5\d{8}$/.test(phone.replace(/\s/g,'')); setErr('parent_phone', !phoneOk); if(!phoneOk) ok=false;
    if(!ok){ msg.style.color='var(--danger)'; msg.textContent='Please review the highlighted fields'; return; }
    msg.textContent=''; btn.classList.add('is-loading');
    NS.api('/api/parent-signup',{parent_name:name,parent_email:email,parent_phone:phone,child_name:child})
    .then(function(d){
      btn.classList.remove('is-loading');
      if(d&&d.ok){
        form.classList.add('hide'); msg.textContent=''; done.classList.remove('hide');
        var line = d.enrolled
          ? 'Great news! <b>'+NS.esc(d.child)+'</b> is already one of our students — we sent the link request to our team.'
          : 'We received your request for <b>'+NS.esc(d.child)+'</b> and will contact you soon — welcome to our family!';
        done.innerHTML='<div class="big">'+I('checkCircle')+'</div>'+
          '<h3 style="color:var(--forest)">Sent successfully</h3>'+
          '<p class="muted" style="margin:8px 0 18px">'+line+'</p>'+
          '<a class="btn btn--primary btn--block btn--lg" href="/login/" rel="nofollow">'+I('google')+' Sign in with Google now</a>'+
          '<p class="muted" style="font-size:.85rem;margin-top:12px">Sign in with the same email ('+NS.esc(email)+') and our team will link you to your child.</p>';
        done.scrollIntoView({behavior:'smooth',block:'center'});
      } else {
        msg.style.color='var(--danger)'; msg.textContent=(d&&d.error)||'Something went wrong, please try again';
      }
    }).catch(function(e){
      btn.classList.remove('is-loading'); msg.style.color='var(--danger)';
      if(e && e.type==='app'){ msg.textContent=e.message; return; }
      msg.innerHTML='Could not send — <a href="'+NS.wa('966541558173','Hello, I would like to register my child at the nursery')+'" target="_blank" rel="noopener" style="color:var(--clay-600);font-weight:800">message us on WhatsApp</a>';
    });
  });
})();
