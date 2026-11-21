// 관리자 방문 통계. 데이터는 /admin/stats (서버가 관리자 세션 검증). 개인별 정보는 존재하지 않는 집계 값만 다룬다.
// 차트: SVG 직접 생성. 모든 텍스트는 textContent 로만 삽입한다.
(function () {
  "use strict";
  const { h, api, icon } = NS;
  if (!NS.isAdmin()) { location.replace("index.html"); return; }
  NS.renderHeader("../");

  const SVGNS = "http://www.w3.org/2000/svg";
  const S = (tag, attrs, ...kids) => {
    const el = document.createElementNS(SVGNS, tag);
    for (const [k, v] of Object.entries(attrs || {})) if (v != null) el.setAttribute(k, String(v));
    for (const kid of kids) if (kid != null) el.append(typeof kid === "string" ? document.createTextNode(kid) : kid);
    return el;
  };
  const DOW = ["일", "월", "화", "수", "목", "금", "토"];
  const fmt = (n) => Number(n || 0).toLocaleString("ko-KR");
  const fmtTick = (v) => (v >= 10000 ? (v / 1000).toLocaleString("ko-KR") + "K" : v.toLocaleString("ko-KR"));
  const d10 = (s) => String(s).slice(0, 10);
  const md = (s) => { const [, m, d] = d10(s).split("-"); return `${+m}.${+d}`; };
  const ymd = (s) => d10(s).replace(/-/g, ".");
  const dowOf = (s) => DOW[new Date(d10(s) + "T00:00:00Z").getUTCDay()];
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  const content = document.getElementById("content");
  const rangeRow = document.getElementById("range-row");
  const RANGES = [["today", "오늘"], ["7", "최근 7일"], ["30", "최근 30일"], ["all", "전체"]];
  let range = "30";
  let observers = [];

  // ---------- 눈금 ----------
  function niceTicks(max) {
    const raw = Math.max(max, 1) / 4;
    const pow = Math.pow(10, Math.floor(Math.log10(raw)));
    const f = raw / pow;
    const step = Math.max(1, (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * pow);
    const top = Math.ceil(max / step) * step || step;
    const ticks = [];
    for (let v = 0; v <= top + 1e-9; v += step) ticks.push(v);
    return { max: top, ticks };
  }

  // ---------- 차트 ----------
  // spec: { title, sub, kind: 'line'|'bar', labels[], fullLabels[], series: [{ name, slot, values[] }], height?, emptyText? }
  function createChart(spec) {
    const n = spec.labels.length;
    const card = h("section", { class: "viz-card" });
    const plot = h("div", { class: "plot" });
    const tip = h("div", { class: "viz-tip", hidden: true });
    const tableWrap = h("div", { class: "tablewrap", hidden: true });
    const toggle = h("button", { type: "button", class: "btn text small", "aria-pressed": "false", text: "표로 보기" });
    const legend = spec.series.length > 1
      ? h("ul", { class: "legend" }, spec.series.map((s) => h("li", {}, h("span", { class: `key ${spec.kind === "bar" ? "box" : "line"} k${s.slot}` }), s.name)))
      : null;
    const tooSmall = n === 0 || (spec.kind === "line" && n < 2);
    card.append(
      h("div", { class: "viz-head" },
        h("div", {}, h("h3", { text: spec.title }), spec.sub ? h("p", { class: "muted small", text: spec.sub }) : null),
        tooSmall ? null : toggle),
      ...(legend ? [legend] : []), plot, tableWrap);

    if (tooSmall) {
      plot.append(h("p", { class: "muted empty", text: spec.emptyText || "표시할 데이터가 아직 없습니다. (기간을 늘려 보세요)" }));
      return { el: card };
    }

    // 표 보기 (모든 값은 툴팁·그래프 없이도 읽을 수 있다)
    const table = h("table", { class: "vt" },
      h("caption", { class: "sr-only", text: spec.title }),
      h("thead", {}, h("tr", {}, h("th", { scope: "col", text: spec.xName || "구분" }), spec.series.map((s) => h("th", { scope: "col", text: s.name })))),
      h("tbody", {}, spec.labels.map((_, i) => h("tr", {}, h("th", { scope: "row", text: spec.fullLabels[i] }), spec.series.map((s) => h("td", { text: fmt(s.values[i]) }))))));
    tableWrap.append(table);
    toggle.addEventListener("click", () => {
      const showTable = tableWrap.hidden;
      tableWrap.hidden = !showTable;
      plot.hidden = showTable;
      toggle.textContent = showTable ? "그래프로 보기" : "표로 보기";
      toggle.setAttribute("aria-pressed", String(showTable));
    });

    let lastW = 0;
    function draw() {
      const W = Math.floor(plot.clientWidth);
      if (!W) return;
      lastW = W;
      const H = spec.height || 190, L = 38, R = 16, T = 10, B = 24;
      const pw = W - L - R, ph = H - T - B;
      const all = spec.series.flatMap((s) => s.values);
      const { max: yMax, ticks } = niceTicks(Math.max(0, ...all));
      const isBar = spec.kind === "bar";
      const band = pw / n;
      const stepX = n === 1 ? 1 : pw / (n - 1);
      const xAt = isBar ? (i) => L + band * (i + 0.5) : (i) => L + (n === 1 ? pw / 2 : stepX * i);
      const yAt = (v) => T + ph - (v / yMax) * ph;

      const svg = S("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, class: "chart", tabindex: 0, role: "img", "aria-label": `${spec.title}. 좌우 방향키로 값을 확인할 수 있고, '표로 보기'로 전체 값을 볼 수 있습니다.` });
      for (const v of ticks) {
        const y = yAt(v);
        svg.append(S("line", { x1: L, x2: W - R, y1: y, y2: y, class: v === 0 ? "axis" : "grid" }), S("text", { x: L - 6, y: y + 4, "text-anchor": "end", class: "tick" }, fmtTick(v)));
      }
      const every = Math.max(1, Math.ceil((isBar ? 40 : 54) / (isBar ? band : stepX)));
      for (let i = 0; i < n; i++) {
        if ((n - 1 - i) % every !== 0) continue;
        svg.append(S("text", { x: xAt(i), y: H - 6, "text-anchor": "middle", class: "tick" }, spec.labels[i]));
      }

      const bars = [];
      let dots = [];
      if (isBar) {
        const s = spec.series[0];
        const bw = Math.max(2, Math.min(24, band - 2));
        const base = yAt(0);
        s.values.forEach((v, i) => {
          if (v <= 0) { bars.push(null); return; }
          const x = xAt(i) - bw / 2, y = yAt(v), hgt = base - y, r = Math.min(4, bw / 2, hgt);
          const p = S("path", { d: `M${x},${base} V${y + r} a${r},${r} 0 0 1 ${r},${-r} H${x + bw - r} a${r},${r} 0 0 1 ${r},${r} V${base} Z`, class: `bar f${s.slot}` });
          bars.push(p);
          svg.append(p);
        });
        const mx = Math.max(...s.values);
        if (mx > 0 && n > 1) {
          const mi = s.values.indexOf(mx);
          svg.append(S("text", { x: xAt(mi), y: yAt(mx) - 5, "text-anchor": "middle", class: "lbl" }, fmt(mx)));
        }
      } else {
        for (const s of spec.series) {
          const pts = s.values.map((v, i) => `${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`);
          svg.append(S("path", { d: "M" + pts.join("L"), class: `line l${s.slot}` }));
          svg.append(S("circle", { cx: xAt(n - 1), cy: yAt(s.values[n - 1]), r: 4, class: `dot ring f${s.slot}` }));
        }
      }
      const xhair = S("line", { y1: T, y2: T + ph, class: "xhair", visibility: "hidden" });
      svg.append(xhair);
      if (!isBar) {
        dots = spec.series.map((s) => S("circle", { r: 4, class: `dot ring f${s.slot}`, visibility: "hidden" }));
        svg.append(...dots);
      }
      const hit = S("rect", { x: L, y: T, width: pw, height: ph + B, fill: "transparent" });
      svg.append(hit);

      let cur = null;
      function hide() {
        cur = null;
        tip.hidden = true;
        xhair.setAttribute("visibility", "hidden");
        dots.forEach((d) => d.setAttribute("visibility", "hidden"));
        bars.forEach((b) => b && b.classList.remove("hot"));
      }
      function show(i) {
        cur = i;
        const x = xAt(i);
        if (isBar) {
          bars.forEach((b, j) => b && b.classList.toggle("hot", j === i));
        } else {
          xhair.setAttribute("x1", x); xhair.setAttribute("x2", x); xhair.setAttribute("visibility", "visible");
          dots.forEach((d, k) => { d.setAttribute("cx", x); d.setAttribute("cy", yAt(spec.series[k].values[i])); d.setAttribute("visibility", "visible"); });
        }
        tip.replaceChildren(
          h("div", { class: "tip-h", text: spec.fullLabels[i] }),
          ...spec.series.map((s) => h("div", { class: "tip-r" },
            h("span", { class: `key line k${s.slot}` }), h("strong", { text: fmt(s.values[i]) }), h("span", { class: "muted", text: s.name }))));
        tip.hidden = false;
        const tw = tip.offsetWidth;
        tip.style.left = clamp(x - tw / 2, 0, Math.max(0, W - tw)) + "px";
      }
      const idxAt = (ev) => {
        const x = ev.clientX - svg.getBoundingClientRect().left;
        return clamp(isBar ? Math.floor((x - L) / band) : Math.round((x - L) / stepX), 0, n - 1);
      };
      svg.addEventListener("pointermove", (ev) => show(idxAt(ev)));
      svg.addEventListener("pointerdown", (ev) => show(idxAt(ev)));
      svg.addEventListener("pointerleave", () => { if (document.activeElement !== svg) hide(); });
      svg.addEventListener("focus", () => show(cur == null ? n - 1 : cur));
      svg.addEventListener("blur", hide);
      svg.addEventListener("keydown", (ev) => {
        const k = ev.key;
        if (k === "ArrowLeft") show(clamp((cur ?? n) - 1, 0, n - 1));
        else if (k === "ArrowRight") show(clamp((cur ?? -1) + 1, 0, n - 1));
        else if (k === "Home") show(0);
        else if (k === "End") show(n - 1);
        else if (k === "Escape") hide();
        else return;
        ev.preventDefault();
      });
      plot.replaceChildren(svg, tip);
    }

    const ro = new ResizeObserver(() => { if (Math.abs(plot.clientWidth - lastW) >= 1) draw(); });
    ro.observe(plot);
    observers.push(ro);
    return { el: card };
  }

  // ---------- 순위 막대 (유입 경로, 조회 순위) ----------
  function rankedBars(items, unit) {
    if (!items.length) return h("p", { class: "muted", text: "아직 데이터가 없습니다." });
    const max = Math.max(1, ...items.map((i) => i.value));
    return h("ol", { class: "ranked" }, items.map((it) => {
      const fill = h("div", { class: "r-fill" });
      fill.style.width = (it.value / max) * 100 + "%";
      return h("li", {},
        h("div", { class: "r-top" }, it.href ? h("a", { href: it.href, text: it.label }) : h("span", { text: it.label }), h("strong", { text: fmt(it.value) + unit })),
        h("div", { class: "r-track" }, fill));
    }));
  }

  // ---------- 증감·판정 ----------
  function delta(cur, prev) {
    if (!cur && !prev) return { dir: "flat", text: "변화 없음", pct: 0 };
    if (!prev) return { dir: "up", text: "신규", pct: Infinity };
    const pct = ((cur - prev) / prev) * 100;
    const dir = Math.abs(pct) < 1 ? "flat" : pct > 0 ? "up" : "down";
    return { dir, text: (pct > 0 ? "+" : "") + pct.toFixed(1) + "%", pct };
  }
  const DIR_ICON = { up: "trending-up", down: "trending-down", flat: "minus" };
  const deltaChip = (dl) => h("span", { class: `delta ${dl.dir}` }, icon(DIR_ICON[dl.dir], 16), dl.text);
  function verdict(label, cur, prev) {
    if (!cur && !prev) return h("span", { class: "verdict none" }, icon("minus", 18), `${label} 데이터 부족`);
    const dl = delta(cur, prev);
    const key = dl.pct >= 10 ? "up" : dl.pct <= -10 ? "down" : "flat";
    const word = { up: "성장", down: "감소", flat: "정체" }[key];
    return h("span", { class: `verdict ${key}` }, icon(DIR_ICON[key], 18), `${label} ${word}`, h("span", { class: "muted", text: dl.text }));
  }
  function growthRow(label, cur, prev) {
    return h("li", { class: "g-row" },
      h("div", { class: "g-label", text: label }),
      h("div", { class: "g-vals" }, h("span", { class: "muted", text: `이전 ${fmt(prev)} → 현재 ` }), h("strong", { text: fmt(cur) })),
      deltaChip(delta(cur, prev)));
  }

  const tile = (label, value) => h("div", { class: "tile" }, h("div", { class: "t-label", text: label }), h("div", { class: "t-value", text: fmt(value) }));

  // ---------- 화면 ----------
  function render(d) {
    observers.forEach((o) => o.disconnect());
    observers = [];
    const c = d.cards, g = d.growth, ct = d.content;
    const daily = d.daily || [];
    const dLabels = daily.map((r) => md(r.date));
    const dFull = daily.map((r) => `${ymd(r.date)} (${dowOf(r.date)})`);
    const dSeries = (defs) => defs.map(([name, slot, key]) => ({ name, slot, values: daily.map((r) => r[key]) }));
    const act = { cur: g.new_posts_28d.current + g.new_comments_28d.current, prev: g.new_posts_28d.previous + g.new_comments_28d.previous };

    const SRC = [["naver", "네이버 검색"], ["google", "구글 검색"], ["other_search", "기타 검색"], ["external", "외부 사이트"], ["direct", "직접 접속 또는 확인 불가"]];
    const refMap = new Map((d.referrers || []).map((r) => [r.source, r.visits]));
    const refs = SRC.map(([k, label]) => ({ label, value: refMap.get(k) || 0 })).sort((a, b) => b.value - a.value);

    const rangeLabel = (RANGES.find((r) => r[0] === range) || [])[1];
    const weekly = d.weekly || [], monthly = d.monthly || [];
    const hourly = d.hourly || [], weekday = d.weekday || [];

    content.replaceChildren(
      h("h2", { text: "핵심 지표" }),
      h("div", { class: "tiles" },
        tile("오늘 방문", c.visits_today), tile("어제 방문", c.visits_yesterday),
        tile("최근 7일 방문", c.visits_7d), tile("최근 30일 방문", c.visits_30d),
        tile("누적 방문", c.visits_total), tile("오늘 페이지뷰", c.pageviews_today),
        tile("누적 페이지뷰", c.pageviews_total)),

      h("h2", { text: "성장·정체·감소" }),
      h("div", { class: "verdicts" }, verdict("방문", g.visits_28d.current, g.visits_28d.previous), verdict("글·댓글 활동", act.cur, act.prev)),
      h("p", { class: "muted small", text: "최근 4주와 이전 4주를 비교해 ±10% 이상 달라지면 성장·감소, 그 안이면 정체로 봅니다. 아직 데이터가 쌓이는 중이면 이전 기간이 0이라 '신규'로 보일 수 있습니다." }),
      h("ul", { class: "g-list" },
        growthRow("방문 · 전주 대비 (최근 7일 / 이전 7일)", g.visits_7d.current, g.visits_7d.previous),
        growthRow("방문 · 전월 대비 (최근 30일 / 이전 30일)", g.visits_30d.current, g.visits_30d.previous),
        growthRow("방문 · 최근 4주 / 이전 4주", g.visits_28d.current, g.visits_28d.previous),
        growthRow("신규 게시글 · 최근 4주 / 이전 4주", g.new_posts_28d.current, g.new_posts_28d.previous),
        growthRow("신규 댓글 · 최근 4주 / 이전 4주", g.new_comments_28d.current, g.new_comments_28d.previous),
        growthRow("검색 유입 · 최근 4주 / 이전 4주", d.search_visits_28d.current, d.search_visits_28d.previous)),

      h("h2", { text: "게시판 활성도" }),
      h("div", { class: "tiles" },
        h("div", { class: "tile" }, h("div", { class: "t-label", text: "게시글당 평균 댓글" }), h("div", { class: "t-value", text: String(ct.avg_comments_per_post) })),
        tile("전체 게시글", ct.posts_total), tile("전체 댓글", ct.comments_total)),

      h("h2", { text: `추이 · ${rangeLabel}` }),
      createChart({ title: "일별 방문·페이지뷰", sub: "단위: 회", kind: "line", xName: "날짜", labels: dLabels, fullLabels: dFull, series: dSeries([["방문", 1, "visits"], ["페이지뷰", 2, "pageviews"]]) }).el,
      createChart({ title: "일별 신규 글·댓글", sub: "단위: 개", kind: "line", xName: "날짜", labels: dLabels, fullLabels: dFull, series: dSeries([["신규 글", 6, "new_posts"], ["신규 댓글", 7, "new_comments"]]) }).el,
      createChart({ title: "일별 추천·비추천", sub: "단위: 회 (취소·변경은 새 투표로 집계)", kind: "line", xName: "날짜", labels: dLabels, fullLabels: dFull, series: dSeries([["추천", 3, "up_votes"], ["비추천", 4, "down_votes"]]) }).el,
      createChart({ title: "주별 방문", sub: "월요일 시작 주 · 단위: 회", kind: "bar", xName: "주", labels: weekly.map((w) => md(w.week_start)), fullLabels: weekly.map((w) => `${ymd(w.week_start)} 주`), series: [{ name: "방문", slot: 1, values: weekly.map((w) => w.visits) }] }).el,
      createChart({ title: "월별 방문", sub: "단위: 회", kind: "bar", xName: "월", labels: monthly.map((m) => d10(m.month_start).slice(2, 7).replace("-", ".")), fullLabels: monthly.map((m) => d10(m.month_start).slice(0, 7).replace("-", ".")), series: [{ name: "방문", slot: 1, values: monthly.map((m) => m.visits) }] }).el,
      createChart({ title: "시간대별 방문", sub: "한국 시간 · 선택 기간 합계", kind: "bar", xName: "시간", labels: hourly.map((x) => `${x.hour}시`), fullLabels: hourly.map((x) => `${x.hour}시 ~ ${x.hour}시 59분`), series: [{ name: "방문", slot: 1, values: hourly.map((x) => x.visits) }] }).el,
      createChart({ title: "요일별 방문", sub: "선택 기간 합계", kind: "bar", xName: "요일", labels: weekday.map((x) => DOW[x.dow]), fullLabels: weekday.map((x) => DOW[x.dow] + "요일"), series: [{ name: "방문", slot: 1, values: weekday.map((x) => x.visits) }] }).el,

      h("h2", { text: `유입 경로 · ${rangeLabel}` }),
      rankedBars(refs, "회"),
      h("h2", { text: `게시글 조회 순위 · ${rangeLabel}` }),
      rankedBars((d.top_posts || []).map((p) => ({ label: p.title, value: p.views, href: "../post.html?id=" + encodeURIComponent(p.post_id) })), "회"),

      h("h2", { text: "측정 기준" }),
      h("ul", { class: "basis" },
        h("li", { text: "방문: 브라우저 탭을 새로 연 세션당 1회입니다. 새로고침·페이지 이동은 방문이 아니라 페이지뷰로만 더해지며, 순방문자 수가 아닙니다." }),
        h("li", { text: "관리자 본인이 로그인한 상태의 방문은 집계하지 않습니다." }),
        h("li", { text: "시간대는 한국 시간(Asia/Seoul)입니다. 주는 월요일부터 시작합니다." }),
        h("li", { text: "방문자 식별번호, IP, 브라우저 지문, 개인별 열람 기록은 저장하지 않고 합계만 저장합니다." }),
        h("li", { text: "유입 경로는 브라우저가 알려준 이전 페이지 주소 기준이며, 알 수 없으면 '직접 접속 또는 확인 불가'로 분류합니다. 검색어와 노출 수는 구글 서치 콘솔·네이버 서치어드바이저에서 확인합니다." })));
  }

  async function load() {
    content.classList.add("loading");
    try {
      render(await api("/admin/stats?range=" + range, { admin: true }));
    } catch (e) {
      if (e.status === 401) { location.replace("index.html"); return; }
      content.replaceChildren(NS.errorBox(e, load));
    }
    content.classList.remove("loading");
  }

  function renderRange() {
    rangeRow.replaceChildren(...RANGES.map(([k, label]) => h("button", {
      type: "button", class: "btn small", "aria-pressed": String(k === range), text: label,
      onclick: () => { if (k !== range) { range = k; renderRange(); load(); } },
    })));
  }

  renderRange();
  load();
})();
