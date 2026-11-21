-- 헛소리 대마왕 — 3/3 트리거·보안·정리 작업·저장소

-- 트리거
create trigger posts_set_updated_at before update of title, body on public.posts for each row execute function public.set_updated_at();
create trigger comments_set_updated_at before update of body on public.comments for each row execute function public.set_updated_at();
create trigger posts_bump_daily after insert on public.posts for each row execute function public.bump_daily_new();
create trigger comments_bump_daily after insert on public.comments for each row execute function public.bump_daily_new();
create trigger comments_refresh_count after insert or delete or update of is_deleted, is_hidden on public.comments for each row execute function public.refresh_post_comment_count();
create trigger attachments_refresh_has_image after insert or delete or update of is_hidden on public.post_attachments for each row execute function public.refresh_post_has_image();
create trigger votes_apply_counts after insert or delete or update of value on public.votes for each row execute function public.apply_vote_counts();

-- 보안: 모든 테이블 RLS 켜기(정책 없음 = anon/authenticated 접근 불가). service_role 만 접근합니다.
do $$
declare r record;
begin
  for r in select tablename from pg_tables where schemaname = 'public' loop
    execute format('alter table public.%I enable row level security', r.tablename);
    execute format('revoke all on table public.%I from anon, authenticated', r.tablename);
  end loop;
  for r in select p.oid::regprocedure as f from pg_proc p where p.pronamespace = 'public'::regnamespace and p.prokind = 'f' loop
    execute format('revoke all on function %s from public, anon, authenticated', r.f);
    execute format('grant execute on function %s to service_role', r.f);
  end loop;
end $$;

-- 서버(service_role)에는 명시적으로 권한 부여 (Supabase 기본값과 동일)
grant usage on schema public to service_role;
grant all on all tables in schema public to service_role;
grant all on all sequences in schema public to service_role;

-- 속도 제한·IP 등을 해시할 때 쓰는 서버 전용 키 (한 번만 생성. 이미 있으면 유지)
insert into public.app_secrets (name, value)
values ('hmac_key', encode(extensions.gen_random_bytes(32), 'hex'))
on conflict (name) do nothing;

-- 정리 작업
select cron.schedule('purge-rate-limits', '*/30 * * * *', $$ delete from public.rate_limits where window_start < now() - interval '2 hours' $$);
select cron.schedule('purge-admin-sessions', '17 3 * * *', $$ delete from public.admin_sessions where expires_at < now() - interval '1 day' or revoked_at < now() - interval '1 day' $$);

-- 이미지 저장소: 비공개 버킷, 5MB, JPG/PNG/GIF/WebP. 정책을 만들지 않으므로 서버(service_role)만 접근합니다.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('post-images', 'post-images', false, 5242880, array['image/jpeg', 'image/png', 'image/webp', 'image/gif'])
on conflict (id) do update set public = false, file_size_limit = 5242880,
  allowed_mime_types = array['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
