-- DB 함수 통합 테스트. 빈 Postgres(16 이상, pgcrypto·pg_trgm 설치 가능)에서 확인용으로 실행합니다. 운영 DB 에서는 실행하지 마세요.
-- 준비: createdb t; psql t 에 아래 스텁을 만든 뒤 supabase/migrations 001→002→003 을 순서대로 실행하고 이 파일을 실행합니다.
--   create role anon nologin; create role authenticated nologin; create role service_role nologin;
--   create schema extensions; create schema cron; create schema storage;
--   create table storage.buckets (id text primary key, name text, public boolean, file_size_limit bigint, allowed_mime_types text[]);
--   create function cron.schedule(text, text, text) returns bigint language sql as 'select 1::bigint';
--   (001 의 "create extension ... pg_cron" 줄은 빼고 실행)
create temp table ids(k text primary key, v uuid);
insert into ids select 'a', public.api_create_post('갑','첫글','본문 하나','pass1234');
insert into ids select 'b', public.api_create_post('을','둘째글 부자','본문 둘','pass1234');
insert into ids select 'c', public.api_create_post('병','셋째','본문 셋','pass1234');
insert into ids select 'r1', public.api_create_post('답1','a의 답글','x','pass1234', (select v from ids where k='a'));
insert into ids select 'r2', public.api_create_post('답2','r1의 답글','x','pass1234', (select v from ids where k='r1'));
select 'reply depth(기대 2): ' || reply_depth from public.posts where id=(select v from ids where k='r2');
insert into ids select 'c1', public.api_create_comment((select v from ids where k='b'), null, null, '댓', '댓글1', 'pass1234');
insert into ids select 'c2', public.api_create_comment((select v from ids where k='b'), (select v from ids where k='c1'), (select v from ids where k='c1'), '댓2', '대댓', 'pass1234');
select 'vote(기대 1): ' || up_count from public.api_vote('post', (select v from ids where k='c'), 'voter-token-aaaaaaaa1', 1::smallint);
select 'vote 취소(기대 0): ' || up_count from public.api_vote('post', (select v from ids where k='c'), 'voter-token-aaaaaaaa1', 1::smallint);
select 'popular(번호는 작성순 고정): ' || coalesce(display_no::text,'-') || ' ' || title from public.api_list_posts('popular','',20,0);
select 'latest: ' || coalesce(display_no::text,'-') || ' ' || title from public.api_list_posts('latest','',20,0);
select 'search(기대 번호 2): ' || coalesce(display_no::text,'-') || ' ' || title from public.api_list_posts('popular','부자',20,0);
select 'password ok/bad(기대 true/false): ' || public.api_check_password('post',(select v from ids where k='a'),'pass1234') || '/' || public.api_check_password('post',(select v from ids where k='a'),'nope');
select 'report(기대 true/false): ' || public.api_report('post',(select v from ids where k='a'),'spam',null,'rep-1') || '/' || public.api_report('post',(select v from ids where k='a'),'spam',null,'rep-1');
select 'comment_count(기대 2): ' || comment_count from public.posts where id=(select v from ids where k='b');
insert into public.post_attachments (post_id, storage_path, mime_type, size_bytes) select v,'p/x.gif','image/gif',4000000 from ids where k='b';
select 'gif 4MB 허용, has_image(기대 true): ' || has_image from public.posts where id=(select v from ids where k='b');
