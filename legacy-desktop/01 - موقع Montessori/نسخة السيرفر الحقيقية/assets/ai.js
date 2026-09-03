(function(){
'use strict';
var TOKEN=NS.token('mt'), app=document.getElementById('app');
var CONTEXT=null, SUGGESTIONS=[], HISTORY=[], BUSY=false;

if(!TOKEN){ gate(); } else { render(); loadContext(false); }

function gate(){
  document.body.style.overflow='auto';
  app.innerHTML='';
  var mount=document.createElement('div'); app.appendChild(mount);
  NS.gate(mount,{title:'ذكاء الحضانة',body:'سجّلي دخولك كمديرة أو صاحبة الحضانة.'});
}

function render(){
  app.innerHTML=NS.appbar({sub:'ذكاء الحضانة',nav:NS.adminNav('ai')})+
    '<div class="ai-shell">'+
      '<aside class="ai-side" aria-label="الأسئلة الجاهزة">'+
        '<div class="ai-side-head"><h2>أسئلة جاهزة</h2><span class="ai-source" id="provider"><i></i><span>جاري الاتصال</span></span></div>'+
        '<div class="q-wrap" id="questions">'+skeletonQuestions()+'</div>'+ 
      '</aside>'+ 
      '<section class="ai-main" aria-label="محادثة ذكاء الحضانة">'+
        '<div class="ai-top">'+
          '<div class="ai-heading">'+
            '<div class="ai-title"><span class="ai-mark">'+NS.icon('sparkle')+'</span><div><h1>ذكاء الحضانة</h1><p id="stamp">بيانات مباشرة من أنظمة الروضة</p></div></div>'+ 
            '<div class="ai-actions">'+
              '<button class="ai-icon-btn" id="new-chat" type="button" title="محادثة جديدة" aria-label="محادثة جديدة">'+NS.icon('refresh')+'</button>'+ 
              '<button class="ai-icon-btn" id="refresh-data" type="button" title="تحديث البيانات" aria-label="تحديث البيانات">'+NS.icon('refresh')+'</button>'+ 
            '</div>'+ 
          '</div>'+ 
          '<div class="ai-kpis" id="kpis">'+skeletonKpis()+'</div>'+ 
        '</div>'+ 
        '<div class="ai-stream" id="stream"><div class="messages" id="messages"></div></div>'+ 
        '<div class="ai-compose">'+ 
          '<form class="compose-form" id="compose">'+ 
            '<textarea class="compose-input" id="prompt" rows="1" maxlength="1200" aria-label="سؤالك" placeholder="اكتبي سؤالك..."></textarea>'+ 
            '<button class="compose-send" id="send" type="submit" title="إرسال" aria-label="إرسال">'+NS.icon('send')+'</button>'+ 
          '</form>'+ 
        '</div>'+ 
      '</section>'+ 
    '</div>';
  NS.wireLogout('mt');
  wire();
  addMessage('assistant','ما الذي نتابعه اليوم؟','ذكاء الحضانة');
}

function skeletonQuestions(){
  var h='<div class="q-group"><div class="q-list">';
  for(var i=0;i<7;i++) h+='<div class="ai-skel" style="height:46px"></div>';
  return h+'</div></div>';
}
function skeletonKpis(){
  var h=''; for(var i=0;i<4;i++) h+='<div class="ai-kpi"><div class="ai-skel" style="width:70%"></div><div class="ai-skel" style="width:42%;margin-top:10px;height:22px"></div></div>';
  return h;
}
function wire(){
  var form=document.getElementById('compose'), input=document.getElementById('prompt');
  form.addEventListener('submit',function(ev){ev.preventDefault();ask(input.value);});
  input.addEventListener('keydown',function(ev){
    if(ev.key==='Enter'&&!ev.shiftKey){ev.preventDefault();form.requestSubmit();}
  });
  input.addEventListener('input',function(){
    input.style.height='48px'; input.style.height=Math.min(input.scrollHeight,128)+'px';
  });
  document.getElementById('refresh-data').addEventListener('click',function(){loadContext(true);});
  document.getElementById('new-chat').addEventListener('click',function(){
    if(BUSY)return; HISTORY=[]; document.getElementById('messages').innerHTML='';
    addMessage('assistant','ما الذي نتابعه اليوم؟','ذكاء الحضانة'); input.focus();
  });
}

function loadContext(toast){
  var refresh=document.getElementById('refresh-data'); if(refresh)refresh.disabled=true;
  NS.api('/api/manager/ai/context',{mt:TOKEN}).then(function(data){
    if(!data||!data.ok){throw new NS.ApiError('app',(data&&data.error)||'تعذّر تحميل البيانات');}
    CONTEXT=data.context||{}; SUGGESTIONS=data.suggestions||[];
    paintStatus(); paintKpis(); paintQuestions();
    if(toast)NS.toast('تم تحديث البيانات','ok');
  }).catch(function(err){
    if(err&&err.type==='auth'){NS.clearToken('mt');gate();return;}
    if(!CONTEXT)showLoadError((err&&err.message)||'تعذّر تحميل البيانات');
    else NS.toast('تعذّر تحديث البيانات','err');
  }).then(function(){if(refresh)refresh.disabled=false;});
}

function paintStatus(){
  var provider=document.getElementById('provider'), assistant=CONTEXT.assistant||{};
  provider.classList.toggle('is-on',!!assistant.configured);
  provider.querySelector('span').textContent=assistant.configured?'Msty Go متصل':'بيانات النظام';
  var stamp=document.getElementById('stamp');
  stamp.textContent='آخر تحديث '+(CONTEXT.generated_at||'الآن');
}
function fmt(n){return new Intl.NumberFormat('ar-SA').format(Number(n)||0);}
function paintKpis(){
  var wa=CONTEXT.whatsapp||{}, pay=CONTEXT.payments||{}, ny=CONTEXT.new_year||{};
  var sent=wa.available?fmt(wa.sent_today):'—';
  var wait=wa.available?fmt(wa.waiting_reply):'—';
  document.getElementById('kpis').innerHTML=
    kpi('رسائل واتساب اليوم',sent,'')+
    kpi('تنتظر الرد',wait,'is-blue')+
    kpi('يحتاجون متابعة سداد',fmt(pay.needs_payment),'is-red')+
    kpi('طلبات بدون جريد',fmt(ny.without_grade),'is-gold');
}
function kpi(label,value,cls){return '<div class="ai-kpi '+cls+'"><span>'+NS.esc(label)+'</span><b>'+NS.esc(value)+'</b></div>';}

function paintQuestions(){
  var groups=[
    ['واتساب',SUGGESTIONS.slice(0,7)],
    ['الطلاب والسداد',SUGGESTIONS.slice(7,18)],
    ['طلبات السنة الجديدة',SUGGESTIONS.slice(18,24)],
    ['الحضور والزيارات',SUGGESTIONS.slice(24,32)],
    ['المال والتشغيل',SUGGESTIONS.slice(32)]
  ];
  document.getElementById('questions').innerHTML=groups.map(function(group){
    if(!group[1].length)return '';
    return '<div class="q-group"><div class="q-title">'+NS.esc(group[0])+'</div><div class="q-list">'+
      group[1].map(function(q){return '<button class="q-btn" type="button" data-question="'+NS.attr(q)+'">'+NS.esc(q)+'</button>';}).join('')+
      '</div></div>';
  }).join('');
  [].forEach.call(document.querySelectorAll('[data-question]'),function(button){
    button.addEventListener('click',function(){ask(button.getAttribute('data-question'));});
  });
}

function addMessage(role,text,source,id){
  var list=document.getElementById('messages'), row=document.createElement('div');
  row.className='msg '+role+(id?' '+id:'');
  if(id)row.id=id;
  row.innerHTML='<span class="msg-avatar">'+NS.icon(role==='user'?'user':'sparkle')+'</span><div class="msg-body"><div class="msg-text"></div>'+ 
    (source?'<div class="msg-meta">'+NS.esc(source)+'</div>':'')+'</div>';
  row.querySelector('.msg-text').textContent=text;
  list.appendChild(row); scrollBottom(); return row;
}
function addTyping(){
  var list=document.getElementById('messages'), row=document.createElement('div');
  row.className='msg assistant typing'; row.id='typing';
  row.innerHTML='<span class="msg-avatar">'+NS.icon('sparkle')+'</span><div class="msg-body"><div class="msg-text"><i></i><i></i><i></i></div></div>';
  list.appendChild(row); scrollBottom();
}
function scrollBottom(){var s=document.getElementById('stream');requestAnimationFrame(function(){s.scrollTop=s.scrollHeight;});}
function busy(on){
  BUSY=on; document.getElementById('send').disabled=on; document.getElementById('prompt').disabled=on;
  [].forEach.call(document.querySelectorAll('.q-btn'),function(b){b.disabled=on;});
}
function ask(raw){
  var question=String(raw||'').trim(), input=document.getElementById('prompt');
  if(!question||BUSY)return;
  var prior=HISTORY.slice(-8);
  HISTORY.push({role:'user',content:question}); addMessage('user',question,'');
  input.value=''; input.style.height='48px'; busy(true); addTyping();
  NS.api('/api/manager/ai/ask',{mt:TOKEN,prompt:question,history:prior}).then(function(data){
    var typing=document.getElementById('typing'); if(typing)typing.remove();
    if(!data||!data.ok){
      addMessage('assistant',(data&&data.error)||'تعذّر تنفيذ السؤال.','لم تكتمل الإجابة'); return;
    }
    var answer=String(data.answer||''); HISTORY.push({role:'assistant',content:answer});
    addMessage('assistant',answer,data.source==='msty-go'?'Msty Go':'بيانات مباشرة');
  }).catch(function(err){
    var typing=document.getElementById('typing'); if(typing)typing.remove();
    if(err&&err.type==='auth'){NS.clearToken('mt');gate();return;}
    addMessage('assistant','تعذّر الاتصال الآن. جرّبي مرة أخرى.','خطأ اتصال');
  }).then(function(){busy(false);if(document.getElementById('prompt'))document.getElementById('prompt').focus();});
}

function showLoadError(message){
  var shell=document.querySelector('.ai-shell'); if(!shell)return;
  shell.innerHTML='<div class="ai-error" style="grid-column:1/-1"><div class="ai-error-box"><h2>تعذّر فتح ذكاء الحضانة</h2><p>'+NS.esc(message)+'</p><button class="btn btn--primary" type="button" onclick="location.reload()">'+NS.icon('refresh')+' إعادة المحاولة</button></div></div>';
}
})();
