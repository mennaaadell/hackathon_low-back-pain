create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  name text not null,
  phone text,
  age integer check (age between 13 and 120),
  gender text,
  created_at timestamptz not null default now()
);

create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default 'New conversation',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  sources jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.guideline_chunks (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  page_number integer,
  section text not null default 'General',
  chunk_number integer not null default 1,
  content text not null,
  search_vector tsvector generated always as (
    to_tsvector('english', coalesce(title, '') || ' ' || content)
  ) stored,
  created_at timestamptz not null default now()
);

alter table public.guideline_chunks add column if not exists section text not null default 'General';
alter table public.guideline_chunks add column if not exists chunk_number integer not null default 1;

create index if not exists guideline_chunks_search_idx
  on public.guideline_chunks using gin(search_vector);
create index if not exists conversations_user_idx
  on public.conversations(user_id, updated_at desc);
create index if not exists messages_conversation_idx
  on public.messages(conversation_id, created_at);

drop function if exists public.search_guideline_chunks(text, integer);
create or replace function public.search_guideline_chunks(query_text text, match_count integer default 5)
returns table (id uuid, title text, page_number integer, section text, chunk_number integer, content text, confidence real)
language sql stable
as $$
  with ranked as (
    select gc.id, gc.title, gc.page_number, gc.section, gc.chunk_number, gc.content,
      ts_rank(
        gc.search_vector,
        websearch_to_tsquery(
          'english',
          regexp_replace(trim(query_text), '\s+', ' OR ', 'g')
        )
      ) as raw_rank
    from public.guideline_chunks gc
    where gc.search_vector @@ websearch_to_tsquery(
      'english',
      regexp_replace(trim(query_text), '\s+', ' OR ', 'g')
    )
  )
  select ranked.id, ranked.title, ranked.page_number, ranked.section, ranked.chunk_number,
    ranked.content,
    case when max(ranked.raw_rank) over () = 0 then 0
      else ranked.raw_rank / max(ranked.raw_rank) over () end as confidence
  from ranked
  order by ranked.raw_rank desc
  limit greatest(1, least(match_count, 20));
$$;

alter table public.profiles enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.guideline_chunks enable row level security;

drop policy if exists "users can read own profile" on public.profiles;
create policy "users can read own profile" on public.profiles for select using (auth.uid() = id);
drop policy if exists "users can read own conversations" on public.conversations;
create policy "users can read own conversations" on public.conversations for select using (auth.uid() = user_id);
drop policy if exists "users can read own messages" on public.messages;
create policy "users can read own messages" on public.messages for select using (auth.uid() = user_id);
drop policy if exists "published guidelines are readable" on public.guideline_chunks;
create policy "published guidelines are readable" on public.guideline_chunks for select using (true);

create or replace function public.touch_conversation()
returns trigger language plpgsql as $$
begin
  update public.conversations set updated_at = now() where id = new.conversation_id;
  return new;
end;
$$;

drop trigger if exists messages_touch_conversation on public.messages;
create trigger messages_touch_conversation after insert on public.messages
for each row execute function public.touch_conversation();

-- Example seed. Replace with chunks from your guideline PDF.
insert into public.guideline_chunks (title, page_number, content)
select 'Low back pain and sciatica guideline', 1,
'Assess people with low back pain and sciatica for serious underlying pathology. Give advice to continue normal activities and provide tailored self-management information.'
where not exists (select 1 from public.guideline_chunks);
