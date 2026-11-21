// 관리자 로그인: 비밀번호만 입력. 검증은 서버에서만 이뤄지고, 토큰은 탭을 닫으면 사라진다.
(function () {
  const { api } = NS;
  const form = document.getElementById("login-form");
  const msg = document.getElementById("form-msg");
  const btn = document.getElementById("login-btn");

  NS.renderHeader("../");
  if (NS.isAdmin()) {
    api("/admin/me", { admin: true }).then(() => location.replace("../index.html")).catch(() => {});
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    btn.disabled = true;
    msg.hidden = true;
    try {
      const r = await api("/admin/login", { json: { password: document.getElementById("password").value } });
      NS.setAdmin(r.token, r.expires_at);
      location.href = "../index.html";
    } catch (err) {
      msg.hidden = false;
      msg.textContent = err.code === "wrong_password" ? "비밀번호가 올바르지 않습니다." : NS.errMsg(err);
      btn.disabled = false;
      document.getElementById("password").value = "";
    }
  });
})();
