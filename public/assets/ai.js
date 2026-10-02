(function(){
'use strict';
var TOKEN=NS.token('mt'), app=document.getElementById('app');
var CONTEXT=null, SUGGESTIONS=[], GROUPS=[], HISTORY=[], BUSY=false;

if(!TOKEN){ gate(); } else { render(); loadContext(false); }

function gate(){
  document.body.classList.add('ai-scroll');
  app.innerHTML='';
  var mount=document.createElement('div'); app.appendChild(mount);
  NS.gate(mount,{title:'ذكاء الحضانة',body:'سجّلي دخولك كمديرة أو صاحبة الحضانة.'});
}

function render(){
  /* 2/10: صفحة بعمود واحد — الشات يأخذ العرض كله، والأسئلة المقترحة قائمة
     منسدلة أول الصفحة بدل عمود جانبي. */
  app.innerHTML=NS.appbar({sub:'ذكاء الحضانة',nav:NS.adminNav('ai')})+
    '<div class="ai-shell">'+
      '<section class="ai-main" aria-label="محادثة ذكاء الحضانة">'+
        '<div class="ai-top">'+
          '<div class="ai-heading">'+
            '<div class="ai-title"><span class="ai-mark">'+NS.icon('sparkle')+'</span><div><h1>ذكاء الحضانة</h1><p id="stamp">بيانات مباشرة من أنظمة الروضة</p></div></div>'+
            '<div class="ai-tools">'+
              '<label class="q-pick" for="q-select"><select class="q-select" id="q-select" aria-label="أسئلة مقترحة"><option value="">أسئلة مقترحة…</option></select></label>'+
              '<span class="ai-source" id="provider"><i></i><span>جاري الاتصال</span></span>'+
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

function skeletonKpis(){
  return '<div class="ai-kpi"><div class="ai-skel ai-skel--kpi-label"></div><div class="ai-skel ai-skel--kpi-value"></div></div>';
}
function wire(){
  var form=document.getElementById('compose'), input=document.getElementById('prompt');
  form.addEventListener('submit',function(ev){ev.preventDefault();ask(input.value);});
  input.addEventListener('keydown',function(ev){
    if(ev.key==='Enter'&&!ev.shiftKey){ev.preventDefault();form.requestSubmit();}
  });
  input.addEventListener('input',function(){ NS.autoGrowInput(input,4); });
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
    CONTEXT=data.context||{}; SUGGESTIONS=data.suggestions||[]; GROUPS=data.suggestion_groups||[];
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
  /* 2/10: مؤشر واحد فقط بطلب المديرة — الطلاب المتأخرون في السداد
     (paid_until قبل اليوم). */
  var pay=CONTEXT.payments||{};
  document.getElementById('kpis').innerHTML=
    kpi('الطلاب المتأخرون في السداد',fmt(pay.overdue),'is-red');
}
function kpi(label,value,cls){return '<div class="ai-kpi '+cls+'"><span>'+NS.esc(label)+'</span><b>'+NS.esc(value)+'</b></div>';}

function paintQuestions(){
  /* 2/10: ترتيب المجموعات بحسب الأهمية للمديرة — الطلاب والسداد أولاً ثم
     المال والتشغيل؛ الفهارس (slices) تبقى كما هي لأنها تشير إلى ترتيب
     SUGGESTIONS القادم من الخادم. */
  /* 2/10: المجموعات تأتي جاهزة من الخادم (suggestion_groups: الأهم → الشهور →
     …)؛ التقسيم بالأرقام أدناه احتياط لخادم أقدم. */
  var groups=(GROUPS&&GROUPS.length)?GROUPS.map(function(g){return [g.label,g.items||[]];}):[
    ['الطلاب والسداد',SUGGESTIONS.slice(7,18)],
    ['المال والتشغيل',SUGGESTIONS.slice(32)],
    ['واتساب',SUGGESTIONS.slice(0,7)],
    ['طلبات السنة الجديدة',SUGGESTIONS.slice(18,24)],
    ['الحضور والزيارات',SUGGESTIONS.slice(24,32)]
  ];
  /* 2/10: قائمة منسدلة واحدة مقسّمة بمجموعات؛ الاختيار يرسل السؤال فوراً
     ويرجّع القائمة لعنوانها. السؤال الحر = خانة الكتابة نفسها. */
  var sel=document.getElementById('q-select'); if(!sel)return;
  var h='<option value="">أسئلة مقترحة…</option>'+
    '<option value="__free__">✦ سؤال حر — اكتبي سؤالك بنفسك</option>';
  groups.forEach(function(group){
    if(!group[1].length)return;
    h+='<optgroup label="'+NS.attr(group[0])+'">'+
      group[1].map(function(q){return '<option value="'+NS.attr(q)+'">'+NS.esc(q)+'</option>';}).join('')+
      '</optgroup>';
  });
  sel.innerHTML=h;
  if(!sel.dataset.wired){
    sel.dataset.wired='1';
    sel.addEventListener('change',function(){
      var q=sel.value; sel.value='';
      if(q==='__free__'){
        var input=document.getElementById('prompt'); if(!input)return;
        input.value=''; input.rows=1; input.placeholder='اكتبي سؤالك الحر هنا ثم اضغطي إرسال…';
        setTimeout(function(){input.focus();},50); return;
      }
      if(q)ask(q);
    });
  }
}

/* 2/10: ردود المساعد تُعرض كـ Markdown مبسّط — جداول | عريض | قوائم | فقرات.
   النص يُهرَّب أولاً (NS.esc) ثم تُبنى الوسوم من العلامات البنيوية فقط، فلا يمرّ
   أي HTML من الموديل. رسائل المستخدم تبقى نصاً خاماً (textContent). */
function renderMd(src){
  /* الموديلات بتحط علامات اتجاه خفية (RLM/LRM/isolates) ومسافات غير فاصلة
     أول السطر في النص العربي فتكسر التعرّف على «|» — تُشال قبل التحليل. */
  var lines=String(src||'').replace(/\r\n?/g,'\n').split('\n').map(function(l){
    return l.replace(/[‎‏‪-‮⁦-⁩﻿]/g,'').replace(/ /g,' ');
  }), out=[], i=0;
  var LI=/^\s*([-*•]|\d+[.)])\s+/, H=/^\s*#{1,4}\s+/;
  function inline(s){
    s=NS.esc(s);
    s=s.replace(/\*\*([^*\n]+)\*\*/g,'<b>$1</b>');
    s=s.replace(/`([^`\n]+)`/g,'<code>$1</code>');
    return s;
  }
  function isRow(l){return /^\s*\|/.test(l);}
  function isSep(l){return /^\s*\|?[\s:|-]*-[\s:|-]*$/.test(l)&&/-/.test(l);}
  function cells(l){return l.trim().replace(/^\|/,'').replace(/\|$/,'').split('|').map(function(c){return c.trim();});}
  while(i<lines.length){
    var l=lines[i];
    if(isRow(l)&&i+1<lines.length&&isSep(lines[i+1])){
      var head=cells(l), rows=[]; i+=2;
      while(i<lines.length&&isRow(lines[i])){rows.push(cells(lines[i]));i++;}
      var h='<div class="md-table"><table><thead><tr>'+head.map(function(c){return '<th>'+inline(c)+'</th>';}).join('')+'</tr></thead><tbody>';
      rows.forEach(function(r){
        var tot=/إجمالي|الإجمالي|المجموع|total/i.test(r[0]||'');
        h+='<tr'+(tot?' class="md-total"':'')+'>'+r.map(function(c){return '<td>'+inline(c)+'</td>';}).join('')+'</tr>';
      });
      out.push(h+'</tbody></table></div>'); continue;
    }
    if(LI.test(l)){
      var OL=/^\s*\d+[.)]\s+/, ordered=OL.test(l), items=[];
      while(i<lines.length&&LI.test(lines[i])&&OL.test(lines[i])===ordered){items.push(lines[i].replace(LI,''));i++;}
      var tag=ordered?'ol':'ul';
      out.push('<'+tag+'>'+items.map(function(t){return '<li>'+inline(t)+'</li>';}).join('')+'</'+tag+'>'); continue;
    }
    if(H.test(l)){out.push('<p><b>'+inline(l.replace(H,''))+'</b></p>');i++;continue;}
    if(!l.trim()){i++;continue;}
    var para=[];
    while(i<lines.length&&lines[i].trim()&&!isRow(lines[i])&&!LI.test(lines[i])&&!H.test(lines[i])){para.push(inline(lines[i]));i++;}
    out.push('<p>'+para.join('<br>')+'</p>');
  }
  return out.join('');
}
function addMessage(role,text,source,id){
  var list=document.getElementById('messages'), row=document.createElement('div');
  row.className='msg '+role+(id?' '+id:'');
  if(id)row.id=id;
  row.innerHTML='<span class="msg-avatar">'+NS.icon(role==='user'?'user':'sparkle')+'</span><div class="msg-body"><div class="msg-text"></div>'+
    (source?'<div class="msg-meta">'+NS.esc(source)+'</div>':'')+'</div>';
  var box=row.querySelector('.msg-text');
  if(role==='assistant'){box.innerHTML=renderMd(text);}else{box.textContent=text;}
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
  var qs=document.getElementById('q-select'); if(qs)qs.disabled=on;
}
function ask(raw){
  var question=String(raw||'').trim(), input=document.getElementById('prompt');
  if(!question||BUSY)return;
  var prior=HISTORY.slice(-8);
  HISTORY.push({role:'user',content:question}); addMessage('user',question,'');
  input.value=''; input.rows=1; busy(true); addTyping();
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
  shell.innerHTML='<div class="ai-error ai-error--span"><div class="ai-error-box"><h2>تعذّر فتح ذكاء الحضانة</h2><p>'+NS.esc(message)+'</p><button class="btn btn--primary" type="button" id="ai-reload">'+NS.icon('refresh')+' إعادة المحاولة</button></div></div>';
  var reload=document.getElementById('ai-reload');
  if(reload)reload.addEventListener('click',function(){location.reload();});
}
})();
