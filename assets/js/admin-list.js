// 관리자 전용 목록: 신고 접수 / 신고된 글 / 숨김 글 / 삭제 글
// 접근 권한은 서버(/admin/*)가 검증한다. 이 파일은 화면만 그린다.
(function () {
  if (!NS.isAdmin()) return;
  const params = new URLSearchParams(location.search);
  const v = params.get("v");
  if (!["reports", "reported", "hidden", "deleted"].includes(v)) return;
  const { h, api, icon } = NS;

  const page = Math.max(1, Math.min(10000, parseInt(params.get("page") || "1", 10) || 1));
  const status = ["pending", "resolved", "dismissed"].includes(params.get("s")) ? params.get("s") : "pending";
  const listEl = document.getElementById("post-list");
  const pagerEl = document.getElementById("pager");
  const infoEl = document.getElementById("result-info");
  document.querySelector(".toolbar").hidden = true;
  document.querySelector(".bar").hidden = true;

  const href = (n) => {
    const p = new URLSearchParams({ v });
    if (v === "reports" && status !== "pending") p.set("s", status);
    if (n > 1) p.set("page", String(n));
    return "index.html?" + p.toString();
  };

  const TYPE_LABEL = { post: "글", comment: "댓글", image: "이미지" };
  const TITLES = { reports: "신고 접수", reported: "신고된 글", hidden: "숨김 처리된 글", deleted: "삭제된 글" };

  function expired() {
    NS.toast("관리자 세션이 만료되었습니다. 다시 로그인해 주세요.");
    setTimeout(() => { location.href = "admin/index.html"; }, 1200);
  }

  function statusTabs() {
    const tabs = [["pending", "접수됨"], ["resolved", "처리됨"], ["dismissed", "기각됨"]];
    return h("nav", { class: "tabs", "aria-label": "신고 상태" }, tabs.map(([k, label]) => {
      const p = new URLSearchParams({ v: "reports" });
      if (k !== "pending") p.set("s", k);
      return h("a", { href: "index.html?" + p.toString(), "aria-current": k === status ? "page" : null, text: label });
    }));
  }

  function postItem(p) {
    const badges = [];
    if (p.is_deleted) badges.push(p.deleted_by === "admin" ? "삭제됨(관리자)" : "삭제됨(작성자)");
    if (p.is_hidden) badges.push("숨김");
    return h("li", { class: "post-item" },
      h("a", { href: "post.html?id=" + encodeURIComponent(p.id) },
        h("div", { class: "row1" },
          h("span", { class: "title", text: p.title }),
          p.has_image ? h("span", { class: "muted", "aria-label": "이미지 첨부" }, icon("image", 16)) : null),
        h("div", { class: "meta" },
          badges.map((b) => h("span", { class: "badge", text: b })),
          h("span", { text: p.nickname }),
          h("span", { text: NS.fmtDate(p.created_at, true) }),
          h("span", { class: "stat", title: "추천" }, icon("thumbs-up", 14), String(p.up_count)),
          h("span", { class: "stat", title: "비추천" }, icon("thumbs-down", 14), String(p.down_count)),
          h("span", { class: "stat", title: "댓글" }, icon("message-circle", 14), String(p.comment_count)))));
  }

  async function resolve(r, to, li) {
    try {
      await api(`/admin/reports/${r.id}/resolve`, { json: { status: to }, admin: true });
      NS.toast(to === "resolved" ? "처리 완료로 표시했습니다." : "기각했습니다.");
      li.remove();
    } catch (e) { if (e.status === 401) expired(); else NS.toast(NS.errMsg(e)); }
  }

  function reportItem(r) {
    const li = h("li", { class: "post-item report" });
    const target = r.post_id
      ? "post.html?id=" + encodeURIComponent(r.post_id) + (r.target_type === "comment" ? "#c-" + r.target_id : "")
      : null;
    li.append(
      h("div", { class: "meta" },
        h("span", { class: "badge", text: TYPE_LABEL[r.target_type] || r.target_type }),
        h("strong", { text: NS.REASON_LABEL[r.reason] || r.reason }),
        h("span", { text: NS.fmtDate(r.created_at, true) })),
      h("p", { class: "preview", text: r.target_preview || "(대상을 찾을 수 없음 — 영구 삭제되었을 수 있습니다)" }),
      r.detail ? h("p", { class: "muted", text: "신고 내용: " + r.detail }) : null,
      h("div", { class: "actions start" },
        target ? h("a", { class: "btn small", href: target, text: "대상 보기" }) : null,
        r.status === "pending" ? [
          h("button", { type: "button", class: "btn small primary", text: "처리 완료", onclick: () => resolve(r, "resolved", li) }),
          h("button", { type: "button", class: "btn small", text: "기각", onclick: () => resolve(r, "dismissed", li) }),
        ] : h("span", { class: "muted", text: r.status === "resolved" ? "처리됨" : "기각됨" })));
    return li;
  }

  async function load() {
    listEl.replaceChildren(h("li", { class: "notice", text: "불러오는 중…" }));
    try {
      let d;
      if (v === "reports") d = await api(`/admin/reports?status=${status}&page=${page}`, { admin: true });
      else d = await api(`/admin/posts?filter=${v}&page=${page}`, { admin: true });
      const rows = v === "reports" ? d.reports : d.posts;
      infoEl.hidden = false;
      infoEl.replaceChildren(TITLES[v] + " " + d.total + "건");
      listEl.replaceChildren();
      if (!rows.length) {
        listEl.append(h("li", { class: "notice", text: "해당하는 항목이 없습니다." }));
        pagerEl.replaceChildren();
        return;
      }
      listEl.append(...rows.map(v === "reports" ? reportItem : postItem));
      NS.pager(pagerEl, d.page, d.total, d.page_size, href);
    } catch (e) {
      if (e.status === 401) return expired();
      listEl.replaceChildren(h("li", {}, NS.errorBox(e, load)));
    }
  }

  if (v === "reports") infoEl.before(h("div", { class: "bar" }, statusTabs()));
  load();
})();
