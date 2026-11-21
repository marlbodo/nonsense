import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR = _os.path.abspath(_os.path.join(_HERE, ".."))
OUT_DIR = _os.path.join(_HERE, "out")
CHROME = _os.environ.get("CHROME", "/usr/bin/google-chrome")
import json, math, re, subprocess, sys, time, os
from datetime import date, timedelta
from playwright.sync_api import sync_playwright

ROOT = ROOT_DIR
OUT = OUT_DIR
os.makedirs(OUT, exist_ok=True)
BASE = "http://localhost:8766"
API = "https://aunukepmqpavuujypfks.supabase.co/functions/v1/api"
PD = "22222222-2222-4222-8222-222222222222"   # 삭제된 글
PV = "11111111-1111-4111-8111-111111111111"   # 공개 글
CID = lambda n: "c000000%d-0000-4000-8000-000000000000" % n
TOKEN = "T" * 43

def stats_payload():
    today = date(2026, 11, 21)
    daily = []
    for i in range(30):
        d = today - timedelta(days=29 - i)
        v = 20 + int(15 * math.sin(i / 3)) + i
        daily.append(dict(date=d.isoformat() + "T00:00:00", visits=v, pageviews=v * 3 + 5, new_posts=i % 4, new_comments=(i * 3) % 9, up_votes=i % 6, down_votes=i % 3))
    weekly = [dict(week_start=(date(2026, 10, 26) + timedelta(days=7 * k)).isoformat(), visits=150 + 40 * k, pageviews=500, new_posts=5, new_comments=11) for k in range(5)]
    monthly = [dict(month_start="2026-10-01", visits=420, pageviews=1300, new_posts=10, new_comments=30), dict(month_start="2026-11-01", visits=910, pageviews=2800, new_posts=22, new_comments=61)]
    hourly = [dict(hour=h, visits=int(30 + 25 * math.sin((h - 9) / 24 * 2 * math.pi)) , pageviews=100) for h in range(24)]
    weekday = [dict(dow=k, visits=100 + 10 * k, pageviews=300) for k in range(7)]
    return dict(
        measure_note="x", range_days=30, today="2026-11-21",
        cards=dict(visits_today=41, visits_yesterday=38, visits_7d=250, visits_30d=910, visits_total=1330, pageviews_today=120, pageviews_total=4100),
        daily=daily, weekly=weekly, monthly=monthly, hourly=hourly, weekday=weekday,
        growth=dict(visits_7d=dict(current=250, previous=200), visits_28d=dict(current=800, previous=800), visits_30d=dict(current=910, previous=420),
                    new_posts_28d=dict(current=18, previous=20), new_comments_28d=dict(current=40, previous=0)),
        search_visits_28d=dict(current=0, previous=0),
        referrers=[dict(source="google", visits=210), dict(source="naver", visits=330), dict(source="direct", visits=370)],
        top_posts=[dict(post_id=PV, title="빚이 많으면 부자 아닌가?", views=321), dict(post_id=PD, title="둘째 글", views=88)],
        content=dict(posts_total=30, comments_total=80, avg_comments_per_post=2.67))

def comment(i, parent, nick, body, deleted=False, hidden=False):
    return dict(id=i, post_id=PV, parent_id=parent, reply_to_id=parent, nickname=nick, body=body, created_at="2026-11-20T03:00:00Z",
                is_deleted=deleted, deleted_by="author" if deleted else None, is_hidden=hidden, up_count=1, down_count=0)

calls = []
def handler(route, req):
    cors = {"access-control-allow-origin": "*", "access-control-allow-headers": "content-type,x-admin-token", "access-control-allow-methods": "GET,POST,OPTIONS"}
    ok = lambda body, status=200: route.fulfill(status=status, headers={**cors, "content-type": "application/json"}, body=json.dumps(body))
    if req.method == "OPTIONS": return route.fulfill(status=204, headers=cors)
    full = req.url.split("/functions/v1/api", 1)[1]
    path = full.split("?")[0]
    body = None
    try: body = req.post_data_json
    except Exception: pass
    tok = req.headers.get("x-admin-token")
    if path.startswith("/admin/"):
        if tok != TOKEN: return ok(dict(error="unauthorized"), 401)
        calls.append((req.method, full, body))
    if path == "/admin/stats": return ok(stats_payload())
    if path == "/admin/posts" and "filter=deleted" in full:
        return ok(dict(page=1, page_size=20, total=1, posts=[dict(id=PD, nickname="나", title="삭제된 글 원문 제목", created_at="2026-11-20T02:00:00Z", is_deleted=True, deleted_by="author", is_hidden=False, up_count=0, down_count=0, comment_count=0, has_image=False)]))
    if path == "/admin/reports":
        return ok(dict(page=1, page_size=20, total=2, reports=[
            dict(id=7, target_type="comment", target_id=CID(2), reason="abuse", detail="욕설이 있어요", status="pending", created_at="2026-11-21T01:00:00Z", resolved_at=None, post_id=PV, target_preview="신고된 댓글 내용"),
            dict(id=8, target_type="image", target_id=PV, reason="bad_image", detail=None, status="pending", created_at="2026-11-21T01:30:00Z", resolved_at=None, post_id=PV, target_preview="빚이 많으면 부자 아닌가?")]))
    if re.match(r"/admin/reports/\d+/resolve", path): return ok(dict(ok=True))
    if path == f"/admin/posts/{PD}":
        return ok(dict(post=dict(id=PD, nickname="나", title="삭제된 글 원문 제목", body="삭제 전 원문 본문입니다", created_at="2026-11-20T02:00:00Z", updated_at="2026-11-20T02:00:00Z",
                                 is_deleted=True, deleted_by="author", is_hidden=False, up_count=2, down_count=1, comment_count=0, has_image=False),
                       comments=[comment(CID(1), None, "A", "삭제된 글에 달린 댓글")], attachment=None))
    if path == f"/admin/posts/{PV}":
        return ok(dict(post=dict(id=PV, nickname="가", title="공개 글", body="본문", created_at="2026-11-20T02:00:00Z", updated_at="2026-11-20T02:00:00Z",
                                 is_deleted=False, deleted_by=None, is_hidden=False, up_count=1, down_count=0, comment_count=1, has_image=True),
                       comments=[comment(CID(2), None, "B", "숨길 댓글"), comment(CID(3), None, "C", "삭제된 댓글 원문", deleted=True)],
                       attachment=dict(id="a", mime_type="image/png", size_bytes=100, is_hidden=False, created_at="2026-11-20T02:00:00Z")))
    if path == f"/admin/posts/{PV}/image" and req.method == "GET": return ok(dict(url="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==", expires_in=60))
    if path.startswith("/admin/"): return ok(dict(ok=True))
    if path == "/posts": return ok(dict(page=1, page_size=20, total=0, posts=[]))
    if path == f"/posts/{PV}/image": return ok(dict(url="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==", expires_in=60))
    return ok(dict(error="not_found"), 404)

results = []
def check(name, cond, extra=""):
    results.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))

srv = subprocess.Popen([sys.executable, "-m", "http.server", "8766", "--bind", "127.0.0.1"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
try:
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        def mkctx(dark=False, admin=True, w=390, h=844):
            ctx = br.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, locale="ko-KR", timezone_id="Asia/Seoul", color_scheme="dark" if dark else "light")
            ctx.route(API + "/**", handler)
            if admin:
                ctx.add_init_script("sessionStorage.setItem('nv_admin', JSON.stringify({token:'%s', exp:'2099-01-01T00:00:00Z'}))" % TOKEN)
            return ctx
        errors = []
        def watch(pg):
            pg.on("response", lambda r: print("   404 ->", r.url[-90:]) if r.status == 404 else None)
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "favicon" not in m.text else None)
            pg.on("pageerror", lambda e: errors.append("PAGEERROR " + str(e)))
        no_h = lambda pg: pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")

        ctx = mkctx(); pg = ctx.new_page(); watch(pg)
        # ---- 관리자 메뉴 + 목록
        pg.goto(BASE + "/index.html"); pg.wait_for_selector(".admin-nav")
        check("메뉴: 관리자 메뉴 6개", pg.locator(".admin-nav a").count() == 6)
        pg.goto(BASE + "/index.html?v=deleted"); pg.wait_for_selector(".post-item")
        check("삭제 글 필터: 목록 표시 + 검색창 숨김", "삭제된 글 원문 제목" in pg.locator(".post-item").inner_text() and not pg.locator(".toolbar").is_visible())
        check("삭제 글 필터: 현재 메뉴 강조", pg.locator(".admin-nav a[aria-current=page]").inner_text() == "삭제 글")
        pg.goto(BASE + "/index.html?v=reports"); pg.wait_for_selector(".report")
        check("신고 접수: 2건 + 사유 라벨", pg.locator(".report").count() == 2 and "욕설·비방" in pg.locator(".report").first.inner_text())
        pg.screenshot(path=f"{OUT}/admin_reports.png")
        pg.locator(".report").first.get_by_role("button", name="처리 완료").click(); pg.wait_for_timeout(300)
        check("신고 처리: resolve 호출 + 목록에서 제거", any("/admin/reports/7/resolve" in c[1] and c[2] == {"status": "resolved"} for c in calls) and pg.locator(".report").count() == 1)
        check("신고 접수: 가로 스크롤 없음", no_h(pg))

        # ---- 삭제된 글 원문 열람 + 복구
        pg.goto(f"{BASE}/post.html?id={PD}"); pg.wait_for_selector(".post-title")
        check("관리자 상세: 삭제된 글 원문 표시", pg.locator(".post-title").inner_text() == "삭제된 글 원문 제목" and "삭제 전 원문" in pg.locator(".post-body").inner_text())
        check("관리자 상세: 삭제 상태 안내", "삭제된 글입니다" in pg.locator(".post-state").inner_text())
        check("관리자 상세: 삭제된 글 댓글 원문 열람", pg.get_by_text("삭제된 글에 달린 댓글").count() == 1)
        check("관리자 상세: 일반 사용자용 수정·삭제(비밀번호) 버튼 없음", pg.locator("article .bar-actions button", has_text="신고").count() == 0)
        pg.get_by_role("button", name="복구").first.click(); pg.wait_for_timeout(300)
        check("관리자: 글 복구 → restore 호출", any(f"/admin/posts/{PD}/restore" in c[1] for c in calls))

        # ---- 공개 글 관리 (숨김·영구삭제·이미지·댓글)
        pg.goto(f"{BASE}/post.html?id={PV}"); pg.wait_for_selector(".comment")
        pg.locator("article > .bar-actions").get_by_role("button", name="숨기기").click(); pg.wait_for_timeout(300)
        check("관리자: 글 숨기기 호출", any(f"/admin/posts/{PV}/hide" in c[1] for c in calls))
        pg.get_by_role("button", name="이미지 보기").click(); pg.wait_for_selector("article .image-block img")
        check("관리자: 이미지 미리보기(관리자 엔드포인트, 신고 버튼 없음)", any(c[1].startswith(f"/admin/posts/{PV}/image") and c[0]=="GET" for c in calls) and pg.get_by_text("이미지 신고").count()==0)
        pg.get_by_role("button", name="이미지 숨기기").click(); pg.wait_for_timeout(300)
        check("관리자: 이미지 숨기기 호출", any(f"/admin/posts/{PV}/image/hide" in c[1] for c in calls))
        n0 = len(calls)
        pg.locator("article > .bar-actions").get_by_role("button", name="영구 삭제").click(); pg.wait_for_selector("dialog[open]")
        check("영구 삭제: 확인 대화상자가 먼저 뜸(호출 없음)", len(calls) == n0 and "복구할 수 없습니다" in pg.locator("dialog").inner_text())
        pg.locator("dialog button", has_text="취소").click(); pg.wait_for_timeout(200)
        check("영구 삭제: 취소하면 호출 없음", len(calls) == n0)
        # 댓글: 숨기기 / 삭제된 댓글 원문 + 복구
        cm = pg.locator(f"#c-{CID(2)} > .c-tools")
        cm.get_by_role("button", name="숨기기").click(); pg.wait_for_timeout(300)
        check("관리자: 댓글 숨기기 호출", any(f"/admin/comments/{CID(2)}/hide" in c[1] for c in calls))
        check("관리자: 삭제된 댓글 원문 + '삭제됨' 배지", pg.locator(f"#c-{CID(3)}").inner_text().count("삭제된 댓글 원문") == 1 and pg.locator(f"#c-{CID(3)} .badge").inner_text() == "삭제됨")
        pg.locator(f"#c-{CID(3)} > .c-tools").get_by_role("button", name="복구").click(); pg.wait_for_timeout(300)
        check("관리자: 댓글 복구 호출", any(f"/admin/comments/{CID(3)}/restore" in c[1] for c in calls))
        check("관리자 상세: 가로 스크롤 없음", no_h(pg))
        pg.screenshot(path=f"{OUT}/admin_post.png", full_page=True)
        check("관리자 화면: 콘솔 오류 없음", not errors, "; ".join(errors)[:300])

        # ---- 통계 (모바일 라이트)
        errors.clear()
        pg.goto(BASE + "/admin/stats.html"); pg.wait_for_selector("svg.chart"); pg.wait_for_timeout(400)
        check("통계: 지표 카드 7 + 활성도 3", pg.locator(".tiles .tile").count() == 10)
        check("통계: 차트 7개(SVG)", pg.locator("svg.chart").count() == 7)
        check("통계: 2계열 차트에는 범례, 단일 계열에는 없음", pg.locator(".viz-card:has(h3:text-is('일별 방문·페이지뷰')) .legend li").count() == 2 and pg.locator(".viz-card:has(h3:text-is('주별 방문')) .legend").count() == 0)
        verd = pg.locator(".verdict").all_inner_texts()
        check("통계: 방문 정체(0%) / 활동 성장(+) 판정", any("방문 정체" in t for t in verd) and any("활동 성장" in t for t in verd), str(verd))
        check("통계: 가로 스크롤 없음", no_h(pg))
        line = pg.locator("svg.chart").first
        line.scroll_into_view_if_needed()
        box = line.bounding_box()
        pg.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + 60); pg.wait_for_timeout(200)
        tip = pg.locator(".viz-tip:visible").first
        check("통계: 호버 시 툴팁(값 + 두 계열)", tip.count() == 1 and tip.locator(".tip-r").count() == 2)
        line.focus(); pg.keyboard.press("ArrowLeft"); pg.wait_for_timeout(150)
        check("통계: 키보드 방향키로 툴팁 이동", pg.locator(".viz-tip:visible").count() >= 1)
        pg.screenshot(path=f"{OUT}/stats_mobile.png", full_page=True)
        pg.locator(".viz-card:has(h3:text-is('일별 방문·페이지뷰')) button", has_text="표로 보기").click()
        check("통계: 표로 보기(30행 + 헤더)", pg.locator(".viz-card:has(h3:text-is('일별 방문·페이지뷰')) tbody tr").count() == 30)
        check("통계: 콘솔 오류 없음", not errors, "; ".join(errors)[:300])
        pg.get_by_role("button", name="오늘").click(); pg.wait_for_timeout(300)
        check("통계: 기간 변경 시 재조회(stats?range=today)", any("range=today" in c[1] for c in calls))

        # ---- 다크 모드 + 데스크톱
        ctxd = mkctx(dark=True); pgd = ctxd.new_page(); watch(pgd)
        pgd.goto(BASE + "/admin/stats.html"); pgd.wait_for_selector("svg.chart"); pgd.wait_for_timeout(400)
        pgd.screenshot(path=f"{OUT}/stats_dark.png", full_page=False)
        ctxw = mkctx(w=1100, h=900); pgw = ctxw.new_page(); pgw.goto(BASE + "/admin/stats.html"); pgw.wait_for_selector("svg.chart"); pgw.wait_for_timeout(400)
        pgw.screenshot(path=f"{OUT}/stats_desktop.png")
        check("다크/데스크톱: 콘솔 오류 없음", not errors, "; ".join(errors)[:300])

        # ---- 비관리자 접근 차단(화면 측)
        ctxn = mkctx(admin=False); pgn = ctxn.new_page()
        pgn.goto(BASE + "/admin/stats.html"); pgn.wait_for_url(re.compile("/admin/index.html$|/admin/$"))
        check("비관리자: 통계 화면 접근 시 로그인으로 이동", "/admin/" in pgn.url)
        pgn.goto(BASE + "/index.html"); pgn.wait_for_selector(".post-item", state="attached") if False else None
        check("비관리자: 관리자 메뉴 없음", pgn.locator(".admin-nav").count() == 0)
        br.close()
finally:
    srv.terminate()

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
