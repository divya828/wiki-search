create extension if not exists vector;

create table if not exists chunks (
    id              bigserial primary key,
    article_title   text not null,
    section         text,
    chunk_text      text not null,
    embedding       vector(384),
    tsv             tsvector generated always as (to_tsvector('english', chunk_text)) stored,
    created_at      timestamptz default now()
);

create index if not exists chunks_embedding_idx
    on chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create index if not exists chunks_tsv_idx on chunks using gin (tsv);

create index if not exists chunks_article_title_idx on chunks (article_title);
