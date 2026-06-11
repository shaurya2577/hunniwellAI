create extension if not exists vector;

create table if not exists companies (
  id uuid primary key default gen_random_uuid(),
  name_norm text unique not null,
  name_raw text not null,
  country text,
  website text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists company_appearances (
  id uuid primary key default gen_random_uuid(),
  company_id uuid references companies(id) on delete cascade,
  event text not null,
  relpath text unique not null,
  created_at timestamptz default now()
);

create table if not exists sources (
  id uuid primary key default gen_random_uuid(),
  company_id uuid references companies(id) on delete cascade,
  kind text not null,
  reliability smallint,
  uri text,
  tag text,
  title text,
  writer text not null,
  captured_at timestamptz default now()
);

create table if not exists claims (
  id text primary key,
  company_id uuid references companies(id) on delete cascade,
  field text,
  value text not null,
  source_id uuid references sources(id),
  writer text not null,
  confidence real,
  embedding vector(1024),
  status text not null default 'active',
  superseded_by text references claims(id),
  created_at timestamptz default now()
);

create index if not exists claims_company_field on claims(company_id, field);

create index if not exists claims_embedding on claims using hnsw (embedding vector_cosine_ops);

create unique index if not exists claims_idem
  on claims(company_id, coalesce(field, ''), md5(value), source_id)
  where status = 'active';
