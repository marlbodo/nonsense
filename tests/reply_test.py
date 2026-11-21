import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR = _os.path.abspath(_os.path.join(_HERE, ".."))
OUT_DIR = _os.path.join(_HERE, "out")
CHROME = _os.environ.get("CHROME", "/usr/bin/google-chrome")
import json, re, subprocess, sys, time, os
from playwright.sync_api import sync_playwright
BASE = "http://localhost:8767"; OUT = OUT_DIR; os.makedirs(OUT, exist_ok=True)
API = "https://aunukepmqpavuujypfks.supabase.co/functions/v1/api"
U = lambda n: "d000000%d-0000-4000-8000-000000000000" % n
R1, A1, A2, R2, B1, R3, NEW = U(1), U(2), U(3), U(4), U(5), U(6), U(9)
def row(i, no, nick, title, depth=0, to=None, ph=None, rc=0):
    return dict(id=i, display_no=no, nickname=nick, title=title, preview="미리보기 " + title if not ph else None, created_at="2026-11-21T03:00:00Z",
                up_count=1, down_count=0, comment_count=2, has_image=False, reply_depth=depth, reply_to_id=None, reply_to_nickname=to, placeholder=ph, reply_count=rc)
THREAD = [row(R1, 3, "R", "원글 제목", rc=2), row(A1, None, "A", "첫 답글", 1, "R"), row(A2, None, "B", "답글의 답글", 2, "A"),
          row(R2, 2, None, None, ph="deleted", rc=1), row(B1, None, "C", "삭제된 원글의 답글", 1, None), row(R3, 1, "Z", "많은 답글 원글", rc=33)]
FLAT = [row(A2, 2, "B", "답글의 답글", 2, "A"), row(R1, 1, "R", "원글 제목")]
REPLIES_R1 = [dict(id=A1, nickname="A", title="첫 답글", preview="p1", created_at="2026-11-21T03:00:00Z", up_count=1, down_count=0, comment_count=0, has_image=False, reply_depth=1, reply_to_id=R1, reply_to_nickname="R"),
              dict(id=A2, nickname="B", title="답글의 답글", preview="p2", created_at="2026-11-21T03:01:00Z", up_count=0, down_count=0, comment_count=0, has_image=False, reply_depth=2, reply_to_id=A1, reply_to_nickname="A")]
def post(i, title, nick, **kw):
    d = dict(id=i, status="visible", nickname=nick, title=title, body="본문", created_at="2026-11-21T03:00:00Z", updated_at="2026-11-21T03:00:00Z", up_count=0, down_count=0, comment_count=0, has_image=False,
             reply_depth=0, reply_to_id=None, reply_to_status=None, reply_to_nickname=None, reply_to_title=None); d.update(kw); return d
state = dict(posted=[])
def handler(route, req):
    cors = {"access-control-allow-origin": "*", "access-control-allow-headers": "content-type", "access-control-allow-methods": "GET,POST,OPTIONS"}
    ok = lambda body, st=200: route.fulfill(status=st, headers={**cors, "content-type": "application/json"}, body=json.dumps(body))
    if req.method == "OPTIONS": return route.fulfill(status=204, headers=cors)
    full = req.url.split("/functions/v1/api", 1)[1]; path = full.split("?")[0]
    if path == "/posts" and req.method == "GET":
        return ok(dict(page=1, page_size=20, total=3, posts=FLAT if "q=" in full and "q=&" not in full else THREAD))
    if path == "/posts" and req.method == "POST":
        state["posted"].append(req.post_data_json); return ok(dict(id=NEW), 201)
    if path == f"/posts/{R1}": return ok(dict(post=post(R1, "원글 제목", "R"), comments=[], replies=REPLIES_R1))
    if path == f"/posts/{A1}": return ok(dict(post=post(A1, "첫 답글", "A", reply_depth=1, reply_to_id=R1, reply_to_status="visible", reply_to_nickname="R", reply_to_title="원글 제목"), comments=[], replies=REPLIES_R1[1:]))
    if path == f"/posts/{R2}": return ok(dict(post=post(R2, None, None, status="deleted", body=None), comments=[], replies=[REPLIES_R1[0]]))
    if path == f"/posts/{NEW}": return ok(dict(post=post(NEW, "새 답글", "N", reply_depth=1, reply_to_id=R1, reply_to_status="visible", reply_to_nickname="R", reply_to_title="원글 제목"), comments=[], replies=[]))
    if path == "/track": return ok(dict(ok=True))
    return ok(dict(error="not_found"), 404)
res = []
def check(n, c, x=""): res.append(bool(c)); print(("PASS " if c else "FAIL ") + n + (f" [{x}]" if x and not c else ""))
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8767", "--bind", "127.0.0.1"], cwd=ROOT_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
BASE = "http://127.0.0.1:8767"
try:
  with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
    ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, locale="ko-KR", timezone_id="Asia/Seoul"); ctx.route(API + "/**", handler)
    errs = []
    def watch(pg):
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg = ctx.new_page(); watch(pg); pg.goto(BASE + "/index.html"); pg.wait_for_selector(".post-item")
    items = pg.locator(".post-item")
    check("목록: 줄 수(원글3 + 답글3 + 더보기1)", items.count() == 7, str(items.count()))
    check("목록: 번호는 원글에만(3,2,1)", pg.locator(".post-item .no").all_inner_texts() == ["3", "2", "1"], str(pg.locator(".post-item .no").all_inner_texts()))
    check("목록: 답글 3개가 reply(들여쓰기) 클래스", pg.locator(".post-item.reply:not(.more)").count() == 3)
    xs = [pg.locator(".post-item.reply:not(.more)").nth(i).evaluate("e => e.getBoundingClientRect().left") for i in range(3)]
    check("목록: 모든 깊이의 답글이 같은 들여쓰기 위치", max(xs) - min(xs) < 1, str(xs))
    tos = pg.locator(".post-item .to").all_inner_texts()
    check("목록: 모든 답글에 @대상(@R, @A, @삭제된 글)", [t.strip() for t in tos] == ["@R", "@A", "@삭제된 글"], str(tos))
    check("목록: 삭제된 원글은 자리 표시 + 답글 유지", "삭제된 글입니다." in pg.locator(".post-item.gone").inner_text())
    check("목록: 답글 33개 원글에 '3개 더 보기'", pg.get_by_text("답글 3개 더 보기").count() == 1)
    check("목록: 가로 스크롤 없음", pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))
    pg.screenshot(path=f"{OUT}/threads.png", full_page=True)
    pg.goto(BASE + "/index.html?q=답글"); pg.wait_for_selector(".post-item")
    check("검색: 평평하게(들여쓰기 없음)·답글에 @대상", pg.locator(".post-item.reply").count() == 0 and pg.locator(".post-item .to").count() == 1)
    pg.goto(f"{BASE}/post.html?id={R1}"); pg.wait_for_selector(".replies-box")
    check("원글 상세: 답글 2개 섹션", pg.locator(".replies-box .post-item").count() == 2 and "답글 2" in pg.locator(".replies-box h2").inner_text())
    check("원글 상세: 답글 쓰기 링크", f"reply_to={R1}" in pg.get_by_role("link", name="답글 쓰기").get_attribute("href"))
    pg.screenshot(path=f"{OUT}/reply_detail_root.png", full_page=True)
    pg.goto(f"{BASE}/post.html?id={A1}"); pg.wait_for_selector(".reply-line")
    check("답글 상세: '원글 제목 글에 대한 답글 @R' 안내 + 링크", "원글 제목" in pg.locator(".reply-line").inner_text() and "@R" in pg.locator(".reply-line").inner_text() and f"id={R1}" in pg.locator(".reply-line a").get_attribute("href"))
    pg.goto(f"{BASE}/post.html?id={R2}"); pg.wait_for_selector(".post-state")
    check("삭제된 원글 상세: 안내 + 남은 답글 표시", "삭제된 게시글입니다" in pg.locator(".post-state").inner_text() and pg.locator(".replies-box .post-item").count() == 1)
    pg.goto(f"{BASE}/write.html?reply_to={R1}"); pg.wait_for_selector(".reply-ctx strong")
    check("답글쓰기: 제목·대상 표시", pg.locator("h1").inner_text() == "답글 쓰기" and pg.locator(".reply-ctx").inner_text().startswith("답글 대상") and "원글 제목" in pg.locator(".reply-ctx").inner_text())
    pg.fill("#nickname", "N"); pg.fill("#password", "pw1234"); pg.fill("#title", "새 답글"); pg.fill("#body", "내용")
    pg.click("#submit"); pg.wait_for_url(re.compile("post.html\\?id=" + NEW))
    check("답글쓰기: reply_to_id 전송", state["posted"] and state["posted"][0].get("reply_to_id") == R1, str(state["posted"]))
    pg.goto(BASE + "/write.html"); pg.wait_for_selector("#submit")
    check("일반 글쓰기에는 답글 안내 없음", pg.locator(".reply-ctx").count() == 0 and pg.locator("h1").inner_text() == "글쓰기")
    check("콘솔 오류 없음", not errs, "; ".join(errs)[:200])
    br.close()
finally: srv.terminate()
print(f"{sum(res)}/{len(res)} passed"); sys.exit(0 if all(res) else 1)
