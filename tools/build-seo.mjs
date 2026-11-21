// 배포용 사이트(dist/)를 만든다: 정적 파일 복사 + 글별 정적 HTML(/p/<id>/) + sitemap.xml + robots.txt + 메타 태그.
// 사용:  SITE_URL=https://계정.github.io/nonsense node tools/build-seo.mjs
// 의존성 없음(Node 18+). 공개 글만 /feed 에서 받아 쓰므로 삭제·숨김 글은 자동으로 사라진다.
import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.resolve(process.env.OUT_DIR || path.join(ROOT, "dist"));
const SITE = (process.env.SITE_URL || "").replace(/\/+$/, "");
const NAME = "헛소리 대마왕";
const DESC_SITE = "가입 없이 누구나 헛소리를 쓰고 댓글로 떠드는 익명 게시판. 비밀번호만 있으면 내 글과 댓글을 수정·삭제할 수 있습니다.";
const NO_FEED_OK = process.env.ALLOW_EMPTY_ON_FEED_ERROR === "1"; // 로컬 시험용

if (!/^https?:\/\/[^/]+/.test(SITE)) {
  console.error("SITE_URL 환경변수가 필요합니다. 예: SITE_URL=https://myid.github.io/nonsense");
  process.exit(1);
}

const cfg = await readFile(path.join(ROOT, "assets/js/config.js"), "utf8");
const API = (process.env.API_URL || (cfg.match(/API:\s*"([^"]+)"/) || [])[1] || "").replace(/\/+$/, "");
if (!API) { console.error("API 주소를 config.js 에서 찾지 못했습니다."); process.exit(1); }

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
const squash = (s) => String(s).replace(/\s+/g, " ").trim();
const cut = (s, n) => { const t = squash(s); return t.length <= n ? t : t.slice(0, n - 1).trimEnd() + "…"; };
const jsonLd = (o) => JSON.stringify(o).replace(/</g, "\\u003c");

// ---------- 글 목록 받기 ----------
async function fetchFeed() {
  const posts = [];
  for (let page = 1; page <= 50; page++) {
    let res;
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        res = await fetch(`${API}/feed?page=${page}`, { headers: { accept: "application/json" } });
        if (res.ok) break;
      } catch { /* 재시도 */ }
      await new Promise((r) => setTimeout(r, 1500 * attempt));
    }
    if (!res || !res.ok) {
      if (NO_FEED_OK) return posts;
      throw new Error(`feed 요청 실패 (page ${page}, status ${res ? res.status : "network"})`);
    }
    const j = await res.json();
    posts.push(...j.posts);
    if (j.posts.length < (j.page_size || 200)) break;
  }
  return posts;
}

// ---------- 공통 head 조각 ----------
function headMeta({ title, desc, url, type = "website", robots, extra = "" }) {
  return [
    `<meta name="description" content="${esc(desc)}">`,
    robots ? `<meta name="robots" content="${robots}">` : "",
    url ? `<link rel="canonical" href="${esc(url)}">` : "",
    `<meta property="og:type" content="${type}">`,
    `<meta property="og:site_name" content="${NAME}">`,
    `<meta property="og:locale" content="ko_KR">`,
    `<meta property="og:title" content="${esc(title)}">`,
    `<meta property="og:description" content="${esc(desc)}">`,
    url ? `<meta property="og:url" content="${esc(url)}">` : "",
    `<meta name="twitter:card" content="summary">`,
    `<meta name="twitter:title" content="${esc(title)}">`,
    `<meta name="twitter:description" content="${esc(desc)}">`,
    extra,
  ].filter(Boolean).join("\n  ");
}
const setTitle = (html, title) => html.replace(/<title>[\s\S]*?<\/title>/, () => `<title>${esc(title)}</title>`);
const addHead = (html, frag) => html.replace("</head>", () => `  ${frag}\n</head>`);

// ---------- 빌드 ----------
await rm(OUT, { recursive: true, force: true });
await mkdir(OUT, { recursive: true });
for (const f of ["index.html", "write.html", "post.html"]) await cp(path.join(ROOT, f), path.join(OUT, f));
await cp(path.join(ROOT, "assets"), path.join(OUT, "assets"), { recursive: true });
await cp(path.join(ROOT, "admin"), path.join(OUT, "admin"), { recursive: true });
await writeFile(path.join(OUT, ".nojekyll"), "");

const posts = await fetchFeed();
console.log(`공개 글 ${posts.length}개`);

// 1) 글별 정적 페이지: 본문이 HTML 에 들어 있어 검색엔진이 바로 읽고, 사람이 열면 같은 화면이 댓글·추천까지 동작한다.
const tpl = await readFile(path.join(ROOT, "post.html"), "utf8");
for (const p of posts) {
  const url = `${SITE}/p/${p.id}/`;
  const title = `${squash(p.title)} - ${NAME}`;
  const desc = cut(p.body, 150) || DESC_SITE;
  const ld = {
    "@context": "https://schema.org",
    "@type": "DiscussionForumPosting",
    headline: cut(p.title, 110),
    text: cut(p.body, 500),
    author: { "@type": "Person", name: squash(p.nickname) },
    datePublished: p.created_at,
    dateModified: p.updated_at || p.created_at,
    url,
    mainEntityOfPage: url,
    interactionStatistic: { "@type": "InteractionCounter", interactionType: "https://schema.org/CommentAction", userInteractionCount: p.comment_count },
  };
  const meta = headMeta({
    title, desc, url, type: "article",
    extra: `<meta property="article:published_time" content="${esc(p.created_at)}">\n  <script type="application/ld+json">${jsonLd(ld)}</script>`,
  });
  const paragraphs = String(p.body).replace(/\r\n?/g, "\n").split(/\n{2,}/).map((t) => `<p>${esc(t).replace(/\n/g, "<br>")}</p>`).join("\n    ");
  const pre = [
    `<a class="back" href="../../index.html">← 목록</a>`,
    `<article class="post">`,
    `  <h1 class="post-title">${esc(p.title)}</h1>`,
    `  <div class="post-meta"><span>${esc(p.nickname)}</span> · <span>${esc(String(p.created_at).slice(0, 10))}</span></div>`,
    `  <div class="post-body">${paragraphs}</div>`,
    `</article>`,
  ].join("\n    ");
  let html = setTitle(tpl, title);
  html = html.replace('<html lang="ko">', '<html lang="ko" data-root="../../">');
  html = html.replace(/(href|src)="assets\//g, '$1="../../assets/');
  html = html.replace(/<p class="notice">불러오는 중…<\/p>/, () => pre);
  html = addHead(html, meta);
  const dir = path.join(OUT, "p", p.id);
  await mkdir(dir, { recursive: true });
  await writeFile(path.join(dir, "index.html"), html);
}

// 2) 목록(홈): 메타 + 스크립트가 꺼진 환경(검색 로봇 포함)용 최신 글 링크
let home = await readFile(path.join(ROOT, "index.html"), "utf8");
home = setTitle(home, `${NAME} - 익명 헛소리 게시판`);
home = addHead(home, headMeta({ title: `${NAME} - 익명 헛소리 게시판`, desc: DESC_SITE, url: `${SITE}/` }));
if (posts.length) {
  const items = posts.slice(0, 100).map((p) => `<li><a href="p/${p.id}/">${esc(squash(p.title))}</a></li>`).join("");
  home = home.replace("</body>", () => `  <noscript><nav aria-label="최신 글"><h2>최신 글</h2><ul>${items}</ul></nav></noscript>\n</body>`);
}
await writeFile(path.join(OUT, "index.html"), home);

// 3) 검색에 노출하지 않을 화면
for (const f of ["write.html", "post.html"]) {
  let html = await readFile(path.join(OUT, f), "utf8");
  html = addHead(html, `<meta name="robots" content="noindex, follow">`);
  await writeFile(path.join(OUT, f), html);
}

// 4) sitemap.xml / robots.txt
const day = (s) => String(s).slice(0, 10);
const urls = [`  <url><loc>${esc(SITE + "/")}</loc>${posts[0] ? `<lastmod>${day(posts[0].updated_at || posts[0].created_at)}</lastmod>` : ""}</url>`]
  .concat(posts.map((p) => `  <url><loc>${esc(`${SITE}/p/${p.id}/`)}</loc><lastmod>${day(p.updated_at || p.created_at)}</lastmod></url>`));
await writeFile(path.join(OUT, "sitemap.xml"), `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join("\n")}\n</urlset>\n`);
await writeFile(path.join(OUT, "robots.txt"), `User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /write.html\nDisallow: /post.html\n\nSitemap: ${SITE}/sitemap.xml\n`);

console.log(`완료: ${OUT} (글 페이지 ${posts.length}개, sitemap ${urls.length}개 주소)`);
