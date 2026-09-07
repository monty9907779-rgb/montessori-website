(function(){
'use strict';

var TOKEN = NS.token('mt');
var app = document.getElementById('app');
var DATA = null;

function appbar(){
  return NS.appbar({sub:'واتساب والرد الآلي', nav:NS.adminNav('whatsapp')});
}

function gate(){
  app.innerHTML = appbar() + '<main class="app-main app-narrow" id="wa-gate"></main>';
  NS.gate(document.getElementById('wa-gate'), {
    title:'إدارة واتساب',
    body:'سجّلي دخولك كمديرة أو صاحبة الحضانة.'
  });
}

function loading(){
  app.innerHTML = appbar() +
    '<main class="app-main"><div class="wa-admin"><div class="wa-loading">'+
      NS.icon('refresh')+'<div>جاري تحميل إعدادات واتساب...</div>'+
    '</div></div></main>';
  NS.wireLogout('mt');
}

function boot(){
  if(!TOKEN){ gate(); return; }
  loading();
  NS.api('/api/manager/whatsapp_settings',{mt:TOKEN,action:'list'}).then(function(data){
    if(!data || data.ok===false){ throw new Error((data&&data.error)||'تعذّر تحميل الإعدادات'); }
    DATA = data;
    render();
  }).catch(function(error){
    if(error.type==='auth'){ NS.clearToken('mt'); gate(); return; }
    app.innerHTML = appbar() +
      '<main class="app-main"><div class="wa-admin"><div class="card card--pad u-center">'+
        '<h3 class="u-mb8">تعذّر تحميل إعدادات واتساب</h3>'+
        '<button class="btn btn--primary" id="wa-retry">'+NS.icon('refresh')+' إعادة المحاولة</button>'+
      '</div></div></main>';
    NS.wireLogout('mt');
    document.getElementById('wa-retry').addEventListener('click',boot);
  });
}

function formatUpdated(value){
  if(!value) return 'لم تُعدّل الإعدادات بعد';
  var date = new Date(String(value).replace(' ','T')+'Z');
  if(isNaN(date.getTime())) return '';
  return 'آخر تعديل: '+date.toLocaleString('ar-EG',{dateStyle:'medium',timeStyle:'short'});
}

function render(){
  var questions = DATA.questions || [];
  var enabled = !!DATA.enabled;
  var stateClass = enabled ? 'is-on' : 'is-off';
  var controlClass = enabled ? '' : ' is-off';
  var toggleClass = enabled ? ' is-stop' : '';
  var toggleIcon = enabled ? 'x' : 'check';
  var toggleText = enabled ? 'إيقاف الرد الآلي' : 'تشغيل الرد الآلي';

  var rows = questions.map(function(item,index){
    var image = item.image_url
      ? '<img class="qa-answer__image" src="'+NS.attr(item.image_url)+'" alt="صورة مرفقة بالإجابة"/>'
      : '';
    return '<article class="qa-item" data-id="'+NS.attr(item.id)+'">'+
      '<div class="qa-number">'+(index+1)+'</div>'+
      '<div><h3 class="qa-question">'+NS.esc(item.question)+'</h3>'+
        '<div class="qa-answer">'+NS.esc(item.answer)+'</div>'+image+'</div>'+
      '<div class="qa-actions">'+
        '<button type="button" class="qa-icon-button" data-edit="'+NS.attr(item.id)+'" title="تعديل" aria-label="تعديل السؤال">'+NS.icon('edit')+'</button>'+
        '<button type="button" class="qa-icon-button is-danger" data-delete="'+NS.attr(item.id)+'" title="حذف" aria-label="حذف السؤال">'+NS.icon('trash')+'</button>'+
      '</div></article>';
  }).join('');

  app.innerHTML = appbar()+
    '<main class="app-main"><div class="wa-admin">'+
      '<div class="page-head wa-page-head"><div>'+
        '<h1 class="page-title">'+NS.icon('whatsapp')+' واتساب والرد الآلي</h1>'+
        '<div class="sub">إدارة الأسئلة والإجابات</div>'+
      '</div></div>'+
      '<section class="wa-control'+controlClass+'">'+
        '<div class="wa-control__main"><span class="wa-control__icon">'+NS.icon('whatsapp')+'</span>'+
          '<div><div class="wa-control__title">الرد الآلي '+
            '<span class="wa-state '+stateClass+'"><span class="wa-state__dot"></span>'+(enabled?'يعمل الآن':'متوقف')+'</span>'+
          '</div><div class="wa-control__meta">'+NS.esc(formatUpdated(DATA.updated_at))+'</div></div>'+
        '</div>'+
        '<div class="wa-control__actions">'+
          '<button type="button" class="btn btn--soft wa-sync-bot" id="wa-sync-bot" title="تحديث البوت الآن">'+NS.icon('refresh')+' تحديث البوت</button>'+
          '<button type="button" class="btn btn--primary wa-toggle'+toggleClass+'" id="wa-toggle">'+NS.icon(toggleIcon)+' '+toggleText+'</button>'+
        '</div>'+
      '</section>'+
      '<section class="qa-section">'+
        '<div class="qa-toolbar">'+
          '<h2 class="qa-toolbar__title">'+NS.icon('chat')+' الأسئلة والإجابات <span class="qa-count">'+questions.length+'</span></h2>'+
          '<span class="qa-toolbar__spacer"></span>'+
          '<label class="qa-search">'+NS.icon('search')+'<input class="input" id="qa-search" type="search" placeholder="بحث" aria-label="بحث في الأسئلة والإجابات"/></label>'+
          '<button type="button" class="btn btn--primary btn--sm qa-add" id="qa-add">'+NS.icon('plus')+' إضافة سؤال</button>'+
        '</div>'+
        '<div class="qa-list" id="qa-list">'+
          (rows || '<div class="qa-empty"><span class="qa-empty__icon">'+NS.icon('chat')+'</span><b>لا توجد أسئلة</b><span>أضيفي أول سؤال وإجابته.</span></div>')+
        '</div>'+
        '<div class="qa-empty qa-no-results" id="qa-no-results"><b>لا توجد نتائج</b></div>'+
      '</section>'+
    '</div></main>';

  NS.wireLogout('mt');
  wireControls();
}

function wireControls(){
  document.getElementById('wa-toggle').addEventListener('click',toggleAutoReply);
  document.getElementById('wa-sync-bot').addEventListener('click',syncBot);
  document.getElementById('qa-add').addEventListener('click',function(){ openEditor(null); });
  Array.prototype.forEach.call(document.querySelectorAll('[data-edit]'),function(button){
    button.addEventListener('click',function(){ openEditor(findItem(button.getAttribute('data-edit'))); });
  });
  Array.prototype.forEach.call(document.querySelectorAll('[data-delete]'),function(button){
    button.addEventListener('click',function(){ deleteItem(button.getAttribute('data-delete')); });
  });
  document.getElementById('qa-search').addEventListener('input',filterQuestions);
}

function syncBot(){
  var button = document.getElementById('wa-sync-bot');
  button.classList.add('is-loading');
  callSettings('refresh_bot').then(function(data){
    DATA = data;
    render();
    NS.toast('تم إرسال آخر الإعدادات إلى البوت');
  }).catch(function(error){
    button.classList.remove('is-loading');
    NS.toast(error.message||'تعذّر تحديث البوت','err');
  });
}

function findItem(itemId){
  return (DATA.questions||[]).find(function(item){ return item.id===itemId; }) || null;
}

function filterQuestions(event){
  var query = event.target.value.trim().toLowerCase();
  var shown = 0;
  Array.prototype.forEach.call(document.querySelectorAll('.qa-item'),function(card){
    var item = findItem(card.getAttribute('data-id'));
    var haystack = item ? (item.question+' '+item.answer).toLowerCase() : '';
    var visible = !query || haystack.indexOf(query)!==-1;
    card.hidden = !visible;
    if(visible) shown++;
  });
  var empty = document.getElementById('qa-no-results');
  empty.classList.toggle('show', !!query && shown===0 && (DATA.questions||[]).length>0);
}

function toggleAutoReply(){
  var next = !DATA.enabled;
  NS.confirm({
    icon:'whatsapp',
    title:next?'تشغيل الرد الآلي؟':'إيقاف الرد الآلي؟',
    body:next?'سيبدأ الرد على رسائل واتساب الجديدة.':'لن يرسل النظام أي رد تلقائي حتى تشغيله مرة أخرى.',
    okText:next?'تشغيل':'إيقاف',
    danger:!next
  }).then(function(confirmed){
    if(!confirmed) return;
    var button = document.getElementById('wa-toggle');
    button.classList.add('is-loading');
    callAutoReply(next).then(function(data){
      DATA = data;
      render();
      NS.toast(next?'تم تشغيل الرد الآلي':'تم إيقاف الرد الآلي');
    }).catch(function(error){
      button.classList.remove('is-loading');
      NS.toast(error.message||'تعذّر حفظ الحالة','err');
    });
  });
}

function callAutoReply(enabled){
  return NS.api('/api/manager/whatsapp_autoreply',{
    mt:TOKEN,action:'set',enabled:enabled?1:0
  }).then(requireOk);
}

function callSettings(action,payload){
  var params = {mt:TOKEN,action:action};
  Object.keys(payload||{}).forEach(function(key){ params[key]=payload[key]; });
  return NS.api('/api/manager/whatsapp_settings',params).then(requireOk);
}

function requireOk(data){
  if(!data || data.ok===false) throw new Error((data&&data.error)||'تعذّر حفظ التغييرات');
  return data;
}

function openEditor(item){
  var editing = !!item;
  var existingImageUrl = editing && item.image_url ? item.image_url : '';
  var modal = NS.modal(
    '<form class="qa-editor" id="qa-editor">'+
      '<h3>'+(editing?'تعديل السؤال والإجابة':'إضافة سؤال وإجابة')+'</h3>'+
      '<div class="field"><label for="qa-question">السؤال</label>'+
        '<input class="input" id="qa-question" maxlength="200" autocomplete="off" value="'+NS.attr(editing?item.question:'')+'"/></div>'+
      '<div class="field"><label for="qa-answer">الإجابة</label>'+
        '<textarea class="input" id="qa-answer" maxlength="5000">'+NS.esc(editing?item.answer:'')+'</textarea></div>'+
      '<div class="field qa-image-field"><label for="qa-image">صورة الإجابة <span class="qa-image-optional">اختياري</span></label>'+
        '<div class="qa-image-controls">'+
          '<input class="qa-image-input" id="qa-image" type="file" accept="image/jpeg,image/png,image/webp" aria-label="اختيار صورة الإجابة"/>'+
          '<button class="btn btn--soft btn--sm qa-image-upload" type="button" id="qa-image-upload">'+NS.icon('camera')+' رفع صورة</button>'+
          '<button class="btn btn--ghost btn--sm qa-image-remove" type="button" id="qa-image-remove"'+(existingImageUrl?'':' hidden')+'>'+NS.icon('trash')+' حذف الصورة</button>'+
        '</div>'+
        '<div class="qa-image-preview" id="qa-image-preview"'+(existingImageUrl?'':' hidden')+'>'+
          (existingImageUrl?'<img src="'+NS.attr(existingImageUrl)+'" alt="معاينة صورة الإجابة"/>':'')+
        '</div>'+
      '</div>'+
      '<div class="qa-editor__error" id="qa-editor-error" role="alert"></div>'+
      '<div class="actions">'+
        '<button class="btn btn--primary" type="submit" data-save>'+NS.icon('check')+' حفظ</button>'+
        '<button class="btn btn--ghost" type="button" data-cancel>إلغاء</button>'+
      '</div>'+
    '</form>'
  );
  var form = modal.el.querySelector('#qa-editor');
  var questionInput = modal.el.querySelector('#qa-question');
  var answerInput = modal.el.querySelector('#qa-answer');
  var imageInput = modal.el.querySelector('#qa-image');
  var imageUploadButton = modal.el.querySelector('#qa-image-upload');
  var imagePreview = modal.el.querySelector('#qa-image-preview');
  var imageRemoveButton = modal.el.querySelector('#qa-image-remove');
  var errorBox = modal.el.querySelector('#qa-editor-error');
  var saveButton = modal.el.querySelector('[data-save]');
  modal.el.querySelector('[data-cancel]').addEventListener('click',modal.close);
  setTimeout(function(){ questionInput.focus(); },80);

  var imageState = {data:null, name:'', remove:false, url:existingImageUrl};
  function renderImagePreview(){
    var url = imageState.data || imageState.url;
    imagePreview.hidden = !url;
    imageRemoveButton.hidden = !url;
    imagePreview.innerHTML = url
      ? '<img src="'+NS.attr(url)+'" alt="معاينة صورة الإجابة"/>'
      : '';
  }

  imageUploadButton.addEventListener('click',function(){ imageInput.click(); });

  imageInput.addEventListener('change',function(){
    var file = imageInput.files && imageInput.files[0];
    if(!file) return;
    var allowedTypes = ['image/jpeg','image/png','image/webp'];
    if(allowedTypes.indexOf(file.type)===-1){
      errorBox.textContent='الصيغ المتاحة هي JPG وPNG وWebP فقط';
      imageInput.value='';
      return;
    }
    if(file.size > 4*1024*1024){
      errorBox.textContent='يجب ألا يتجاوز حجم الصورة 4 ميجابايت';
      imageInput.value='';
      return;
    }
    errorBox.textContent='';
    var reader = new FileReader();
    reader.onload = function(){
      imageState.data = String(reader.result||'');
      imageState.name = file.name;
      imageState.remove = false;
      renderImagePreview();
    };
    reader.onerror = function(){
      errorBox.textContent='تعذّر قراءة ملف الصورة';
      imageInput.value='';
    };
    reader.readAsDataURL(file);
  });

  imageRemoveButton.addEventListener('click',function(){
    imageState.data = null;
    imageState.name = '';
    imageState.url = '';
    imageState.remove = true;
    imageInput.value = '';
    renderImagePreview();
  });

  form.addEventListener('submit',function(event){
    event.preventDefault();
    var question = questionInput.value.trim();
    var answer = answerInput.value.trim();
    errorBox.textContent = '';
    if(!question){ errorBox.textContent='اكتبي السؤال أولاً'; questionInput.focus(); return; }
    if(!answer){ errorBox.textContent='اكتبي إجابة السؤال أولاً'; answerInput.focus(); return; }
    saveButton.classList.add('is-loading');
    callSettings(editing?'update':'create',{
      item_id:editing?item.id:null,
      question:question,
      answer:answer,
      image_data:imageState.data,
      image_name:imageState.name,
      remove_image:imageState.remove?1:0
    }).then(function(data){
      DATA = data;
      modal.close();
      render();
      NS.toast(editing?'تم حفظ التعديل':'تمت إضافة السؤال');
    }).catch(function(error){
      saveButton.classList.remove('is-loading');
      errorBox.textContent = error.message||'تعذّر الحفظ';
    });
  });
}

function deleteItem(itemId){
  var item = findItem(itemId);
  if(!item) return;
  NS.confirm({
    title:'حذف السؤال؟',
    body:'سيُحذف السؤال وإجابته من ردود واتساب.',
    okText:'حذف',
    cancelText:'إلغاء',
    danger:true
  }).then(function(confirmed){
    if(!confirmed) return;
    callSettings('delete',{item_id:itemId}).then(function(data){
      DATA = data;
      render();
      NS.toast('تم حذف السؤال');
    }).catch(function(error){
      NS.toast(error.message||'تعذّر حذف السؤال','err');
    });
  });
}

boot();
})();
