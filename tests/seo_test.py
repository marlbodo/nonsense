import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR = _os.path.abspath(_os.path.join(_HERE, ".."))
OUT_DIR = _os.path.join(_HERE, "out")
CHROME = _os.environ.get("CHROME", "/usr/bin/google-chrome")
import json, subprocess, sys, time, re
from playwright.sync_api import sync_playwright
API="https://aunukepmqpavuujypfks.supabase.co/functions/v1/api"
PID="11111111-1111-4111-8111-111111111111"
res=[]
def check(n,c,x=""):
    res.append(bool(c)); print(("PASS " if c else "FAIL ")+n+(f" [{x}]" if x and not c else ""))
srv=subprocess.Popen([sys.executable,"-m","http.server","8771","--bind","127.0.0.1"],cwd="/tmp/dist",stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1)
try:
  with sync_playwright() as p:
    br=p.chromium.launch(executable_path=CHROME,args=["--no-sandbox"])
    ctx=br.new_context(viewport={"width":390,"height":844},locale="ko-KR")
    calls=[]
    def h(route,req):
        cors={"access-control-allow-origin":"*","access-control-allow-headers":"content-type,x-admin-token"}
        if req.method=="OPTIONS": return route.fulfill(status=204,headers=cors)
        path=req.url.split("/api",1)[1].split("?")[0]; calls.append((req.method,path))
        if path==f"/posts/{PID}": return route.fulfill(status=200,headers={**cors,"content-type":"application/json"},body=json.dumps(dict(post=dict(id=PID,status="visible",nickname="가나다",title="빚이 많으면 <b>부자</b> 아닌가?",body="첫 문단입니다.",created_at="2026-11-20T02:00:00Z",updated_at="2026-11-20T02:00:00Z",up_count=1,down_count=0,comment_count=0,has_image=False),comments=[])))
        return route.fulfill(status=200,headers={**cors,"content-type":"application/json"},body=json.dumps(dict(ok=True,page=1,page_size=20,total=0,posts=[])))
    ctx.route(API+"/**",h)
    pg=ctx.new_page(); errs=[]
    pg.on("console",lambda m: errs.append(m.text) if m.type=="error" else None)
    pg.on("pageerror",lambda e: errs.append(str(e)))
    # JS 없이도 본문이 있는지 (검색 로봇이 보는 HTML)
    raw=pg.request.get(f"http://127.0.0.1:8771/p/{PID}/").text()
    check("정적 HTML에 제목·본문이 들어 있음", "첫 문단입니다." in raw and "<h1" in raw)
    check("정적 HTML: 제목의 태그 문자가 이스케이프됨", "<b>부자</b>" not in raw)
    check("canonical/OG/JSON-LD 존재", 'rel="canonical"' in raw and 'og:title' in raw and 'application/ld+json' in raw)
    check("</script> 가 JSON-LD 를 깨뜨리지 않음", raw.count("</script>")==4, str(raw.count("</script>")))
    pg.goto(f"http://127.0.0.1:8771/p/{PID}/"); pg.wait_for_selector(".post-title"); pg.wait_for_timeout(500)
    check("브라우저: 스타일 로드(../../assets)", pg.evaluate("getComputedStyle(document.body).backgroundColor")=="rgb(255, 255, 255)")
    check("브라우저: 스크립트가 글을 다시 불러와 상호작용 렌더", any(c[1]==f"/posts/{PID}" for c in calls) and pg.locator("article .bar-actions button[aria-label='추천']").count()==1)
    check("브라우저: 방문 집계(track) 호출", any(c[1]=="/track" for c in calls))
    check("메인 링크·뒤로 버튼(오른쪽)", pg.locator(".site-title").get_attribute("href")=="../../index.html" and pg.locator(".header-actions .back-btn").count()==1)
    check("콘솔 오류 없음", not errs, "; ".join(errs)[:200])
    pg.goto("http://127.0.0.1:8771/index.html"); pg.wait_for_timeout(400)
    html=pg.content()
    check("홈: canonical·description 메타", 'rel="canonical"' in html and 'name="description"' in html)
    pg.goto("http://127.0.0.1:8771/post.html?id="+PID); pg.wait_for_selector(".post-title")
    check("post.html: noindex", 'noindex' in pg.content())
    br.close()
finally: srv.terminate()
print(f"{sum(res)}/{len(res)} passed"); sys.exit(0 if all(res) else 1)
