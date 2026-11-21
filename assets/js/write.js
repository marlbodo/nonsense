// 글쓰기: 글 등록 → (선택) 이미지 업로드 → 상세 화면 이동
(function () {
  const { h, api } = NS;
  const $ = (id) => document.getElementById(id);
  const form = $("write-form"), msg = $("form-msg"), btn = $("submit");

  NS.renderHeader("", { back: true });
  // 답글 쓰기: write.html?reply_to=<글 id>
  const rid = new URLSearchParams(location.search).get("reply_to") || "";
  const replyTo = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(rid) ? rid.toLowerCase() : null;
  if (replyTo) {
    document.querySelector("h1").textContent = "답글 쓰기";
    document.title = "답글 쓰기 - 헛소리 대마왕";
    const box = h("div", { class: "reply-ctx", text: "원글을 불러오는 중…" });
    form.before(box);
    btn.disabled = true;
    api("/posts/" + replyTo).then((d) => {
      if (d.post.status !== "visible") throw { code: "post_not_available" };
      box.replaceChildren(h("span", { class: "muted", text: "답글 대상 " }), h("strong", { text: d.post.title }), h("span", { class: "muted", text: " · " + d.post.nickname }));
      btn.disabled = false;
    }).catch((e) => { box.className = "form-msg error"; box.textContent = NS.errMsg(e); });
  }
  NS.track(null);
  $("nickname").value = NS.store.get("nv_nick") || "";
  $("body").addEventListener("input", () => { $("body-count").textContent = $("body").value.length + " / 10000"; });

  function showMsg(text, isError, link) {
    msg.hidden = false;
    msg.className = "form-msg" + (isError ? " error" : "");
    msg.replaceChildren(text, link ? h("div", {}, link) : null);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const nickname = $("nickname").value.trim(), password = $("password").value;
    const title = $("title").value.trim(), body = $("body").value.trim();
    const file = $("file").files[0] || null;
    if (!nickname) return showMsg("별명을 입력해 주세요.", true);
    if (password.length < 4) return showMsg(NS.errMsg({ code: "invalid_password" }), true);
    if (!title) return showMsg("제목을 입력해 주세요.", true);
    if (!body) return showMsg("내용을 입력해 주세요.", true);
    const imgErr = NS.checkImage(file);
    if (imgErr) return showMsg(NS.errMsg({ code: imgErr }), true);

    btn.disabled = true;
    btn.textContent = "등록 중…";
    msg.hidden = true;
    let postId;
    try {
      postId = (await api("/posts", { json: { nickname, title, body, password, reply_to_id: replyTo } })).id;
    } catch (err) {
      showMsg(NS.errMsg(err), true);
      btn.disabled = false;
      btn.textContent = "등록";
      return;
    }
    NS.store.set("nv_nick", nickname);
    const go = "post.html?id=" + encodeURIComponent(postId);
    if (file) {
      try {
        await NS.uploadImage(postId, password, file);
      } catch (err) {
        showMsg("글은 등록되었지만 이미지를 올리지 못했습니다: " + NS.errMsg(err), true,
          h("a", { href: go, text: "등록된 글 보기 →" }));
        btn.textContent = "등록됨";
        return;
      }
    }
    location.href = go;
  });
})();
