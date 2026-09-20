/* The AI Post — Games runtime.
   One puzzle a day, the same for everyone, no account. State lives in the
   reader's browser only. Every game shares: the day number, seeded picks,
   a stats record with streaks, a share sheet, and the midnight countdown. */
window.Games = (function () {
  var EPOCH = Date.UTC(2026, 8, 19);            // puzzle #1: 19 September 2026

  function today() {
    var n = new Date();
    return Date.UTC(n.getFullYear(), n.getMonth(), n.getDate());
  }
  function day() { return Math.max(0, Math.floor((today() - EPOCH) / 86400000)); }
  function number() { return day() + 1; }

  // mulberry32: small, seedable, good enough to shuffle a puzzle pool
  function rng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function shuffle(list, seed) {
    var r = rng(seed), out = list.slice();
    for (var i = out.length - 1; i > 0; i--) {
      var j = Math.floor(r() * (i + 1)), t = out[i]; out[i] = out[j]; out[j] = t;
    }
    return out;
  }
  function pick(list, d) { return list[((d % list.length) + list.length) % list.length]; }

  // ---- storage: never throw, the page must work without it -------------
  function load(key) {
    try { return JSON.parse(localStorage.getItem("aipost.games." + key) || "null"); } catch (e) { return null; }
  }
  function save(key, value) {
    try { localStorage.setItem("aipost.games." + key, JSON.stringify(value)); } catch (e) {}
  }

  // Today's in-progress or finished state for a game.
  function state(game) {
    var s = load(game + ".today");
    return (s && s.day === day()) ? s : null;
  }
  function setState(game, s) { s.day = day(); save(game + ".today", s); return s; }

  // Stats + streak. A streak counts consecutive days *played and won*.
  function record(game, won) {
    var st = load(game + ".stats") || { played: 0, wins: 0, streak: 0, best: 0, last: null };
    if (st.last === day()) return st;              // already counted today
    st.played += 1;
    if (won) {
      st.streak = (st.last === day() - 1) ? st.streak + 1 : 1;
      st.wins += 1;
    } else {
      st.streak = 0;
    }
    st.best = Math.max(st.best, st.streak);
    st.last = day();
    save(game + ".stats", st);
    return st;
  }
  function stats(game) { return load(game + ".stats") || { played: 0, wins: 0, streak: 0, best: 0, last: null }; }

  // ---- DOM helpers -----------------------------------------------------
  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === "class") n.className = attrs[k];
      else if (k === "html") n.innerHTML = attrs[k];
      else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] !== null && attrs[k] !== undefined) n.setAttribute(k, attrs[k]);
    }
    (children || []).forEach(function (c) {
      if (c === null || c === undefined) return;
      n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return n;
  }
  function toast(msg) {
    // One at a time. Two toasts share the same fixed position, so a player
    // submitting quickly would otherwise stack them and read neither.
    document.querySelectorAll(".toast").forEach(function (old) { old.remove(); });
    var t = el("div", { class: "toast" }, [msg]);
    document.body.appendChild(t);
    requestAnimationFrame(function () { t.classList.add("toast--in"); });
    setTimeout(function () { t.classList.remove("toast--in"); setTimeout(function () { t.remove(); }, 300); }, 1800);
  }

  // ---- share -----------------------------------------------------------
  function share(text) {
    if (navigator.share && /Mobi|Android/i.test(navigator.userAgent)) {
      navigator.share({ text: text }).catch(function () {});
      return;
    }
    var done = function () { toast("Copied to clipboard"); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () { fallback(text); done(); });
    else { fallback(text); done(); }
  }
  function fallback(text) {
    var ta = el("textarea", { style: "position:fixed;opacity:0" }, [text]);
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    ta.remove();
  }

  // ---- countdown to the next puzzle -------------------------------------
  function countdown(node) {
    function tick() {
      var n = new Date(), mid = new Date(n.getFullYear(), n.getMonth(), n.getDate() + 1);
      var s = Math.max(0, Math.floor((mid - n) / 1000));
      var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
      node.textContent = [h, m, sec].map(function (v) { return (v < 10 ? "0" : "") + v; }).join(":");
    }
    tick(); setInterval(tick, 1000);
  }

  // The result panel every game ends on.
  function resultPanel(opts) {
    // opts: {game, title, lines:[...], shareText, stats, extra?: node}
    var st = opts.stats;
    var pct = st.played ? Math.round(100 * st.wins / st.played) : 0;
    var cd = el("span", { class: "result__clock" });
    countdown(cd);
    return el("section", { class: "result" }, [
      el("h2", { class: "result__title" }, [opts.title]),
      el("div", { class: "result__grid" }, opts.lines.map(function (l) { return el("div", null, [l]); })),
      opts.extra || null,
      el("div", { class: "stats" }, [
        stat(st.played, "Played"), stat(pct + "%", "Won"), stat(st.streak, "Streak"), stat(st.best, "Best")
      ]),
      el("div", { class: "result__actions" }, [
        el("button", { class: "btn", onclick: function () { share(opts.shareText); } }, ["Share"]),
        el("span", { class: "result__next" }, ["Next puzzle in ", cd])
      ])
    ]);
  }
  function stat(v, label) {
    return el("div", { class: "stat" }, [el("div", { class: "stat__v" }, [String(v)]), el("div", { class: "stat__l" }, [label])]);
  }

  // ---- timer: starts on the first move, survives a reload, stops on solve
  function timer(game, s, node) {
    function fmt(ms) { var t = Math.max(0, Math.floor(ms / 1000)); return Math.floor(t / 60) + ":" + ("0" + (t % 60)).slice(-2); }
    function paint() { node.textContent = s.elapsed != null ? fmt(s.elapsed) : s.startedAt ? fmt(Date.now() - s.startedAt) : "0:00"; }
    paint();
    var iv = setInterval(function () { paint(); if (s.elapsed != null) clearInterval(iv); }, 250);
    return {
      start: function () { if (!s.startedAt && s.elapsed == null) { s.startedAt = Date.now(); setState(game, s); } },
      stop: function () { if (s.elapsed == null) { s.elapsed = Date.now() - (s.startedAt || Date.now()); setState(game, s); } paint(); return fmt(s.elapsed); },
      text: function () { return fmt(s.elapsed != null ? s.elapsed : Date.now() - (s.startedAt || Date.now())); }
    };
  }

  function fetchJSON(url) { return fetch(url, { cache: "no-cache" }).then(function (r) { return r.json(); }); }

  return { timer: timer, day: day, number: number, rng: rng, shuffle: shuffle, pick: pick, state: state, setState: setState,
           record: record, stats: stats, el: el, toast: toast, share: share, countdown: countdown,
           resultPanel: resultPanel, fetchJSON: fetchJSON, SITE: "theaipost.net" };
})();
