(function(){
'use strict';

var ENDPOINT='/api/manager/excel/import';
var SHEET_ENDPOINT='/api/manager/excel/sheet';
var MAX_FILE_SIZE=12*1024*1024;
var MAX_TOTAL_SIZE=24*1024*1024;

function b64(file){
  return file.arrayBuffer().then(function(buffer){
    var bytes=new Uint8Array(buffer), out=[], step=0x4000;
    for(var i=0;i<bytes.length;i+=step){
      out.push(String.fromCharCode.apply(null,bytes.subarray(i,Math.min(i+step,bytes.length))));
    }
    return btoa(out.join(''));
  });
}

function readFiles(fileList){
  var files=Array.prototype.slice.call(fileList||[]);
  if(!files.length) return Promise.reject(new Error('اختاري ملف Excel واحداً على الأقل'));
  var total=files.reduce(function(sum,file){ return sum+file.size; },0);
  if(total>MAX_TOTAL_SIZE) return Promise.reject(new Error('إجمالي الملفات أكبر من 24 ميجابايت'));
  for(var i=0;i<files.length;i++){
    if(files[i].size>MAX_FILE_SIZE){
      return Promise.reject(new Error('الملف '+files[i].name+' أكبر من 12 ميجابايت'));
    }
    if(!/\.(xlsx|xlsm|xls|csv)$/i.test(files[i].name)){
      return Promise.reject(new Error('الملف '+files[i].name+' ليس Excel أو CSV'));
    }
  }
  return Promise.all(files.map(function(file){
    return b64(file).then(function(content){ return {name:file.name,content:content}; });
  }));
}

function money(value){
  if(value===null||value===undefined||value==='') return '—';
  var n=Number(value);
  if(!isFinite(n)) return NS.esc(value);
  return NS.esc(new Intl.NumberFormat('ar-SA',{maximumFractionDigits:2}).format(n)+' ر.س');
}

function text(value){
  return value===null||value===undefined||value===''?'—':NS.esc(String(value));
}

function labelForKind(kind){
  return kind==='student'?'طالب':kind==='expense'?'مصروف':kind==='salary'?'راتب':'بيانات';
}

function fieldLabel(field){
  return ({
    name:'الاسم',fees:'الرسوم الشهرية',paid:'المدفوع',paid_date:'تاريخ الدفع',
    method:'طريقة الدفع',joining_date:'تاريخ الالتحاق',paid_until:'مدفوع حتى',
    guardian_name:'ولي الأمر',
    guardian_phone:'هاتف ولي الأمر',class_name:'الفصل',books:'الكتب',
    amount:'المبلغ',date:'التاريخ',note:'البيان'
  })[field]||field;
}

function changeHtml(change){
  var rows=(change.changes||[]).map(function(item){
    var numeric=item.field==='paid'||item.field==='fees'||item.field==='books'||item.field==='amount';
    return '<tr><td>'+text(fieldLabel(item.field))+'</td><td>'+
      (numeric?money(item.old):text(item.old))+'</td><td>'+
      (numeric?money(item.new):text(item.new))+'</td></tr>';
  }).join('');
  if(!rows) rows='<tr><td colspan="3">لا يوجد تغيير فعلي</td></tr>';
  return '<details class="excel-review__item" open>'+
    '<summary><span class="excel-review__badge excel-review__badge--'+(change.status==='new'?'new':change.status==='warning'?'warn':'update')+'">'+
      NS.esc(change.status_label||'تحديث')+'</span><strong>'+text(change.name)+'</strong>'+
      '<span class="excel-review__kind">'+NS.esc(labelForKind(change.kind))+'</span></summary>'+
    (change.warning?'<div class="excel-review__warning">'+NS.icon('alert')+text(change.warning)+'</div>':'')+
    '<div class="table-wrap"><table class="table excel-review__table"><thead><tr><th>الحقل</th><th>القديم</th><th>الجديد</th></tr></thead><tbody>'+rows+'</tbody></table></div>'+
  '</details>';
}

function warningsHtml(warnings){
  if(!warnings||!warnings.length) return '';
  return '<div class="excel-review__warnings"><strong>'+NS.icon('alert')+' تحذيرات تحتاج مراجعة</strong>'+
    '<ul>'+warnings.map(function(w){ return '<li>'+NS.esc(w)+'</li>'; }).join('')+'</ul></div>';
}

function classChoicesHtml(choices){
  if(!choices||!choices.length) return '';
  return '<div class="excel-review__classes"><strong>'+NS.icon('users')+' تحديد فصول الطلاب الجدد</strong>'+choices.map(function(choice){
    return '<label><span>'+text(choice.student)+' <small>('+text(choice.source_class)+')</small></span><select data-class-student="'+NS.esc(choice.student)+'"><option value="">اختاري الفصل</option>'+choice.options.map(function(option){ return '<option value="'+NS.esc(option.id)+'">'+text(option.name)+'</option>'; }).join('')+'</select></label>';
  }).join('')+'</div>';
}

function renderPreview(result, files){
  var changes=result.changes||[];
  var choices=result.class_choices||[];
  var baseCanCommit=!!result.can_commit && !result.blocked;
  var canCommit=baseCanCommit && !choices.length;
  var m=NS.modal(
    '<div class="modal__icon">'+NS.icon('wallet')+'</div>'+
    '<h3>مراجعة تحديث Excel</h3>'+
    '<p class="excel-review__intro">الشهر المستهدف: <strong>'+text(result.target_label||result.target_ym)+'</strong>. لن يتغير أي شيء قبل الضغط على اعتماد التحديث.</p>'+
    '<div class="excel-review__meta"><span>'+NS.icon('book')+' '+files.length+' ملف</span><span>'+NS.icon('users')+' '+(result.summary&&result.summary.rows||0)+' صف مقروء</span><span>'+NS.icon('refresh')+' '+changes.length+' تغيير</span></div>'+
    warningsHtml(result.warnings)+
    classChoicesHtml(choices)+
    '<div class="excel-review__list">'+(changes.length?changes.map(changeHtml).join(''):'<div class="empty"><h4>لا توجد تغييرات</h4><p>الملفات لا تحتوي على بيانات جديدة لهذا الشهر.</p></div>')+'</div>'+
    '<div class="actions">'+
      '<button class="btn btn--primary" data-commit '+(canCommit?'':'disabled')+'>'+NS.icon('check')+' اعتماد التحديث</button>'+
      '<button class="btn btn--ghost" data-cancel>إلغاء</button>'+
    '</div>'
  );
  var commit=m.el.querySelector('[data-commit]');
  var cancel=m.el.querySelector('[data-cancel]');
  if(cancel) cancel.addEventListener('click',m.close);
  var selects=Array.prototype.slice.call(m.el.querySelectorAll('[data-class-student]'));
  function selectedClasses(){
    var map={};
    selects.forEach(function(select){ if(select.value) map[select.getAttribute('data-class-student')]=Number(select.value); });
    return map;
  }
  function updateCommit(){ if(commit) commit.disabled=!baseCanCommit||selects.some(function(select){ return !select.value; }); }
  selects.forEach(function(select){ select.addEventListener('change',updateCommit); });
  updateCommit();
  if(commit&&baseCanCommit) commit.addEventListener('click',function(){
    commit.disabled=true;
    commit.innerHTML=NS.icon('refresh')+' جاري الاعتماد...';
    NS.api(ENDPOINT,{mt:NS.token('mt'),mode:'commit',files:files,class_map:selectedClasses()}).then(function(done){
      if(!done||done.ok===false) throw new Error((done&&done.error)||'تعذر اعتماد التحديث');
      m.close();
      NS.toast('تم تحديث '+(done.target_label||done.target_ym||'الشهر')+' بنجاح','ok');
      if(typeof window.__refreshDashboard==='function') window.__refreshDashboard();
    }).catch(function(err){
      commit.disabled=false;
      commit.innerHTML=NS.icon('check')+' اعتماد التحديث';
      NS.toast(err.message||'تعذر اعتماد التحديث','err');
    });
  });
}

function open(token){
  var input=document.createElement('input');
  input.type='file';
  input.accept='.xlsx,.xlsm,.xls,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel';
  input.multiple=true;
  input.addEventListener('change',function(){
    readFiles(input.files).then(function(files){
      NS.toast('جاري قراءة الملفات ومقارنتها بالبيانات الحالية...','ok');
      return NS.api(ENDPOINT,{mt:token,mode:'preview',files:files}).then(function(result){
        if(!result||!result.ok) throw new Error((result&&result.error)||'تعذر قراءة ملف Excel');
        renderPreview(result,files);
      });
    }).catch(function(err){ NS.toast(err.message||'تعذر قراءة الملف','err'); });
  });
  input.click();
}


/* ---- مزامنة من لينك Google Sheets -----------------------------------
   الشيت بيتسحب من الخادم كملف xlsx، وبعدها بيعدّي على نفس مسار
   المعاينة والاعتماد بتاع Excel — مفيش منطق استيراد مكرر. */
function askSheetUrl(token,current){
  return new Promise(function(resolve){
    var m=NS.modal(
      '<div class="modal__icon">'+NS.icon('ledger')+'</div>'+
      '<h3>لينك جوجل شيت</h3>'+
      '<p class="excel-review__intro">الصقي رابط الشيت مرة واحدة وهيتحفظ. لازم يكون مشاركته <strong>أي شخص لديه الرابط — مُشاهد</strong>.</p>'+
      '<input type="url" dir="ltr" id="sheet-url-input" class="input" placeholder="https://docs.google.com/spreadsheets/d/..." value="'+NS.attr(current||'')+'" style="width:100%"/>'+
      '<div class="actions">'+
        '<button class="btn btn--primary" data-save>'+NS.icon('check')+' حفظ ومزامنة</button>'+
        '<button class="btn btn--ghost" data-cancel>إلغاء</button>'+
      '</div>'
    );
    var done=false;
    var input=m.el.querySelector('#sheet-url-input');
    var save=m.el.querySelector('[data-save]');
    var cancel=m.el.querySelector('[data-cancel]');
    function finish(value){ if(done) return; done=true; m.close(); resolve(value); }
    if(cancel) cancel.addEventListener('click',function(){ finish(null); });
    if(save) save.addEventListener('click',function(){
      var url=(input&&input.value||'').trim();
      if(!url){ NS.toast('الصقي رابط الشيت أولاً','err'); return; }
      save.disabled=true;
      save.innerHTML=NS.icon('refresh')+' جاري الحفظ...';
      NS.api(SHEET_ENDPOINT,{mt:token,action:'save',url:url}).then(function(res){
        if(!res||!res.ok) throw new Error((res&&res.error)||'تعذر حفظ الرابط');
        finish(res.url);
      }).catch(function(err){
        save.disabled=false;
        save.innerHTML=NS.icon('check')+' حفظ ومزامنة';
        NS.toast(err.message||'تعذر حفظ الرابط','err');
      });
    });
    if(input) input.focus();
  });
}

function syncSheet(token,button){
  NS.toast('جاري سحب الشيت من جوجل ومقارنته بالبيانات الحالية...','ok');
  return NS.api(SHEET_ENDPOINT,{mt:token,action:'fetch'}).then(function(res){
    if(!res||!res.ok) throw new Error((res&&res.error)||'تعذر سحب الشيت');
    var files=res.files||[];
    if(!files.length) throw new Error('الشيت رجع فاضياً');
    return NS.api(ENDPOINT,{mt:token,mode:'preview',files:files}).then(function(result){
      if(!result||!result.ok) throw new Error((result&&result.error)||'تعذر قراءة الشيت');
      renderPreview(result,files);
    });
  });
}

function openSheet(token){
  var button=document.getElementById('sheet-sync-btn');
  if(button) button.disabled=true;
  function release(){ if(button) button.disabled=false; }
  NS.api(SHEET_ENDPOINT,{mt:token,action:'get'}).then(function(res){
    if(!res||!res.ok) throw new Error((res&&res.error)||'تعذر قراءة إعدادات الشيت');
    if(res.url) return syncSheet(token,button);
    return askSheetUrl(token,'').then(function(url){
      if(!url) return null;
      return syncSheet(token,button);
    });
  }).catch(function(err){
    NS.toast(err.message||'تعذر مزامنة الشيت','err');
  }).then(release,release);
}

function exportAll(token){
  var button=document.getElementById('excel-export-btn');
  if(button) button.disabled=true;
  NS.toast('جاري تجهيز ملف Excel الكامل...','ok');
  fetch('/api/manager/excel/export?mt='+encodeURIComponent(token),{credentials:'same-origin'}).then(function(response){
    if(!response.ok) throw new Error('تعذر تصدير بيانات الموقع');
    return response.blob();
  }).then(function(blob){
    var url=URL.createObjectURL(blob), a=document.createElement('a');
    a.href=url; a.download='montessori-export-'+new Date().toISOString().slice(0,10)+'.xlsx';
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    NS.toast('تم تنزيل ملف Excel بكل البيانات','ok');
  }).catch(function(err){ NS.toast(err.message||'تعذر التصدير','err'); }).finally(function(){ if(button) button.disabled=false; });
}

NS.excelSync={open:open,openSheet:openSheet,exportAll:exportAll,setSheetUrl:askSheetUrl};
})();
