/* ПЛМ — быстрые правки, колесо, прогресс. Без зависимостей. */
"use strict";

const csrf = document.querySelector('meta[name="csrf"]').content;

/* ------------------------------------------------ утилиты */

async function api(url, data) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
    body: JSON.stringify(data || {}),
  });
  let j = {};
  try { j = await r.json(); } catch (e) { j = {}; }
  if (!r.ok || j.ok === false) throw new Error(j.error || "Ошибка сервера");
  return j;
}

function toast(msg, type = "") {
  const box = document.getElementById("toasts");
  const t = document.createElement("div");
  t.className = "toast " + type;
  t.textContent = msg;
  box.appendChild(t);
  setTimeout(() => t.remove(), 4200);
}

function closeModal() {
  document.getElementById("modal-backdrop").classList.add("hidden");
  document.getElementById("modal").innerHTML = "";
}

function openModal(html) {
  document.getElementById("modal").innerHTML = html;
  document.getElementById("modal-backdrop").classList.remove("hidden");
}

function esc(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function formField(label, name, value, opts = {}) {
  const type = opts.type || "text";
  if (type === "textarea") {
    return `<label class="stack">${label}<textarea name="${name}" rows="${opts.rows || 4}">${esc(value)}</textarea></label>`;
  }
  if (type === "select") {
    const o = (opts.options || [])
      .map(([v, l]) => `<option value="${v}" ${String(value) === String(v) ? "selected" : ""}>${l}</option>`)
      .join("");
    return `<label class="stack">${label}<select name="${name}">${o}</select></label>`;
  }
  return `<label class="stack">${label}<input type="${type}" name="${name}" value="${esc(value)}"></label>`;
}

/* ------------------------------------------------ каналы (pjax) */

async function loadChannel(slug, push = true) {
  const r = await fetch(`/c/${slug}/?partial=1`);
  if (!r.ok) { location.href = `/c/${slug}/`; return; }
  const j = await r.json();
  document.getElementById("pane").innerHTML = j.html;
  document.getElementById("channel-title").textContent = j.title;
  document.getElementById("channel-desc").textContent = j.desc || "";
  document.querySelector(".channel-header .ch-icon").textContent = j.icon;
  document.body.dataset.slug = j.slug;
  document.body.dataset.kind = j.kind;
  document.querySelectorAll(".channel").forEach((a) => {
    a.classList.toggle("active", a.dataset.slug === slug);
  });
  const comp = document.getElementById("composer-input");
  if (comp) comp.placeholder = `Сообщение в #${j.title.replace(/^#/, "")} — Enter отправить, Shift+Enter новая строка`;
  if (push) history.pushState({ slug }, "", `/c/${slug}/`);
  document.title = `${j.title} · ПЛМ`;
  afterRender();
}

function reloadPartial() {
  return loadChannel(document.body.dataset.slug, false);
}

document.querySelectorAll(".channel, .rail-icon").forEach((a) => {
  a.addEventListener("click", (e) => {
    const href = a.getAttribute("href") || "";
    const m = href.match(/^\/c\/([\w-]+)\/$/);
    if (!m) return;
    e.preventDefault();
    loadChannel(m[1]).catch((err) => toast(err.message, "err"));
  });
});

window.addEventListener("popstate", (e) => {
  const slug = (e.state && e.state.slug) || location.pathname.split("/")[2];
  if (slug) loadChannel(slug, false);
});

/* ------------------------------------------------ доступ (замок) */

document.getElementById("edit-lock").addEventListener("click", async () => {
  if (document.body.classList.contains("can-edit")) {
    await api("/api/logout");
    location.reload();
    return;
  }
  openModal(`
    <h3>🔑 Ключ правки</h3>
    <div class="form">
      <p class="muted">Сайт открыт для всех, но правки защищены общим ключом (переменная окружения <code>FDZHTT_EDIT_CODE</code>).</p>
      <label class="stack">Ключ <input type="password" id="code-input" autocomplete="off"></label>
    </div>
    <div class="btns">
      <button class="btn" id="m-cancel">Отмена</button>
      <button class="btn primary" id="m-ok">Открыть</button>
    </div>`);
  const go = async () => {
    try {
      await api("/api/auth", { code: document.getElementById("code-input").value });
      location.reload();
    } catch (err) {
      toast(err.message, "err");
    }
  };
  document.getElementById("m-ok").onclick = go;
  document.getElementById("m-cancel").onclick = closeModal;
  document.getElementById("code-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") go();
  });
});

document.getElementById("modal-backdrop").addEventListener("click", (e) => {
  if (e.target.id === "modal-backdrop") closeModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});

/* ------------------------------------------------ сообщения: быстрая правка */

function bindPostEdit(article) {
  const raw = article.dataset.raw || "";
  const content = article.querySelector(".msg-content");
  const original = article.dataset.html || content.innerHTML;
  content.innerHTML = `
    <textarea class="edit-area"></textarea>
    <div class="edit-hint">Ctrl+Enter — сохранить · Esc — отмена. Разметка: **жирный**, *курсив*, ++подчёркнутый++, ~~зачёркнутый~~, [[термин]], --- разделитель, > цитата, списки «1.» / «-»</div>`;
  const ta = content.querySelector("textarea");
  ta.value = raw;
  ta.focus();
  ta.setSelectionRange(raw.length, raw.length);
  let done = false;
  const save = async () => {
    if (done) return;
    done = true;
    if (ta.value === raw) { content.innerHTML = original; return; }
    try {
      const j = await api(`/api/post/${article.dataset.post}/update`, { content: ta.value });
      article.outerHTML = j.html;
    } catch (err) {
      done = false;
      toast(err.message, "err");
    }
  };
  ta.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); save(); }
    if (e.key === "Escape") {
      e.preventDefault();
      done = true;
      content.innerHTML = original;
    }
  });
  ta.addEventListener("blur", () => setTimeout(save, 150));
}

/* ------------------------------------------------ делегирование кликов */

document.getElementById("pane").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-act]");
  if (!btn) return;
  const act = btn.dataset.act;

  try {
    /* --- посты --- */
    if (act === "edit-post") {
      const article = btn.closest(".msg");
      if (!article.dataset.html) article.dataset.html = article.querySelector(".msg-content").innerHTML;
      bindPostEdit(article);
    }
    if (act === "delete-post") {
      const article = btn.closest(".msg");
      if (confirm("Удалить сообщение?")) {
        await api(`/api/post/${article.dataset.post}/delete`);
        article.remove();
        toast("Сообщение удалено", "ok");
      }
    }

    /* --- термины --- */
    if (act === "edit-term") {
      const card = btn.closest(".term-card");
      openModal(`
        <h3>✏️ Правка термина</h3>
        <form class="form" id="m-form">
          ${formField("Коротко (в текстах так и будет подсвечен)", "short", card.dataset.short || "")}
          ${formField("Название", "title", card.dataset.title || "")}
          ${formField("Определение", "definition", card.dataset.def || "", { type: "textarea" })}
          <div class="btns"><button type="button" class="btn" id="m-cancel">Отмена</button><button class="btn primary">Сохранить</button></div>
        </form>`);
      document.getElementById("m-cancel").onclick = closeModal;
      document.getElementById("m-form").onsubmit = async (ev) => {
        ev.preventDefault();
        await api(`/api/term/${card.dataset.termId}/update`, Object.fromEntries(new FormData(ev.target)));
        closeModal();
        toast("Термин сохранён", "ok");
        reloadPartial();
      };
    }
    if (act === "delete-term") {
      const card = btn.closest(".term-card");
      if (confirm("Удалить термин?")) {
        await api(`/api/term/${card.dataset.termId}/delete`);
        card.remove();
        toast("Термин удалён", "ok");
      }
    }

    /* --- подсосы --- */
    if (act === "toggle-podsos") {
      const card = btn.closest(".podsos-card");
      const active = card.querySelector(".chip").classList.contains("ok");
      await api(`/api/podsos/${card.dataset.pid}/update`, { active: !active });
      reloadPartial();
    }
    if (act === "edit-podsos") {
      const card = btn.closest(".podsos-card");
      openModal(`
        <h3>✏️ Правка подсоса</h3>
        <form class="form" id="m-form">
          ${formField("Название", "title", card.dataset.title || "")}
          ${formField("Описание", "description", card.dataset.def || "", { type: "textarea" })}
          <div class="btns"><button type="button" class="btn" id="m-cancel">Отмена</button><button class="btn primary">Сохранить</button></div>
        </form>`);
      document.getElementById("m-cancel").onclick = closeModal;
      document.getElementById("m-form").onsubmit = async (ev) => {
        ev.preventDefault();
        await api(`/api/podsos/${card.dataset.pid}/update`, Object.fromEntries(new FormData(ev.target)));
        closeModal();
        toast("Подсос сохранён", "ok");
        reloadPartial();
      };
    }
    if (act === "delete-podsos") {
      const card = btn.closest(".podsos-card");
      if (confirm("Удалить подсос?")) {
        await api(`/api/podsos/${card.dataset.pid}/delete`);
        card.remove();
        toast("Подсос удалён", "ok");
      }
    }

    /* --- наказания --- */
    if (act === "approve-pun") {
      const card = btn.closest(".pun-card");
      if (confirm("Добавить в кол? Убрать потом будет нельзя (правило ООН).")) {
        await api(`/api/punishment/${card.dataset.pun}/update`, { status: "approved" });
        toast("Добавлено в кол навсегда 🔒", "ok");
        reloadPartial();
      }
    }
    if (act === "edit-pun") {
      const card = btn.closest(".pun-card");
      const d = card.dataset;
      openModal(`
        <h3>✏️ Правка наказания</h3>
        <form class="form" id="m-form">
          ${formField("Название", "title", d.title || "")}
          ${formField("Тип", "kind", d.kind || "series", { type: "select", options: [["series", "📺 сериал / аниме / дорама"], ["movie", "🎬 фильм / мультфильм"], ["vn", "🎮 визуальная новелла"]] })}
          ${formField("Минут в серии (1–85)", "episode_minutes", d.ep || "")}
          ${formField("Длительность, мин (для фильма)", "duration_minutes", d.dur || "")}
          ${formField("Заметка о сезонах", "seasons_note", d.seasons || "")}
          ${formField("Ссылка", "link", d.link || "")}
          ${formField("Описание", "description", d.desc || "", { type: "textarea" })}
          ${formField("Вес в колесе (у ВН — малый)", "weight", d.weight || 10)}
          <div class="btns"><button type="button" class="btn" id="m-cancel">Отмена</button><button class="btn primary">Сохранить</button></div>
        </form>`);
      document.getElementById("m-cancel").onclick = closeModal;
      document.getElementById("m-form").onsubmit = async (ev) => {
        ev.preventDefault();
        await api(`/api/punishment/${card.dataset.pun}/update`, Object.fromEntries(new FormData(ev.target)));
        closeModal();
        toast("Наказание сохранено", "ok");
        reloadPartial();
      };
    }
    if (act === "delete-pun") {
      const card = btn.closest(".pun-card");
      const approved = card.dataset.status === "approved";
      const q = approved
        ? "Одобренное наказание убрать нельзя (ООН). Отправить в архив целиком?"
        : "Удалить предложенное наказание?";
      if (confirm(q)) {
        const j = await api(`/api/punishment/${card.dataset.pun}/delete`);
        toast(j.message || (approved ? "В архиве" : "Удалено"), "ok");
        reloadPartial();
      }
    }

    /* --- мероприятия: счётчики --- */
    if (btn.classList.contains("step")) {
      const counter = btn.closest(".counter");
      const card = btn.closest(".session");
      const field = counter.dataset.field;
      const valEl = counter.querySelector(".val");
      const next = Math.max(0, parseInt(valEl.textContent, 10) + parseInt(btn.dataset.delta, 10));
      const j = await api(`/api/session/${card.dataset.sid}/update`, { [field]: next });
      valEl.textContent = next;
      card.querySelector(".js-op").textContent = j.fail_points;
      card.querySelector(".js-need").textContent = j.need;
      const hasWarn = !!card.querySelector(".chip.warn");
      const hasSplit = !!card.querySelector(".chip.danger");
      if (hasWarn !== j.needs_extra || hasSplit !== j.needs_split) {
        reloadPartial();
      }
    }
    if (act === "edit-session") {
      const card = btn.closest(".session");
      openModal(`
        <h3>✏️ Мероприятие</h3>
        <form class="form" id="m-form">
          ${formField("Название (пусто = «ПЛМ от даты»)", "title", card.dataset.title || "")}
          ${formField("Заметки", "notes", card.dataset.notes || "", { type: "textarea" })}
          <div class="btns"><button type="button" class="btn" id="m-cancel">Отмена</button><button class="btn primary">Сохранить</button></div>
        </form>`);
      document.getElementById("m-cancel").onclick = closeModal;
      document.getElementById("m-form").onsubmit = async (ev) => {
        ev.preventDefault();
        await api(`/api/session/${card.dataset.sid}/update`, Object.fromEntries(new FormData(ev.target)));
        closeModal();
        toast("Сохранено", "ok");
        reloadPartial();
      };
    }
    if (act === "delete-session") {
      const card = btn.closest(".session");
      if (confirm("Удалить мероприятие со всеми отработками?")) {
        await api(`/api/session/${card.dataset.sid}/delete`);
        toast("Мероприятие удалено", "ok");
        reloadPartial();
      }
    }

    /* --- отработки --- */
    if (btn.classList.contains("step-x")) {
      const row = btn.closest(".sentence");
      const next = Math.max(0, parseInt(row.dataset.watched, 10) + parseInt(btn.dataset.delta, 10));
      const j = await api(`/api/sentence/${row.dataset.xid}/update`, { watched_units: next });
      row.dataset.watched = j.watched;
      row.querySelector(".units").textContent = `${j.watched}/${j.planned} ${j.unit}`;
      row.querySelector(".bar-fill").style.width = j.percent + "%";
    }
    if (act === "done-x") {
      const row = btn.closest(".sentence");
      const j = await api(`/api/sentence/${row.dataset.xid}/update`, { status: "done" });
      if (j.achievement) toast(`🏆 Достижение: ${j.achievement.icon} ${j.achievement.title}`, "ach");
      else toast("Отработано ✅", "ok");
      reloadPartial();
    }
    if (act === "delete-x") {
      const row = btn.closest(".sentence");
      if (confirm("Удалить отработку?")) {
        await api(`/api/sentence/${row.dataset.xid}/delete`);
        row.remove();
        toast("Отработка удалена", "ok");
      }
    }
  } catch (err) {
    toast(err.message, "err");
  }
});

/* ------------------------------------------------ формы в каналах */

document.getElementById("pane").addEventListener("submit", async (e) => {
  const form = e.target;
  e.preventDefault();
  const data = Object.fromEntries(new FormData(form));
  try {
    if (form.id === "form-term") {
      await api("/api/term/create", data);
      toast("Термин добавлен", "ok");
      reloadPartial();
    } else if (form.id === "form-podsos") {
      await api("/api/podsos/create", data);
      toast("Подсос добавлен", "ok");
      reloadPartial();
    } else if (form.id === "form-pun") {
      await api("/api/punishment/create", data);
      toast("Наказание предложено — добавьте в кол, когда решите", "ok");
      reloadPartial();
    } else if (form.id === "form-session") {
      const j = await api("/api/session/create", data);
      toast(`Мероприятие создано · оп: ${j.fail_points}`, "ok");
      reloadPartial();
    } else if (form.id.startsWith("form-sentence-")) {
      data.session = form.dataset.sid;
      await api("/api/sentence/create", data);
      toast("Кол записан в отработку", "ok");
      reloadPartial();
    }
  } catch (err) {
    toast(err.message, "err");
  }
});

document.getElementById("pane").addEventListener("change", (e) => {
  if (e.target.name === "kind" && e.target.closest("#form-pun")) {
    const f = e.target.closest("form");
    f.querySelector(".only-series").classList.toggle("hidden", e.target.value !== "series");
    f.querySelector(".only-movie").classList.toggle("hidden", e.target.value !== "movie");
  }
  if (e.target.classList.contains("podsos-pick")) {
    api(`/api/session/${e.target.dataset.sid}/update`, { extra_podsos: e.target.value || null })
      .then(() => toast("Подсос выбран (ровно один)", "ok"))
      .catch((err) => toast(err.message, "err"));
  }
});

/* ------------------------------------------------ композер */

async function sendPost() {
  const ta = document.getElementById("composer-input");
  const content = ta.value.trim();
  if (!content) return;
  try {
    await api("/api/post/create", { channel: document.body.dataset.slug, content });
    ta.value = "";
    ta.style.height = "auto";
    await reloadPartial();
    const pane = document.getElementById("pane");
    pane.scrollTop = pane.scrollHeight;
  } catch (err) {
    toast(err.message, "err");
  }
}

const composer = document.getElementById("composer-input");
if (composer) {
  composer.addEventListener("input", () => {
    composer.style.height = "auto";
    composer.style.height = Math.min(180, composer.scrollHeight) + "px";
  });
  composer.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendPost();
    }
  });
}
document.getElementById("composer-send").addEventListener("click", sendPost);

/* ------------------------------------------------ подсказки терминов */

let TERMS = null;
const pop = document.getElementById("term-pop");

async function loadTerms() {
  if (TERMS) return TERMS;
  try {
    const r = await fetch("/api/terms.json");
    const j = await r.json();
    TERMS = Object.fromEntries(j.terms.map((t) => [t.short.toLowerCase(), t]));
  } catch (e) {
    TERMS = {};
  }
  return TERMS;
}

document.addEventListener("mouseover", async (e) => {
  const chip = e.target.closest(".term-chip");
  if (!chip) return;
  const terms = await loadTerms();
  const key = (chip.dataset.term || chip.textContent).trim().toLowerCase();
  const t = terms[key];
  if (!t) return;
  pop.innerHTML = `<div class="t-short">${esc(t.short)}</div><div class="t-title">${esc(t.title)}</div><div class="t-def">${esc(t.definition)}</div>`;
  const r = chip.getBoundingClientRect();
  pop.style.left = Math.min(window.innerWidth - 300, r.left) + "px";
  pop.style.top = Math.min(window.innerHeight - 120, r.bottom + 8) + "px";
  pop.classList.remove("hidden");
});
document.addEventListener("mouseout", (e) => {
  if (e.target.closest(".term-chip")) pop.classList.add("hidden");
});

/* ------------------------------------------------ калькулятор пятницы */

function calcUpdate() {
  const tEl = document.getElementById("calc-t");
  const out = document.getElementById("calc-out");
  if (!tEl || !out) return;
  const t = parseInt(tEl.value, 10) || 0;
  const os = parseInt(document.getElementById("calc-os").value, 10) || 0;
  const need = t < 200 ? 1 : t < 500 ? 2 : 3;
  const op = Math.floor(os / need);
  let html = `
    <span class="chip">нужно <b>${need}</b> ос / 1 оп</span>
    <span class="chip blurple">оп: <b>${op}</b> → колов: <b>${op}</b></span>`;
  if (t < 200) html += `<span class="chip warn">+ ДОПОЛНИТЕЛЬНОЕ сос (одно подсос)</span>`;
  if (t > 700) html += `<span class="chip danger">больше 700 — делить пополам на 2 мероприятия</span>`;
  out.innerHTML = html;
}

/* ------------------------------------------------ колесо наказаний */

const WHEEL_COLORS = ["#5865f2", "#4752c4", "#3b428c", "#7289da", "#99aab5", "#2c2f33", "#72767d", "#5865f2", "#4752c4", "#7289da"];

function initWheel() {
  const canvas = document.getElementById("wheel");
  if (!canvas) return;
  let items = [];
  try { items = JSON.parse(document.getElementById("wheel-data").textContent || "[]"); } catch (e) {}
  const ctx = canvas.getContext("2d");
  const CX = 180, CY = 180, R = 170;

  const arcs = [];
  if (items.length) {
    const total = items.reduce((s, it) => s + it.weight, 0);
    let a = -Math.PI / 2;
    items.forEach((it) => {
      const sweep = (it.weight / total) * Math.PI * 2;
      arcs.push(Object.assign({}, it, { start: a, sweep }));
      a += sweep;
    });
  }

  function draw(rotation) {
    rotation = rotation || 0;
    ctx.clearRect(0, 0, 360, 360);
    ctx.save();
    ctx.translate(CX, CY);
    ctx.rotate(rotation);
    if (!arcs.length) {
      ctx.fillStyle = "#2b2d31";
      ctx.beginPath();
      ctx.arc(0, 0, R, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#949ba4";
      ctx.font = "16px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("колесо пустое", 0, 6);
      ctx.restore();
      return;
    }
    arcs.forEach((arc, i) => {
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.arc(0, 0, R, arc.start, arc.start + arc.sweep);
      ctx.closePath();
      ctx.fillStyle = WHEEL_COLORS[i % WHEEL_COLORS.length];
      ctx.fill();
      ctx.strokeStyle = "#1e1f22";
      ctx.stroke();
      ctx.save();
      ctx.rotate(arc.start + arc.sweep / 2);
      ctx.textAlign = "right";
      ctx.fillStyle = "#fff";
      ctx.font = "13px sans-serif";
      let label = arc.title;
      if (label.length > 26) label = label.slice(0, 25) + "…";
      ctx.fillText(arc.emoji + " " + label, R - 12, 4);
      ctx.restore();
    });
    ctx.beginPath();
    ctx.arc(0, 0, 26, 0, Math.PI * 2);
    ctx.fillStyle = "#1e1f22";
    ctx.fill();
    ctx.restore();
  }
  draw(0);

  let spinning = false;
  let lastPick = null;
  const btn = document.getElementById("spin-btn");
  const resultBody = document.getElementById("wheel-result-body");
  if (!btn) return;

  function showResult(p) {
    lastPick = p;
    resultBody.innerHTML = `
      <div class="row"><span style="font-size:24px">${p.emoji}</span>
      <strong style="font-size:17px">${esc(p.title)}</strong></div>
      <div class="muted">⚖️ ${esc(p.load_label)}</div>
      <div class="row" style="margin-top:8px">
        <button class="btn primary" id="take-btn">➕ Взять в работу</button>
      </div>
      <div class="muted small" style="margin-top:6px">Одно кручение = одна отработка (кол) в выбранное мероприятие.</div>`;
    const take = document.getElementById("take-btn");
    take.onclick = async () => {
      const sid = document.getElementById("wheel-session").value;
      if (!sid) { toast("Сначала создай мероприятие в #прогресс", "err"); return; }
      const spins = document.getElementById("wheel-spins2").checked ? 2 : 1;
      try {
        await api("/api/sentence/create", { session: sid, punishment: p.id, spins });
        toast("Кол записан в отработку ✅", "ok");
      } catch (err) {
        toast(err.message, "err");
      }
    };
  }

  btn.addEventListener("click", async () => {
    if (spinning) return;
    if (!arcs.length) { toast("В колесе пусто — добавь наказания", "err"); return; }
    spinning = true;
    btn.disabled = true;
    try {
      const j = await api("/api/spin");
      const pick = j.punishment;
      const idx = Math.max(0, arcs.findIndex((a) => a.id === pick.id));
      const arc = arcs[idx];
      // стрелка сверху (-90°): крутим так, чтобы центр сектора оказался под ней.
      const target = -(arc.start + arc.sweep / 2) - Math.PI / 2;
      const cur = parseFloat(canvas.dataset.rot || "0");
      const turns = 6 * Math.PI * 2;
      // ближайший поворот вперёд от cur, чтобы центр сектора встал под стрелкой
      const twoPi = Math.PI * 2;
      const delta = (((target - cur) % twoPi) + twoPi) % twoPi;
      const final = cur + turns + delta;
      const start = performance.now();
      const dur = 4200;
      await new Promise((res) => {
        function frame(now) {
          const k = Math.min(1, (now - start) / dur);
          const ease = 1 - Math.pow(1 - k, 3);
          const rot = cur + (final - cur) * ease;
          canvas.dataset.rot = rot;
          draw(rot);
          if (k < 1) requestAnimationFrame(frame);
          else res();
        }
        requestAnimationFrame(frame);
      });
      showResult(pick);
    } catch (err) {
      toast(err.message, "err");
    }
    spinning = false;
    btn.disabled = false;
  });
}

/* ------------------------------------------------ инициализация */

function afterRender() {
  initWheel();
  const t = document.getElementById("calc-t");
  const o = document.getElementById("calc-os");
  if (t && o) {
    t.oninput = calcUpdate;
    o.oninput = calcUpdate;
    calcUpdate();
  }
}

afterRender();
