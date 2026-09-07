(function () {
  if (window.__newYearTransferUI) return;
  window.__newYearTransferUI = true;

  if (!window.NS || !window.NS.api || !window.NS.token) return;

  var NS = window.NS;
  var TOKEN = NS.token("mt");
  if (!TOKEN) return;

  var LEVELS = [
    { value: "prekg", label: "Pre-KG" },
    { value: "kg1", label: "KG1" },
    { value: "kg2", label: "KG2" },
    { value: "kg3", label: "KG3" }
  ];

  var state = {
    data: null,
    selected: {},
    assignments: {},
    moving: false,
    scheduled: false
  };

  function hasOwn(obj, key) {
    return Object.prototype.hasOwnProperty.call(obj, key);
  }

  function text(value) {
    return value === null || value === undefined ? "" : String(value);
  }

  function rows() {
    return state.data && Array.isArray(state.data.students) ? state.data.students : [];
  }

  function classes() {
    return state.data && Array.isArray(state.data.classes) ? state.data.classes : [];
  }

  function rowById(id) {
    var wanted = text(id);
    for (var i = 0; i < rows().length; i += 1) {
      if (text(rows()[i].id) === wanted) return rows()[i];
    }
    return null;
  }

  function levelLabel(value, fallback) {
    for (var i = 0; i < LEVELS.length; i += 1) {
      if (LEVELS[i].value === value) return LEVELS[i].label;
    }
    return fallback || value || "بدون جريد";
  }

  function notify(message, kind) {
    if (typeof NS.toast === "function") {
      NS.toast(message, kind || "ok");
    } else {
      window.alert(message);
    }
  }

  function schedule() {
    if (state.scheduled) return;
    state.scheduled = true;
    window.setTimeout(function () {
      state.scheduled = false;
      enhance();
    }, 0);
  }

  function addStyle() {
    if (document.getElementById("new-year-transfer-style")) return;
    var style = document.createElement("style");
    style.id = "new-year-transfer-style";
    style.textContent =
      ".en-target-fields{display:grid;grid-template-columns:1fr 1.15fr;gap:8px;margin:0 0 14px;direction:rtl}" +
      ".en-target-field{display:grid;grid-template-columns:1fr;gap:5px;min-width:0;padding:8px 10px;border:1px solid rgba(38,100,79,.16);border-radius:12px;background:#f8fbf8}" +
      ".en-target-field label{font-size:12px;font-weight:700;color:#557268;line-height:1.2}" +
      ".en-transfer-select{width:100%;min-width:0;height:38px;padding:0 9px;border:1px solid #d9e5df;border-radius:9px;background:#fff;color:#173f34;font:inherit;font-size:13px;outline:none}" +
      ".en-transfer-select:focus{border-color:#2e8065;box-shadow:0 0 0 3px rgba(46,128,101,.12)}" +
      ".en-transfer-status{display:inline-flex;align-items:center;min-height:36px;margin-inline-start:8px;color:#557268;font-size:13px;font-weight:700}" +
      ".en-transfer-external{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:38px;padding:0 15px;border:0;border-radius:10px;background:#17604d;color:#fff;font:inherit;font-weight:800;cursor:pointer;white-space:nowrap}" +
      ".en-transfer-external:hover:not(:disabled){background:#0f4b3b}" +
      ".en-transfer-external:disabled{background:#b9c9c2;color:#fff;cursor:not-allowed;opacity:.85}" +
      "@media(max-width:640px){.en-target-fields{grid-template-columns:1fr}.en-transfer-status{display:block;margin:7px 0 0;width:100%;text-align:center}.en-transfer-external{width:100%;margin-top:8px}}";
    document.head.appendChild(style);
  }

  function makeOption(value, label, disabled) {
    var option = document.createElement("option");
    option.value = text(value);
    option.textContent = text(label);
    if (disabled) option.disabled = true;
    return option;
  }

  function makeField(labelText, id, attribute, extraClass) {
    var select = document.createElement("select");
    select.id = id;
    select.className = "en-transfer-select" + (extraClass ? " " + extraClass : "");
    select.setAttribute(attribute, "1");

    var field = document.createElement("div");
    field.className = "en-target-field";

    var label = document.createElement("label");
    label.htmlFor = id;
    label.textContent = labelText;

    field.appendChild(label);
    field.appendChild(select);
    return { field: field, select: select };
  }

  function fillGradeOptions(select, row) {
    if (select.options.length) return;
    select.appendChild(makeOption("", "اختر الجريد", true));
    var found = false;
    for (var i = 0; i < LEVELS.length; i += 1) {
      select.appendChild(makeOption(LEVELS[i].value, LEVELS[i].label));
      if (LEVELS[i].value === text(row.level)) found = true;
    }
    if (row.level && !found) {
      select.appendChild(makeOption(row.level, row.level_label || row.level));
    }
  }

  function fillClassOptions(select) {
    if (select.options.length) return;
    select.appendChild(makeOption("", "اختر الفصل الفعلي", true));
    var list = classes();
    for (var i = 0; i < list.length; i += 1) {
      var item = list[i];
      var capacity = item.capacity ? " (" + text(item.student_count || 0) + "/" + text(item.capacity) + ")" : "";
      select.appendChild(makeOption(item.id, text(item.name) + capacity));
    }
  }

  function saveGrade(row, select) {
    var value = select.value;
    var previous = row.level || "";
    row.level = value;
    row.level_label = levelLabel(value, value);
    select.disabled = true;

    NS.api("/api/manager/enrollment/save", {
      mt: TOKEN,
      id: row.id,
      name: row.name || "",
      parent_name: row.parent_name || row.guardian_name || "",
      father_name: row.father_name || "",
      mother_name: row.mother_name || "",
      parent_email: row.parent_email || "",
      parent_phone: row.parent_phone || row.guardian_phone || "",
      joining_date: row.joining_date || "2026-09-01",
      level: value,
      fees: row.fees || "",
      remark: row.remark || ""
    }).then(function (result) {
      select.disabled = false;
      if (result && result.ok) {
        var card = select.closest(".en-card");
        var who = card && card.querySelector(".who span");
        if (who) who.textContent = levelLabel(value, row.level_label);
        notify("تم حفظ الجريد", "ok");
      } else {
        row.level = previous;
        select.value = previous;
        notify((result && result.error) || "تعذّر حفظ الجريد", "err");
      }
    }).catch(function () {
      row.level = previous;
      select.value = previous;
      select.disabled = false;
      notify("تعذّر حفظ الجريد", "err");
    });
  }

  function syncCard(card) {
    var pick = card.querySelector("input[data-pick]");
    if (!pick) return;

    var id = text(pick.getAttribute("data-pick"));
    var row = rowById(id);
    if (!row) return;

    if (pick.checked) state.selected[id] = true;
    else delete state.selected[id];

    if (!pick.getAttribute("data-transfer-wired")) {
      pick.setAttribute("data-transfer-wired", "1");
      pick.addEventListener("change", function () {
        if (pick.checked) state.selected[id] = true;
        else delete state.selected[id];
        schedule();
      });
    }

    var wrap = card.querySelector("[data-enrollment-targets]");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.className = "en-target-fields";
      wrap.setAttribute("data-enrollment-targets", "1");

      var anchor = card.querySelector(".en-select-row");
      if (anchor) card.insertBefore(wrap, anchor);
      else card.appendChild(wrap);
    }

    var gradeField = wrap.querySelector("[data-transfer-grade]");
    if (!gradeField) {
      var grade = makeField("الجريد", "transfer-grade-" + id, "data-transfer-grade");
      gradeField = grade.select;
      fillGradeOptions(gradeField, row);
      wrap.appendChild(grade.field);
    } else {
      fillGradeOptions(gradeField, row);
    }

    if (document.activeElement !== gradeField && !gradeField.disabled) {
      gradeField.value = text(row.level);
    }

    gradeField.onchange = function () {
      saveGrade(row, gradeField);
    };

    var classField = wrap.querySelector("[data-transfer-class]");
    if (!classField) {
      var target = makeField("الفصل الفعلي للسنة الجديدة", "transfer-class-" + id, "data-transfer-class");
      classField = target.select;
      fillClassOptions(classField);
      wrap.appendChild(target.field);
    } else {
      fillClassOptions(classField);
    }

    var assigned = hasOwn(state.assignments, id) ? state.assignments[id] : "";
    if (document.activeElement !== classField) classField.value = text(assigned);

    classField.onchange = function () {
      var value = classField.value;
      if (value) state.assignments[id] = value;
      else delete state.assignments[id];
      refreshBar();
    };
  }

  function selectedRows() {
    var result = [];
    var list = rows();
    for (var i = 0; i < list.length; i += 1) {
      if (state.selected[text(list[i].id)]) result.push(list[i]);
    }
    return result;
  }

  function refreshBar() {
    var bar = document.querySelector("#selection-bar, .en-selection");
    if (!bar) return;

    var selected = selectedRows();
    var assigned = 0;
    for (var i = 0; i < selected.length; i += 1) {
      if (state.assignments[text(selected[i].id)]) assigned += 1;
    }

    var status = bar.querySelector("[data-transfer-status]");
    if (!status) {
      status = document.createElement("span");
      status.className = "en-transfer-status";
      status.setAttribute("data-transfer-status", "1");
      bar.appendChild(status);
    }

    var statusText = selected.length
      ? (assigned === selected.length
        ? "جاهز للنقل اليدوي: " + assigned + " طلب"
        : "تم اختيار " + selected.length + " طلب - حددي الفصل الفعلي لكل طالب (" + assigned + "/" + selected.length + ")")
      : "اختر الطلبات وحدد الفصل الفعلي لكل طالب";

    if (status.textContent !== statusText) status.textContent = statusText;

    var button = bar.querySelector("[data-transfer-selected]");
    if (!button) {
      button = document.createElement("button");
      button.type = "button";
      button.className = "en-transfer-external";
      button.setAttribute("data-transfer-selected", "1");
      button.textContent = "تحويل الطلبة للفصول المختارة";
      bar.appendChild(button);
    }

    button.disabled = state.moving || !selected.length || assigned !== selected.length;
    button.textContent = state.moving ? "جارٍ التحويل..." : "تحويل الطلبة للفصول المختارة";
    button.onclick = transferSelected;
  }

  function replaceAutomaticCopy() {
    var nodes = document.querySelectorAll("#app *");
    for (var i = 0; i < nodes.length; i += 1) {
      var node = nodes[i];
      if (node.children.length) continue;
      var current = (node.textContent || "").trim();
      var next = current;

      if (current === "يظهر تلقائياً في سبتمبر" || current === "يظهر تلقائيا في سبتمبر") {
        next = "جاهز للنقل اليدوي";
      } else if (current === "جاهزة للترحيل") {
        next = "جاهزة للنقل اليدوي";
      } else if (current.indexOf("لا يوجد نقل يدوي عند إغلاق أغسطس") >= 0) {
        next = current.replace("لا يوجد نقل يدوي عند إغلاق أغسطس", "النقل يدوي حسب الفصل المختار");
      } else if (current.indexOf("سيظهر الطالب في كشف سبتمبر تلقائياً") >= 0) {
        next = current.replace("سيظهر الطالب في كشف سبتمبر تلقائياً", "سيظهر الطالب هنا حتى تنقله يدوياً");
      } else if (current.indexOf("سيظهر الطالب في كشف سبتمبر تلقائيا") >= 0) {
        next = current.replace("سيظهر الطالب في كشف سبتمبر تلقائيا", "سيظهر الطالب هنا حتى تنقله يدوياً");
      }

      if (next !== current) node.textContent = next;
    }
  }

  function transferSelected() {
    if (state.moving) return;

    var selected = selectedRows();
    var assignments = {};
    var levels = {};
    var missing = [];

    for (var i = 0; i < selected.length; i += 1) {
      var id = text(selected[i].id);
      if (!state.assignments[id]) missing.push(selected[i].name || id);
      else assignments[id] = state.assignments[id];
      if (selected[i].level) levels[id] = selected[i].level;
    }

    if (!selected.length) {
      notify("اختر طلبًا واحدًا على الأقل", "err");
      return;
    }

    if (missing.length) {
      notify("حدد الفصل الفعلي لكل الطلبات المختارة أولاً", "err");
      return;
    }

    var message = "سيتم نقل " + selected.length + " طلب إلى الفصول المختارة. هل تريد المتابعة؟";
    if (!window.confirm("تحذير: سيتم نقل الطلبة المحددين إلى الفصول المختارة. راجعي الجريد والفصل قبل المتابعة.")) return;
    if (!window.confirm("تأكيد نهائي: سيتم تنفيذ النقل الآن. هل تريدين المتابعة؟")) return;

    state.moving = true;
    refreshBar();

    NS.api("/api/manager/enrollment/transfer", {
      mt: TOKEN,
      ids: JSON.stringify(selected.map(function (item) { return item.id; })),
      assignments: JSON.stringify(assignments),
      levels: JSON.stringify(levels)
    }).then(function (result) {
      if (result && result.ok) {
        notify("تم تحويل " + (result.count || selected.length) + " طالبًا للفصول المختارة", "ok");
        window.setTimeout(function () { window.location.reload(); }, 500);
      } else {
        state.moving = false;
        refreshBar();
        notify((result && result.error) || "تعذّر تنفيذ التحويل", "err");
      }
    }).catch(function () {
      state.moving = false;
      refreshBar();
      notify("تعذّر تنفيذ التحويل", "err");
    });
  }

  function enhance() {
    if (!state.data) return;
    addStyle();

    var cards = document.querySelectorAll(".en-card");
    for (var i = 0; i < cards.length; i += 1) syncCard(cards[i]);

    replaceAutomaticCopy();
    refreshBar();
  }

  function loadData() {
    NS.api("/api/manager/enrollments", { mt: TOKEN }).then(function (result) {
      if (result && result.ok) {
        state.data = result;
        enhance();
      }
    }).catch(function () {});
  }

  var app = document.getElementById("app");
  if (app && window.MutationObserver) {
    new MutationObserver(function () {
      schedule();
    }).observe(app, { childList: true, subtree: true });
  }

  window.setTimeout(loadData, 200);
})();