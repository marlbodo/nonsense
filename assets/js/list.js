// 메인 게시판: 최신/인기 정렬, 검색, 페이지 이동, 연속 번호
(function () {
  const { h, api, icon } = NS;
  const params = new URLSearchParams(location.search);
  const q = (params.get("q") || "").trim().slice(0, 50);
  const sort = params.get("sort") === "popular" ? "popular" : "latest";
  const page = Math.max(1, Math.min(10000, parseInt(params.get("page") || "1", 10) || 1));

  const listEl = document.getElementById("post-list");
  const pagerEl = document.getElementById("pager");
  const infoEl = document.getElementById("result-info");

  function href(o) {
    const p = new URLSearchParams();
    const nq = "q" in o ? o.q : q;
    const ns = "sort" in o ? o.sort : sort;
    const np = "page" in o ? o.page : 1;
    if (nq) p.set("q", nq);
    if (ns === "popular") p.set("sort", "popular");
    if (np > 1) p.set("page", String(np));
    const s = p.toString();
    return "index.html" + (s ? "?" + s : "");
  }

  function setup() {
    NS.renderHeader("");
    document.getElementById("q").value = q;
    document.getElementById("search-btn").append(icon("search", 18));
    const sortInput = document.getElementById("search-form");
    if (sort === "popular") sortInput.prepend(h("input", { type: "hidden", name: "sort", value: "popular" }));
    const tl = document.getElementById("tab-latest"), tp = document.getElementById("tab-popular");
    tl.href = href({ sort: "latest" });
    tp.href = href({ sort: "popular" });
    (sort === "popular" ? tp : tl).setAttribute("aria-current", "page");
    document.getElementById("write-btn").prepend(icon("plus", 16));
  }

  // 목록 한 줄. 원글은 번호, 답글은 번호 없이 한 번만 들여쓰고(모든 깊이 같은 위치) "@대상"을 표시한다.
  // 검색 결과에서는 평평하게 보여 주고 답글에는 @대상만 붙인다.
  function item(p, flat) {
    const isReply = p.reply_depth > 0;
    const href = "post.html?id=" + encodeURIComponent(p.id);
    if (p.placeholder) {
      return h("li", { class: "post-item gone" },
        h("a", { href },
          h("div", { class: "row1" },
            h("span", { class: "no", text: String(p.display_no) }),
            h("span", { class: "title muted", text: p.placeholder === "deleted" ? "삭제된 글입니다." : "관리자에 의해 숨김 처리된 글입니다." })),
          p.reply_count ? h("div", { class: "meta" }, h("span", { class: "stat", title: "답글" }, icon("corner-down-right", 14), String(p.reply_count))) : null));
    }
    const to = isReply ? h("span", { class: "to" }, icon("corner-down-right", 13), " @" + (p.reply_to_nickname || "삭제된 글")) : null;
    return h("li", { class: "post-item" + (isReply && !flat ? " reply" : "") },
      h("a", { href },
        h("div", { class: "row1" },
          isReply ? null : h("span", { class: "no", text: String(p.display_no) }),
          h("span", { class: "title", text: p.title }),
          p.has_image ? h("span", { class: "muted", title: "이미지 첨부", "aria-label": "이미지 첨부" }, icon("image", 16)) : null),
        h("p", { class: "preview", text: (p.preview || "").replace(/\s+/g, " ").trim() }),
        h("div", { class: "meta" },
          to,
          h("span", { text: p.nickname }),
          h("span", { text: NS.fmtDate(p.created_at) }),
          h("span", { class: "stat", title: "추천" }, icon("thumbs-up", 14), String(p.up_count)),
          h("span", { class: "stat", title: "비추천" }, icon("thumbs-down", 14), String(p.down_count)),
          h("span", { class: "stat", title: "댓글" }, icon("message-circle", 14), String(p.comment_count)),
          !isReply && p.reply_count ? h("span", { class: "stat", title: "답글" }, icon("corner-down-right", 14), String(p.reply_count)) : null)));
  }

  // 원글 아래에 붙은 답글들. 한 원글에서 목록에 보이는 답글은 최대 30개이고 나머지는 원글에서 본다.
  function rows(posts) {
    if (q) return posts.map((p) => item(p, true));
    const out = [];
    let cur = null;
    const flush = () => {
      if (cur && cur.reply_count > 30) {
        out.push(h("li", { class: "post-item reply more" },
          h("a", { href: "post.html?id=" + encodeURIComponent(cur.id), text: `답글 ${cur.reply_count - 30}개 더 보기` })));
      }
    };
    for (const p of posts) {
      if (p.reply_depth === 0) { flush(); cur = p; }
      out.push(item(p, false));
    }
    flush();
    return out;
  }

  function pager(total, size) {
    const pages = Math.ceil(total / size);
    pagerEl.replaceChildren();
    if (pages <= 1) return;
    const link = (n, label, cur) => cur
      ? h("span", { "aria-current": "page", text: String(label ?? n) })
      : h("a", { href: href({ page: n }), text: String(label ?? n) });
    const out = [];
    if (page > 1) out.push(link(page - 1, "이전"));
    const start = Math.max(1, Math.min(page - 2, pages - 4));
    const end = Math.min(pages, start + 4);
    if (start > 1) { out.push(link(1)); if (start > 2) out.push(h("span", { class: "gap", text: "…" })); }
    for (let n = start; n <= end; n++) out.push(link(n, n, n === page));
    if (end < pages) { if (end < pages - 1) out.push(h("span", { class: "gap", text: "…" })); out.push(link(pages)); }
    if (page < pages) out.push(link(page + 1, "다음"));
    pagerEl.append(...out);
  }

  async function load() {
    listEl.replaceChildren(h("li", { class: "notice", text: "불러오는 중…" }));
    try {
      const d = await api("/posts?" + new URLSearchParams({ sort, q, page: String(page) }).toString());
      listEl.replaceChildren();
      if (q) { infoEl.hidden = false; infoEl.textContent = `'${q}' 검색 결과 ${d.total}건`; }
      if (!d.posts.length) {
        const empty = q ? "검색 결과가 없습니다." : page > 1 ? "이 페이지에는 글이 없습니다." : "아직 글이 없습니다. 첫 글을 써보세요.";
        listEl.append(h("li", { class: "notice" }, empty, page > 1 ? h("div", {}, h("a", { class: "btn", href: href({ page: 1 }), text: "첫 페이지로" })) : null));
        pagerEl.replaceChildren();
        return;
      }
      listEl.append(...rows(d.posts));
      pager(d.total, d.page_size);
    } catch (e) {
      listEl.replaceChildren(h("li", {}, NS.errorBox(e, load)));
      pagerEl.replaceChildren();
    }
  }

  // 관리자가 ?v=... 필터를 열면 admin-list.js 가 화면을 맡는다
  if (NS.isAdmin() && params.get("v")) {
    NS.renderHeader("");
  } else {
    setup();
    NS.track(null);
    load();
  }
})();
