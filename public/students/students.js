(function(){
var I=NS.icon, TOKEN=NS.token('mt'), DATA=null, Q='', LINK='all', GRADE='all', QUICK='all';
var app=document.getElementById('app');
var LEVELS=[['','بدون جريد'],['prekg','Pre-KG'],['kg1','KG1'],['kg2','KG2'],['kg3','KG3']];

var AR=['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'];
/* تاريخ اليوم من السيرفر (توقيت الرياض) — لا نعتمد على ساعة الجهاز (قد تكون غلط) */
var SERVER_TODAY=null;
try{ NS.api('/api/today',{}).then(function(d){ if(d&&d.date) SERVER_TODAY=d.date; }).catch(function(){}); }catch(e){}
function todayISO(){ if(SERVER_TODAY) return SERVER_TODAY; var d=new Date(); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }
function plusMonthISO(iso){ var base=iso||todayISO(); var d=new Date(base); d.setMonth(d.getMonth()+1); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }
function fmtD(iso){ return NS.fmtShort?NS.fmtShort(iso):iso; }

if(!TOKEN){ gate(); } else { boot(); }
function gate(){ app.innerHTML=''; var m=document.createElement('div'); app.appendChild(m);
  NS.gate(m,{title:'الطلاب',body:'سجّلي دخولك كمديرة أو صاحبة الحضانة لإدارة الطلاب والرسوم.'}); }
function netError(){ app.innerHTML=''; var m=document.createElement('div'); m.className='app-main app-narrow'; app.appendChild(m);
  m.innerHTML='<div class="card card--pad" style="text-align:center"><div class="modal__icon" style="margin:0 auto 14px">'+I('wifi')+'</div>'+
  '<h3 style="margin-bottom:8px">تعذّر الاتصال</h3><p class="muted" style="margin-bottom:20px">حاولي مرة أخرى.</p>'+
  '<button class="btn btn--primary btn--block btn--lg" data-reload="1">'+I('refresh')+' إعادة المحاولة</button></div>'; }

function boot(){
  document.getElementById('boot').innerHTML=NS.skelCard()+NS.skelCard();
  NS.api('/api/manager/students',{mt:TOKEN}).then(function(d){
    if(!d||!d.ok){ NS.clearToken('mt'); gate(); return; }
    DATA=d; render();
  }).catch(function(err){ if(err.type==='auth'){ NS.clearToken('mt'); gate(); } else netError(); });
}

function statusBadge(s){
  if(s.status==='overdue') return '<span class="pay-badge pay-over">متأخّر '+Math.abs(s.days)+' يوم</span>';
  if(s.status==='due_soon') return '<span class="pay-badge pay-soon">'+(s.days<=0?'مستحقّ اليوم':('باقٍ '+s.days+' يوم')) +'</span>';
  if(s.status==='paid') return '<span class="pay-badge pay-paid">مُسدَّد'+(s.paid_until?(' حتى '+fmtD(s.paid_until)):'')+'</span>';
  return '<span class="pay-badge pay-none">لم يُسجَّل دفع</span>';
}

var XLSX_ENC = new TextEncoder();
var XLSX_CRC_TABLE = (function(){
  var table = new Uint32Array(256);
  for(var i=0;i<256;i++){
    var c = i;
    for(var k=0;k<8;k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    table[i] = c >>> 0;
  }
  return table;
})();
function xlsxBytes(value){ return XLSX_ENC.encode(String(value)); }
function xlsxU16(value){ var b=new Uint8Array(2); new DataView(b.buffer).setUint16(0, value, true); return b; }
function xlsxU32(value){ var b=new Uint8Array(4); new DataView(b.buffer).setUint32(0, value >>> 0, true); return b; }
function xlsxConcat(parts){
  var size = 0;
  for(var i=0;i<parts.length;i++) size += parts[i].length;
  var out = new Uint8Array(size), off = 0;
  for(var j=0;j<parts.length;j++){ out.set(parts[j], off); off += parts[j].length; }
  return out;
}
function xlsxCrc32(bytes){
  var crc = 0xffffffff;
  for(var i=0;i<bytes.length;i++) crc = XLSX_CRC_TABLE[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}
function xlsxEscapeXml(value){
  return String(value)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;')
    .replace(/'/g,'&apos;');
}
function xlsxColumnName(index){
  var n = index + 1, name = '';
  while(n > 0){
    var rem = (n - 1) % 26;
    name = String.fromCharCode(65 + rem) + name;
    n = Math.floor((n - 1) / 26);
  }
  return name;
}
function xlsxCellXml(value, ref){
  if(value === null || value === undefined || value === '') return '<c r="'+ref+'" t="inlineStr"><is><t></t></is></c>';
  if(typeof value === 'number' && isFinite(value)) return '<c r="'+ref+'"><v>'+value+'</v></c>';
  if(value instanceof Date) return '<c r="'+ref+'" t="inlineStr"><is><t>'+xlsxEscapeXml(value.toISOString())+'</t></is></c>';
  return '<c r="'+ref+'" t="inlineStr"><is><t xml:space="preserve">'+xlsxEscapeXml(value)+'</t></is></c>';
}
function buildSheetXml(headers, rows){
  var headerRow = '';
  for(var i=0;i<headers.length;i++) headerRow += xlsxCellXml(headers[i], xlsxColumnName(i)+'1');
  var body = '';
  for(var r=0;r<rows.length;r++){
    var cells = '';
    for(var c=0;c<rows[r].length;c++) cells += xlsxCellXml(rows[r][c], xlsxColumnName(c)+(r+2));
    body += '<row r="'+(r+2)+'">'+cells+'</row>';
  }
  var lastColumn = xlsxColumnName(Math.max(headers.length - 1, 0));
  var lastRow = rows.length + 1;
  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' +
    '<dimension ref="A1:' + lastColumn + lastRow + '"/>' +
    '<sheetViews><sheetView workbookViewId="0"/></sheetViews>' +
    '<sheetFormatPr defaultRowHeight="15"/>' +
    '<sheetData><row r="1">' + headerRow + '</row>' + body + '</sheetData>' +
    '</worksheet>';
}
function zipStore(files){
  var localParts = [], centralParts = [], offset = 0;
  for(var i=0;i<files.length;i++){
    var nameBytes = xlsxBytes(files[i].name);
    var contentBytes = xlsxBytes(files[i].content);
    var crc = xlsxCrc32(contentBytes);
    var local = xlsxConcat([
      xlsxU32(0x04034b50), xlsxU16(20), xlsxU16(0), xlsxU16(0), xlsxU16(0), xlsxU16(0),
      xlsxU32(crc), xlsxU32(contentBytes.length), xlsxU32(contentBytes.length),
      xlsxU16(nameBytes.length), xlsxU16(0), nameBytes, contentBytes
    ]);
    localParts.push(local);
    centralParts.push(xlsxConcat([
      xlsxU32(0x02014b50), xlsxU16(20), xlsxU16(20), xlsxU16(0), xlsxU16(0), xlsxU16(0), xlsxU16(0),
      xlsxU32(crc), xlsxU32(contentBytes.length), xlsxU32(contentBytes.length),
      xlsxU16(nameBytes.length), xlsxU16(0), xlsxU16(0), xlsxU16(0), xlsxU16(0), xlsxU32(0),
      xlsxU32(offset), nameBytes
    ]));
    offset += local.length;
  }
  var central = xlsxConcat(centralParts);
  var end = xlsxConcat([
    xlsxU32(0x06054b50), xlsxU16(0), xlsxU16(0), xlsxU16(files.length), xlsxU16(files.length),
    xlsxU32(central.length), xlsxU32(offset), xlsxU16(0)
  ]);
  return new Blob(localParts.concat([central, end]), {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  });
}
function downloadStudentsXlsx(rows){
  var blob = zipStore([
    { name: '[Content_Types].xml', content: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>' },
    { name: '_rels/.rels', content: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>' },
    { name: 'xl/workbook.xml', content: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Students" sheetId="1" r:id="rId1"/></sheets></workbook>' },
    { name: 'xl/_rels/workbook.xml.rels', content: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>' },
    { name: 'xl/worksheets/sheet1.xml', content: buildSheetXml(['اسم الطالب','الفصل','ولي الأمر','الجوال','الحالة','الرسوم الشهرية','آخر دفعة','إجمالي المدفوع','مدفوع حتى','تاريخ الالتحاق'], rows) },
    { name: 'xl/styles.xml', content: '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts><fills count="1"><fill><patternFill patternType="none"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs></styleSheet>' }
  ]);
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'students-' + todayISO() + '.xlsx';
  document.body.appendChild(a);
  a.click();
  setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}
function exportStudents(){
  var list=filtered();
  if(!list.length){ NS.toast('لا يوجد طلاب للتصدير','err'); return; }
  downloadStudentsXlsx(list.map(function(s){
    return [
      s.name || '—',
      s.class_name || 'بدون فصل',
      personName(s,['guardian_name','parent_name']) || '—',
      s.guardian_phone || '—',
      s.status==='overdue'?'متأخر':(s.status==='due_soon'?'قرب موعده':(s.status==='paid'?'مُسدَّد':'لم يُسجَّل دفع')),
      s.fees || 0,
      s.last_amount || 0,
      s.total_paid || 0,
      s.paid_until ? fmtD(s.paid_until) : '—',
      s.joining_date ? fmtD(s.joining_date) : '—'
    ];
  }));
}

function render(){
  var st=DATA.students||[];
  var overdue=st.filter(function(s){return s.status==='overdue';}).length;
  var soon=st.filter(function(s){return s.status==='due_soon';}).length;
  var linked=st.filter(function(s){return !!s.linked;}).length;
  var h=NS.appbar({sub:'الطلاب', nav:NS.adminNav('students')})+
    '<main class="app-main">'+
      '<div class="page-head between" style="flex-wrap:wrap;gap:12px">'+
        '<div><h1>الطلاب</h1><div class="sub">أضيفي الطلاب، وسجّلي رسومهم ومتى دفعوا.</div></div>'+
        '<div style="display:flex;gap:10px;flex-wrap:wrap">'+
          '<button class="btn btn--soft" id="export">تصدير Excel</button>'+
          '<button class="btn btn--primary" id="add">'+I('plus')+' طالب جديد</button>'+
        '</div>'+
      '</div>'+
      '<div class="st-summary">'+
        stat('is-forest','users','إجمالي الطلاب',st.length,'all')+
        stat(linked?'is-forest':'is-amber','user','مرتبط بولي الأمر',linked,'linked')+
        stat(st.length-linked?'is-amber':'is-forest','alert','غير مرتبط',st.length-linked,'unlinked')+
        stat(overdue?'is-danger':'is-forest','alert','متأخرو السداد',overdue,'overdue')+
        stat(soon?'is-amber':'is-forest','clock','قرب موعدهم',soon,'due_soon')+
      '</div>'+
      '<div class="st-toolbar">'+
        '<div class="search"><input class="input" id="q" type="search" placeholder="ابحثي باسم الطالب أو ولي الأمر…" value="'+NS.attr(Q)+'"/></div>'+
        '<div class="st-filter" id="link-filter">'+linkSeg('all','كل الربط')+linkSeg('linked','مرتبط بولي الأمر')+linkSeg('unlinked','غير مرتبط')+'</div>'+
      '</div>'+
      '<div id="grade-tabs"></div>'+
      '<div class="st-list-head" id="list-head"></div>'+
      '<div id="list"></div>'+
  '</main>';
  app.innerHTML=h; NS.wireLogout('mt');
  document.getElementById('export').addEventListener('click',exportStudents);
  document.getElementById('add').addEventListener('click',function(){ edit(null); });
  [].forEach.call(document.querySelectorAll('[data-stat]'),function(b){b.addEventListener('click',function(){applyStat(b.getAttribute('data-stat'));});});
  var q=document.getElementById('q');
  q.addEventListener('input',function(){ Q=q.value; renderList(); });
  [].forEach.call(document.querySelectorAll('#link-filter button'),function(b){b.addEventListener('click',function(){LINK=b.dataset.link;GRADE='all';QUICK='all';render();});});
  renderList();
}
function linkSeg(v,label){return '<button type="button" data-link="'+v+'" class="'+(LINK===v?'on':'')+'">'+NS.esc(label)+'</button>';}
function linkOk(s){return LINK==='all'||(LINK==='linked'&&!!s.linked)||(LINK==='unlinked'&&!s.linked);}
function quickOk(s){return QUICK==='all'||s.status===QUICK;}
function statOn(key){
  if(key==='all') return QUICK==='all'&&LINK==='all';
  if(key==='linked') return QUICK==='all'&&LINK==='linked';
  if(key==='unlinked') return QUICK==='all'&&LINK==='unlinked';
  return QUICK===key;
}
function applyStat(key){
  if(key==='linked'||key==='unlinked'){LINK=key;QUICK='all';}
  else {QUICK=key||'all';LINK='all';}
  GRADE='all';
  render();
}
function filterTitle(){
  var title;
  if(QUICK==='overdue') return 'متأخرو السداد';
  if(QUICK==='due_soon') return 'قرب موعدهم';
  if(LINK==='linked') title='الطلاب المرتبطون بولي الأمر';
  else if(LINK==='unlinked') title='الطلاب غير المرتبطين';
  else title='كل الطلاب';
  return GRADE==='all'?title:(title+' · '+levelLabel(GRADE));
}
function stat(accent,icon,label,value,key){
  return '<button type="button" data-stat="'+NS.attr(key)+'" class="stat '+accent+(statOn(key)?' is-on':'')+'"><div class="k">'+I(icon)+'<span>'+NS.esc(label)+'</span></div>'+ 
    '<div class="v tabnum">'+value+'</div></button>';
}

function gradeKey(s){return s.level||'__none';}
function gradeLabel(s){return s.level_label||levelLabel(s.level||'__none');}
function levelLabel(v){
  if(v==='__none')return 'بدون جريد';
  for(var i=0;i<LEVELS.length;i++){if(LEVELS[i][0]===v)return LEVELS[i][1];}
  return v||'بدون جريد';
}
function levelOptions(v){
  return LEVELS.map(function(x){return '<option value="'+NS.attr(x[0])+'"'+(x[0]===(v||'')?' selected':'')+'>'+NS.esc(x[1])+'</option>';}).join('');
}
function gradeTabs(base){
  var map={}, order=[];
  base.forEach(function(s){var k=gradeKey(s);if(!map[k]){map[k]={key:k,label:gradeLabel(s),count:0};order.push(map[k]);}map[k].count++;});
  order.sort(function(a,b){return a.label.localeCompare(b.label,'ar');});
  var tabs=[{key:'all',label:'كل الجريدات',count:base.length}].concat(order);
  return '<div class="st-grade-tabs">'+tabs.map(function(t){
    return '<button type="button" data-grade="'+NS.attr(t.key)+'" class="'+(t.key===GRADE?'is-on':'')+'">'+
      '<span>'+NS.esc(t.label)+'</span><span class="count tabnum">'+t.count+'</span></button>';
  }).join('')+'</div>';
}
function saveLevel(s,value,select){
  if(!s||!select)return;
  var prev=s.level||'';
  var box=select.closest('.st-grade-field');
  select.disabled=true;if(box)box.classList.add('is-saving');
  NS.api('/api/manager/student/save',{mt:TOKEN,id:s.id,name:s.name||'',
    class_id:s.class_id||'',guardian_name:s.guardian_name||'',guardian_phone:s.guardian_phone||'',
    parent_email:s.parent_email||'',father_name:s.father_name||'',mother_name:s.mother_name||'',
    fees:s.fees||0,joining_date:s.joining_date||'',level:value}).then(function(r){
      select.disabled=false;if(box)box.classList.remove('is-saving');
      if(r&&r.ok){s.level=value;s.level_label=value?levelLabel(value):'';NS.toast('تم تحديث الجريد','ok');renderList();}
      else{select.value=prev;NS.toast((r&&r.error)||'تعذّر حفظ الجريد','err');}
    }).catch(function(){
      select.disabled=false;if(box)box.classList.remove('is-saving');select.value=prev;
      NS.toast('تعذّر حفظ الجريد','err');
    });
}

function searchOk(s,q){
  return ([s.name,s.guardian_name,s.father_name,s.mother_name,s.guardian_phone,s.parent_name,s.parent_email].join(' ')).indexOf(q)>=0;
}
function baseFiltered(){
  var q=Q.trim();
  var list=(DATA.students||[]).slice().sort(function(a,b){
    var rank={overdue:0,due_soon:1,none:2,paid:3};
    return (rank[a.status]-rank[b.status]) || a.name.localeCompare(b.name,'ar');
  });
  list=list.filter(linkOk);
  list=list.filter(quickOk);
  if(q) list=list.filter(function(s){return searchOk(s,q);});
  return list;
}
function filtered(){
  var list=baseFiltered();
  if(GRADE!=='all') list=list.filter(function(s){return gradeKey(s)===GRADE;});
  return list;
}
function personName(s,keys){
  for(var i=0;i<keys.length;i++){var v=(s[keys[i]]||'').trim();if(v)return v;}
  return '';
}
function fitClass(value){
  var n=(value||'').trim().length;
  return n>34?' is-xxl':(n>25?' is-xl':(n>17?' is-long':''));
}
function studentName(name){
  return '<b class="name-fit'+fitClass(name)+'" title="'+NS.attr(name||'')+'">'+NS.esc(name||'—')+'</b>';
}
function familyRow(label,value){
  var shown=value||'—';
  return '<div class="fr"><span class="fl">'+NS.esc(label)+'</span><b class="fv'+fitClass(value)+(value?'':' is-empty')+'" title="'+NS.attr(shown)+'">'+NS.esc(shown)+'</b></div>';
}
function familyRows(s){
  var father=personName(s,['father_name','father','dad_name','parent_father_name']);
  var mother=personName(s,['mother_name','mother','mom_name','parent_mother_name']);
  return '<div class="st-family">'+familyRow('اسم الأب',father)+familyRow('اسم الأم',mother)+'</div>';
}

function renderList(){
  var L=document.getElementById('list'); if(!L) return;
  var base=baseFiltered();
  var list=filtered();
  var H=document.getElementById('list-head');
  var T=document.getElementById('grade-tabs');
  if(T){T.innerHTML=gradeTabs(base);T.querySelectorAll('[data-grade]').forEach(function(b){b.onclick=function(){GRADE=b.dataset.grade;renderList();};});}
  if(H) H.innerHTML='<b>'+NS.esc(filterTitle())+'</b><span><span class="tabnum">'+list.length+'</span> طالب مطابق</span>';
  if(!(DATA.students||[]).length){ L.innerHTML=NS.empty('users','لا يوجد طلاب بعد','اضغطي «طالب جديد» لإضافة أول طالب.'); return; }
  if(!list.length){ L.innerHTML=NS.empty('search','لا نتائج','جرّبي بحثاً آخر.'); return; }
  var h='<div class="st-grid">';
  list.forEach(function(s){
    var initial=(s.name||'؟').trim().charAt(0);
    var linkTxt=s.linked?'مرتبط بولي أمر':(s.link_state==='pending'?'بانتظار الربط':'غير مرتبط');
    h+='<div class="st-card">'+
      '<div class="top"><span class="avatar avatar--sm">'+NS.esc(initial)+'</span>'+
        '<div class="who">'+studentName(s.name)+'<span>'+(s.class_name?NS.esc(s.class_name):'بدون فصل')+
          (s.level_label?' · '+NS.esc(s.level_label):'')+
          ' · <span class="'+(s.linked?'is-linked':'is-unlinked')+'">'+NS.esc(linkTxt)+'</span></span></div>'+ 
        statusBadge(s)+'</div>'+familyRows(s)+
      '<div class="st-grade-field"><label for="student-grade-'+s.id+'">الجريد</label><select class="input" id="student-grade-'+s.id+'" data-level-select="'+s.id+'">'+levelOptions(s.level)+'</select></div>'+ 
      '<div class="st-rows">'+
        '<div class="r"><span class="l">تاريخ الالتحاق</span><b class="tabnum">'+(s.joining_date?fmtD(s.joining_date):'—')+'</b></div>'+ 
        '<div class="r"><span class="l">الرسوم الشهرية المتفق عليها</span><b class="tabnum">'+NS.riyal(s.fees)+'</b></div>'+ 
        '<div class="r"><span class="l">رسوم الكتب</span><b class="tabnum">'+NS.riyal(Number(s.books_due||0))+'</b></div>'+
        '<div class="r"><span class="l">مدفوع الكتب</span><b class="tabnum">'+NS.riyal(s.books_paid||0)+'</b></div>'+
        '<div class="r"><span class="l">المتبقي من الكتب</span><b class="tabnum '+(s.books_remaining>0?'is-unlinked':'is-linked')+'">'+NS.riyal(s.books_remaining||0)+'</b></div>'+
        '<div class="r"><span class="l">آخر دفعة</span><b class="tabnum">'+(s.last_date?(NS.riyal(s.last_amount)+' · '+fmtD(s.last_date)):'—')+'</b></div>'+ 
        '<div class="r"><span class="l">إجمالي المدفوع</span><b class="tabnum">'+NS.riyal(s.total_paid)+'</b></div>'+ 
      '</div>'+ 
      '<div class="st-actions">'+
        '<button class="btn btn--primary btn--sm" data-pay="'+NS.attr(s.id)+'">'+I('wallet')+' تسجيل دفعة</button>'+ 
        (s.books_remaining>0.01?'<button class="btn btn--soft btn--sm" data-book-pay="'+NS.attr(s.id)+'">'+I('book')+' دفع الكتب</button>':'')+
        '<button class="btn btn--soft btn--sm" data-hist="'+NS.attr(s.id)+'">'+I('clock')+' الدفعات</button>'+ 
        '<button class="btn btn--soft btn--sm" data-book-hist="'+NS.attr(s.id)+'">'+I('book')+' دفعات الكتب</button>'+ 
        '<button class="btn btn--soft btn--sm" data-edit="'+NS.attr(s.id)+'">'+I('user')+' تعديل</button>'+ 
      '</div>'+ 
      '<div class="st-wa'+(s.guardian_phone?'':' is-empty')+'">'+
        (s.guardian_phone?('<button class="btn btn--soft btn--block" data-wa="'+NS.attr(s.id)+'">'+I('whatsapp')+'</button>'):'<button class="btn btn--soft btn--block" type="button" tabindex="-1">'+I('whatsapp')+'</button>')+
      '</div></div>';
  });
  h+='</div>'; L.innerHTML=h;
  bind(L,'data-pay',function(id){ pay(get(id)); });
  bind(L,'data-book-pay',function(id){ payBooks(get(id)); });
  bind(L,'data-hist',function(id){ history(get(id)); });
  bind(L,'data-book-hist',function(id){ history(get(id),'books'); });
  bind(L,'data-edit',function(id){ edit(get(id)); });
  bind(L,'data-wa',function(id){ remind(get(id)); });
  L.querySelectorAll('[data-level-select]').forEach(function(select){select.onchange=function(){saveLevel(get(select.dataset.levelSelect),select.value,select);};});
}
function bind(root,attr,fn){ [].forEach.call(root.querySelectorAll('['+attr+']'),function(b){ b.addEventListener('click',function(){ fn(b.getAttribute(attr)); }); }); }
function get(id){ return (DATA.students||[]).filter(function(s){return String(s.id)===String(id);})[0]; }
function refreshRow(row){ if(!row) return boot(); var i=DATA.students.findIndex(function(s){return s.id===row.id;}); if(i>=0) DATA.students[i]=row; renderList(); }

/* ---- add / edit student ---- */
function edit(s){
  var opts='<option value="">— بدون فصل —</option>';
  (DATA.classes||[]).forEach(function(c){ opts+='<option value="'+c.id+'"'+(s&&s.class_id===c.id?' selected':'')+'>'+NS.esc(c.name)+'</option>'; });
  var levels=levelOptions(s?s.level:'');
  var m=NS.modal(
    '<div class="modal__icon">'+I(s?'user':'plus')+'</div>'+
    '<h3>'+(s?'تعديل بيانات '+NS.esc(s.name):'طالب جديد')+'</h3>'+
    '<div class="field"><label>اسم الطالب *</label><input class="input" id="f-name" value="'+NS.attr(s?s.name:'')+'" placeholder="الاسم الكامل"/></div>'+
    '<div class="field"><label>الفصل</label><select class="input" id="f-class">'+opts+'</select></div>'+
    '<div class="field"><label>الجريد</label><select class="input" id="f-level">'+levels+'</select></div>'+ 
    '<div class="field"><label>الرسوم الشهرية (ر.س)</label><input class="input" type="number" min="0" id="f-fees" value="'+(s?s.fees:'')+'" placeholder="مثال: 1500"/></div>'+ 
    '<div class="field"><label>اسم الأب</label><input class="input" id="f-father" value="'+NS.attr(s?(s.father_name||''):'')+'"/></div>'+ 
    '<div class="field"><label>اسم الأم</label><input class="input" id="f-mother" value="'+NS.attr(s?(s.mother_name||''):'')+'"/></div>'+ 
    '<div class="field"><label>اسم ولي الأمر</label><input class="input" id="f-gn" value="'+NS.attr(s?s.guardian_name:'')+'"/></div>'+ 
    '<div class="field"><label>البريد الإلكتروني لولي الأمر</label><input class="input" id="f-ge" type="email" value="'+NS.attr(s?s.parent_email:'')+'" placeholder="parent@email.com"/></div>'+ 
    '<div class="field"><label>جوال ولي الأمر</label><input class="input" id="f-gp" type="tel" inputmode="tel" value="'+NS.attr(s?s.guardian_phone:'')+'" placeholder="05xxxxxxxx"/></div>'+ 
    '<div class="field"><label>تاريخ الالتحاق</label><input class="input" type="date" id="f-jd" value="'+NS.attr(s?s.joining_date:todayISO())+'"/></div>'+
    '<div class="actions"><button class="btn btn--primary" data-ok>'+I('check')+' حفظ</button>'+
      (s?'<button class="btn btn--ghost" data-del style="color:var(--danger)">حذف</button>':'')+
      '<button class="btn btn--ghost" data-cancel>إلغاء</button></div>');
  m.el.querySelector('[data-cancel]').addEventListener('click',m.close);
  if(s) m.el.querySelector('[data-del]').addEventListener('click',function(){
    m.close();
    NS.confirm({title:'حذف الطالب نهائياً؟',body:'سيُخفى '+NS.esc(s.name)+' من قوائم الطلاب ومن كشوف الحسابات للشهور المفتوحة. الشهور المُقفَلة تحتفظ بسجله ولا تُحذف الدفعات السابقة.',okText:'حذف',danger:true}).then(function(ok){
      if(!ok) return;
      NS.api('/api/manager/student/delete',{mt:TOKEN,id:s.id}).then(function(r){ if(r&&r.ok){ NS.toast('تم الحذف'); boot(); } else NS.toast((r&&r.error)||'خطأ','err'); });
    });
  });
  m.el.querySelector('[data-ok]').addEventListener('click',function(){
    var btn=this; if(btn.classList.contains('is-loading')) return;
    var name=m.el.querySelector('#f-name').value.trim();
    if(!name){ NS.toast('اكتبي اسم الطالب','err'); return; }
    btn.classList.add('is-loading');
    NS.api('/api/manager/student/save',{mt:TOKEN, id:s?s.id:'', name:name,
      class_id:m.el.querySelector('#f-class').value, fees:m.el.querySelector('#f-fees').value,
      level:m.el.querySelector('#f-level').value,
      father_name:m.el.querySelector('#f-father').value,
      mother_name:m.el.querySelector('#f-mother').value,
      guardian_name:m.el.querySelector('#f-gn').value, parent_email:m.el.querySelector('#f-ge').value,
      guardian_phone:m.el.querySelector('#f-gp').value,
      joining_date:m.el.querySelector('#f-jd').value})
    .then(function(r){ if(r&&r.ok){ m.close(); NS.toast(s?'تم الحفظ':'تمت إضافة الطالب'); boot(); } else { btn.classList.remove('is-loading'); NS.toast((r&&r.error)||'خطأ','err'); } })
    .catch(function(){ btn.classList.remove('is-loading'); NS.toast('تعذّر الحفظ','err'); });
  });
}

/* ---- record a payment ---- */
function pay(s){
  var defUntil = plusMonthISO(s.paid_until && s.paid_until>=todayISO() ? s.paid_until : todayISO());
  var m=NS.modal(
    '<div class="modal__icon">'+I('wallet')+'</div>'+
    '<h3>تسجيل دفعة — '+NS.esc(s.name)+'</h3>'+
    '<p class="muted" style="font-size:.86rem;margin-bottom:6px">الرسوم الشهرية: '+NS.riyal(s.fees)+'</p>'+
    '<div class="field"><label>المبلغ المدفوع (ر.س) *</label><input class="input" type="number" min="1" id="p-amt" value="'+(s.fees||'')+'"/></div>'+
    '<div class="field"><label>تاريخ الدفع</label><input class="input" type="date" id="p-date" value="'+todayISO()+'"/></div>'+
    '<div class="field"><label>مدفوع حتى (موعد التجديد القادم)</label><input class="input" type="date" id="p-until" value="'+defUntil+'"/></div>'+
    '<div class="field"><label>طريقة الدفع</label><select class="input" id="p-method">'+
      '<option value="cash">نقداً</option><option value="transfer">تحويل</option><option value="card">شبكة</option><option value="other">أخرى</option></select></div>'+
    '<div class="field"><label>ملاحظة (اختياري)</label><input class="input" id="p-note" placeholder="مثال: رسوم شهر يوليو"/></div>'+
    '<div class="actions"><button class="btn btn--primary" data-ok>'+I('check')+' تأكيد الدفعة</button><button class="btn btn--ghost" data-cancel>إلغاء</button></div>');
  m.el.querySelector('[data-cancel]').addEventListener('click',m.close);
  m.el.querySelector('[data-ok]').addEventListener('click',function(){
    var btn=this; if(btn.classList.contains('is-loading')) return;
    var amt=parseFloat(m.el.querySelector('#p-amt').value);
    if(!(amt>0)){ NS.toast('اكتبي مبلغاً صحيحاً','err'); return; }
    btn.classList.add('is-loading');
    NS.api('/api/manager/student/pay',{mt:TOKEN, student_id:s.id, amount:amt,
      date:m.el.querySelector('#p-date').value, paid_until:m.el.querySelector('#p-until').value,
      method:m.el.querySelector('#p-method').value, note:m.el.querySelector('#p-note').value})
    .then(function(r){ if(r&&r.ok){ m.close(); NS.toast('تم تسجيل الدفعة ✔'); refreshRow(r.row); } else { btn.classList.remove('is-loading'); NS.toast((r&&r.error)||'خطأ','err'); } })
    .catch(function(){ btn.classList.remove('is-loading'); NS.toast('تعذّر التسجيل','err'); });
  });
}

function payBooks(s){
  var remaining=Number(s.books_remaining||0);
  var m=NS.modal(
    '<div class="modal__icon">'+I('book')+'</div>'+
    '<h3>دفع رسوم الكتب — '+NS.esc(s.name)+'</h3>'+
    '<p class="muted" style="font-size:.86rem;margin-bottom:6px">المطلوب: '+NS.riyal(Number(s.books_due||0))+' · المدفوع: '+NS.riyal(s.books_paid||0)+' · المتبقي: '+NS.riyal(remaining)+'</p>'+
    '<div class="field"><label>المبلغ المدفوع (ر.س) *</label><input class="input" type="number" min="1" max="'+remaining+'" id="bp-amt" value="'+remaining+'"/></div>'+
    '<div class="field"><label>تاريخ الدفع</label><input class="input" type="date" id="bp-date" value="'+todayISO()+'"/></div>'+
    '<div class="field"><label>طريقة الدفع</label><select class="input" id="bp-method">'+
      '<option value="cash">نقداً</option><option value="transfer">تحويل</option><option value="card">شبكة</option><option value="other">أخرى</option></select></div>'+
    '<div class="field"><label>ملاحظة (اختياري)</label><input class="input" id="bp-note" placeholder="مثال: دفعة أولى من رسوم الكتب"/></div>'+
    '<div class="actions"><button class="btn btn--primary" data-ok>'+I('check')+' تأكيد دفعة الكتب</button><button class="btn btn--ghost" data-cancel>إلغاء</button></div>');
  m.el.querySelector('[data-cancel]').addEventListener('click',m.close);
  m.el.querySelector('[data-ok]').addEventListener('click',function(){
    var btn=this; if(btn.classList.contains('is-loading')) return;
    var amt=parseFloat(m.el.querySelector('#bp-amt').value);
    if(!(amt>0)||amt>remaining+0.01){ NS.toast('المبلغ أكبر من المتبقي أو غير صحيح','err'); return; }
    btn.classList.add('is-loading');
    NS.api('/api/manager/student/pay',{mt:TOKEN, student_id:s.id, amount:amt,
      payment_type:'books', date:m.el.querySelector('#bp-date').value,
      method:m.el.querySelector('#bp-method').value, period:'رسوم الكتب',
      note:m.el.querySelector('#bp-note').value})
    .then(function(r){ if(r&&r.ok){ m.close(); NS.toast('تم تسجيل دفعة الكتب ✔'); refreshRow(r.row); } else { btn.classList.remove('is-loading'); NS.toast((r&&r.error)||'خطأ','err'); } })
    .catch(function(){ btn.classList.remove('is-loading'); NS.toast('تعذّر التسجيل','err'); });
  });
}

/* ---- payment history ---- */
function history(s,type){
  var isBooks=type==='books';
  var m=NS.modal('<div class="modal__icon">'+I(isBooks?'book':'clock')+'</div><h3>'+(isBooks?'دفعات الكتب لـ':'دفعات ')+NS.esc(s.name)+'</h3><div id="ph-body"><div class="skel skel-line" style="width:80%"></div><div class="skel skel-line" style="width:60%;margin-top:8px"></div></div>'+
    '<div class="actions"><button class="btn btn--ghost" data-cancel>إغلاق</button></div>');
  m.el.querySelector('[data-cancel]').addEventListener('click',m.close);
  NS.api('/api/manager/student/payments',{mt:TOKEN,student_id:s.id,payment_type:isBooks?'books':'tuition'}).then(function(d){
    var B=m.el.querySelector('#ph-body'); if(!B) return;
    if(!d||!d.ok){ B.innerHTML='<p class="muted">تعذّر التحميل.</p>'; return; }
    if(!d.payments.length){ B.innerHTML=NS.empty('wallet','لا توجد دفعات','لم تُسجَّل أي دفعة لهذا الطالب بعد.'); return; }
    var h='<div class="ph">';
    d.payments.forEach(function(p){
      h+='<div class="p"><span class="amt">'+NS.riyal(p.amount)+'</span>'+
        '<div class="meta"><b>'+fmtD(p.date)+(p.period?(' · '+NS.esc(p.period)):'')+'</b>'+
        '<span>'+NS.esc(p.method)+(p.note?(' · '+NS.esc(p.note)):'')+'</span></div>'+
        '<button class="del" data-del="'+NS.attr(p.id)+'" title="حذف الدفعة">'+I('trash')+'</button></div>';
    });
    h+='</div><div style="display:flex;justify-content:space-between;padding-top:10px;border-top:2px solid var(--line-2);font-weight:800;color:var(--forest)"><span>الإجمالي</span><span class="tabnum">'+NS.riyal(d.total_paid)+'</span></div>';
    B.innerHTML=h;
    bind(B,'data-del',function(id){
      NS.confirm({title:'حذف الدفعة؟',body:'سيُحذف هذا السجل نهائياً.',okText:'حذف',danger:true}).then(function(ok){
        if(!ok) return;
        NS.api('/api/manager/payment/delete',{mt:TOKEN,id:id}).then(function(r){ if(r&&r.ok){ NS.toast('تم الحذف'); if(r.row) refreshRow(r.row); m.close(); history(get(s.id),type); } else NS.toast((r&&r.error)||'خطأ','err'); });
      });
    });
  }).catch(function(){ var B=m.el.querySelector('#ph-body'); if(B) B.innerHTML='<p class="muted">تعذّر التحميل.</p>'; });
}

/* ---- whatsapp reminder ---- */
function remind(s){
  var msg='السلام عليكم، تذكير ودّي برسوم الطالب '+s.name+' ('+Math.round(s.fees)+' ر.س)';
  if(s.status==='overdue') msg+=' — المتأخرة منذ '+Math.abs(s.days)+' يوم';
  msg+='. يسعدنا استقبال السداد أو الإجابة عن أي استفسار. شكراً لتعاونكم 🌿';
  window.open(NS.wa(s.guardian_phone,msg),'_blank','noopener');
}
})();
