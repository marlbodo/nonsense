import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR = _os.path.abspath(_os.path.join(_HERE, ".."))
OUT_DIR = _os.path.join(_HERE, "out")
CHROME = _os.environ.get("CHROME", "/usr/bin/google-chrome")
import json, re, subprocess, sys, time, os
from playwright.sync_api import sync_playwright

ROOT = ROOT_DIR
OUT = OUT_DIR
os.makedirs(OUT, exist_ok=True)
BASE = "http://localhost:8765"
API = "https://aunukepmqpavuujypfks.supabase.co/functions/v1/api"
P1 = "11111111-1111-4111-8111-111111111111"
P2 = "22222222-2222-4222-8222-222222222222"
P3 = "33333333-3333-4333-8333-333333333333"
NEW = "44444444-4444-4444-8444-444444444444"
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

def c(i, parent, reply, nick, body, status="visible", reply_nick=None):
    return dict(id=i, parent_id=parent, reply_to_id=reply, reply_to_nickname=reply_nick, status=status,
                nickname=None if status != "visible" else nick, body=None if status != "visible" else body,
                created_at="2026-11-20T03:00:00Z", updated_at="2026-11-20T03:00:00Z", up_count=2, down_count=0)

CID = lambda n: "c000000%d-0000-4000-8000-000000000000" % n
COMMENTS = [
    c(CID(1), None, None, "A", "빚이 많으면 부자 아닌가?"),
    c(CID(2), CID(1), CID(1), "B", "그럼 빚이 100억이면 재벌이냐?", reply_nick="A"),
    c(CID(3), CID(2), CID(2), "C", "은행이 100억을 빌려줬다는 건 신용이 있다는 뜻이지.", reply_nick="B"),
    c(CID(4), CID(3), CID(3), "D", "그건 자산이 아니라 부채잖아.", reply_nick="C"),
    c(CID(5), CID(4), CID(4), "E", "부채도 레버리지지!", reply_nick="D"),
    c(CID(6), None, None, "", "", status="deleted"),
    c(CID(7), CID(6), CID(6), "F", "원 댓글은 사라졌지만 나는 남았다", reply_nick=None),
]
POSTS = [
    dict(id=P3, display_no=3, nickname="다", title="셋째 글: 라면은 국물 요리인가", preview="면보다 국물이 본체라는 주장\n\n길게 이어지는 미리보기 텍스트입니다. " * 3,
         created_at="2026-11-21T02:00:00Z", up_count=5, down_count=1, comment_count=4, has_image=True),
    dict(id=P2, display_no=2, nickname="나", title="둘째 글", preview="본문 둘", created_at="2026-11-20T02:00:00Z", up_count=0, down_count=0, comment_count=0, has_image=False),
    dict(id=P1, display_no=1, nickname="가", title="빚이 많으면 부자 아닌가?", preview="자산과 부채의 경계에서",
         created_at="2025-10-01T02:00:00Z", up_count=3, down_count=0, comment_count=6, has_image=False),
]
state = dict(posted=[], votes=0, track=[], reports=[])

def handler(route, req):
    cors = {"access-control-allow-origin": "*", "access-control-allow-headers": "content-type,x-admin-token",
            "access-control-allow-methods": "GET,POST,OPTIONS"}
    def ok(body, status=200):
        route.fulfill(status=status, headers={**cors, "content-type": "application/json"}, body=json.dumps(body))
    if req.method == "OPTIONS":
        return route.fulfill(status=204, headers=cors)
    path = req.url.split("/functions/v1/api", 1)[1].split("?")[0]
    body = None
    try: body = req.post_data_json
    except Exception: pass
    if path == "/posts" and req.method == "GET":
        return ok(dict(page=1, page_size=20, total=3, posts=POSTS))
    if path == "/posts" and req.method == "POST":
        state["posted"].append(body); return ok(dict(id=NEW), 201)
    if path == f"/posts/{P1}":
        return ok(dict(post=dict(id=P1, status="visible", nickname="가", title="빚이 많으면 부자 아닌가?", body="자산과 부채의 경계에서\n줄바꿈 <b>태그</b> & <script>alert(1)</script> 도 그대로 보여야 함 😈",
                                 created_at="2025-10-01T02:00:00Z", updated_at="2025-10-01T02:00:00Z", up_count=3, down_count=0, comment_count=6, has_image=True), comments=COMMENTS))
    if path == f"/posts/{P2}":
        return ok(dict(post=dict(id=P2, status="deleted", nickname=None, title=None, body=None, created_at="2026-11-20T02:00:00Z", updated_at="2026-11-20T02:00:00Z", up_count=0, down_count=0, comment_count=0, has_image=False), comments=[]))
    if path == f"/posts/{NEW}":
        return ok(dict(post=dict(id=NEW, status="visible", nickname="새글러", title="새로 쓴 글", body="ok", created_at="2026-11-21T03:00:00Z", updated_at="2026-11-21T03:00:00Z", up_count=0, down_count=0, comment_count=0, has_image=False), comments=[]))
    if path == f"/posts/{P1}/image":
        return ok(dict(url=PNG, expires_in=60))
    if path == "/vote":
        state["votes"] += 1; return ok(dict(up_count=4, down_count=0, my_value=body["value"]))
    if path == "/track":
        state["track"].append(body); return ok(dict(ok=True))
    if path == "/report":
        state["reports"].append(body); return ok(dict(ok=True, duplicate=False))
    if path == "/admin/login":
        if body.get("password") == "good-password":
            return ok(dict(token="T" * 43, expires_at="2099-01-01T00:00:00Z"))
        return ok(dict(error="wrong_password"), 401)
    if path == "/admin/me":
        return ok(dict(ok=True))
    return ok(dict(error="not_found"), 404)

results = []
def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))

srv = subprocess.Popen([sys.executable, "-m", "http.server", "8765", "--bind", "127.0.0.1"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
try:
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, locale="ko-KR", timezone_id="Asia/Seoul")
        ctx.route(API + "/**", handler)
        errors = []
        def watch(pg):
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "favicon" not in m.text else None)
            pg.on("pageerror", lambda e: errors.append("PAGEERROR " + str(e)))
        no_hscroll = lambda pg: pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")

        # ---- 목록
        pg = ctx.new_page(); watch(pg)
        pg.goto(BASE + "/index.html"); pg.wait_for_selector(".post-item")
        items = pg.locator(".post-item")
        check("목록: 글 3개 렌더", items.count() == 3)
        check("목록: 최신 글이 번호 3", items.nth(0).locator(".no").inner_text().strip() == "3")
        check("목록: 이미지 아이콘은 첨부 글에만", pg.locator(".post-item [aria-label='이미지 첨부']").count() == 1)
        check("목록: 이미지 자동 로딩 없음(img 태그 0개)", pg.locator(".post-list img").count() == 0)
        check("목록: 가로 스크롤 없음", no_hscroll(pg))
        check("목록: 방문 집계 1회 전송(새 세션)", len(state["track"]) == 1 and state["track"][0]["new_session"] is True)
        pg.screenshot(path=f"{OUT}/list.png")

        # ---- 상세
        pg2 = ctx.new_page(); watch(pg2)
        pg2.goto(f"{BASE}/post.html?id={P1}"); pg2.wait_for_selector(".comment")
        body_html = pg2.locator(".post-body").inner_html()
        check("상세: 본문 HTML 이스케이프(태그가 텍스트로 표시)", "<b>" not in body_html.replace("&lt;b&gt;", "") and pg2.locator(".post-body b").count() == 0 and pg2.locator(".post-body script").count() == 0)
        check("상세: 이미지 자동 로딩 없음", pg2.locator("article img").count() == 0)
        check("상세: 댓글 7개 렌더", pg2.locator(".comment").count() == 7)
        check("상세: 삭제된 댓글 표시", pg2.get_by_text("삭제된 댓글입니다.").count() >= 1)
        check("상세: 삭제된 댓글의 하위 답글 유지", pg2.get_by_text("원 댓글은 사라졌지만 나는 남았다").count() == 1)
        check("상세: 모든 답글에 '→ @대상' 표시(B→A, C→B, D→C, E→D, F→삭제된 댓글)", pg2.locator(".to").count() == 5 and pg2.locator(".to", has_text="@A").count() == 1 and pg2.locator(".to", has_text="@B").count() == 1)
        check("상세: 최상위 댓글에는 '→ @' 없음", pg2.locator(f"#c-{CID(1)} > .c-head .to").count() == 0)
        cls = lambda n: pg2.locator(f"#c-{CID(n)}").evaluate("e => e.parentElement.className")
        check("상세: 직속 답글만 들여쓰기, 그 아래는 flat", "flat" not in cls(2) and all("flat" in cls(n) for n in (3, 4, 5)), f"{cls(2)} / {cls(3)} / {cls(4)} / {cls(5)}")
        x = lambda n: pg2.locator(f"#c-{CID(n)}").evaluate("e => e.getBoundingClientRect().left")
        check("상세: B~E 모두 같은 왼쪽 위치(들여쓰기 한 번)", max(x(n) for n in (2, 3, 4, 5)) - min(x(n) for n in (2, 3, 4, 5)) < 2, str([x(n) for n in (2,3,4,5)]))
        check("상세: 가로 스크롤 없음", no_hscroll(pg2))
        pg2.screenshot(path=f"{OUT}/post.png", full_page=True)

        pg2.get_by_role("button", name=re.compile("이미지 보기")).click()
        pg2.wait_for_selector("article img")
        check("이미지: 버튼 클릭 후에만 표시", pg2.locator("article img").count() == 1)
        pg2.get_by_role("button", name=re.compile("이미지 접기")).click()
        check("이미지: 다시 누르면 접힘", pg2.locator("article img").count() == 0)

        top = pg2.locator(f"#c-{CID(1)}")
        top.locator(".c-tools button", has_text=re.compile("답글 \\d+개 접기")).first.click()
        check("댓글: 접기 → 하위 답글 숨김", not pg2.locator(f"#c-{CID(2)}").is_visible())
        top.locator(".c-tools button", has_text=re.compile("펼치기")).first.click()
        check("댓글: 펼치기 → 다시 표시", pg2.locator(f"#c-{CID(2)}").is_visible())

        pg2.locator(f"#c-{CID(1)} > .c-tools button", has_text="답글").first.click()
        check("댓글: 답글 폼 열림", pg2.locator(f"#c-{CID(1)} > .reply-slot form").count() == 1)

        up = pg2.locator("article .bar-actions button[aria-label='추천']")
        up.click(); pg2.wait_for_timeout(300)
        check("추천: 서버 값으로 갱신 + 눌림 표시", up.inner_text().strip() == "4" and up.get_attribute("aria-pressed") == "true")
        check("방문 집계: 상세에서 post_id 전송", any(t.get("post_id") == P1 for t in state["track"]))

        pg2.locator("article .bar-actions button", has_text="신고").click()
        pg2.wait_for_selector("dialog[open]")
        pg2.locator("dialog button[type=submit]").click(); pg2.wait_for_timeout(300)
        check("신고: 대화상자 → 전송", len(state["reports"]) == 1 and state["reports"][0]["target_type"] == "post")
        check("상세: 콘솔 오류 없음", not errors, "; ".join(errors)[:300])

        # ---- 삭제된 글
        pgb = ctx.new_page(); watch(pgb)
        pgb.goto(BASE + "/index.html?sort=popular"); pgb.wait_for_selector(".post-item")
        pgb.locator(f".post-item a[href*='{P1}']").first.click(); pgb.wait_for_selector(".post-title")
        check("뒤로 버튼: 헤더 오른쪽에 표시", pgb.locator(".header-actions .back-btn").count() == 1)
        pgb.locator(".back-btn").click(); pgb.wait_for_selector(".post-item")
        check("뒤로 버튼: 보던 목록(인기순)으로 복귀", "sort=popular" in pgb.url, pgb.url)
        pgb.locator(f".post-item a[href*='{P1}']").first.click(); pgb.wait_for_selector(".post-title")
        pgb.locator(".site-title").click(); pgb.wait_for_selector(".post-item")
        check("제목 클릭: 메인(기본 목록)으로 이동", "sort=popular" not in pgb.url, pgb.url)
        pgd = ctx.new_page(); pgd.goto(f"{BASE}/post.html?id={P1}"); pgd.wait_for_selector(".post-title")
        pgd.locator(".back-btn").click(); pgd.wait_for_selector(".post-item")
        check("뒤로 버튼: 직접 진입이면 메인으로", pgd.url.endswith("/index.html"), pgd.url)
        check("본문 위 여백 확보", pgb.evaluate("parseFloat(getComputedStyle(document.querySelector('main')).paddingTop)") >= 16)
        pg3 = ctx.new_page(); watch(pg3)
        pg3.goto(f"{BASE}/post.html?id={P2}"); pg3.wait_for_selector(".post-state")
        check("삭제된 글: 안내 문구만 표시", pg3.locator(".post-state").inner_text().strip() == "삭제된 게시글입니다." and pg3.locator("form.cform").count() == 0)

        # ---- 글쓰기
        pg4 = ctx.new_page(); watch(pg4)
        pg4.goto(BASE + "/write.html")
        pg4.fill("#nickname", "새글러"); pg4.fill("#password", "pw1234"); pg4.fill("#title", "새로 쓴 글"); pg4.fill("#body", "본문입니다\n둘째 줄")
        pg4.screenshot(path=f"{OUT}/write.png")
        pg4.click("#submit"); pg4.wait_for_url(re.compile("post.html\\?id=" + NEW))
        sent = state["posted"][0]
        check("글쓰기: 전송 본문 확인 후 상세 이동", sent["title"] == "새로 쓴 글" and sent["password"] == "pw1234" and "\n" in sent["body"])
        check("글쓰기: 콘솔 오류 없음", not [e for e in errors if "write" in e.lower()])

        # ---- 관리자 로그인
        pg5 = ctx.new_page(); watch(pg5)
        pg5.goto(BASE + "/admin/index.html")
        check("관리자: 아이디 입력창 없음(비밀번호만)", pg5.locator("input").count() == 1)
        pg5.fill("#password", "wrong"); pg5.click("#login-btn"); pg5.wait_for_selector("#form-msg:not([hidden])")
        check("관리자: 실패 메시지", "올바르지 않습니다" in pg5.locator("#form-msg").inner_text())
        pg5.fill("#password", "good-password"); pg5.click("#login-btn"); pg5.wait_for_url(re.compile("/index.html$"))
        pg5.wait_for_selector(".badge")
        check("관리자: 로그인 후 게시판 이동 + 관리자 배지", pg5.locator(".badge").inner_text() == "관리자")
        n_before = len(state["track"])
        pg5.reload(); pg5.wait_for_selector(".post-item"); pg5.wait_for_timeout(300)
        check("관리자: 본인 방문은 통계 제외", len(state["track"]) == n_before)

        # ---- 데스크톱 폭
        ctx2 = br.new_context(viewport={"width": 1100, "height": 800}, locale="ko-KR", timezone_id="Asia/Seoul")
        ctx2.route(API + "/**", handler)
        pg6 = ctx2.new_page(); pg6.goto(BASE + "/index.html"); pg6.wait_for_selector(".post-item")
        pg6.screenshot(path=f"{OUT}/list_desktop.png")
        check("데스크톱: 본문 폭 720px 이하", pg6.locator("main").evaluate("e => e.getBoundingClientRect().width") <= 721)
        br.close()
finally:
    srv.terminate()

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
