(function () {
  if (window.__studentsTransferUI || !/\/students\/?$/.test(location.pathname)) return;
  window.__studentsTransferUI = true;

  if (!window.NS || !window.NS.api || !window.NS.token) return;

  var NS = window.NS;
  var TOKEN = NS.token("mt");
  if (!TOKEN) return;

  var state = {
    classes: [],
    selected: {},
    assignments: {},
    records: {},
    busy: false,
    scheduled: false
  };

  function text(value) {
    return value === null || value === undefined ? "" : String(value);
  }

  function hasOwn(object, key) {
    return Object.prototype.hasOwnProperty.call(object, key);
  }

  function notify(message, kind) {
    if (typeof NS.toast === "function") NS.toast(message, kind || "ok");
    else window.alert(message);
  }

  function schedule() {
    if (state.scheduled) return;
    state.scheduled = true;
    window.setTimeout(function () {
      state.scheduled = false;
      enhance();
    }, 0);
  }

  function makeOption(value, label, disabled) {
    var option = document.createElement("option");
    option.value = text(value);
    option.textContent = text(label);
    if (disabled) option.disabled = true;
    return option;
  }

  function makeTargetField(id) {
    var field = document.createElement("div");
    field.className = "st-transfer-target";
    field.setAttribute("data-summer-transfer-target", "1");

    var label = document.createElement("label");
    label.htmlFor = id;
    label.textContent = "الفصل الفعلي للسنة الجديدة";

    var select = document.createElement("select");
    select.id = id;
    select.className = "input st-transfer-class-select";
    select.setAttribute("data-summer-transfer-class", "1");

    field.appendChild(label);
    field.appendChild(select);
    return { field: field, select: select };
  }

  function fillClassOptions(select) {
    if (select.options.length) return;
    select.appendChild(makeOption("", "اختر الفصل الفعلي", true));

    for (var i = 0; i < state.classes.length; i += 1) {
      var item = state.classes[i];
      var capacity = item.capacity
        ? " (" + text(item.student_count || 0) + "/" + text(item.capacity) + ")"
        : "";
      select.appendChild(makeOption(item.id, text(item.name) + capacity));
    }
  }

  function cardInfo(card) {
    var grade = card.querySelector("[data-level-select]");
    if (!grade) return null;

    var id = text(grade.getAttribute("data-level-select"));
    var nameNode = card.querySelector(".name-fit, .who b");
    state.records[id] = {
      id: id,
      name: nameNode ? text(nameNode.textContent).trim() : id,
      level: grade.value || ""
    };
    return { id: id, grade: grade };
  }

  function syncCard(card) {
    var info = cardInfo(card);
    if (!info) return;

    var id = info.id;
    var checkbox = card.querySelector("[data-summer-transfer-pick]");

    if (!checkbox) {
      var pickRow = document.createElement("div");
      pickRow.className = "st-transfer-pick-row";

      checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "st-transfer-check";
      checkbox.setAttribute("data-summer-transfer-pick", id);

      var label = document.createElement("label");
      label.className = "st-transfer-pick-label";
      label.htmlFor = "summer-transfer-pick-" + id;
      label.textContent = "اختيار";
      checkbox.id = "summer-transfer-pick-" + id;

      pickRow.appendChild(checkbox);
      pickRow.appendChild(label);

      var top = card.querySelector(".top");
      if (top) card.insertBefore(pickRow, top);
      else card.insertBefore(pickRow, card.firstChild);
    }

    if (hasOwn(state.selected, id)) checkbox.checked = !!state.selected[id];
    else if (checkbox.checked) state.selected[id] = true;

    if (!checkbox.getAttribute("data-summer-transfer-wired")) {
      checkbox.setAttribute("data-summer-transfer-wired", "1");
      checkbox.addEventListener("change", function () {
        if (checkbox.checked) state.selected[id] = true;
        else delete state.selected[id];
        refreshBar();
      });
    }

    var target = card.querySelector("[data-summer-transfer-target]");
    if (!target) {
      var targetField = makeTargetField("summer-transfer-class-" + id);
      target = targetField.field;

      var gradeField = card.querySelector(".st-grade-field");
      if (gradeField && gradeField.nextSibling) {
        card.insertBefore(target, gradeField.nextSibling);
      } else if (gradeField) {
        card.appendChild(target);
      } else {
        card.insertBefore(target, card.firstChild);
      }
    }

    var select = target.querySelector("[data-summer-transfer-class]");
    fillClassOptions(select);

    var assigned = hasOwn(state.assignments, id) ? state.assignments[id] : "";
    if (document.activeElement !== select) select.value = text(assigned);

    select.onchange = function () {
      if (select.value) state.assignments[id] = select.value;
      else delete state.assignments[id];
      refreshBar();
    };
  }

  function selectedRecords() {
    var result = [];
    var ids = Object.keys(state.selected);

    for (var i = 0; i < ids.length; i += 1) {
      var id = ids[i];
      if (state.selected[id] && state.records[id]) result.push(state.records[id]);
    }
    return result;
  }

  function refreshVisibleLevels() {
    var grades = document.querySelectorAll("[data-level-select]");
    for (var i = 0; i < grades.length; i += 1) {
      var id = text(grades[i].getAttribute("data-level-select"));
      if (state.records[id]) state.records[id].level = grades[i].value || "";
    }
  }

  function ensureBar() {
    var list = document.getElementById("list");
    if (!list || !list.parentNode) return null;

    var bar = document.getElementById("summer-transfer-bar");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "summer-transfer-bar";
      bar.className = "st-transfer-bar";

      var title = document.createElement("strong");
      title.className = "st-transfer-bar__title";
      title.textContent = "نقل طلاب الصيف للسنة الجديدة";

      var status = document.createElement("span");
      status.className = "st-transfer-bar__status";
      status.setAttribute("data-summer-transfer-status", "1");

      var button = document.createElement("button");
      button.type = "button";
      button.className = "btn btn--primary st-transfer-bar__button";
      button.setAttribute("data-summer-transfer-selected", "1");
      button.textContent = "تحويل الطلبة للفصول المختارة";

      bar.appendChild(title);
      bar.appendChild(status);
      bar.appendChild(button);
      list.parentNode.insertBefore(bar, list);
    }

    return bar;
  }

  function refreshBar() {
    var bar = ensureBar();
    if (!bar) return;

    var selected = selectedRecords();
    var assigned = 0;

    for (var i = 0; i < selected.length; i += 1) {
      if (state.assignments[text(selected[i].id)]) assigned += 1;
    }

    var status = bar.querySelector("[data-summer-transfer-status]");
    var button = bar.querySelector("[data-summer-transfer-selected]");
    if (!status || !button) return;

    var statusText = selected.length
      ? (assigned === selected.length
        ? "جاهز للنقل اليدوي: " + assigned + " طالب"
        : "تم اختيار " + selected.length + " طالب، الفصول المحددة " + assigned + "/" + selected.length)
      : "اختر الطلاب وحدد الفصل الفعلي لكل طالب";

    if (status.textContent !== statusText) status.textContent = statusText;
    button.disabled = state.busy || !selected.length || assigned !== selected.length;
    button.textContent = state.busy ? "جارٍ التحويل..." : "تحويل الطلبة للفصول المختارة";
    button.onclick = transferSelected;
  }

  function transferSelected() {
    if (state.busy) return;

    refreshVisibleLevels();
    var selected = selectedRecords();
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
      notify("اختر طالبًا واحدًا على الأقل", "err");
      return;
    }

    if (missing.length) {
      notify("حدد الفصل الفعلي لكل الطلاب المختارين أولاً", "err");
      return;
    }

    if (!window.confirm("تحذير: سيتم نقل الطلبة المحددين إلى الفصول المختارة. راجعي الجريد والفصل قبل المتابعة.")) return;

    if (!window.confirm("تأكيد نهائي: سيتم تنفيذ النقل الآن. هل تريدين المتابعة؟")) return;

    state.busy = true;
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
        state.busy = false;
        refreshBar();
        notify((result && result.error) || "تعذّر تنفيذ التحويل", "err");
      }
    }).catch(function () {
      state.busy = false;
      refreshBar();
      notify("تعذّر تنفيذ التحويل", "err");
    });
  }

  function enhance() {
    if (!state.classes.length) return;

    var cards = document.querySelectorAll(".st-card");
    for (var i = 0; i < cards.length; i += 1) syncCard(cards[i]);
    refreshBar();
  }

  function loadClasses() {
    NS.api("/api/manager/classes", { mt: TOKEN }).then(function (result) {
      if (result && result.ok && Array.isArray(result.classes)) {
        state.classes = result.classes;
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

  window.setTimeout(loadClasses, 250);
})();