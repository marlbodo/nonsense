import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
ROOT_DIR = _os.path.abspath(_os.path.join(_HERE, ".."))
OUT_DIR = _os.path.join(_HERE, "out")
CHROME = _os.environ.get("CHROME", "/usr/bin/google-chrome")
import json, http.server
posts=[dict(id="11111111-1111-4111-8111-111111111111",nickname="가나다",title="빚이 많으면 <b>부자</b> 아닌가?",body="첫 문단입니다.\n줄바꿈 포함.\n\n둘째 문단 & 특수문자 \"따옴표\" </script>",created_at="2026-11-20T02:00:00+00:00",updated_at="2026-11-21T02:00:00+00:00",comment_count=3,has_image=False),
 dict(id="22222222-2222-4222-8222-222222222222",nickname="라마",title="두번째",body="x"*400,created_at="2026-11-19T02:00:00+00:00",updated_at="2026-11-19T02:00:00+00:00",comment_count=0,has_image=True)]
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b=json.dumps(dict(page=1,page_size=200,posts=posts)).encode()
        self.send_response(200);self.send_header("content-type","application/json");self.end_headers();self.wfile.write(b)
    def log_message(self,*a):pass
http.server.HTTPServer(("127.0.0.1",8770),H).serve_forever()
