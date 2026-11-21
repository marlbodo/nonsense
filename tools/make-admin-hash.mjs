// 관리자 비밀번호 해시 생성기 (본인 컴퓨터에서 실행, 비밀번호는 채팅에 붙여넣지 마세요)
//   node tools/make-admin-hash.mjs
// 출력된 한 줄을 Supabase 대시보드 > Edge Functions > Secrets 의 ADMIN_PASSWORD_HASH 값으로 저장합니다.
import { pbkdf2Sync, randomBytes } from "node:crypto";
import { createInterface } from "node:readline";

const ITER = 600000;
const rl = createInterface({ input: process.stdin, output: process.stderr, terminal: true });
rl._writeToOutput = function (s) { if (s.includes("비밀번호")) rl.output.write(s); };

rl.question("관리자 비밀번호(12자 이상 권장): ", (pw) => {
  rl.close();
  process.stderr.write("\n");
  if (pw.length < 8) {
    console.error("비밀번호가 너무 짧습니다.");
    process.exit(1);
  }
  const salt = randomBytes(16);
  const hash = pbkdf2Sync(pw, salt, ITER, 32, "sha256");
  console.log(`pbkdf2$sha256$${ITER}$${salt.toString("base64")}$${hash.toString("base64")}`);
});
