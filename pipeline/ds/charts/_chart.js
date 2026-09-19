/* Newsroom Editorial — Chart renderer
   Reads <script id="chart-data" type="application/json"> and renders SVG.
   Brand: white canvas, off-black ink (#111111), action blue accent (#166dfc).
   To edit a chart, only edit the JSON. Coordinates are computed.
*/
(function () {
  // ---- palette ---------------------------------------------------------
  var P = {
    white: "#ffffff",
    ink: "#111111",
    inkDeep: "#000000",
    ink700: "#2a2a2a",
    ink600: "#595959",
    ink500: "#767676",
    ink400: "#9e9e9e",
    ink300: "#c4c4c4",
    ink200: "#e0e0e0",
    ink100: "#f2f2f2",
    ink050: "#f7f7f7",
    lime: "#166dfc",
    limeDeep: "#1366b3",
    limeSoft: "#e3edfd",
    success: "#1f7a4d",
    warning: "#a8710f",
    danger: "#c9221c"
  };
  // sequence used when a chart has multiple series and JSON does not specify colors
  var SERIES = [P.lime, P.ink, P.ink400, P.limeDeep, P.ink600, P.ink300, P.ink700, P.lime, P.ink200];

  // ---- tiny SVG builder -----------------------------------------------
  function el(tag, attrs, children) {
    var n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    if (attrs) for (var k in attrs) {
      if (attrs[k] === null || attrs[k] === undefined || attrs[k] === false) continue;
      n.setAttribute(k, attrs[k]);
    }
    if (children) {
      if (typeof children === "string" || typeof children === "number") n.textContent = children;
      else children.forEach(function (c) { if (c) n.appendChild(c); });
    }
    return n;
  }
  function g(attrs, kids) { return el("g", attrs, kids); }

  // ---- math helpers ---------------------------------------------------
  function nice(max) {
    if (max === 0) return 1;
    var exp = Math.floor(Math.log10(Math.abs(max)));
    var f = Math.abs(max) / Math.pow(10, exp);
    var nf = f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10;
    return nf * Math.pow(10, exp) * (max < 0 ? -1 : 1);
  }
  function ticks(min, max, count) {
    count = count || 5;
    var step = nice((max - min) / count);
    var lo = Math.floor(min / step) * step;
    var hi = Math.ceil(max / step) * step;
    var out = [];
    for (var v = lo; v <= hi + 1e-9; v += step) out.push(+v.toFixed(6));
    return out;
  }
  function fmt(v, opts) {
    opts = opts || {};
    if (opts.format === "%") return Math.round(v) + "%";
    if (opts.format === "€M") return "€" + v + "M";
    if (opts.format === "€B") return "€" + v + "B";
    if (opts.format === "x") return v + "×";
    if (typeof v === "number" && Math.abs(v) >= 1000) return v.toLocaleString("en-US");
    return String(v);
  }
  function pct(part, total) { return total ? (part / total) * 100 : 0; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  // shared header (eyebrow / title / subtitle / legend) is rendered in HTML, not SVG
  function header(d) {
    var host = document.getElementById("chart-host");
    var html = "";
    if (d.eyebrow) html += '<div class="eyebrow">' + escapeHtml(d.eyebrow) + "</div>";
    if (d.title) html += '<div class="title">' + escapeHtml(d.title) + "</div>";
    if (d.subtitle) html += '<div class="subtitle">' + escapeHtml(d.subtitle) + "</div>";
    host.innerHTML = html;
  }
  function escapeHtml(s) { return String(s).replace(/[&<>]/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]); }); }

  function legend(items) {
    var host = document.getElementById("chart-host");
    var div = document.createElement("div");
    div.className = "legend";
    items.forEach(function (it) {
      var s = document.createElement("span");
      s.innerHTML = '<span class="swatch" style="background:' + (it.color || P.lime) + '"></span>' + escapeHtml(it.label);
      div.appendChild(s);
    });
    host.appendChild(div);
  }

  // create a sized SVG and append it
  function makeSvg(w, h) {
    var svg = el("svg", { viewBox: "0 0 " + w + " " + h, width: "100%", preserveAspectRatio: "xMidYMid meet" });
    document.getElementById("chart-host").appendChild(svg);
    return svg;
  }

  // gridlines + y-axis labels (linear)
  function yAxis(svg, x0, x1, y0, y1, min, max, opts) {
    opts = opts || {};
    var ts = opts.ticks || ticks(min, max, 4);
    ts.forEach(function (t) {
      var y = y1 - ((t - min) / (max - min)) * (y1 - y0);
      svg.appendChild(el("line", { class: "gridline", x1: x0, y1: y, x2: x1, y2: y }));
      svg.appendChild(el("text", { class: "tick", x: x0 - 6, y: y + 3, "text-anchor": "end" }, fmt(t, opts)));
    });
    return ts;
  }

  // ---- chart types ====================================================
  var TYPES = {};

  // ====== BAR FAMILY ===================================================
  TYPES.bar = function (d) {
    var W = 640, H = 300, L = 40, R = 20, T = 16, B = 36;
    var data = d.data; // [{label,value}]
    var max = Math.max.apply(null, data.map(function (r) { return r.value; }));
    var maxT = nice(max * 1.1);
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, 0, maxT, { ticks: ticks(0, maxT, 4), format: d.format });
    var bw = (W - L - R) / data.length * 0.65;
    var step = (W - L - R) / data.length;
    data.forEach(function (r, i) {
      var x = L + step * i + (step - bw) / 2;
      var h = (r.value / maxT) * (H - B - T);
      var y = H - B - h;
      svg.appendChild(el("rect", { x: x, y: y, width: bw, height: h, fill: r.color || P.lime }));
      svg.appendChild(el("text", { class: "tick", x: x + bw / 2, y: H - B + 16, "text-anchor": "middle" }, r.label));
      svg.appendChild(el("text", { class: "value", x: x + bw / 2, y: y - 6, "text-anchor": "middle" }, fmt(r.value, d)));
    });
  };

  TYPES.hbar = function (d) {
    var data = d.data;
    var rowH = 36, gap = 8, L = 130, R = 50, T = 10, B = 10;
    var H = T + B + data.length * rowH;
    var W = 640;
    var max = Math.max.apply(null, data.map(function (r) { return r.value; }));
    var svg = makeSvg(W, H);
    svg.appendChild(el("line", { class: "axis", x1: L, y1: T, x2: L, y2: H - B }));
    data.forEach(function (r, i) {
      var y = T + i * rowH + 4;
      var w = (r.value / max) * (W - L - R);
      svg.appendChild(el("rect", { x: L, y: y, width: w, height: rowH - gap, fill: r.color || (i === 0 ? P.ink : P.lime) }));
      svg.appendChild(el("text", { class: "label", x: L - 10, y: y + (rowH - gap) / 2 + 4, "text-anchor": "end" }, r.label));
      svg.appendChild(el("text", { class: "value", x: L + w + 6, y: y + (rowH - gap) / 2 + 4 }, fmt(r.value, d)));
    });
  };

  TYPES.stackedBar = function (d) {
    var W = 640, H = 300, L = 40, R = 20, T = 16, B = 36;
    var cats = d.categories, ser = d.series;
    var totals = cats.map(function (_, i) { return ser.reduce(function (s, x) { return s + x.values[i]; }, 0); });
    var max = nice(Math.max.apply(null, totals) * 1.1);
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, 0, max, { ticks: ticks(0, max, 4), format: d.format });
    var bw = (W - L - R) / cats.length * 0.6;
    var step = (W - L - R) / cats.length;
    cats.forEach(function (c, i) {
      var x = L + step * i + (step - bw) / 2;
      var yCur = H - B;
      ser.forEach(function (s, si) {
        var v = s.values[i];
        var h = (v / max) * (H - B - T);
        yCur -= h;
        svg.appendChild(el("rect", { x: x, y: yCur, width: bw, height: h, fill: s.color || SERIES[si] }));
      });
      svg.appendChild(el("text", { class: "tick", x: x + bw / 2, y: H - B + 16, "text-anchor": "middle" }, c));
      svg.appendChild(el("text", { class: "value", x: x + bw / 2, y: yCur - 6, "text-anchor": "middle" }, fmt(totals[i], d)));
    });
    legend(ser.map(function (s, i) { return { label: s.name, color: s.color || SERIES[i] }; }));
  };

  TYPES.groupedBar = function (d) {
    var W = 640, H = 300, L = 40, R = 20, T = 16, B = 36;
    var cats = d.categories, ser = d.series;
    var max = nice(Math.max.apply(null, ser.reduce(function (a, s) { return a.concat(s.values); }, [])) * 1.1);
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, 0, max, { ticks: ticks(0, max, 4), format: d.format });
    var groupW = (W - L - R) / cats.length * 0.7;
    var step = (W - L - R) / cats.length;
    var bw = groupW / ser.length;
    cats.forEach(function (c, i) {
      var gx = L + step * i + (step - groupW) / 2;
      ser.forEach(function (s, si) {
        var v = s.values[i];
        var h = (v / max) * (H - B - T);
        var x = gx + si * bw;
        svg.appendChild(el("rect", { x: x + 1, y: H - B - h, width: bw - 2, height: h, fill: s.color || SERIES[si] }));
      });
      svg.appendChild(el("text", { class: "tick", x: gx + groupW / 2, y: H - B + 16, "text-anchor": "middle" }, c));
    });
    legend(ser.map(function (s, i) { return { label: s.name, color: s.color || SERIES[i] }; }));
  };

  TYPES.stacked100 = function (d) {
    var W = 640, H = 300, L = 40, R = 20, T = 16, B = 36;
    var cats = d.categories, ser = d.series;
    var svg = makeSvg(W, H);
    [0, 25, 50, 75, 100].forEach(function (t) {
      var y = T + (1 - t / 100) * (H - T - B);
      svg.appendChild(el("line", { class: "gridline", x1: L, y1: y, x2: W - R, y2: y }));
      svg.appendChild(el("text", { class: "tick", x: L - 6, y: y + 3, "text-anchor": "end" }, t + "%"));
    });
    var bw = (W - L - R) / cats.length * 0.6;
    var step = (W - L - R) / cats.length;
    cats.forEach(function (c, i) {
      var total = ser.reduce(function (s, x) { return s + x.values[i]; }, 0);
      var x = L + step * i + (step - bw) / 2;
      var yCur = H - B;
      ser.forEach(function (s, si) {
        var v = s.values[i];
        var h = (v / total) * (H - T - B);
        yCur -= h;
        svg.appendChild(el("rect", { x: x, y: yCur, width: bw, height: h, fill: s.color || SERIES[si] }));
        if (h > 18) svg.appendChild(el("text", {
          x: x + bw / 2, y: yCur + h / 2 + 4, "text-anchor": "middle",
          "font-size": 10, "font-weight": 700, fill: si === 0 ? P.ink : P.white
        }, Math.round(v / total * 100) + "%"));
      });
      svg.appendChild(el("text", { class: "tick", x: x + bw / 2, y: H - B + 16, "text-anchor": "middle" }, c));
    });
    legend(ser.map(function (s, i) { return { label: s.name, color: s.color || SERIES[i] }; }));
  };

  TYPES.divergingBar = function (d) {
    var data = d.data;
    var rowH = 30, L = 200, R = 30, T = 10;
    var H = T + data.length * rowH + 10, W = 640;
    var max = Math.max.apply(null, data.map(function (r) { return Math.abs(r.value); }));
    var mid = (L + (W - R)) / 2;
    var halfW = (W - R - L) / 2;
    var svg = makeSvg(W, H);
    svg.appendChild(el("line", { class: "axis", x1: mid, y1: T, x2: mid, y2: H - 4 }));
    data.forEach(function (r, i) {
      var y = T + i * rowH + 3;
      var w = (Math.abs(r.value) / max) * halfW;
      var x = r.value >= 0 ? mid : mid - w;
      svg.appendChild(el("rect", { x: x, y: y, width: w, height: rowH - 8, fill: r.value >= 0 ? P.lime : P.ink }));
      svg.appendChild(el("text", { class: "label", x: r.value >= 0 ? mid - 8 : mid + 8, y: y + (rowH - 8) / 2 + 4, "text-anchor": r.value >= 0 ? "end" : "start" }, r.label));
      svg.appendChild(el("text", { class: "value", x: r.value >= 0 ? x + w + 6 : x - 6, y: y + (rowH - 8) / 2 + 4, "text-anchor": r.value >= 0 ? "start" : "end" }, (r.value > 0 ? "+" : "") + fmt(r.value, d)));
    });
  };

  TYPES.population = function (d) {
    var L = d.left, R = d.right;
    var bins = d.bins;
    var W = 640, rowH = 22;
    var H = bins.length * rowH + 50, mid = W / 2, halfW = (W - 200) / 2;
    var max = Math.max.apply(null, bins.map(function (b) { return Math.max(b.left, b.right); }));
    var svg = makeSvg(W, H);
    bins.forEach(function (b, i) {
      var y = 20 + i * rowH;
      var lw = (b.left / max) * halfW;
      var rw = (b.right / max) * halfW;
      svg.appendChild(el("rect", { x: mid - lw, y: y, width: lw, height: rowH - 6, fill: P.ink }));
      svg.appendChild(el("rect", { x: mid, y: y, width: rw, height: rowH - 6, fill: P.lime }));
      svg.appendChild(el("text", { x: mid, y: y + rowH / 2 + 3, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink }, b.label));
    });
    svg.appendChild(el("text", { x: 20, y: 14, "font-size": 11, "font-weight": 700, fill: P.ink }, L));
    svg.appendChild(el("text", { x: W - 20, y: 14, "font-size": 11, "font-weight": 700, "text-anchor": "end", fill: P.ink }, R));
  };

  TYPES.lollipop = function (d) {
    var data = d.data;
    var rowH = 32, L = 130, R = 50, T = 12;
    var H = T + data.length * rowH + 10, W = 640;
    var max = Math.max.apply(null, data.map(function (r) { return r.value; }));
    var svg = makeSvg(W, H);
    svg.appendChild(el("line", { class: "axis", x1: L, y1: T, x2: L, y2: H - 4 }));
    data.forEach(function (r, i) {
      var y = T + i * rowH + rowH / 2;
      var x2 = L + (r.value / max) * (W - L - R);
      svg.appendChild(el("line", { x1: L, y1: y, x2: x2, y2: y, stroke: P.ink, "stroke-width": 1.5 }));
      svg.appendChild(el("circle", { cx: x2, cy: y, r: 8, fill: P.lime, stroke: P.ink, "stroke-width": 1.5 }));
      svg.appendChild(el("text", { class: "label", x: L - 10, y: y + 4, "text-anchor": "end" }, r.label));
      svg.appendChild(el("text", { class: "value", x: x2 + 14, y: y + 4 }, fmt(r.value, d)));
    });
  };

  TYPES.dotPlot = function (d) {
    var data = d.data; // {label, a, b}
    var rowH = 32, L = 140, R = 60, T = 16;
    var H = T + data.length * rowH + 10, W = 640;
    var all = data.reduce(function (a, r) { return a.concat([r.a, r.b]); }, []);
    var min = Math.min.apply(null, all), max = Math.max.apply(null, all);
    var pad = (max - min) * 0.1;
    var lo = min - pad, hi = max + pad;
    var svg = makeSvg(W, H);
    var sx = function (v) { return L + (v - lo) / (hi - lo) * (W - L - R); };
    data.forEach(function (r, i) {
      var y = T + i * rowH + rowH / 2;
      svg.appendChild(el("line", { x1: sx(r.a), y1: y, x2: sx(r.b), y2: y, stroke: P.ink300, "stroke-width": 2 }));
      svg.appendChild(el("circle", { cx: sx(r.a), cy: y, r: 6, fill: P.ink }));
      svg.appendChild(el("circle", { cx: sx(r.b), cy: y, r: 6, fill: P.lime, stroke: P.ink, "stroke-width": 1 }));
      svg.appendChild(el("text", { class: "label", x: L - 10, y: y + 4, "text-anchor": "end" }, r.label));
    });
    legend([{ label: d.aLabel || "A", color: P.ink }, { label: d.bLabel || "B", color: P.lime }]);
  };

  TYPES.errorBars = function (d) {
    var W = 640, H = 280, L = 40, R = 20, T = 16, B = 36;
    var data = d.data; // {label, value, lo, hi}
    var max = nice(Math.max.apply(null, data.map(function (r) { return r.hi; })) * 1.1);
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, 0, max, { format: d.format });
    var step = (W - L - R) / data.length;
    data.forEach(function (r, i) {
      var x = L + step * i + step / 2;
      var sy = function (v) { return H - B - (v / max) * (H - B - T); };
      svg.appendChild(el("line", { x1: x, y1: sy(r.lo), x2: x, y2: sy(r.hi), stroke: P.ink, "stroke-width": 1.5 }));
      svg.appendChild(el("line", { x1: x - 8, y1: sy(r.hi), x2: x + 8, y2: sy(r.hi), stroke: P.ink, "stroke-width": 1.5 }));
      svg.appendChild(el("line", { x1: x - 8, y1: sy(r.lo), x2: x + 8, y2: sy(r.lo), stroke: P.ink, "stroke-width": 1.5 }));
      svg.appendChild(el("circle", { cx: x, cy: sy(r.value), r: 7, fill: P.lime, stroke: P.ink, "stroke-width": 1.2 }));
      svg.appendChild(el("text", { class: "tick", x: x, y: H - B + 16, "text-anchor": "middle" }, r.label));
    });
  };

  // ====== TREND FAMILY =================================================
  function lineCommon(d, opts) {
    opts = opts || {};
    var W = 640, H = 260, L = 40, R = 20, T = 14, B = 30;
    var labels = d.labels;
    var series = d.series || [{ name: d.name || "Value", values: d.values, color: P.lime }];
    var all = series.reduce(function (a, s) { return a.concat(s.values); }, []);
    var max = nice(Math.max.apply(null, all) * 1.1);
    var min = opts.includeNegative ? Math.min(0, Math.min.apply(null, all)) : 0;
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, min, max, { format: d.format });
    var step = labels.length > 1 ? (W - L - R) / (labels.length - 1) : 0;
    var sx = function (i) { return L + i * step; };
    var sy = function (v) { return H - B - ((v - min) / (max - min)) * (H - B - T); };
    labels.forEach(function (lb, i) {
      svg.appendChild(el("text", { class: "tick", x: sx(i), y: H - B + 16, "text-anchor": "middle" }, lb));
    });
    return { svg: svg, sx: sx, sy: sy, series: series, W: W, H: H, L: L, R: R, T: T, B: B };
  }

  TYPES.line = function (d) {
    var ctx = lineCommon(d);
    ctx.series.forEach(function (s, si) {
      var pts = s.values.map(function (v, i) { return ctx.sx(i) + "," + ctx.sy(v); }).join(" L ");
      ctx.svg.appendChild(el("path", { d: "M" + pts, fill: "none", stroke: s.color || (si === 0 ? P.lime : SERIES[si]), "stroke-width": 3, "stroke-linejoin": "round", "stroke-linecap": "round" }));
      s.values.forEach(function (v, i) {
        ctx.svg.appendChild(el("circle", { cx: ctx.sx(i), cy: ctx.sy(v), r: 4, fill: s.color || P.lime, stroke: P.ink, "stroke-width": 1.2 }));
      });
    });
    if (ctx.series.length > 1) legend(ctx.series.map(function (s, i) { return { label: s.name, color: s.color || SERIES[i] }; }));
  };
  TYPES.multiLine = TYPES.line;

  TYPES.spline = function (d) {
    var ctx = lineCommon(d);
    function smooth(pts) {
      if (pts.length < 2) return "";
      var path = "M" + pts[0][0] + "," + pts[0][1];
      for (var i = 0; i < pts.length - 1; i++) {
        var p0 = pts[i === 0 ? 0 : i - 1];
        var p1 = pts[i];
        var p2 = pts[i + 1];
        var p3 = pts[i + 2 < pts.length ? i + 2 : i + 1];
        var c1x = p1[0] + (p2[0] - p0[0]) / 6;
        var c1y = p1[1] + (p2[1] - p0[1]) / 6;
        var c2x = p2[0] - (p3[0] - p1[0]) / 6;
        var c2y = p2[1] - (p3[1] - p1[1]) / 6;
        path += " C" + c1x + "," + c1y + " " + c2x + "," + c2y + " " + p2[0] + "," + p2[1];
      }
      return path;
    }
    ctx.series.forEach(function (s, si) {
      var pts = s.values.map(function (v, i) { return [ctx.sx(i), ctx.sy(v)]; });
      ctx.svg.appendChild(el("path", { d: smooth(pts), fill: "none", stroke: s.color || (si === 0 ? P.lime : SERIES[si]), "stroke-width": 3 }));
    });
  };

  TYPES.area = function (d) {
    var ctx = lineCommon(d);
    var s = ctx.series[0];
    var pts = s.values.map(function (v, i) { return ctx.sx(i) + "," + ctx.sy(v); });
    var area = "M" + ctx.sx(0) + "," + ctx.sy(0) + " L" + pts.join(" L ") + " L" + ctx.sx(s.values.length - 1) + "," + ctx.sy(0) + " Z";
    ctx.svg.appendChild(el("path", { d: area, fill: s.color || P.lime, opacity: 0.5 }));
    ctx.svg.appendChild(el("path", { d: "M" + pts.join(" L "), fill: "none", stroke: P.ink, "stroke-width": 1.5 }));
  };

  TYPES.stackedArea = function (d) {
    var ctx = lineCommon({ labels: d.labels, series: [{ values: d.series.reduce(function (a, s) { return s.values.map(function (v, i) { return v + (a[i] || 0); }); }, []) }], format: d.format });
    var labels = d.labels, ser = d.series;
    // recompute scale on totals
    var totals = labels.map(function (_, i) { return ser.reduce(function (s, x) { return s + x.values[i]; }, 0); });
    var max = nice(Math.max.apply(null, totals) * 1.1);
    // wipe and redraw
    ctx.svg.innerHTML = "";
    yAxis(ctx.svg, ctx.L, ctx.W - ctx.R, ctx.T, ctx.H - ctx.B, 0, max, { format: d.format });
    var step = (ctx.W - ctx.L - ctx.R) / (labels.length - 1);
    var sx = function (i) { return ctx.L + i * step; };
    var sy = function (v) { return ctx.H - ctx.B - (v / max) * (ctx.H - ctx.B - ctx.T); };
    labels.forEach(function (lb, i) { ctx.svg.appendChild(el("text", { class: "tick", x: sx(i), y: ctx.H - ctx.B + 16, "text-anchor": "middle" }, lb)); });
    var stack = labels.map(function () { return 0; });
    ser.forEach(function (s, si) {
      var top = s.values.map(function (v, i) { return stack[i] + v; });
      var pts = "";
      top.forEach(function (v, i) { pts += (i ? " L" : "M") + sx(i) + "," + sy(v); });
      for (var i = stack.length - 1; i >= 0; i--) pts += " L" + sx(i) + "," + sy(stack[i]);
      pts += " Z";
      ctx.svg.appendChild(el("path", { d: pts, fill: s.color || SERIES[si], opacity: 0.85 }));
      stack = top;
    });
    legend(ser.map(function (s, i) { return { label: s.name, color: s.color || SERIES[i] }; }));
  };

  TYPES.step = function (d) {
    var ctx = lineCommon(d);
    var s = ctx.series[0];
    var path = "M" + ctx.sx(0) + "," + ctx.sy(s.values[0]);
    for (var i = 1; i < s.values.length; i++) {
      path += " L" + ctx.sx(i) + "," + ctx.sy(s.values[i - 1]);
      path += " L" + ctx.sx(i) + "," + ctx.sy(s.values[i]);
    }
    ctx.svg.appendChild(el("path", { d: path, fill: "none", stroke: P.lime, "stroke-width": 3 }));
    s.values.forEach(function (v, i) {
      ctx.svg.appendChild(el("circle", { cx: ctx.sx(i), cy: ctx.sy(v), r: 3, fill: P.ink }));
    });
  };

  TYPES.stepArea = function (d) {
    var ctx = lineCommon(d);
    var s = ctx.series[0];
    var path = "M" + ctx.sx(0) + "," + ctx.sy(0) + " L" + ctx.sx(0) + "," + ctx.sy(s.values[0]);
    for (var i = 1; i < s.values.length; i++) {
      path += " L" + ctx.sx(i) + "," + ctx.sy(s.values[i - 1]);
      path += " L" + ctx.sx(i) + "," + ctx.sy(s.values[i]);
    }
    path += " L" + ctx.sx(s.values.length - 1) + "," + ctx.sy(0) + " Z";
    ctx.svg.appendChild(el("path", { d: path, fill: P.lime, opacity: 0.55 }));
  };

  TYPES.slope = function (d) {
    var W = 640, H = 280, L = 100, R = 100, T = 30, B = 30;
    var data = d.data;
    var leftLabel = d.leftLabel || "A", rightLabel = d.rightLabel || "B";
    var all = data.reduce(function (a, r) { return a.concat([r.left, r.right]); }, []);
    var min = Math.min.apply(null, all), max = Math.max.apply(null, all);
    var pad = (max - min) * 0.15 || 1;
    var lo = min - pad, hi = max + pad;
    var sy = function (v) { return H - B - (v - lo) / (hi - lo) * (H - B - T); };
    var svg = makeSvg(W, H);
    svg.appendChild(el("text", { x: L, y: T - 10, "font-size": 11, "font-weight": 700, "text-anchor": "middle", fill: P.ink }, leftLabel));
    svg.appendChild(el("text", { x: W - R, y: T - 10, "font-size": 11, "font-weight": 700, "text-anchor": "middle", fill: P.ink }, rightLabel));
    data.forEach(function (r) {
      var color = r.color || (r.right > r.left ? P.lime : P.ink400);
      svg.appendChild(el("line", { x1: L, y1: sy(r.left), x2: W - R, y2: sy(r.right), stroke: color, "stroke-width": 2 }));
      svg.appendChild(el("circle", { cx: L, cy: sy(r.left), r: 4, fill: color }));
      svg.appendChild(el("circle", { cx: W - R, cy: sy(r.right), r: 4, fill: color }));
      svg.appendChild(el("text", { x: L - 8, y: sy(r.left) + 4, "text-anchor": "end", "font-size": 11, fill: P.ink }, r.label + " " + fmt(r.left, d)));
      svg.appendChild(el("text", { x: W - R + 8, y: sy(r.right) + 4, "font-size": 11, fill: P.ink }, fmt(r.right, d)));
    });
  };

  TYPES.threshold = function (d) {
    var ctx = lineCommon(d);
    var s = ctx.series[0];
    var thr = d.threshold;
    var ty = ctx.sy(thr);
    ctx.svg.appendChild(el("line", { x1: ctx.L, y1: ty, x2: ctx.W - ctx.R, y2: ty, stroke: P.ink, "stroke-width": 1, "stroke-dasharray": "4 3" }));
    ctx.svg.appendChild(el("text", { x: ctx.W - ctx.R, y: ty - 4, "text-anchor": "end", "font-size": 10, "font-weight": 700, fill: P.ink }, "Target " + fmt(thr, d)));
    var pts = s.values.map(function (v, i) { return [ctx.sx(i), ctx.sy(v)]; });
    ctx.svg.appendChild(el("path", { d: "M" + pts.map(function (p) { return p.join(","); }).join(" L "), fill: "none", stroke: P.ink, "stroke-width": 2 }));
    s.values.forEach(function (v, i) {
      ctx.svg.appendChild(el("circle", { cx: ctx.sx(i), cy: ctx.sy(v), r: 5, fill: v >= thr ? P.lime : P.white, stroke: P.ink, "stroke-width": 1.5 }));
    });
  };

  TYPES.dualAxis = function (d) {
    var W = 640, H = 280, L = 50, R = 50, T = 16, B = 30;
    var labels = d.labels, bars = d.bars, line = d.line;
    var maxB = nice(Math.max.apply(null, bars.values) * 1.1);
    var maxL = nice(Math.max.apply(null, line.values) * 1.1);
    var svg = makeSvg(W, H);
    var step = (W - L - R) / labels.length;
    var bw = step * 0.55;
    [0, 0.25, 0.5, 0.75, 1].forEach(function (t) {
      var y = H - B - t * (H - B - T);
      svg.appendChild(el("line", { class: "gridline", x1: L, y1: y, x2: W - R, y2: y }));
      svg.appendChild(el("text", { class: "tick", x: L - 6, y: y + 3, "text-anchor": "end" }, fmt(maxB * t, { format: bars.format })));
      svg.appendChild(el("text", { class: "tick", x: W - R + 6, y: y + 3 }, fmt(maxL * t, { format: line.format })));
    });
    labels.forEach(function (lb, i) {
      var x = L + step * i + (step - bw) / 2;
      var h = (bars.values[i] / maxB) * (H - B - T);
      svg.appendChild(el("rect", { x: x, y: H - B - h, width: bw, height: h, fill: P.lime }));
      svg.appendChild(el("text", { class: "tick", x: L + step * i + step / 2, y: H - B + 16, "text-anchor": "middle" }, lb));
    });
    var lp = line.values.map(function (v, i) { return (L + step * i + step / 2) + "," + (H - B - (v / maxL) * (H - B - T)); }).join(" L ");
    svg.appendChild(el("path", { d: "M" + lp, fill: "none", stroke: P.ink, "stroke-width": 2.5 }));
    line.values.forEach(function (v, i) {
      svg.appendChild(el("circle", { cx: L + step * i + step / 2, cy: H - B - (v / maxL) * (H - B - T), r: 4, fill: P.ink }));
    });
    legend([{ label: bars.name, color: P.lime }, { label: line.name, color: P.ink }]);
  };

  TYPES.candlestick = function (d) {
    var W = 640, H = 280, L = 40, R = 20, T = 16, B = 30;
    var data = d.data; // {label, o, h, l, c}
    var all = data.reduce(function (a, r) { return a.concat([r.h, r.l]); }, []);
    var min = Math.min.apply(null, all) * 0.98, max = Math.max.apply(null, all) * 1.02;
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, min, max, { format: d.format });
    var step = (W - L - R) / data.length;
    var bw = step * 0.5;
    data.forEach(function (r, i) {
      var x = L + step * i + step / 2;
      var sy = function (v) { return H - B - (v - min) / (max - min) * (H - B - T); };
      var up = r.c >= r.o;
      svg.appendChild(el("line", { x1: x, y1: sy(r.h), x2: x, y2: sy(r.l), stroke: P.ink, "stroke-width": 1 }));
      svg.appendChild(el("rect", { x: x - bw / 2, y: sy(Math.max(r.o, r.c)), width: bw, height: Math.max(2, Math.abs(sy(r.o) - sy(r.c))), fill: up ? P.lime : P.ink }));
      svg.appendChild(el("text", { class: "tick", x: x, y: H - B + 16, "text-anchor": "middle" }, r.label));
    });
  };

  TYPES.stream = function (d) {
    var W = 640, H = 260, L = 30, R = 20, T = 16, B = 26;
    var labels = d.labels, ser = d.series;
    var totals = labels.map(function (_, i) { return ser.reduce(function (s, x) { return s + x.values[i]; }, 0); });
    var maxT = Math.max.apply(null, totals);
    var step = (W - L - R) / (labels.length - 1);
    var sx = function (i) { return L + i * step; };
    var midY = (H - B + T) / 2;
    var svg = makeSvg(W, H);
    var stack = labels.map(function (_, i) { return -totals[i] / 2; });
    ser.forEach(function (s, si) {
      var top = stack.map(function (v, i) { return v + s.values[i]; });
      var path = "";
      top.forEach(function (v, i) {
        var y = midY + (v / maxT) * (H - T - B) * 0.9;
        path += (i ? " L" : "M") + sx(i) + "," + y;
      });
      for (var i = stack.length - 1; i >= 0; i--) {
        var y = midY + (stack[i] / maxT) * (H - T - B) * 0.9;
        path += " L" + sx(i) + "," + y;
      }
      path += " Z";
      svg.appendChild(el("path", { d: path, fill: s.color || SERIES[si], opacity: 0.85 }));
      stack = top;
    });
    labels.forEach(function (lb, i) { svg.appendChild(el("text", { class: "tick", x: sx(i), y: H - 8, "text-anchor": "middle" }, lb)); });
    legend(ser.map(function (s, i) { return { label: s.name, color: s.color || SERIES[i] }; }));
  };

  // ====== COMPOSITION =================================================
  TYPES.pie = function (d) {
    var W = 640, H = 260, cx = 160, cy = 130, r = 100;
    var data = d.data; // {label, value, color}
    var total = data.reduce(function (s, x) { return s + x.value; }, 0);
    var svg = makeSvg(W, H);
    var a0 = -Math.PI / 2;
    data.forEach(function (s, i) {
      var a1 = a0 + (s.value / total) * Math.PI * 2;
      var large = (a1 - a0) > Math.PI ? 1 : 0;
      var x1 = cx + r * Math.cos(a0), y1 = cy + r * Math.sin(a0);
      var x2 = cx + r * Math.cos(a1), y2 = cy + r * Math.sin(a1);
      svg.appendChild(el("path", { d: "M" + cx + "," + cy + " L" + x1 + "," + y1 + " A" + r + "," + r + " 0 " + large + " 1 " + x2 + "," + y2 + " Z", fill: s.color || SERIES[i], stroke: P.white, "stroke-width": 2 }));
      a0 = a1;
    });
    // legend on right
    data.forEach(function (s, i) {
      var y = 30 + i * 24;
      svg.appendChild(el("rect", { x: 320, y: y - 10, width: 12, height: 12, fill: s.color || SERIES[i] }));
      svg.appendChild(el("text", { x: 340, y: y, "font-size": 12, fill: P.ink }, s.label + " · " + Math.round(s.value / total * 100) + "%"));
    });
  };

  TYPES.donut = function (d) {
    var W = 640, H = 260, cx = 160, cy = 130, r = 100, ir = 65;
    var data = d.data;
    var total = data.reduce(function (s, x) { return s + x.value; }, 0);
    var svg = makeSvg(W, H);
    var a0 = -Math.PI / 2;
    data.forEach(function (s, i) {
      var a1 = a0 + (s.value / total) * Math.PI * 2;
      var large = (a1 - a0) > Math.PI ? 1 : 0;
      var x1 = cx + r * Math.cos(a0), y1 = cy + r * Math.sin(a0);
      var x2 = cx + r * Math.cos(a1), y2 = cy + r * Math.sin(a1);
      var ix1 = cx + ir * Math.cos(a1), iy1 = cy + ir * Math.sin(a1);
      var ix2 = cx + ir * Math.cos(a0), iy2 = cy + ir * Math.sin(a0);
      svg.appendChild(el("path", { d: "M" + x1 + "," + y1 + " A" + r + "," + r + " 0 " + large + " 1 " + x2 + "," + y2 + " L" + ix1 + "," + iy1 + " A" + ir + "," + ir + " 0 " + large + " 0 " + ix2 + "," + iy2 + " Z", fill: s.color || SERIES[i], stroke: P.white, "stroke-width": 2 }));
      a0 = a1;
    });
    if (d.center) {
      svg.appendChild(el("text", { x: cx, y: cy - 4, "text-anchor": "middle", "font-family": "Carnas, Arial", "font-size": 28, "font-weight": 700, fill: P.ink }, d.center));
      if (d.centerLabel) svg.appendChild(el("text", { x: cx, y: cy + 16, "text-anchor": "middle", "font-size": 11, fill: P.ink600 }, d.centerLabel));
    }
    data.forEach(function (s, i) {
      var y = 30 + i * 24;
      svg.appendChild(el("rect", { x: 320, y: y - 10, width: 12, height: 12, fill: s.color || SERIES[i] }));
      svg.appendChild(el("text", { x: 340, y: y, "font-size": 12, fill: P.ink }, s.label + " · " + Math.round(s.value / total * 100) + "%"));
    });
  };

  TYPES.multiDonut = function (d) {
    var W = 640, H = 260;
    var rings = d.rings;
    var cx = 160, cy = 130;
    var svg = makeSvg(W, H);
    rings.forEach(function (r, i) {
      var rad = 110 - i * 22;
      var ir = rad - 14;
      var midR = (rad + ir) / 2;
      svg.appendChild(el("circle", { cx: cx, cy: cy, r: midR, fill: "none", stroke: P.ink100, "stroke-width": rad - ir }));
      var pct = r.value / r.max;
      var a = pct * Math.PI * 2;
      var sxp = cx, syp = cy - midR;
      var ex = cx + Math.sin(a) * midR;
      var ey = cy - Math.cos(a) * midR;
      var large = a > Math.PI ? 1 : 0;
      svg.appendChild(el("path", { d: "M" + sxp + "," + syp + " A" + midR + "," + midR + " 0 " + large + " 1 " + ex + "," + ey, fill: "none", stroke: P.lime, "stroke-width": rad - ir, "stroke-linecap": "round" }));
      svg.appendChild(el("text", { x: 320, y: 40 + i * 30, "font-size": 12, fill: P.ink, "font-weight": 700 }, r.label));
      svg.appendChild(el("text", { x: 320, y: 56 + i * 30, "font-size": 11, fill: P.ink600 }, fmt(r.value, d) + " / " + fmt(r.max, d) + " · " + Math.round(pct * 100) + "%"));
    });
  };

  TYPES.treemap = function (d) {
    var W = 640, H = 280;
    var data = d.data; // {label, value, color}
    var total = data.reduce(function (s, x) { return s + x.value; }, 0);
    var svg = makeSvg(W, H);
    // simple squarified-like layout (greedy strips)
    var rows = [], curRow = [], curSum = 0, target = total / 2;
    data.sort(function (a, b) { return b.value - a.value; });
    data.forEach(function (r) {
      curRow.push(r); curSum += r.value;
      if (curSum >= target && rows.length === 0) { rows.push(curRow); curRow = []; curSum = 0; target = total - rows[0].reduce(function (s, x) { return s + x.value; }, 0); }
    });
    if (curRow.length) rows.push(curRow);
    var rowH = H / rows.length;
    rows.forEach(function (row, ri) {
      var rowSum = row.reduce(function (s, x) { return s + x.value; }, 0);
      var x = 0;
      row.forEach(function (r, ci) {
        var w = (r.value / rowSum) * W;
        var color = r.color || (ri === 0 && ci === 0 ? P.lime : SERIES[(ri + ci) % SERIES.length]);
        svg.appendChild(el("rect", { x: x, y: ri * rowH, width: w - 2, height: rowH - 2, fill: color }));
        if (w > 60 && rowH > 32) {
          var dark = color === P.ink || color === P.inkDeep || color === P.ink700 || color === P.ink600;
          svg.appendChild(el("text", { x: x + 8, y: ri * rowH + 18, "font-size": 11, "font-weight": 700, fill: dark ? P.white : P.ink }, r.label));
          svg.appendChild(el("text", { x: x + 8, y: ri * rowH + 34, "font-size": 11, fill: dark ? P.lime : P.ink }, fmt(r.value, d)));
        }
        x += w;
      });
    });
  };

  TYPES.marimekko = function (d) {
    var W = 640, H = 280;
    var cols = d.columns; // {label, weight, segments:[{label,value}]}
    var totalW = cols.reduce(function (s, c) { return s + c.weight; }, 0);
    var svg = makeSvg(W, H);
    var x = 0;
    cols.forEach(function (c, ci) {
      var w = (c.weight / totalW) * W;
      var totalS = c.segments.reduce(function (s, x) { return s + x.value; }, 0);
      var y = 0;
      c.segments.forEach(function (s, si) {
        var h = (s.value / totalS) * H;
        svg.appendChild(el("rect", { x: x + 1, y: y + 1, width: w - 2, height: h - 2, fill: s.color || (si === 0 ? P.lime : SERIES[si]) }));
        if (w > 50 && h > 24) svg.appendChild(el("text", { x: x + 6, y: y + 16, "font-size": 10, "font-weight": 700, fill: P.ink }, s.label));
        y += h;
      });
      svg.appendChild(el("text", { x: x + w / 2, y: H + 16, "text-anchor": "middle", "font-size": 11, "font-weight": 700, fill: P.ink }, c.label));
      x += w;
    });
  };

  TYPES.polarArea = function (d) {
    var W = 640, H = 280, cx = 200, cy = 140;
    var data = d.data;
    var max = Math.max.apply(null, data.map(function (r) { return r.value; }));
    var svg = makeSvg(W, H);
    var step = Math.PI * 2 / data.length;
    data.forEach(function (s, i) {
      var a0 = -Math.PI / 2 + i * step, a1 = a0 + step;
      var r = (s.value / max) * 110;
      var x1 = cx + r * Math.cos(a0), y1 = cy + r * Math.sin(a0);
      var x2 = cx + r * Math.cos(a1), y2 = cy + r * Math.sin(a1);
      svg.appendChild(el("path", { d: "M" + cx + "," + cy + " L" + x1 + "," + y1 + " A" + r + "," + r + " 0 0 1 " + x2 + "," + y2 + " Z", fill: s.color || SERIES[i], opacity: 0.85, stroke: P.white }));
    });
    data.forEach(function (s, i) {
      svg.appendChild(el("rect", { x: 380, y: 30 + i * 22, width: 12, height: 12, fill: s.color || SERIES[i] }));
      svg.appendChild(el("text", { x: 400, y: 40 + i * 22, "font-size": 11, fill: P.ink }, s.label + " · " + fmt(s.value, d)));
    });
  };

  TYPES.pyramid = function (d) {
    var W = 640, H = 280;
    var data = d.data; // ordered widest→narrowest
    var svg = makeSvg(W, H);
    var rowH = (H - 20) / data.length;
    data.forEach(function (r, i) {
      var widthFrac = (data.length - i) / data.length;
      var w = widthFrac * (W - 80);
      var x = (W - w) / 2;
      var y = 10 + i * rowH;
      svg.appendChild(el("path", { d: "M" + x + "," + (y + rowH - 4) + " L" + (W - x) + "," + (y + rowH - 4) + " L" + (W - x + (w / data.length) / 2) + "," + (y) + " L" + (x - (w / data.length) / 2 + (w / data.length)) + "," + (y) + " Z", fill: r.color || (i === 0 ? P.lime : SERIES[i % SERIES.length]) }));
      svg.appendChild(el("text", { x: W / 2, y: y + rowH / 2 + 4, "text-anchor": "middle", "font-size": 12, "font-weight": 700, fill: i === 0 ? P.ink : P.white }, r.label + " · " + fmt(r.value, d)));
    });
  };

  TYPES.icicle = function (d) {
    // Top-down hierarchy: root spans full width on row 0, children fill below
    // proportionally to their value. Each level offset visually + label readable.
    var W = 640, H = 280;
    var root = d.root;
    var svg = makeSvg(W, H);
    function depth(n) { if (!n.children || !n.children.length) return 1; return 1 + Math.max.apply(null, n.children.map(depth)); }
    function sumLeaves(n) { if (!n.children || !n.children.length) return n.value || 0; return n.children.reduce(function (s, c) { return s + sumLeaves(c); }, 0); }
    var levels = depth(root);
    var levelH = H / levels;
    // colour per level: ink → lime → soft lime → ink300
    var levelColors = [P.ink, P.lime, P.limeSoft || "#e3edfd", P.ink200, P.ink100];
    function draw(node, x, w, level) {
      var color = node.color || levelColors[level] || P.ink100;
      svg.appendChild(el("rect", { x: x + 1, y: level * levelH + 1, width: Math.max(0, w - 2), height: levelH - 2, fill: color, stroke: P.white, "stroke-width": 1 }));
      var dark = (color === P.ink || color === P.inkDeep);
      if (w > 50) {
        svg.appendChild(el("text", { x: x + 8, y: level * levelH + 18, "font-size": 11, "font-weight": 700, fill: dark ? P.lime : P.ink }, node.label));
        var v = node.value !== undefined ? node.value : sumLeaves(node);
        if (w > 90) svg.appendChild(el("text", { x: x + 8, y: level * levelH + 32, "font-size": 10, fill: dark ? P.white : P.ink700 }, fmt(v, d)));
      }
      if (node.children && node.children.length) {
        var total = node.children.reduce(function (s, c) { return s + (c.value !== undefined ? c.value : sumLeaves(c)); }, 0);
        var cx = x;
        node.children.forEach(function (c) {
          var cw = ((c.value !== undefined ? c.value : sumLeaves(c)) / total) * w;
          draw(c, cx, cw, level + 1);
          cx += cw;
        });
      }
    }
    draw(root, 0, W, 0);
  };

  // ====== CORRELATION =================================================
  TYPES.scatter = function (d) {
    var W = 640, H = 280, L = 40, R = 20, T = 16, B = 30;
    var data = d.data; // {x, y, label?, highlight?}
    var xMin = Math.min.apply(null, data.map(function (r) { return r.x; }));
    var xMax = Math.max.apply(null, data.map(function (r) { return r.x; }));
    var yMin = Math.min.apply(null, data.map(function (r) { return r.y; }));
    var yMax = Math.max.apply(null, data.map(function (r) { return r.y; }));
    var xPad = (xMax - xMin) * 0.1, yPad = (yMax - yMin) * 0.1;
    var xLo = xMin - xPad, xHi = xMax + xPad, yLo = Math.max(0, yMin - yPad), yHi = yMax + yPad;
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, yLo, yHi, { format: d.yFormat });
    [0, 0.25, 0.5, 0.75, 1].forEach(function (t) {
      var x = L + t * (W - L - R);
      svg.appendChild(el("text", { class: "tick", x: x, y: H - B + 16, "text-anchor": "middle" }, fmt(xLo + t * (xHi - xLo), { format: d.xFormat })));
    });
    var sx = function (v) { return L + (v - xLo) / (xHi - xLo) * (W - L - R); };
    var sy = function (v) { return H - B - (v - yLo) / (yHi - yLo) * (H - B - T); };
    data.forEach(function (r) {
      svg.appendChild(el("circle", { cx: sx(r.x), cy: sy(r.y), r: 5, fill: r.highlight ? P.lime : P.ink, stroke: r.highlight ? P.ink : "none", "stroke-width": 1 }));
      if (r.label) svg.appendChild(el("text", { x: sx(r.x) + 8, y: sy(r.y) + 4, "font-size": 10, fill: P.ink600 }, r.label));
    });
    if (d.xLabel) svg.appendChild(el("text", { x: W / 2, y: H - 4, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink600 }, d.xLabel));
    if (d.yLabel) svg.appendChild(el("text", { x: 10, y: H / 2, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink600, transform: "rotate(-90 10 " + H / 2 + ")" }, d.yLabel));
  };

  TYPES.bubble = function (d) {
    var W = 640, H = 280, L = 40, R = 20, T = 16, B = 30;
    var data = d.data; // {x, y, r, label, color?}
    var xs = data.map(function (r) { return r.x; }), ys = data.map(function (r) { return r.y; }), rs = data.map(function (r) { return r.r; });
    var xLo = Math.min.apply(null, xs), xHi = Math.max.apply(null, xs);
    var yLo = Math.min.apply(null, ys), yHi = Math.max.apply(null, ys);
    var rMax = Math.max.apply(null, rs);
    var xPad = (xHi - xLo) * 0.15, yPad = (yHi - yLo) * 0.15;
    xLo -= xPad; xHi += xPad; yLo = Math.max(0, yLo - yPad); yHi += yPad;
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, yLo, yHi, { format: d.yFormat });
    var sx = function (v) { return L + (v - xLo) / (xHi - xLo) * (W - L - R); };
    var sy = function (v) { return H - B - (v - yLo) / (yHi - yLo) * (H - B - T); };
    data.forEach(function (r) {
      var rad = 6 + (r.r / rMax) * 26;
      svg.appendChild(el("circle", { cx: sx(r.x), cy: sy(r.y), r: rad, fill: r.color || P.lime, opacity: 0.7, stroke: P.ink, "stroke-width": 1 }));
      if (r.label) svg.appendChild(el("text", { x: sx(r.x), y: sy(r.y) + 4, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink }, r.label));
    });
    [0, 0.5, 1].forEach(function (t) { svg.appendChild(el("text", { class: "tick", x: L + t * (W - L - R), y: H - B + 16, "text-anchor": "middle" }, fmt(xLo + t * (xHi - xLo), { format: d.xFormat }))); });
  };

  TYPES.connectedScatter = function (d) {
    var W = 640, H = 280, L = 40, R = 20, T = 16, B = 30;
    var data = d.data;
    var xs = data.map(function (r) { return r.x; }), ys = data.map(function (r) { return r.y; });
    var xLo = Math.min.apply(null, xs), xHi = Math.max.apply(null, xs);
    var yLo = Math.min.apply(null, ys), yHi = Math.max.apply(null, ys);
    var pad = 0.1;
    xLo -= (xHi - xLo) * pad; xHi += (xHi - xLo) * pad;
    yLo -= (yHi - yLo) * pad; yHi += (yHi - yLo) * pad;
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, yLo, yHi, { format: d.yFormat });
    var sx = function (v) { return L + (v - xLo) / (xHi - xLo) * (W - L - R); };
    var sy = function (v) { return H - B - (v - yLo) / (yHi - yLo) * (H - B - T); };
    var path = data.map(function (r, i) { return (i ? "L" : "M") + sx(r.x) + "," + sy(r.y); }).join(" ");
    svg.appendChild(el("path", { d: path, fill: "none", stroke: P.lime, "stroke-width": 2 }));
    data.forEach(function (r) {
      svg.appendChild(el("circle", { cx: sx(r.x), cy: sy(r.y), r: 5, fill: P.lime, stroke: P.ink, "stroke-width": 1.5 }));
      if (r.label) svg.appendChild(el("text", { x: sx(r.x) + 8, y: sy(r.y) - 6, "font-size": 10, "font-weight": 700, fill: P.ink }, r.label));
    });
  };

  TYPES.quadrant = function (d) {
    var W = 640, H = 320, L = 30, R = 20, T = 30, B = 40;
    var data = d.data; // {x, y, label, highlight?}
    var xLabels = d.xLabels || ["Low", "High"];
    var yLabels = d.yLabels || ["Low", "High"];
    var quadLabels = d.quadrants || [];
    var svg = makeSvg(W, H);
    svg.appendChild(el("rect", { x: L, y: T, width: W - L - R, height: H - T - B, fill: P.ink050, stroke: P.ink200 }));
    var midX = (L + W - R) / 2, midY = (T + H - B) / 2;
    svg.appendChild(el("line", { x1: midX, y1: T, x2: midX, y2: H - B, stroke: P.ink300, "stroke-dasharray": "3 3" }));
    svg.appendChild(el("line", { x1: L, y1: midY, x2: W - R, y2: midY, stroke: P.ink300, "stroke-dasharray": "3 3" }));
    quadLabels.forEach(function (q, i) {
      var cx = i % 2 === 0 ? L + 12 : W - R - 12;
      var cy = i < 2 ? T + 18 : H - B - 8;
      var anchor = i % 2 === 0 ? "start" : "end";
      svg.appendChild(el("text", { x: cx, y: cy, "text-anchor": anchor, "font-size": 10, "font-weight": 700, fill: P.ink600, "letter-spacing": "0.08em" }, q.toUpperCase()));
    });
    var sx = function (v) { return L + v * (W - L - R); };
    var sy = function (v) { return H - B - v * (H - T - B); };
    data.forEach(function (r) {
      svg.appendChild(el("circle", { cx: sx(r.x), cy: sy(r.y), r: 7, fill: r.highlight ? P.lime : P.ink, stroke: r.highlight ? P.ink : "none", "stroke-width": 1 }));
      svg.appendChild(el("text", { x: sx(r.x) + 12, y: sy(r.y) + 4, "font-size": 11, "font-weight": 700, fill: P.ink }, r.label));
    });
    svg.appendChild(el("text", { x: L, y: H - 10, "font-size": 10, "font-weight": 700, fill: P.ink600 }, xLabels[0]));
    svg.appendChild(el("text", { x: W - R, y: H - 10, "text-anchor": "end", "font-size": 10, "font-weight": 700, fill: P.ink600 }, xLabels[1]));
    svg.appendChild(el("text", { x: 10, y: H - B, "font-size": 10, "font-weight": 700, fill: P.ink600 }, yLabels[0]));
    svg.appendChild(el("text", { x: 10, y: T + 8, "font-size": 10, "font-weight": 700, fill: P.ink600 }, yLabels[1]));
  };

  // ====== DISTRIBUTION ================================================
  TYPES.box = function (d) {
    var W = 640, H = 280, L = 40, R = 20, T = 16, B = 30;
    var data = d.data; // {label, min, q1, median, q3, max, outliers?}
    var all = data.reduce(function (a, r) { return a.concat([r.min, r.max].concat(r.outliers || [])); }, []);
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    var pad = (hi - lo) * 0.1;
    lo -= pad; hi += pad;
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, lo, hi, { format: d.format });
    var step = (W - L - R) / data.length;
    var bw = step * 0.5;
    var sy = function (v) { return H - B - (v - lo) / (hi - lo) * (H - B - T); };
    data.forEach(function (r, i) {
      var x = L + step * i + step / 2;
      svg.appendChild(el("line", { x1: x, y1: sy(r.min), x2: x, y2: sy(r.max), stroke: P.ink }));
      svg.appendChild(el("rect", { x: x - bw / 2, y: sy(r.q3), width: bw, height: sy(r.q1) - sy(r.q3), fill: P.lime, stroke: P.ink }));
      svg.appendChild(el("line", { x1: x - bw / 2, y1: sy(r.median), x2: x + bw / 2, y2: sy(r.median), stroke: P.ink, "stroke-width": 2 }));
      svg.appendChild(el("line", { x1: x - 8, y1: sy(r.min), x2: x + 8, y2: sy(r.min), stroke: P.ink }));
      svg.appendChild(el("line", { x1: x - 8, y1: sy(r.max), x2: x + 8, y2: sy(r.max), stroke: P.ink }));
      (r.outliers || []).forEach(function (o) { svg.appendChild(el("circle", { cx: x, cy: sy(o), r: 3, fill: P.white, stroke: P.ink })); });
      svg.appendChild(el("text", { class: "tick", x: x, y: H - B + 16, "text-anchor": "middle" }, r.label));
    });
  };

  TYPES.histogram = function (d) {
    var W = 640, H = 260, L = 36, R = 20, T = 14, B = 30;
    var bins = d.bins; // {label, value}
    var max = nice(Math.max.apply(null, bins.map(function (b) { return b.value; })) * 1.1);
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, 0, max);
    var step = (W - L - R) / bins.length;
    bins.forEach(function (b, i) {
      var x = L + step * i;
      var h = (b.value / max) * (H - B - T);
      svg.appendChild(el("rect", { x: x + 1, y: H - B - h, width: step - 2, height: h, fill: P.lime }));
      if (i % 2 === 0) svg.appendChild(el("text", { class: "tick", x: x + step / 2, y: H - B + 16, "text-anchor": "middle" }, b.label));
    });
  };

  TYPES.strip = function (d) {
    var W = 640, H = 240, L = 100, R = 30, T = 16;
    var groups = d.groups; // {label, points}
    var rowH = (H - T - 16) / groups.length;
    var all = groups.reduce(function (a, g) { return a.concat(g.points); }, []);
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    var pad = (hi - lo) * 0.05;
    lo -= pad; hi += pad;
    var svg = makeSvg(W, H);
    var sx = function (v) { return L + (v - lo) / (hi - lo) * (W - L - R); };
    groups.forEach(function (g, gi) {
      var y = T + gi * rowH + rowH / 2;
      svg.appendChild(el("line", { x1: L, y1: y, x2: W - R, y2: y, stroke: P.ink100 }));
      svg.appendChild(el("text", { class: "label", x: L - 10, y: y + 4, "text-anchor": "end" }, g.label));
      g.points.forEach(function (p) { svg.appendChild(el("circle", { cx: sx(p), cy: y + (Math.random() - 0.5) * 6, r: 4, fill: P.lime, opacity: 0.7, stroke: P.ink, "stroke-width": 0.6 })); });
    });
  };

  // ====== BRIDGES =====================================================
  TYPES.waterfall = function (d) {
    var W = 640, H = 300, L = 40, R = 20, T = 30, B = 40;
    var data = d.data; // {label, value, type: "start"|"add"|"sub"|"end"}
    var cum = 0;
    var heights = data.map(function (r) {
      if (r.type === "start") { cum = r.value; return { y0: 0, y1: r.value, value: r.value, kind: "start" }; }
      if (r.type === "end") { return { y0: 0, y1: r.value, value: r.value, kind: "end" }; }
      var prev = cum;
      cum += r.value;
      return { y0: r.value >= 0 ? prev : cum, y1: r.value >= 0 ? cum : prev, value: r.value, kind: r.type };
    });
    var max = Math.max.apply(null, heights.map(function (h) { return h.y1; }));
    max = nice(max * 1.15);
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, 0, max, { format: d.format });
    var step = (W - L - R) / data.length;
    var bw = step * 0.6;
    data.forEach(function (r, i) {
      var h = heights[i];
      var x = L + step * i + (step - bw) / 2;
      var sy = function (v) { return H - B - (v / max) * (H - B - T); };
      var fill = h.kind === "start" || h.kind === "end" ? P.ink : (r.value >= 0 ? P.lime : P.ink400);
      svg.appendChild(el("rect", { x: x, y: sy(h.y1), width: bw, height: Math.max(2, sy(h.y0) - sy(h.y1)), fill: fill }));
      svg.appendChild(el("text", { class: "tick", x: x + bw / 2, y: H - B + 16, "text-anchor": "middle" }, r.label));
      svg.appendChild(el("text", { class: "value", x: x + bw / 2, y: sy(h.y1) - 6, "text-anchor": "middle" }, (r.value > 0 && h.kind !== "start" && h.kind !== "end" ? "+" : "") + fmt(r.value, d)));
      // connector
      if (i < data.length - 1 && heights[i + 1].kind !== "end" && h.kind !== "end") {
        var nx = L + step * (i + 1) + (step - bw) / 2;
        svg.appendChild(el("line", { x1: x + bw, y1: sy(cum < r.value ? cum : (h.kind === "start" ? r.value : cum)), x2: nx, y2: sy(cum < r.value ? cum : (h.kind === "start" ? r.value : cum)), stroke: P.ink300, "stroke-dasharray": "2 2" }));
      }
    });
  };

  TYPES.footballField = function (d) {
    var W = 640, H = 280, L = 160, R = 80, T = 30, B = 30;
    var rows = d.rows; // {label, lo, hi}
    var ref = d.reference; // {label, value}?
    var all = rows.reduce(function (a, r) { return a.concat([r.lo, r.hi]); }, ref ? [ref.value] : []);
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    var pad = (hi - lo) * 0.1; lo -= pad; hi += pad;
    var rowH = (H - T - B) / rows.length;
    var svg = makeSvg(W, H);
    var sx = function (v) { return L + (v - lo) / (hi - lo) * (W - L - R); };
    [0, 0.25, 0.5, 0.75, 1].forEach(function (t) {
      var x = L + t * (W - L - R);
      svg.appendChild(el("line", { class: "gridline", x1: x, y1: T, x2: x, y2: H - B }));
      svg.appendChild(el("text", { class: "tick", x: x, y: H - B + 16, "text-anchor": "middle" }, fmt(lo + t * (hi - lo), { format: d.format })));
    });
    rows.forEach(function (r, i) {
      var y = T + i * rowH + rowH / 2;
      svg.appendChild(el("rect", { x: sx(r.lo), y: y - 12, width: sx(r.hi) - sx(r.lo), height: 24, fill: P.lime }));
      svg.appendChild(el("text", { class: "label", x: L - 10, y: y + 4, "text-anchor": "end" }, r.label));
      svg.appendChild(el("text", { x: sx(r.lo) - 6, y: y + 4, "text-anchor": "end", "font-size": 10, "font-weight": 700, fill: P.ink }, fmt(r.lo, d)));
      svg.appendChild(el("text", { x: sx(r.hi) + 6, y: y + 4, "font-size": 10, "font-weight": 700, fill: P.ink }, fmt(r.hi, d)));
    });
    if (ref) {
      svg.appendChild(el("line", { x1: sx(ref.value), y1: T - 8, x2: sx(ref.value), y2: H - B + 4, stroke: P.ink, "stroke-width": 2 }));
      svg.appendChild(el("text", { x: sx(ref.value), y: T - 12, "text-anchor": "middle", "font-size": 11, "font-weight": 700, fill: P.ink }, ref.label + " · " + fmt(ref.value, d)));
    }
  };

  TYPES.pareto = function (d) {
    var W = 640, H = 290, L = 40, R = 50, T = 16, B = 36;
    var data = d.data; // {label, value}
    var total = data.reduce(function (s, x) { return s + x.value; }, 0);
    var maxB = nice(Math.max.apply(null, data.map(function (r) { return r.value; })) * 1.1);
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, 0, maxB);
    var step = (W - L - R) / data.length;
    var bw = step * 0.7;
    var cum = 0;
    var pts = [];
    data.forEach(function (r, i) {
      var x = L + step * i + (step - bw) / 2;
      var h = (r.value / maxB) * (H - B - T);
      svg.appendChild(el("rect", { x: x, y: H - B - h, width: bw, height: h, fill: P.lime }));
      svg.appendChild(el("text", { class: "tick", x: x + bw / 2, y: H - B + 16, "text-anchor": "middle" }, r.label));
      cum += r.value;
      pts.push([L + step * i + step / 2, H - B - (cum / total) * (H - B - T)]);
    });
    svg.appendChild(el("path", { d: "M" + pts.map(function (p) { return p.join(","); }).join(" L "), fill: "none", stroke: P.ink, "stroke-width": 2 }));
    pts.forEach(function (p) { svg.appendChild(el("circle", { cx: p[0], cy: p[1], r: 3, fill: P.ink })); });
  };

  TYPES.variance = function (d) {
    var W = 640, H = 280, L = 80, R = 70, T = 16, B = 30;
    var data = d.data; // {label, plan, actual}
    var maxV = Math.max.apply(null, data.reduce(function (a, r) { return a.concat([r.plan, r.actual]); }, []));
    maxV = nice(maxV * 1.1);
    var rowH = (H - T - B) / data.length;
    var svg = makeSvg(W, H);
    var sx = function (v) { return L + (v / maxV) * (W - L - R); };
    data.forEach(function (r, i) {
      var y = T + i * rowH + rowH / 2;
      svg.appendChild(el("line", { x1: L, y1: y, x2: sx(r.plan), y2: y, stroke: P.ink400, "stroke-width": 2 }));
      svg.appendChild(el("circle", { cx: sx(r.plan), cy: y, r: 5, fill: P.white, stroke: P.ink, "stroke-width": 1.5 }));
      var diff = r.actual - r.plan;
      svg.appendChild(el("line", { x1: sx(r.plan), y1: y, x2: sx(r.actual), y2: y, stroke: diff >= 0 ? P.lime : P.danger, "stroke-width": 5 }));
      svg.appendChild(el("circle", { cx: sx(r.actual), cy: y, r: 6, fill: diff >= 0 ? P.lime : P.danger, stroke: P.ink, "stroke-width": 1 }));
      svg.appendChild(el("text", { class: "label", x: L - 10, y: y + 4, "text-anchor": "end" }, r.label));
      svg.appendChild(el("text", { x: sx(Math.max(r.plan, r.actual)) + 8, y: y + 4, "font-size": 11, "font-weight": 700, fill: diff >= 0 ? P.success : P.danger }, (diff >= 0 ? "+" : "") + fmt(diff, d)));
    });
    legend([{ label: "Plan", color: P.ink400 }, { label: "Actual", color: P.lime }]);
  };

  TYPES.tornado = function (d) {
    var W = 640, H = 280, L = 130, R = 60, T = 16, B = 16;
    var data = d.data; // {label, lo, hi}, ordered widest→narrowest
    var maxAbs = Math.max.apply(null, data.reduce(function (a, r) { return a.concat([Math.abs(r.lo), Math.abs(r.hi)]); }, []));
    var rowH = (H - T - B) / data.length;
    var midX = (L + W - R) / 2;
    var halfW = (W - R - L) / 2;
    var svg = makeSvg(W, H);
    svg.appendChild(el("line", { x1: midX, y1: T, x2: midX, y2: H - B, stroke: P.ink, "stroke-width": 1 }));
    var sx = function (v) { return midX + (v / maxAbs) * halfW; };
    data.forEach(function (r, i) {
      var y = T + i * rowH + 4;
      svg.appendChild(el("rect", { x: sx(r.lo), y: y, width: midX - sx(r.lo), height: rowH - 10, fill: P.ink }));
      svg.appendChild(el("rect", { x: midX, y: y, width: sx(r.hi) - midX, height: rowH - 10, fill: P.lime }));
      svg.appendChild(el("text", { class: "label", x: L - 10, y: y + (rowH - 10) / 2 + 4, "text-anchor": "end" }, r.label));
      svg.appendChild(el("text", { x: sx(r.lo) - 6, y: y + (rowH - 10) / 2 + 4, "text-anchor": "end", "font-size": 10, "font-weight": 700, fill: P.ink }, fmt(r.lo, d)));
      svg.appendChild(el("text", { x: sx(r.hi) + 6, y: y + (rowH - 10) / 2 + 4, "font-size": 10, "font-weight": 700, fill: P.ink }, "+" + fmt(r.hi, d)));
    });
  };

  // ====== PROCESS =====================================================
  TYPES.funnel = function (d) {
    var W = 640, H = 280;
    var data = d.data; // ordered widest→narrowest
    var rowH = H / data.length;
    var svg = makeSvg(W, H);
    var maxV = data[0].value;
    data.forEach(function (r, i) {
      var widthFrac = r.value / maxV;
      var nextFrac = i < data.length - 1 ? data[i + 1].value / maxV : widthFrac * 0.7;
      var w1 = widthFrac * (W - 100), w2 = nextFrac * (W - 100);
      var x1 = (W - w1) / 2, x2 = (W - w2) / 2;
      var y = i * rowH;
      svg.appendChild(el("path", { d: "M" + x1 + "," + y + " L" + (x1 + w1) + "," + y + " L" + (x2 + w2) + "," + (y + rowH - 4) + " L" + x2 + "," + (y + rowH - 4) + " Z", fill: r.color || (i === 0 ? P.ink : P.lime), opacity: 0.9 - i * 0.05 }));
      svg.appendChild(el("text", { x: W / 2, y: y + rowH / 2 + 4, "text-anchor": "middle", "font-size": 13, "font-weight": 700, fill: i === 0 ? P.lime : P.ink }, r.label + " · " + fmt(r.value, d)));
    });
  };

  TYPES.gantt = function (d) {
    var W = 640, H = 280, L = 130, R = 30, T = 16, B = 30;
    var rows = d.rows; // {label, start, end, color?}
    var min = Math.min.apply(null, rows.map(function (r) { return r.start; }));
    var max = Math.max.apply(null, rows.map(function (r) { return r.end; }));
    var rowH = (H - T - B) / rows.length;
    var svg = makeSvg(W, H);
    var sx = function (v) { return L + (v - min) / (max - min) * (W - L - R); };
    var labels = d.timeLabels || [];
    var nT = labels.length || 5;
    for (var i = 0; i <= nT; i++) {
      var t = i / nT;
      var x = L + t * (W - L - R);
      svg.appendChild(el("line", { class: "gridline", x1: x, y1: T, x2: x, y2: H - B }));
      svg.appendChild(el("text", { class: "tick", x: x, y: H - B + 16, "text-anchor": "middle" }, labels[i] || (min + t * (max - min)).toFixed(0)));
    }
    rows.forEach(function (r, i) {
      var y = T + i * rowH + 4;
      svg.appendChild(el("rect", { x: sx(r.start), y: y, width: sx(r.end) - sx(r.start), height: rowH - 8, fill: r.color || P.lime, stroke: P.ink, "stroke-width": 1 }));
      svg.appendChild(el("text", { class: "label", x: L - 10, y: y + (rowH - 8) / 2 + 4, "text-anchor": "end" }, r.label));
    });
  };

  TYPES.orgTree = function (d) {
    var W = 640, H = 280;
    var root = d.root; // {label, children}
    var svg = makeSvg(W, H);
    function depth(n) { if (!n.children || !n.children.length) return 1; return 1 + Math.max.apply(null, n.children.map(depth)); }
    function leaves(n) { if (!n.children || !n.children.length) return 1; return n.children.reduce(function (s, c) { return s + leaves(c); }, 0); }
    var dep = depth(root);
    var lvH = H / dep;
    function draw(n, x, w, level) {
      var cx = x + w / 2, cy = level * lvH + 20;
      svg.appendChild(el("rect", { x: cx - 60, y: cy, width: 120, height: 32, fill: level === 0 ? P.ink : P.white, stroke: P.ink, "stroke-width": 1 }));
      svg.appendChild(el("text", { x: cx, y: cy + 20, "text-anchor": "middle", "font-size": 11, "font-weight": 700, fill: level === 0 ? P.lime : P.ink }, n.label));
      if (n.children && n.children.length) {
        var totalL = leaves(n);
        var cx0 = x;
        n.children.forEach(function (c) {
          var cw = (leaves(c) / totalL) * w;
          var ccx = cx0 + cw / 2, ccy = (level + 1) * lvH + 20;
          svg.appendChild(el("path", { d: "M" + cx + "," + (cy + 32) + " L" + cx + "," + ((cy + 32 + ccy) / 2) + " L" + ccx + "," + ((cy + 32 + ccy) / 2) + " L" + ccx + "," + ccy, fill: "none", stroke: P.ink300, "stroke-width": 1 }));
          draw(c, cx0, cw, level + 1);
          cx0 += cw;
        });
      }
    }
    draw(root, 0, W, 0);
  };

  TYPES.bump = function (d) {
    var W = 640, H = 280, L = 100, R = 100, T = 20, B = 20;
    var labels = d.labels;
    var series = d.series; // {name, ranks}
    var step = (W - L - R) / (labels.length - 1);
    var rowH = (H - T - B) / series.length;
    var sx = function (i) { return L + i * step; };
    var sy = function (rank) { return T + (rank - 1) * rowH + rowH / 2; };
    var svg = makeSvg(W, H);
    labels.forEach(function (lb, i) { svg.appendChild(el("text", { x: sx(i), y: T - 6, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink600 }, lb)); });
    series.forEach(function (s, si) {
      var color = s.color || (si === 0 ? P.lime : SERIES[si]);
      var path = s.ranks.map(function (r, i) { return (i ? "L" : "M") + sx(i) + "," + sy(r); }).join(" ");
      svg.appendChild(el("path", { d: path, fill: "none", stroke: color, "stroke-width": 3 }));
      s.ranks.forEach(function (r, i) {
        svg.appendChild(el("circle", { cx: sx(i), cy: sy(r), r: 8, fill: color, stroke: P.ink, "stroke-width": 1 }));
        svg.appendChild(el("text", { x: sx(i), y: sy(r) + 3, "text-anchor": "middle", "font-size": 9, "font-weight": 700, fill: P.ink }, r));
      });
      svg.appendChild(el("text", { x: L - 10, y: sy(s.ranks[0]) + 4, "text-anchor": "end", "font-size": 10, "font-weight": 700, fill: P.ink }, s.name));
      svg.appendChild(el("text", { x: W - R + 10, y: sy(s.ranks[s.ranks.length - 1]) + 4, "font-size": 10, "font-weight": 700, fill: P.ink }, s.name));
    });
  };

  TYPES.cohort = function (d) {
    var W = 640, H = 260, L = 90, T = 40;
    var rows = d.rows; // {label, values:[]}
    var maxCols = Math.max.apply(null, rows.map(function (r) { return r.values.length; }));
    var cellW = (W - L - 20) / maxCols;
    var cellH = (H - T - 20) / rows.length;
    var svg = makeSvg(W, H);
    if (d.colHeaders) d.colHeaders.forEach(function (h, i) {
      svg.appendChild(el("text", { x: L + i * cellW + cellW / 2, y: T - 10, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink600 }, h));
    });
    rows.forEach(function (r, i) {
      svg.appendChild(el("text", { x: L - 10, y: T + i * cellH + cellH / 2 + 4, "text-anchor": "end", "font-size": 11, "font-weight": 700, fill: P.ink }, r.label));
      r.values.forEach(function (v, j) {
        var t = v / 100;
        var bg = "rgb(" + Math.round(255 - t * (255 - 205)) + "," + Math.round(255 - t * (255 - 240)) + "," + Math.round(255 - t * (255 - 81)) + ")";
        svg.appendChild(el("rect", { x: L + j * cellW + 1, y: T + i * cellH + 1, width: cellW - 2, height: cellH - 2, fill: bg, stroke: P.ink200 }));
        svg.appendChild(el("text", { x: L + j * cellW + cellW / 2, y: T + i * cellH + cellH / 2 + 4, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: t > 0.6 ? P.ink : P.ink600 }, v + "%"));
      });
    });
  };

  // ====== FLOW ========================================================
  TYPES.sankey = function (d) {
    var W = 640, H = 300, L = 80, R = 80, T = 20, B = 20;
    var nodes = d.nodes; // {id, label, side: "left"|"right", value}
    var links = d.links; // {from, to, value, color?}
    var lefts = nodes.filter(function (n) { return n.side === "left"; });
    var rights = nodes.filter(function (n) { return n.side === "right"; });
    var leftTotal = lefts.reduce(function (s, n) { return s + n.value; }, 0);
    var rightTotal = rights.reduce(function (s, n) { return s + n.value; }, 0);
    var avail = H - T - B;
    var pad = 6;
    var svg = makeSvg(W, H);
    function layout(side, total) {
      var y = T;
      side.forEach(function (n) {
        n.h = (n.value / total) * (avail - pad * (side.length - 1));
        n.y0 = y;
        n.y1 = y + n.h;
        n.usedL = 0; n.usedR = 0;
        y += n.h + pad;
      });
    }
    layout(lefts, leftTotal);
    layout(rights, rightTotal);
    // draw links
    links.forEach(function (lk) {
      var a = nodes.find(function (n) { return n.id === lk.from; });
      var b = nodes.find(function (n) { return n.id === lk.to; });
      var ah = (lk.value / a.value) * a.h;
      var bh = (lk.value / b.value) * b.h;
      var ay0 = a.y0 + a.usedR; a.usedR += ah;
      var by0 = b.y0 + b.usedL; b.usedL += bh;
      var x0 = L, x1 = W - R;
      var d1 = "M" + x0 + "," + ay0 + " C" + (x0 + (x1 - x0) / 2) + "," + ay0 + " " + (x0 + (x1 - x0) / 2) + "," + by0 + " " + x1 + "," + by0;
      var d2 = " L" + x1 + "," + (by0 + bh) + " C" + (x0 + (x1 - x0) / 2) + "," + (by0 + bh) + " " + (x0 + (x1 - x0) / 2) + "," + (ay0 + ah) + " " + x0 + "," + (ay0 + ah) + " Z";
      svg.appendChild(el("path", { d: d1 + d2, fill: lk.color || P.lime, opacity: 0.55 }));
    });
    nodes.forEach(function (n) {
      var x = n.side === "left" ? L - 12 : W - R;
      svg.appendChild(el("rect", { x: x, y: n.y0, width: 12, height: n.h, fill: P.ink }));
      svg.appendChild(el("text", { x: n.side === "left" ? x - 6 : x + 18, y: n.y0 + n.h / 2 + 4, "text-anchor": n.side === "left" ? "end" : "start", "font-size": 11, "font-weight": 700, fill: P.ink }, n.label));
    });
  };

  TYPES.chord = function (d) {
    var W = 640, H = 300, cx = 200, cy = 150, R = 110;
    var groups = d.groups; // {label, value, color?}
    var matrix = d.matrix; // [[..]]
    var total = groups.reduce(function (s, g) { return s + g.value; }, 0);
    var svg = makeSvg(W, H);
    var pad = 0.04;
    var angles = [];
    var a = -Math.PI / 2;
    groups.forEach(function (g) {
      var span = (g.value / total) * (Math.PI * 2 - pad * groups.length);
      angles.push({ a0: a, a1: a + span });
      a += span + pad;
    });
    groups.forEach(function (g, i) {
      var ang = angles[i];
      var x0 = cx + R * Math.cos(ang.a0), y0 = cy + R * Math.sin(ang.a0);
      var x1 = cx + R * Math.cos(ang.a1), y1 = cy + R * Math.sin(ang.a1);
      svg.appendChild(el("path", { d: "M" + x0 + "," + y0 + " A" + R + "," + R + " 0 0 1 " + x1 + "," + y1, fill: "none", stroke: g.color || (i === 0 ? P.lime : SERIES[i]), "stroke-width": 14 }));
      var mid = (ang.a0 + ang.a1) / 2;
      svg.appendChild(el("text", { x: cx + (R + 24) * Math.cos(mid), y: cy + (R + 24) * Math.sin(mid) + 4, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink }, g.label));
    });
    // chords
    for (var i = 0; i < groups.length; i++) {
      for (var j = i + 1; j < groups.length; j++) {
        var v = matrix[i][j] || 0;
        if (v === 0) continue;
        var ai = (angles[i].a0 + angles[i].a1) / 2;
        var aj = (angles[j].a0 + angles[j].a1) / 2;
        var x0 = cx + (R - 8) * Math.cos(ai), y0 = cy + (R - 8) * Math.sin(ai);
        var x1 = cx + (R - 8) * Math.cos(aj), y1 = cy + (R - 8) * Math.sin(aj);
        svg.appendChild(el("path", { d: "M" + x0 + "," + y0 + " Q" + cx + "," + cy + " " + x1 + "," + y1, fill: "none", stroke: P.ink, opacity: clamp(v / 100, 0.15, 0.7), "stroke-width": 1 + v / 20 }));
      }
    }
    // legend
    groups.forEach(function (g, i) {
      svg.appendChild(el("rect", { x: 400, y: 30 + i * 22, width: 12, height: 12, fill: g.color || (i === 0 ? P.lime : SERIES[i]) }));
      svg.appendChild(el("text", { x: 420, y: 40 + i * 22, "font-size": 11, fill: P.ink }, g.label));
    });
  };

  // ====== MULTIVARIATE ================================================
  TYPES.radar = function (d) {
    var W = 640, H = 280, cx = 220, cy = 140, R = 110;
    var axes = d.axes; // strings
    var series = d.series; // {name, values, color?}
    var max = d.max || Math.max.apply(null, series.reduce(function (a, s) { return a.concat(s.values); }, []));
    var n = axes.length;
    var svg = makeSvg(W, H);
    [0.25, 0.5, 0.75, 1].forEach(function (t) {
      var pts = [];
      for (var i = 0; i < n; i++) {
        var a = -Math.PI / 2 + (i / n) * Math.PI * 2;
        pts.push((cx + Math.cos(a) * R * t) + "," + (cy + Math.sin(a) * R * t));
      }
      svg.appendChild(el("polygon", { points: pts.join(" "), fill: "none", stroke: P.ink200 }));
    });
    for (var i = 0; i < n; i++) {
      var a = -Math.PI / 2 + (i / n) * Math.PI * 2;
      svg.appendChild(el("line", { x1: cx, y1: cy, x2: cx + Math.cos(a) * R, y2: cy + Math.sin(a) * R, stroke: P.ink200 }));
      svg.appendChild(el("text", { x: cx + Math.cos(a) * (R + 16), y: cy + Math.sin(a) * (R + 16) + 4, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink }, axes[i]));
    }
    series.forEach(function (s, si) {
      var pts = [];
      for (var i = 0; i < n; i++) {
        var a = -Math.PI / 2 + (i / n) * Math.PI * 2;
        var r = (s.values[i] / max) * R;
        pts.push((cx + Math.cos(a) * r) + "," + (cy + Math.sin(a) * r));
      }
      svg.appendChild(el("polygon", { points: pts.join(" "), fill: s.color || (si === 0 ? P.lime : SERIES[si]), "fill-opacity": 0.35, stroke: s.color || (si === 0 ? P.lime : SERIES[si]), "stroke-width": 2 }));
    });
    legend(series.map(function (s, i) { return { label: s.name, color: s.color || (i === 0 ? P.lime : SERIES[i]) }; }));
  };

  TYPES.heatmap = function (d) {
    var W = 640, H = 240, L = 80, T = 40;
    var rows = d.rows, cols = d.cols, values = d.values;
    var max = Math.max.apply(null, values.flat ? values.flat() : [].concat.apply([], values));
    var min = Math.min.apply(null, values.flat ? values.flat() : [].concat.apply([], values));
    var cellW = (W - L - 20) / cols.length;
    var cellH = (H - T - 30) / rows.length;
    var svg = makeSvg(W, H);
    cols.forEach(function (c, j) { svg.appendChild(el("text", { x: L + j * cellW + cellW / 2, y: T - 10, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink600 }, c)); });
    rows.forEach(function (r, i) {
      svg.appendChild(el("text", { x: L - 10, y: T + i * cellH + cellH / 2 + 4, "text-anchor": "end", "font-size": 11, "font-weight": 700, fill: P.ink }, r));
      values[i].forEach(function (v, j) {
        var t = (v - min) / (max - min);
        var bg = "rgb(" + Math.round(255 - t * (255 - 205)) + "," + Math.round(255 - t * (255 - 240)) + "," + Math.round(255 - t * (255 - 81)) + ")";
        svg.appendChild(el("rect", { x: L + j * cellW + 1, y: T + i * cellH + 1, width: cellW - 2, height: cellH - 2, fill: bg }));
        svg.appendChild(el("text", { x: L + j * cellW + cellW / 2, y: T + i * cellH + cellH / 2 + 4, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: t > 0.55 ? P.ink : P.ink600 }, v));
      });
    });
  };

  TYPES.calendar = function (d) {
    var W = 640, H = 200, L = 30, T = 30;
    var values = d.values; // 2D [weeks][7], 0 if no data
    var weeks = values.length;
    var cw = Math.min(14, (W - L - 20) / weeks);
    var ch = 18;
    var max = Math.max.apply(null, values.reduce(function (a, w) { return a.concat(w); }, []));
    var svg = makeSvg(W, H);
    var days = ["M", "T", "W", "T", "F", "S", "S"];
    days.forEach(function (lb, i) { svg.appendChild(el("text", { x: L - 8, y: T + i * ch + 13, "text-anchor": "end", "font-size": 9, fill: P.ink600 }, lb)); });
    for (var w = 0; w < weeks; w++) {
      for (var dy = 0; dy < 7; dy++) {
        var v = values[w][dy] || 0;
        var t = max ? v / max : 0;
        var bg = v === 0 ? P.ink100 : "rgb(" + Math.round(255 - t * (255 - 205)) + "," + Math.round(255 - t * (255 - 240)) + "," + Math.round(255 - t * (255 - 81)) + ")";
        svg.appendChild(el("rect", { x: L + w * (cw + 1), y: T + dy * ch, width: cw, height: ch - 2, fill: bg, stroke: P.white }));
      }
    }
    if (d.monthLabels) d.monthLabels.forEach(function (m) { svg.appendChild(el("text", { x: L + m.week * (cw + 1), y: T - 6, "font-size": 9, "font-weight": 700, fill: P.ink600 }, m.label)); });
  };

  TYPES.radialBar = function (d) {
    var W = 640, H = 280, cx = 200, cy = 140;
    var data = d.data; // {label, value, max}
    var svg = makeSvg(W, H);
    data.forEach(function (r, i) {
      var rad = 110 - i * 18;
      var ir = rad - 12;
      var midR = (rad + ir) / 2;
      svg.appendChild(el("circle", { cx: cx, cy: cy, r: midR, fill: "none", stroke: P.ink100, "stroke-width": rad - ir }));
      var p = r.value / (r.max || 100);
      var a = p * Math.PI * 2;
      var sx = cx, sy = cy - midR;
      var ex = cx + Math.sin(a) * midR;
      var ey = cy - Math.cos(a) * midR;
      var large = a > Math.PI ? 1 : 0;
      svg.appendChild(el("path", { d: "M" + sx + "," + sy + " A" + midR + "," + midR + " 0 " + large + " 1 " + ex + "," + ey, fill: "none", stroke: r.color || (i === 0 ? P.lime : SERIES[i]), "stroke-width": rad - ir, "stroke-linecap": "round" }));
      svg.appendChild(el("text", { x: 350, y: 30 + i * 26, "font-size": 11, "font-weight": 700, fill: P.ink }, r.label));
      svg.appendChild(el("text", { x: 350, y: 44 + i * 26, "font-size": 11, fill: P.ink600 }, fmt(r.value, d) + " · " + Math.round(p * 100) + "%"));
    });
  };

  TYPES.hexbin = function (d) {
    // Hex bin scatter with proper x/y axes.
    var W = 640, H = 300, L = 50, R = 30, T = 20, B = 40;
    var rows = d.rows, cols = d.cols;
    var values = d.values;
    var max = Math.max.apply(null, values.reduce(function (a, b) { return a.concat(b); }, []));
    var xRange = d.xRange || [0, cols], yRange = d.yRange || [0, rows];
    var svg = makeSvg(W, H);
    var plotW = W - L - R, plotH = H - T - B;
    var size = Math.min(plotW / (cols * Math.sqrt(3)), plotH / (rows * 1.5)) * 0.95;
    var hexW = Math.sqrt(3) * size;
    function hex(cx, cy) {
      var pts = [];
      for (var i = 0; i < 6; i++) {
        var a = -Math.PI / 2 + (i / 6) * Math.PI * 2;
        pts.push((cx + Math.cos(a) * size) + "," + (cy + Math.sin(a) * size));
      }
      return pts.join(" ");
    }
    function ramp(t) {
      var lerp = function (a, b, k) { return Math.round(a + (b - a) * k); };
      return "rgb(" + lerp(241, 205, t) + "," + lerp(241, 240, t) + "," + lerp(241, 81, t) + ")";
    }
    // axes
    svg.appendChild(el("line", { class: "axis", x1: L, y1: H - B, x2: W - R, y2: H - B }));
    svg.appendChild(el("line", { class: "axis", x1: L, y1: T, x2: L, y2: H - B }));
    [0, 0.25, 0.5, 0.75, 1].forEach(function (t) {
      var x = L + t * plotW, y = (H - B) - t * plotH;
      svg.appendChild(el("text", { class: "tick", x: x, y: H - B + 16, "text-anchor": "middle" }, fmt(xRange[0] + t * (xRange[1] - xRange[0]), { format: d.xFormat })));
      svg.appendChild(el("text", { class: "tick", x: L - 6, y: y + 3, "text-anchor": "end" }, fmt(yRange[0] + t * (yRange[1] - yRange[0]), { format: d.yFormat })));
    });
    if (d.xLabel) svg.appendChild(el("text", { x: L + plotW / 2, y: H - 4, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink600, "letter-spacing": "0.08em" }, d.xLabel.toUpperCase()));
    if (d.yLabel) svg.appendChild(el("text", { x: 14, y: T + plotH / 2, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink600, "letter-spacing": "0.08em", transform: "rotate(-90 14 " + (T + plotH / 2) + ")" }, d.yLabel.toUpperCase()));
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        var cx = L + c * hexW + (r % 2 ? hexW / 2 : 0) + size;
        var cy = (H - B) - (size + r * (size * 1.5));
        var v = values[r][c];
        var t = max ? v / max : 0;
        if (v === 0) {
          svg.appendChild(el("polygon", { points: hex(cx, cy), fill: "none", stroke: P.ink100 }));
        } else {
          svg.appendChild(el("polygon", { points: hex(cx, cy), fill: ramp(t), stroke: P.white, "stroke-width": 1 }));
          if (t > 0.4 && size > 14) svg.appendChild(el("text", { x: cx, y: cy + 3, "text-anchor": "middle", "font-size": 9, "font-weight": 700, fill: P.ink }, v));
        }
      }
    }
  };

  // ====== GEOGRAPHIC ==================================================
  TYPES.choropleth = function (d) {
    // Schematic Spain map: regions as paths (or fall back to grid). Each region
    // gets a fill from the lime ramp. Includes a small horizontal legend.
    var W = 640, H = 320, L = 30, T = 20;
    var regions = d.regions;
    var max = Math.max.apply(null, regions.map(function (r) { return r.value; }));
    var min = Math.min.apply(null, regions.map(function (r) { return r.value; }));
    var svg = makeSvg(W, H);
    function ramp(t) {
      // Lime ramp: charcoal -> lime -> soft cream. Use lime-deep at high values.
      // 0 = #f2f2f2 (ink100), 1 = #166dfc (lime). Mid blends through #e3edfd.
      var lerp = function (a, b, k) { return Math.round(a + (b - a) * k); };
      var r = lerp(241, 205, t), g = lerp(241, 240, t), b = lerp(241, 81, t);
      return "rgb(" + r + "," + g + "," + b + ")";
    }
    if (d.shapes) {
      // shapes: [{ id, label, value, path }] — path in 0..640 / 0..280 coords
      d.shapes.forEach(function (s) {
        var t = (s.value - min) / (max - min || 1);
        svg.appendChild(el("path", { d: s.path, fill: ramp(t), stroke: P.ink, "stroke-width": 1 }));
      });
      d.shapes.forEach(function (s) {
        if (s.cx === undefined) return;
        svg.appendChild(el("text", { x: s.cx, y: s.cy, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink }, s.label));
        if (s.value !== undefined) svg.appendChild(el("text", { x: s.cx, y: s.cy + 12, "text-anchor": "middle", "font-size": 9, fill: P.ink700 }, fmt(s.value, d)));
      });
    } else {
      // grid fallback
      var cw = 70, ch = 56;
      regions.forEach(function (r) {
        var t = (r.value - min) / (max - min || 1);
        svg.appendChild(el("rect", { x: L + r.gx * cw, y: T + 30 + r.gy * ch, width: cw - 3, height: ch - 3, fill: ramp(t), stroke: P.ink, "stroke-width": 0.8 }));
        svg.appendChild(el("text", { x: L + r.gx * cw + (cw - 3) / 2, y: T + 30 + r.gy * ch + ch / 2 - 2, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink }, r.label));
        svg.appendChild(el("text", { x: L + r.gx * cw + (cw - 3) / 2, y: T + 30 + r.gy * ch + ch / 2 + 12, "text-anchor": "middle", "font-size": 9, fill: P.ink700 }, fmt(r.value, d)));
      });
    }
    // legend
    var lx = W - 200, ly = H - 30;
    for (var i = 0; i < 20; i++) {
      svg.appendChild(el("rect", { x: lx + i * 8, y: ly, width: 8, height: 10, fill: ramp(i / 19) }));
    }
    svg.appendChild(el("text", { x: lx, y: ly - 4, "font-size": 9, fill: P.ink600 }, fmt(min, d) + "  " + (d.legendLabel || "")));
    svg.appendChild(el("text", { x: lx + 160, y: ly - 4, "text-anchor": "end", "font-size": 9, fill: P.ink600 }, fmt(max, d)));
  };

  TYPES.spikeMap = function (d) {
    var W = 640, H = 280, L = 30, T = 20;
    var spikes = d.spikes; // {label, x, y, value}
    var max = Math.max.apply(null, spikes.map(function (s) { return s.value; }));
    var svg = makeSvg(W, H);
    // backdrop
    svg.appendChild(el("rect", { x: L, y: T, width: W - L * 2, height: H - T - 20, fill: P.ink050, stroke: P.ink200 }));
    spikes.forEach(function (s) {
      var x = L + s.x * (W - L * 2);
      var y = T + (H - T - 20) - s.y * (H - T - 20);
      var h = (s.value / max) * 100 + 10;
      svg.appendChild(el("path", { d: "M" + (x - 4) + "," + y + " L" + x + "," + (y - h) + " L" + (x + 4) + "," + y + " Z", fill: P.lime, stroke: P.ink, "stroke-width": 1, opacity: 0.85 }));
      svg.appendChild(el("circle", { cx: x, cy: y, r: 2, fill: P.ink }));
      svg.appendChild(el("text", { x: x, y: y - h - 4, "text-anchor": "middle", "font-size": 9, "font-weight": 700, fill: P.ink }, s.label));
    });
  };

  TYPES.rangeBand = function (d) {
    var ctx = lineCommon({ labels: d.labels, series: [{ values: d.values.map(function (v) { return v.hi; }) }], format: d.format });
    var s = d.values; // {lo, hi, value}
    var pts = s.map(function (v, i) { return [ctx.sx(i), ctx.sy(v.value)]; });
    var top = s.map(function (v, i) { return ctx.sx(i) + "," + ctx.sy(v.hi); });
    var bot = s.map(function (v, i) { return ctx.sx(i) + "," + ctx.sy(v.lo); });
    ctx.svg.appendChild(el("path", { d: "M" + top.join(" L ") + " L " + bot.slice().reverse().join(" L ") + " Z", fill: P.lime, opacity: 0.4 }));
    ctx.svg.appendChild(el("path", { d: "M" + pts.map(function (p) { return p.join(","); }).join(" L "), fill: "none", stroke: P.ink, "stroke-width": 2 }));
    pts.forEach(function (p) { ctx.svg.appendChild(el("circle", { cx: p[0], cy: p[1], r: 3, fill: P.lime, stroke: P.ink })); });
  };

  // ====== NUMBERS =====================================================
  TYPES.kpiTile = function (d) {
    var W = 640, H = 200;
    var svg = makeSvg(W, H);
    var dark = d.dark !== false;
    svg.appendChild(el("rect", { x: 0, y: 0, width: W, height: H, fill: dark ? P.inkDeep : P.white, stroke: dark ? "none" : P.ink200 }));
    svg.appendChild(el("text", { x: 40, y: 50, "font-family": "Arial", "font-size": 11, "font-weight": 700, fill: dark ? P.lime : P.ink600, "letter-spacing": 1.6 }, (d.eyebrowText || d.eyebrow || "").toUpperCase()));
    svg.appendChild(el("text", { x: 40, y: 135, "font-family": "Carnas, Arial", "font-size": 100, "font-weight": 700, fill: dark ? P.white : P.ink, "letter-spacing": -3 }, d.value));
    if (d.suffix) svg.appendChild(el("text", { x: 40 + (String(d.value).length * 56), y: 135, "font-family": "Carnas, Arial", "font-size": 100, "font-weight": 700, fill: P.lime, "letter-spacing": -3 }, d.suffix));
    if (d.note) svg.appendChild(el("text", { x: 40, y: 170, "font-family": "Arial", "font-size": 13, fill: dark ? P.ink300 : P.ink600 }, d.note));
  };

  TYPES.kpiRow = function (d) {
    var items = d.items;
    var W = 640, H = 180;
    var svg = makeSvg(W, H);
    svg.appendChild(el("rect", { x: 0, y: 0, width: W, height: H, fill: P.inkDeep }));
    var cw = W / items.length;
    items.forEach(function (it, i) {
      var x = i * cw;
      if (i > 0) svg.appendChild(el("line", { x1: x, y1: 32, x2: x, y2: H - 32, stroke: P.ink700 }));
      svg.appendChild(el("text", { x: x + 24, y: 44, "font-size": 10, "font-weight": 700, fill: P.lime, "letter-spacing": "0.16em" }, (it.label || "").toUpperCase()));
      svg.appendChild(el("text", { x: x + 24, y: 110, "font-family": "Carnas, Arial", "font-size": 54, "font-weight": 700, fill: P.white, "letter-spacing": -2 }, String(it.value)));
      if (it.suffix) {
        var off = 24 + String(it.value).length * 30;
        svg.appendChild(el("text", { x: x + off, y: 110, "font-family": "Carnas, Arial", "font-size": 26, "font-weight": 700, fill: P.lime }, it.suffix));
      }
      if (it.note) svg.appendChild(el("text", { x: x + 24, y: 140, "font-size": 12, fill: P.ink300 }, it.note));
    });
  };

  TYPES.sparklineGrid = function (d) {
    var items = d.items; // {label, values, value, change}
    var W = 640, H = items.length > 4 ? 280 : 200;
    var cols = 2, rows = Math.ceil(items.length / cols);
    var cw = W / cols, ch = H / rows;
    var svg = makeSvg(W, H);
    items.forEach(function (it, i) {
      var col = i % cols, row = Math.floor(i / cols);
      var x = col * cw, y = row * ch;
      svg.appendChild(el("rect", { x: x + 1, y: y + 1, width: cw - 2, height: ch - 2, fill: P.white, stroke: P.ink200 }));
      svg.appendChild(el("text", { x: x + 16, y: y + 24, "font-size": 11, "font-weight": 700, fill: P.ink600, "letter-spacing": 1.4 }, (it.label || "").toUpperCase()));
      svg.appendChild(el("text", { x: x + 16, y: y + 64, "font-family": "Carnas, Arial", "font-size": 32, "font-weight": 700, fill: P.ink, "letter-spacing": -1.2 }, it.value));
      if (it.change) svg.appendChild(el("text", { x: x + 16, y: y + 84, "font-size": 11, "font-weight": 700, fill: it.change.startsWith("-") ? P.danger : P.success }, it.change));
      // sparkline
      var lo = Math.min.apply(null, it.values), hi = Math.max.apply(null, it.values);
      var sx0 = x + cw - 140, sx1 = x + cw - 20, sy0 = y + 26, sy1 = y + ch - 26;
      var pts = it.values.map(function (v, j) {
        var px = sx0 + (j / (it.values.length - 1)) * (sx1 - sx0);
        var py = sy1 - ((v - lo) / (hi - lo || 1)) * (sy1 - sy0);
        return [px, py];
      });
      svg.appendChild(el("path", { d: "M" + pts.map(function (p) { return p.join(","); }).join(" L "), fill: "none", stroke: P.lime, "stroke-width": 2 }));
      var last = pts[pts.length - 1];
      svg.appendChild(el("circle", { cx: last[0], cy: last[1], r: 3, fill: P.lime, stroke: P.ink, "stroke-width": 1 }));
    });
  };

  TYPES.bullet = function (d) {
    var W = 640, H = 240, L = 140, R = 30, T = 30;
    var rows = d.rows; // {label, value, target, ranges:[]}
    var rowH = (H - T - 20) / rows.length;
    var svg = makeSvg(W, H);
    rows.forEach(function (r, i) {
      var max = r.ranges[r.ranges.length - 1];
      var y = T + i * rowH;
      var bw = W - L - R;
      // ranges in increasing greys
      var greys = [P.ink200, P.ink300, P.ink400];
      var prev = 0;
      r.ranges.forEach(function (rg, j) {
        svg.appendChild(el("rect", { x: L + (prev / max) * bw, y: y, width: ((rg - prev) / max) * bw, height: 22, fill: greys[j] || P.ink400 }));
        prev = rg;
      });
      svg.appendChild(el("rect", { x: L, y: y + 6, width: (r.value / max) * bw, height: 10, fill: P.lime }));
      svg.appendChild(el("line", { x1: L + (r.target / max) * bw, y1: y - 2, x2: L + (r.target / max) * bw, y2: y + 24, stroke: P.ink, "stroke-width": 3 }));
      svg.appendChild(el("text", { class: "label", x: L - 10, y: y + 16, "text-anchor": "end" }, r.label));
      svg.appendChild(el("text", { x: L + (r.value / max) * bw + 6, y: y + 16, "font-size": 11, "font-weight": 700, fill: P.ink }, fmt(r.value, d)));
    });
  };

  TYPES.gauge = function (d) {
    var W = 640, H = 220, cx = 320, cy = 180, R = 130;
    var value = d.value, max = d.max || 100;
    var svg = makeSvg(W, H);
    // arc
    svg.appendChild(el("path", { d: "M" + (cx - R) + "," + cy + " A" + R + "," + R + " 0 0 1 " + (cx + R) + "," + cy, fill: "none", stroke: P.ink200, "stroke-width": 24 }));
    var p = clamp(value / max, 0, 1);
    var a = -Math.PI + p * Math.PI;
    var ex = cx + Math.cos(a) * R, ey = cy + Math.sin(a) * R;
    var large = p > 0.5 ? 1 : 0;
    svg.appendChild(el("path", { d: "M" + (cx - R) + "," + cy + " A" + R + "," + R + " 0 " + large + " 1 " + ex + "," + ey, fill: "none", stroke: P.lime, "stroke-width": 24, "stroke-linecap": "butt" }));
    svg.appendChild(el("text", { x: cx, y: cy - 30, "text-anchor": "middle", "font-family": "Carnas, Arial", "font-size": 56, "font-weight": 700, fill: P.ink }, fmt(value, d)));
    svg.appendChild(el("text", { x: cx, y: cy - 4, "text-anchor": "middle", "font-size": 12, fill: P.ink600 }, d.subtitle2 || ""));
    if (d.note) svg.appendChild(el("text", { x: cx, y: cy + 30, "text-anchor": "middle", "font-size": 12, fill: P.ink600 }, d.note));
  };

  TYPES.ringProgress = function (d) {
    var W = 640, H = 220, cx = 320, cy = 110;
    var value = d.value, max = d.max || 100;
    var p = clamp(value / max, 0, 1);
    var R = 80, sw = 22;
    var svg = makeSvg(W, H);
    svg.appendChild(el("circle", { cx: cx, cy: cy, r: R, fill: "none", stroke: P.ink100, "stroke-width": sw }));
    var a = p * Math.PI * 2;
    var sx = cx, sy = cy - R;
    var ex = cx + Math.sin(a) * R, ey = cy - Math.cos(a) * R;
    var large = a > Math.PI ? 1 : 0;
    svg.appendChild(el("path", { d: "M" + sx + "," + sy + " A" + R + "," + R + " 0 " + large + " 1 " + ex + "," + ey, fill: "none", stroke: P.lime, "stroke-width": sw, "stroke-linecap": "round" }));
    svg.appendChild(el("text", { x: cx, y: cy + 8, "text-anchor": "middle", "font-family": "Carnas, Arial", "font-size": 36, "font-weight": 700, fill: P.ink }, Math.round(p * 100) + "%"));
    if (d.note) svg.appendChild(el("text", { x: cx, y: cy + 30, "text-anchor": "middle", "font-size": 12, fill: P.ink600 }, d.note));
  };

  TYPES.pictogram = function (d) {
    var total = d.total, filled = d.filled;
    var perRow = d.perRow || 10;
    var rows = Math.ceil(total / perRow);
    var W = 640, H = 60 + rows * 24, cell = 22;
    var svg = makeSvg(W, H);
    for (var i = 0; i < total; i++) {
      var r = Math.floor(i / perRow), c = i % perRow;
      var x = 30 + c * cell, y = 20 + r * cell;
      svg.appendChild(el("rect", { x: x, y: y, width: cell - 4, height: cell - 4, fill: i < filled ? P.lime : P.ink200, stroke: P.ink, "stroke-width": 0.6 }));
    }
    svg.appendChild(el("text", { x: 30, y: H - 16, "font-size": 11, fill: P.ink600 }, filled + " of " + total + (d.note ? " · " + d.note : "")));
  };

  TYPES.forecastCone = function (d) {
    // History line that joins seamlessly into a fan of P10/P50/P90.
    // The cone widens *from the last history point*, so all three forecast
    // series share their starting value with history (no off-centre lines).
    var W = 640, H = 280, L = 40, R = 30, T = 20, B = 36;
    var labels = d.labels;
    var hist = d.history.slice();
    var lastH = hist[hist.length - 1];
    // ensure each forecast series starts at lastH at the join index
    var joinIdx = hist.length - 1;
    var p10 = labels.map(function (_, i) { return i < joinIdx ? hist[i] : (i === joinIdx ? lastH : d.p10[i]); });
    var p50 = labels.map(function (_, i) { return i < joinIdx ? hist[i] : (i === joinIdx ? lastH : d.p50[i]); });
    var p90 = labels.map(function (_, i) { return i < joinIdx ? hist[i] : (i === joinIdx ? lastH : d.p90[i]); });
    var all = [].concat(hist, p10, p50, p90);
    var max = nice(Math.max.apply(null, all) * 1.12);
    var min = 0;
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, min, max, { format: d.format });
    var step = (W - L - R) / (labels.length - 1);
    var sx = function (i) { return L + i * step; };
    var sy = function (v) { return H - B - (v - min) / (max - min) * (H - B - T); };
    labels.forEach(function (lb, i) { svg.appendChild(el("text", { class: "tick", x: sx(i), y: H - B + 16, "text-anchor": "middle" }, lb)); });
    // separator band (forecast region tint)
    svg.appendChild(el("rect", { x: sx(joinIdx), y: T, width: (W - R) - sx(joinIdx), height: (H - B) - T, fill: P.ink050 }));
    // outer cone (P10-P90), only forecast portion
    var topPts = [], botPts = [];
    for (var i = joinIdx; i < labels.length; i++) {
      topPts.push([sx(i), sy(p90[i])]);
      botPts.push([sx(i), sy(p10[i])]);
    }
    svg.appendChild(el("path", { d: "M" + topPts.map(function (p) { return p.join(","); }).join(" L ") + " L " + botPts.slice().reverse().map(function (p) { return p.join(","); }).join(" L ") + " Z", fill: P.lime, opacity: 0.28 }));
    // P50 line in forecast region
    var p50Pts = [];
    for (var i = joinIdx; i < labels.length; i++) p50Pts.push(sx(i) + "," + sy(p50[i]));
    svg.appendChild(el("path", { d: "M" + p50Pts.join(" L "), fill: "none", stroke: P.ink, "stroke-width": 2, "stroke-dasharray": "5 4" }));
    // history (solid lime)
    var hPts = hist.map(function (v, i) { return sx(i) + "," + sy(v); });
    svg.appendChild(el("path", { d: "M" + hPts.join(" L "), fill: "none", stroke: P.lime, "stroke-width": 3, "stroke-linecap": "round" }));
    // history dots (last one emphasised)
    hist.forEach(function (v, i) {
      svg.appendChild(el("circle", { cx: sx(i), cy: sy(v), r: i === joinIdx ? 5 : 3.5, fill: i === joinIdx ? P.ink : P.lime, stroke: P.ink, "stroke-width": 1 }));
    });
    // separator vertical at join
    svg.appendChild(el("line", { x1: sx(joinIdx), y1: T, x2: sx(joinIdx), y2: H - B, stroke: P.ink, "stroke-width": 1, "stroke-dasharray": "2 3" }));
    // "Forecast" label tag
    svg.appendChild(el("rect", { x: sx(joinIdx) + 6, y: T + 6, width: 70, height: 18, fill: P.ink }));
    svg.appendChild(el("text", { x: sx(joinIdx) + 41, y: T + 19, "text-anchor": "middle", "font-size": 9, "font-weight": 700, fill: P.lime, "letter-spacing": "0.14em" }, "FORECAST"));
    legend([{ label: "History", color: P.lime }, { label: "P50 (median)", color: P.ink }, { label: "P10–P90 range", color: P.lime }]);
  };

  TYPES.ranking = function (d) {
    var rows = d.rows; // {rank, label, value, prev?}
    var W = 640, rowH = 36;
    var H = 20 + rows.length * rowH;
    var svg = makeSvg(W, H);
    rows.forEach(function (r, i) {
      var y = 10 + i * rowH;
      var highlight = r.highlight;
      svg.appendChild(el("rect", { x: 10, y: y, width: W - 20, height: rowH - 6, fill: highlight ? P.lime : P.ink050, stroke: P.ink200 }));
      svg.appendChild(el("text", { x: 30, y: y + (rowH - 6) / 2 + 4, "font-family": "Carnas, Arial", "font-size": 18, "font-weight": 700, fill: P.ink }, "#" + r.rank));
      svg.appendChild(el("text", { x: 80, y: y + (rowH - 6) / 2 + 4, "font-size": 13, "font-weight": 700, fill: P.ink }, r.label));
      svg.appendChild(el("text", { x: W - 30, y: y + (rowH - 6) / 2 + 4, "text-anchor": "end", "font-size": 13, "font-weight": 700, fill: P.ink }, fmt(r.value, d)));
      if (r.prev !== undefined) {
        var diff = r.prev - r.rank;
        var t = diff > 0 ? "▲ " + diff : (diff < 0 ? "▼ " + Math.abs(diff) : "—");
        svg.appendChild(el("text", { x: W - 110, y: y + (rowH - 6) / 2 + 4, "text-anchor": "end", "font-size": 11, "font-weight": 700, fill: diff > 0 ? P.success : (diff < 0 ? P.danger : P.ink400) }, t));
      }
    });
  };

  // ====== NEW: 67–86 ==================================================
  TYPES.timeline = function (d) {
    // Horizontal milestone timeline
    var W = 640, H = 200, L = 40, R = 40, midY = 100;
    var events = d.events; // {label, date, side?: "above"|"below"}
    var svg = makeSvg(W, H);
    svg.appendChild(el("line", { x1: L, y1: midY, x2: W - R, y2: midY, stroke: P.ink, "stroke-width": 2 }));
    var step = (W - L - R) / (events.length - 1);
    events.forEach(function (e, i) {
      var x = L + i * step;
      var above = e.side === "above" || (e.side !== "below" && i % 2 === 0);
      svg.appendChild(el("circle", { cx: x, cy: midY, r: 7, fill: P.lime, stroke: P.ink, "stroke-width": 2 }));
      svg.appendChild(el("text", { x: x, y: midY + (above ? -28 : 24), "text-anchor": "middle", "font-size": 11, "font-weight": 700, fill: P.ink }, e.label));
      svg.appendChild(el("text", { x: x, y: midY + (above ? -14 : 38), "text-anchor": "middle", "font-size": 10, fill: P.ink600 }, e.date));
    });
  };

  TYPES.dependencyWheel = function (d) {
    var W = 640, H = 300, cx = 200, cy = 150, R = 110;
    var nodes = d.nodes; // [label]
    var links = d.links; // [{from, to, weight}]
    var svg = makeSvg(W, H);
    var n = nodes.length;
    var positions = nodes.map(function (lb, i) {
      var a = -Math.PI / 2 + (i / n) * Math.PI * 2;
      return { x: cx + Math.cos(a) * R, y: cy + Math.sin(a) * R, a: a, label: lb };
    });
    links.forEach(function (lk) {
      var a = positions[lk.from], b = positions[lk.to];
      svg.appendChild(el("path", { d: "M" + a.x + "," + a.y + " Q" + cx + "," + cy + " " + b.x + "," + b.y, fill: "none", stroke: P.ink, opacity: clamp(lk.weight / 100, 0.1, 0.6), "stroke-width": 1 + lk.weight / 25 }));
    });
    positions.forEach(function (p, i) {
      svg.appendChild(el("circle", { cx: p.x, cy: p.y, r: 9, fill: P.lime, stroke: P.ink, "stroke-width": 1.5 }));
      var lx = cx + Math.cos(p.a) * (R + 22);
      var ly = cy + Math.sin(p.a) * (R + 22) + 4;
      var anchor = Math.cos(p.a) > 0.3 ? "start" : (Math.cos(p.a) < -0.3 ? "end" : "middle");
      svg.appendChild(el("text", { x: lx, y: ly, "text-anchor": anchor, "font-size": 10, "font-weight": 700, fill: P.ink }, p.label));
    });
    // legend
    if (d.legend) d.legend.forEach(function (lg, i) {
      svg.appendChild(el("text", { x: 380, y: 30 + i * 18, "font-size": 10, fill: P.ink600 }, lg));
    });
  };

  TYPES.dumbbell = function (d) {
    // before/after dumbbell - similar to dotPlot but emphasises the change as a thicker line
    var data = d.data;
    var rowH = 36, L = 160, R = 80, T = 16;
    var H = T + data.length * rowH + 10, W = 640;
    var all = data.reduce(function (a, r) { return a.concat([r.before, r.after]); }, []);
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    var pad = (hi - lo) * 0.1; lo -= pad; hi += pad;
    var sx = function (v) { return L + (v - lo) / (hi - lo) * (W - L - R); };
    var svg = makeSvg(W, H);
    data.forEach(function (r, i) {
      var y = T + i * rowH + rowH / 2;
      var increased = r.after > r.before;
      svg.appendChild(el("line", { x1: sx(r.before), y1: y, x2: sx(r.after), y2: y, stroke: increased ? P.lime : P.ink400, "stroke-width": 6 }));
      svg.appendChild(el("circle", { cx: sx(r.before), cy: y, r: 7, fill: P.white, stroke: P.ink, "stroke-width": 2 }));
      svg.appendChild(el("circle", { cx: sx(r.after), cy: y, r: 7, fill: P.ink, stroke: P.ink, "stroke-width": 2 }));
      svg.appendChild(el("text", { class: "label", x: L - 10, y: y + 4, "text-anchor": "end" }, r.label));
      svg.appendChild(el("text", { x: W - R + 10, y: y + 4, "font-size": 11, "font-weight": 700, fill: increased ? P.success : P.danger }, (increased ? "+" : "") + fmt(r.after - r.before, d)));
    });
    legend([{ label: d.beforeLabel || "Before", color: P.white }, { label: d.afterLabel || "After", color: P.ink }]);
  };

  TYPES.matrixGrid = function (d) {
    // 2x2 / 3x3 strategy grid with labelled cells
    var W = 640, H = 320, L = 80, R = 20, T = 30, B = 30;
    var rows = d.rows, cols = d.cols, cells = d.cells; // cells[ri][ci] = {label, items}
    var cw = (W - L - R) / cols.length, ch = (H - T - B) / rows.length;
    var svg = makeSvg(W, H);
    cols.forEach(function (c, j) { svg.appendChild(el("text", { x: L + j * cw + cw / 2, y: T - 10, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink600, "letter-spacing": "0.08em" }, c.toUpperCase())); });
    rows.forEach(function (r, i) {
      svg.appendChild(el("text", { x: L - 10, y: T + i * ch + ch / 2 + 4, "text-anchor": "end", "font-size": 10, "font-weight": 700, fill: P.ink600, "letter-spacing": "0.08em" }, r.toUpperCase()));
      cols.forEach(function (c, j) {
        var cell = cells[i][j] || {};
        var hl = cell.highlight;
        svg.appendChild(el("rect", { x: L + j * cw + 2, y: T + i * ch + 2, width: cw - 4, height: ch - 4, fill: hl ? P.lime : P.white, stroke: P.ink200 }));
        if (cell.label) svg.appendChild(el("text", { x: L + j * cw + 12, y: T + i * ch + 22, "font-size": 11, "font-weight": 700, fill: P.ink }, cell.label));
        (cell.items || []).slice(0, 4).forEach(function (it, k) {
          svg.appendChild(el("text", { x: L + j * cw + 12, y: T + i * ch + 40 + k * 14, "font-size": 10, fill: P.ink700 }, "· " + it));
        });
      });
    });
  };

  TYPES.deltaBar = function (d) {
    // bars with a delta vs prior period inline beside each bar
    var W = 640, H = 300, L = 40, R = 60, T = 16, B = 36;
    var data = d.data; // {label, value, prev}
    var max = nice(Math.max.apply(null, data.map(function (r) { return Math.max(r.value, r.prev); })) * 1.1);
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, 0, max, { format: d.format });
    var step = (W - L - R) / data.length;
    var bw = step * 0.55;
    data.forEach(function (r, i) {
      var x = L + step * i + (step - bw) / 2;
      var sy = function (v) { return H - B - (v / max) * (H - B - T); };
      svg.appendChild(el("rect", { x: x, y: sy(r.prev), width: bw, height: H - B - sy(r.prev), fill: P.ink200 }));
      svg.appendChild(el("rect", { x: x + bw * 0.18, y: sy(r.value), width: bw * 0.64, height: H - B - sy(r.value), fill: P.lime }));
      var diff = r.value - r.prev;
      var pctV = r.prev ? (diff / r.prev) * 100 : 0;
      svg.appendChild(el("text", { x: x + bw / 2, y: sy(Math.max(r.value, r.prev)) - 6, "text-anchor": "middle", "font-size": 11, "font-weight": 700, fill: diff >= 0 ? P.success : P.danger }, (diff >= 0 ? "+" : "") + Math.round(pctV) + "%"));
      svg.appendChild(el("text", { class: "tick", x: x + bw / 2, y: H - B + 16, "text-anchor": "middle" }, r.label));
    });
    legend([{ label: d.prevLabel || "Prior", color: P.ink200 }, { label: d.valueLabel || "Current", color: P.lime }]);
  };

  TYPES.donutMatrix = function (d) {
    // small-multiple donuts
    var items = d.items; // {label, value, max}
    var W = 640, H = 240, cols = items.length, cw = W / cols;
    var svg = makeSvg(W, H);
    items.forEach(function (it, i) {
      var cx = cw * i + cw / 2, cy = 110, R = 50, ir = 32;
      svg.appendChild(el("circle", { cx: cx, cy: cy, r: (R + ir) / 2, fill: "none", stroke: P.ink100, "stroke-width": R - ir }));
      var p = it.value / (it.max || 100);
      var a = p * Math.PI * 2;
      var midR = (R + ir) / 2;
      var sx = cx, sy = cy - midR;
      var ex = cx + Math.sin(a) * midR, ey = cy - Math.cos(a) * midR;
      var large = a > Math.PI ? 1 : 0;
      svg.appendChild(el("path", { d: "M" + sx + "," + sy + " A" + midR + "," + midR + " 0 " + large + " 1 " + ex + "," + ey, fill: "none", stroke: P.lime, "stroke-width": R - ir, "stroke-linecap": "round" }));
      svg.appendChild(el("text", { x: cx, y: cy + 4, "text-anchor": "middle", "font-family": "Carnas, Arial", "font-size": 22, "font-weight": 700, fill: P.ink }, Math.round(p * 100) + "%"));
      svg.appendChild(el("text", { x: cx, y: 200, "text-anchor": "middle", "font-size": 11, "font-weight": 700, fill: P.ink600 }, it.label));
      svg.appendChild(el("text", { x: cx, y: 220, "text-anchor": "middle", "font-size": 10, fill: P.ink500 }, fmt(it.value, d) + " / " + fmt(it.max, d)));
    });
  };

  TYPES.flowDiagram = function (d) {
    // simple left→right blocks with arrows
    var W = 640, H = 220;
    var stages = d.stages; // [{label, value?}]
    var svg = makeSvg(W, H);
    var bw = (W - 60 - (stages.length - 1) * 40) / stages.length;
    stages.forEach(function (s, i) {
      var x = 30 + i * (bw + 40);
      svg.appendChild(el("rect", { x: x, y: 60, width: bw, height: 100, fill: i === 0 ? P.ink : P.lime, stroke: P.ink }));
      svg.appendChild(el("text", { x: x + bw / 2, y: 110, "text-anchor": "middle", "font-size": 13, "font-weight": 700, fill: i === 0 ? P.lime : P.ink }, s.label));
      if (s.value !== undefined) svg.appendChild(el("text", { x: x + bw / 2, y: 132, "text-anchor": "middle", "font-family": "Carnas, Arial", "font-size": 18, "font-weight": 700, fill: i === 0 ? P.white : P.ink }, fmt(s.value, d)));
      if (i < stages.length - 1) {
        var ax = x + bw + 4;
        svg.appendChild(el("path", { d: "M" + ax + ",100 L" + (ax + 30) + ",100 M" + (ax + 22) + ",94 L" + (ax + 30) + ",100 L" + (ax + 22) + ",106", fill: "none", stroke: P.ink, "stroke-width": 2 }));
      }
    });
  };

  TYPES.geoBubble = function (d) {
    // schematic country bubbles on a soft-grey backdrop
    var W = 640, H = 280, L = 30, T = 20;
    var bubbles = d.bubbles; // {label, x, y, value}
    var maxV = Math.max.apply(null, bubbles.map(function (b) { return b.value; }));
    var svg = makeSvg(W, H);
    svg.appendChild(el("rect", { x: L, y: T, width: W - L * 2, height: H - T - 20, fill: P.ink050, stroke: P.ink200 }));
    bubbles.forEach(function (b) {
      var x = L + b.x * (W - L * 2);
      var y = T + b.y * (H - T - 20);
      var r = 6 + (b.value / maxV) * 30;
      svg.appendChild(el("circle", { cx: x, cy: y, r: r, fill: P.lime, opacity: 0.7, stroke: P.ink, "stroke-width": 1 }));
      svg.appendChild(el("text", { x: x, y: y + 4, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink }, b.label));
      svg.appendChild(el("text", { x: x, y: y + r + 12, "text-anchor": "middle", "font-size": 9, fill: P.ink600 }, fmt(b.value, d)));
    });
  };

  TYPES.benchmark = function (d) {
    // metric vs benchmark + percentile band
    var W = 640, H = 260, L = 30, R = 30, T = 30;
    var metrics = d.metrics; // {label, value, p25, p50, p75, max}
    var rowH = (H - T - 20) / metrics.length;
    var svg = makeSvg(W, H);
    metrics.forEach(function (m, i) {
      var y = T + i * rowH + 6;
      var bw = W - L - R - 200;
      svg.appendChild(el("text", { x: L, y: y + 16, "font-size": 11, "font-weight": 700, fill: P.ink }, m.label));
      var sx = function (v) { return L + 200 + (v / m.max) * bw; };
      svg.appendChild(el("line", { x1: L + 200, y1: y + 14, x2: L + 200 + bw, y2: y + 14, stroke: P.ink200, "stroke-width": 6 }));
      svg.appendChild(el("rect", { x: sx(m.p25), y: y + 8, width: sx(m.p75) - sx(m.p25), height: 18, fill: P.ink200 }));
      svg.appendChild(el("line", { x1: sx(m.p50), y1: y + 6, x2: sx(m.p50), y2: y + 28, stroke: P.ink, "stroke-width": 2 }));
      svg.appendChild(el("circle", { cx: sx(m.value), cy: y + 17, r: 8, fill: P.lime, stroke: P.ink, "stroke-width": 1.5 }));
      svg.appendChild(el("text", { x: sx(m.value), y: y + 21, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink }, fmt(m.value, d)));
    });
    legend([{ label: "P25–P75 band", color: P.ink200 }, { label: "Median", color: P.ink }, { label: "Subject", color: P.lime }]);
  };

  TYPES.compoundGrowth = function (d) {
    // CAGR-style line w/ end-point CAGR badge
    var ctx = lineCommon(d);
    var s = ctx.series[0];
    var pts = s.values.map(function (v, i) { return [ctx.sx(i), ctx.sy(v)]; });
    ctx.svg.appendChild(el("path", { d: "M" + pts.map(function (p) { return p.join(","); }).join(" L "), fill: "none", stroke: P.lime, "stroke-width": 3 }));
    pts.forEach(function (p) { ctx.svg.appendChild(el("circle", { cx: p[0], cy: p[1], r: 4, fill: P.lime, stroke: P.ink, "stroke-width": 1 })); });
    var first = s.values[0], last = s.values[s.values.length - 1];
    var n = s.values.length - 1;
    var cagr = n > 0 ? (Math.pow(last / first, 1 / n) - 1) * 100 : 0;
    var bx = pts[pts.length - 1][0] - 110, by = pts[pts.length - 1][1] - 38;
    ctx.svg.appendChild(el("rect", { x: bx, y: by, width: 100, height: 32, fill: P.ink, stroke: P.ink }));
    ctx.svg.appendChild(el("text", { x: bx + 8, y: by + 13, "font-size": 9, "font-weight": 700, fill: P.lime, "letter-spacing": "0.1em" }, "CAGR"));
    ctx.svg.appendChild(el("text", { x: bx + 8, y: by + 28, "font-family": "Carnas, Arial", "font-size": 16, "font-weight": 700, fill: P.white }, (cagr >= 0 ? "+" : "") + cagr.toFixed(1) + "%"));
  };

  TYPES.heatStrip = function (d) {
    // 1-row heatmap (timeline density)
    var W = 640, H = 120, L = 30, T = 50;
    var values = d.values; // [{label, value}]
    var max = Math.max.apply(null, values.map(function (v) { return v.value; }));
    var min = Math.min.apply(null, values.map(function (v) { return v.value; }));
    var cw = (W - L - 20) / values.length;
    var svg = makeSvg(W, H);
    values.forEach(function (v, i) {
      var t = (v.value - min) / (max - min || 1);
      var bg = "rgb(" + Math.round(255 - t * (255 - 205)) + "," + Math.round(255 - t * (255 - 240)) + "," + Math.round(255 - t * (255 - 81)) + ")";
      svg.appendChild(el("rect", { x: L + i * cw, y: T, width: cw - 1, height: 36, fill: bg }));
      if (i % Math.ceil(values.length / 8) === 0) svg.appendChild(el("text", { x: L + i * cw + cw / 2, y: T + 56, "text-anchor": "middle", "font-size": 10, fill: P.ink600 }, v.label));
    });
    svg.appendChild(el("text", { x: L, y: T - 12, "font-size": 10, "font-weight": 700, fill: P.ink600 }, fmt(min, d) + " min"));
    svg.appendChild(el("text", { x: W - 20, y: T - 12, "text-anchor": "end", "font-size": 10, "font-weight": 700, fill: P.ink600 }, fmt(max, d) + " max"));
  };

  TYPES.areaRange = function (d) {
    // alias for rangeBand for clarity
    TYPES.rangeBand(d);
  };

  TYPES.stackedHbar = function (d) {
    var W = 640, L = 130, R = 30;
    var cats = d.categories, ser = d.series;
    var rowH = 28;
    var H = 30 + cats.length * rowH;
    var svg = makeSvg(W, H);
    var totals = cats.map(function (_, i) { return ser.reduce(function (s, x) { return s + x.values[i]; }, 0); });
    cats.forEach(function (c, i) {
      var y = 20 + i * rowH;
      var cum = 0;
      ser.forEach(function (s, si) {
        var v = s.values[i];
        var w = (v / totals[i]) * (W - L - R);
        svg.appendChild(el("rect", { x: L + cum, y: y, width: w, height: rowH - 8, fill: s.color || SERIES[si] }));
        if (w > 24) svg.appendChild(el("text", { x: L + cum + w / 2, y: y + (rowH - 8) / 2 + 4, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: si === 0 ? P.ink : P.white }, Math.round(v / totals[i] * 100) + "%"));
        cum += w;
      });
      svg.appendChild(el("text", { class: "label", x: L - 10, y: y + (rowH - 8) / 2 + 4, "text-anchor": "end" }, c));
    });
    legend(ser.map(function (s, i) { return { label: s.name, color: s.color || SERIES[i] }; }));
  };

  TYPES.cumulative = function (d) {
    var labels = d.labels, values = d.values;
    var cum = [];
    values.reduce(function (s, v, i) { cum[i] = s + v; return cum[i]; }, 0);
    var ctx = lineCommon({ labels: labels, series: [{ values: cum }], format: d.format });
    var s = cum.map(function (v, i) { return [ctx.sx(i), ctx.sy(v)]; });
    var area = "M" + ctx.sx(0) + "," + ctx.sy(0) + " L" + s.map(function (p) { return p.join(","); }).join(" L ") + " L" + ctx.sx(cum.length - 1) + "," + ctx.sy(0) + " Z";
    ctx.svg.appendChild(el("path", { d: area, fill: P.lime, opacity: 0.4 }));
    ctx.svg.appendChild(el("path", { d: "M" + s.map(function (p) { return p.join(","); }).join(" L "), fill: "none", stroke: P.ink, "stroke-width": 2 }));
    s.forEach(function (p) { ctx.svg.appendChild(el("circle", { cx: p[0], cy: p[1], r: 3, fill: P.lime, stroke: P.ink })); });
  };

  TYPES.rugStrip = function (d) {
    // single-axis density: tick rug + KDE-ish smoothing line
    var W = 640, H = 200, L = 30, R = 30, T = 50, B = 30;
    var values = d.values;
    var lo = Math.min.apply(null, values), hi = Math.max.apply(null, values);
    var pad = (hi - lo) * 0.05; lo -= pad; hi += pad;
    var sx = function (v) { return L + (v - lo) / (hi - lo) * (W - L - R); };
    var svg = makeSvg(W, H);
    // axis
    svg.appendChild(el("line", { x1: L, y1: H - B, x2: W - R, y2: H - B, stroke: P.ink, "stroke-width": 1 }));
    // density (simple kernel)
    var samples = 60;
    var bw = (hi - lo) / 8;
    var dens = [];
    for (var i = 0; i <= samples; i++) {
      var x = lo + (i / samples) * (hi - lo);
      var k = 0;
      values.forEach(function (v) { var u = (x - v) / bw; k += Math.exp(-0.5 * u * u); });
      dens.push(k);
    }
    var maxD = Math.max.apply(null, dens);
    var pts = dens.map(function (v, i) {
      var x = L + (i / samples) * (W - L - R);
      var y = (H - B) - (v / maxD) * (H - B - T);
      return [x, y];
    });
    svg.appendChild(el("path", { d: "M" + pts[0][0] + "," + (H - B) + " L" + pts.map(function (p) { return p.join(","); }).join(" L ") + " L" + pts[pts.length - 1][0] + "," + (H - B) + " Z", fill: P.lime, opacity: 0.4 }));
    svg.appendChild(el("path", { d: "M" + pts.map(function (p) { return p.join(","); }).join(" L "), fill: "none", stroke: P.ink, "stroke-width": 2 }));
    // rug
    values.forEach(function (v) {
      svg.appendChild(el("line", { x1: sx(v), y1: H - B, x2: sx(v), y2: H - B + 8, stroke: P.ink, "stroke-width": 1 }));
    });
    [lo, (lo + hi) / 2, hi].forEach(function (t) { svg.appendChild(el("text", { x: sx(t), y: H - B + 22, "text-anchor": "middle", "font-size": 10, fill: P.ink600 }, fmt(t, d))); });
  };

  TYPES.violin = function (d) {
    // approximate violins per group
    var W = 640, H = 280, L = 40, R = 20, T = 20, B = 30;
    var groups = d.groups; // {label, points}
    var all = groups.reduce(function (a, g) { return a.concat(g.points); }, []);
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    var pad = (hi - lo) * 0.1; lo -= pad; hi += pad;
    var step = (W - L - R) / groups.length;
    var maxW = step * 0.4;
    var svg = makeSvg(W, H);
    yAxis(svg, L, W - R, T, H - B, lo, hi, { format: d.format });
    var sy = function (v) { return H - B - (v - lo) / (hi - lo) * (H - B - T); };
    groups.forEach(function (g, gi) {
      var cx = L + step * gi + step / 2;
      var samples = 30;
      var bw = (hi - lo) / 6;
      var d1 = [], d2 = [];
      for (var i = 0; i <= samples; i++) {
        var v = lo + (i / samples) * (hi - lo);
        var k = 0;
        g.points.forEach(function (p) { var u = (v - p) / bw; k += Math.exp(-0.5 * u * u); });
        d1.push([v, k]); d2.push([v, k]);
      }
      var maxK = Math.max.apply(null, d1.map(function (p) { return p[1]; }));
      var rightPts = d1.map(function (p) { return [cx + (p[1] / maxK) * maxW, sy(p[0])]; });
      var leftPts = d1.map(function (p) { return [cx - (p[1] / maxK) * maxW, sy(p[0])]; }).reverse();
      svg.appendChild(el("path", { d: "M" + rightPts.concat(leftPts).map(function (p) { return p.join(","); }).join(" L ") + " Z", fill: P.lime, opacity: 0.7, stroke: P.ink }));
      // median
      var sorted = g.points.slice().sort(function (a, b) { return a - b; });
      var med = sorted[Math.floor(sorted.length / 2)];
      svg.appendChild(el("line", { x1: cx - 8, y1: sy(med), x2: cx + 8, y2: sy(med), stroke: P.ink, "stroke-width": 2 }));
      svg.appendChild(el("text", { class: "tick", x: cx, y: H - B + 16, "text-anchor": "middle" }, g.label));
    });
  };

  TYPES.matrixBubble = function (d) {
    // grid where each cell holds a bubble sized to its value
    var W = 640, H = 280, L = 100, T = 30;
    var rows = d.rows, cols = d.cols, values = d.values;
    var cw = (W - L - 30) / cols.length, ch = (H - T - 20) / rows.length;
    var max = Math.max.apply(null, values.reduce(function (a, b) { return a.concat(b); }, []));
    var svg = makeSvg(W, H);
    cols.forEach(function (c, j) { svg.appendChild(el("text", { x: L + j * cw + cw / 2, y: T - 8, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink600 }, c)); });
    rows.forEach(function (r, i) {
      svg.appendChild(el("text", { x: L - 8, y: T + i * ch + ch / 2 + 4, "text-anchor": "end", "font-size": 10, "font-weight": 700, fill: P.ink }, r));
      values[i].forEach(function (v, j) {
        var rad = max ? (v / max) * Math.min(cw, ch) * 0.4 : 0;
        svg.appendChild(el("rect", { x: L + j * cw + 1, y: T + i * ch + 1, width: cw - 2, height: ch - 2, fill: P.white, stroke: P.ink100 }));
        if (v > 0) {
          svg.appendChild(el("circle", { cx: L + j * cw + cw / 2, cy: T + i * ch + ch / 2, r: rad, fill: P.lime, opacity: 0.85, stroke: P.ink, "stroke-width": 1 }));
          svg.appendChild(el("text", { x: L + j * cw + cw / 2, y: T + i * ch + ch / 2 + 4, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink }, v));
        }
      });
    });
  };

  TYPES.scoreCard = function (d) {
    // grid of metrics, each with status color + sparkline-less score
    var W = 640, items = d.items;
    var cols = 3, rows = Math.ceil(items.length / cols);
    var H = 20 + rows * 110;
    var cw = W / cols, ch = 110;
    var svg = makeSvg(W, H);
    items.forEach(function (it, i) {
      var col = i % cols, row = Math.floor(i / cols);
      var x = col * cw, y = 10 + row * ch;
      var status = it.status; // "good" | "warn" | "bad"
      var bar = status === "good" ? P.lime : (status === "bad" ? P.danger : P.warning);
      svg.appendChild(el("rect", { x: x + 6, y: y, width: cw - 12, height: ch - 12, fill: P.white, stroke: P.ink200 }));
      svg.appendChild(el("rect", { x: x + 6, y: y, width: 4, height: ch - 12, fill: bar }));
      svg.appendChild(el("text", { x: x + 22, y: y + 22, "font-size": 10, "font-weight": 700, fill: P.ink600, "letter-spacing": "0.1em" }, (it.label || "").toUpperCase()));
      svg.appendChild(el("text", { x: x + 22, y: y + 60, "font-family": "Carnas, Arial", "font-size": 30, "font-weight": 700, fill: P.ink, "letter-spacing": -1 }, it.value));
      if (it.target) svg.appendChild(el("text", { x: x + 22, y: y + 80, "font-size": 11, fill: P.ink600 }, "Target " + it.target));
      if (it.note) svg.appendChild(el("text", { x: x + 22, y: y + 96, "font-size": 11, "font-weight": 700, fill: bar }, it.note));
    });
  };

  TYPES.deltaDot = function (d) {
    // dot above each label moves up/down vs zero, sized by magnitude
    var W = 640, H = 280, L = 30, R = 20, T = 30, B = 60;
    var data = d.data; // {label, value}
    var max = Math.max.apply(null, data.map(function (r) { return Math.abs(r.value); }));
    var step = (W - L - R) / data.length;
    var midY = (T + (H - B)) / 2;
    var svg = makeSvg(W, H);
    svg.appendChild(el("line", { x1: L, y1: midY, x2: W - R, y2: midY, stroke: P.ink, "stroke-width": 1 }));
    data.forEach(function (r, i) {
      var x = L + step * i + step / 2;
      var y = midY - (r.value / max) * (H - T - B) / 2;
      var rad = 6 + (Math.abs(r.value) / max) * 16;
      svg.appendChild(el("line", { x1: x, y1: midY, x2: x, y2: y, stroke: P.ink300, "stroke-width": 1 }));
      svg.appendChild(el("circle", { cx: x, cy: y, r: rad, fill: r.value >= 0 ? P.lime : P.ink, stroke: P.ink, "stroke-width": 1 }));
      svg.appendChild(el("text", { x: x, y: y + 4, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: r.value >= 0 ? P.ink : P.lime }, fmt(r.value, d)));
      svg.appendChild(el("text", { x: x, y: H - B + 18, "text-anchor": "middle", "font-size": 10, fill: P.ink600 }, r.label));
    });
  };

  TYPES.swimLane = function (d) {
    // grouped horizontal bars by lane (e.g. workstreams)
    var W = 640, L = 130, R = 30;
    var lanes = d.lanes; // {label, items:[{label, start, end, color?}]}
    var laneH = 70;
    var H = 30 + lanes.length * laneH + 20;
    var min = Math.min.apply(null, lanes.reduce(function (a, l) { return a.concat(l.items.map(function (it) { return it.start; })); }, []));
    var max = Math.max.apply(null, lanes.reduce(function (a, l) { return a.concat(l.items.map(function (it) { return it.end; })); }, []));
    var svg = makeSvg(W, H);
    var sx = function (v) { return L + (v - min) / (max - min) * (W - L - R); };
    [0, 0.25, 0.5, 0.75, 1].forEach(function (t) {
      var x = L + t * (W - L - R);
      svg.appendChild(el("line", { class: "gridline", x1: x, y1: 20, x2: x, y2: H - 20 }));
      svg.appendChild(el("text", { class: "tick", x: x, y: H - 6, "text-anchor": "middle" }, (d.timeLabels || [])[Math.round(t * 4)] || (min + t * (max - min)).toFixed(0)));
    });
    lanes.forEach(function (lane, li) {
      var y0 = 20 + li * laneH;
      svg.appendChild(el("rect", { x: 6, y: y0, width: L - 12, height: laneH - 6, fill: P.ink050, stroke: P.ink200 }));
      svg.appendChild(el("text", { x: L - 14, y: y0 + laneH / 2 + 4, "text-anchor": "end", "font-size": 11, "font-weight": 700, fill: P.ink }, lane.label));
      lane.items.forEach(function (it, ii) {
        var y = y0 + 8 + ii * 18;
        svg.appendChild(el("rect", { x: sx(it.start), y: y, width: sx(it.end) - sx(it.start), height: 14, fill: it.color || P.lime, stroke: P.ink, "stroke-width": 1 }));
        svg.appendChild(el("text", { x: sx(it.start) + 6, y: y + 11, "font-size": 9, "font-weight": 700, fill: P.ink }, it.label));
      });
    });
  };

  TYPES.calloutNumber = function (d) {
    // Big editorial number with caption + side note
    var W = 640, H = 220;
    var svg = makeSvg(W, H);
    svg.appendChild(el("rect", { x: 0, y: 0, width: W, height: H, fill: P.lime }));
    svg.appendChild(el("text", { x: 40, y: 50, "font-size": 11, "font-weight": 700, fill: P.ink, "letter-spacing": 1.6 }, (d.eyebrowText || "").toUpperCase()));
    svg.appendChild(el("text", { x: 40, y: 150, "font-family": "Carnas, Arial", "font-size": 110, "font-weight": 700, fill: P.ink, "letter-spacing": -3 }, d.value));
    if (d.unit) svg.appendChild(el("text", { x: 40 + (String(d.value).length * 60), y: 150, "font-family": "Carnas, Arial", "font-size": 30, "font-weight": 700, fill: P.ink }, d.unit));
    if (d.caption) svg.appendChild(el("text", { x: 40, y: 190, "font-size": 14, "font-weight": 700, fill: P.ink }, d.caption));
    if (d.note) svg.appendChild(el("text", { x: W - 40, y: 50, "text-anchor": "end", "font-size": 12, fill: P.ink }, d.note));
  };

  TYPES.competitorMap = function (d) {
    // 2x2 with logos / company labels positioned, with optional axis titles
    var W = 640, H = 320, L = 50, R = 30, T = 30, B = 50;
    var data = d.data; // {label, x, y, highlight?}
    var svg = makeSvg(W, H);
    svg.appendChild(el("rect", { x: L, y: T, width: W - L - R, height: H - T - B, fill: P.white, stroke: P.ink200 }));
    var midX = (L + W - R) / 2, midY = (T + H - B) / 2;
    svg.appendChild(el("line", { x1: midX, y1: T, x2: midX, y2: H - B, stroke: P.ink300, "stroke-dasharray": "4 3" }));
    svg.appendChild(el("line", { x1: L, y1: midY, x2: W - R, y2: midY, stroke: P.ink300, "stroke-dasharray": "4 3" }));
    var sx = function (v) { return L + v * (W - L - R); };
    var sy = function (v) { return H - B - v * (H - T - B); };
    data.forEach(function (r) {
      var hl = r.highlight;
      svg.appendChild(el("rect", { x: sx(r.x) - 40, y: sy(r.y) - 14, width: 80, height: 28, fill: hl ? P.lime : P.white, stroke: P.ink, "stroke-width": hl ? 2 : 1 }));
      svg.appendChild(el("text", { x: sx(r.x), y: sy(r.y) + 4, "text-anchor": "middle", "font-size": 11, "font-weight": 700, fill: P.ink }, r.label));
    });
    if (d.xLow) svg.appendChild(el("text", { x: L + 8, y: H - B + 18, "font-size": 10, "font-weight": 700, fill: P.ink600 }, d.xLow));
    if (d.xHigh) svg.appendChild(el("text", { x: W - R - 8, y: H - B + 18, "text-anchor": "end", "font-size": 10, "font-weight": 700, fill: P.ink600 }, d.xHigh));
    if (d.yLow) svg.appendChild(el("text", { x: L - 8, y: H - B - 4, "text-anchor": "end", "font-size": 10, "font-weight": 700, fill: P.ink600, transform: "rotate(-90 " + (L - 8) + " " + (H - B - 4) + ")" }, d.yLow));
    if (d.yHigh) svg.appendChild(el("text", { x: L - 8, y: T + 60, "text-anchor": "end", "font-size": 10, "font-weight": 700, fill: P.ink600, transform: "rotate(-90 " + (L - 8) + " " + (T + 60) + ")" }, d.yHigh));
    if (d.xLabel) svg.appendChild(el("text", { x: midX, y: H - 12, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink, "letter-spacing": "0.08em" }, d.xLabel.toUpperCase()));
    if (d.yLabel) svg.appendChild(el("text", { x: 18, y: midY, "text-anchor": "middle", "font-size": 10, "font-weight": 700, fill: P.ink, "letter-spacing": "0.08em", transform: "rotate(-90 18 " + midY + ")" }, d.yLabel.toUpperCase()));
  };

  // ---- public API ------------------------------------------------------
  function render() {
    var script = document.getElementById("chart-data");
    if (!script) return;
    var d = JSON.parse(script.textContent);
    header(d);
    var fn = TYPES[d.type];
    if (!fn) {
      var host = document.getElementById("chart-host");
      var err = document.createElement("div");
      err.style.color = "#c9221c";
      err.textContent = 'Unknown chart type: "' + d.type + '"';
      host.appendChild(err);
      return;
    }
    fn(d);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", render);
  else render();

  window.BTChart = { render: render, types: TYPES, palette: P };
})();
