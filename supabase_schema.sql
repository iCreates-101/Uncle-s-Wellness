-- Uncle's Wellness — Supabase schema
-- Run this in the Supabase SQL editor before first deploy.

create table if not exists public.users (
  id text primary key,
  name text,
  email text unique,
  password text,
  role text default 'customer',
  created_at timestamptz default now()
);

create table if not exists public.categories (
  id text primary key,
  name text,
  slug text,
  description text,
  subcategories jsonb default '[]'::jsonb
);

create table if not exists public.products (
  id text primary key,
  name text,
  slug text,
  description text,
  price numeric default 0,
  cost_price numeric default 0,
  stock integer default 0,
  category_id text references public.categories (id),
  subcategory text default '',
  subcategory_slug text default '',
  featured integer default 0,
  active integer default 1,
  barcode text,
  created_at timestamptz default now(),
  image text
);

create table if not exists public.carts (
  id text primary key,
  session_id text,
  product_id text references public.products (id),
  quantity integer default 1
);

create table if not exists public.orders (
  id text primary key,
  order_number text,
  user_id text,
  customer_name text,
  customer_email text,
  customer_phone text,
  shipping_address text,
  payment_method text default 'cod',
  subtotal numeric default 0,
  tax numeric default 0,
  total numeric default 0,
  shipping numeric default 0,
  discount numeric default 0,
  order_status text default 'pending',
  payment_status text default 'pending',
  notes text,
  pos_order integer default 0,
  created_at timestamptz default now()
);

create table if not exists public.order_items (
  id text primary key,
  order_id text references public.orders (id),
  product_id text,
  product_name text,
  price numeric default 0,
  quantity integer default 0,
  total numeric default 0
);

create table if not exists public.logs (
  id text primary key,
  action text,
  description text,
  user_id text,
  user_name text,
  target_type text,
  target_id text,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create index if not exists idx_carts_session on public.carts (session_id);
create index if not exists idx_orders_user on public.orders (user_id);
create index if not exists idx_orders_created on public.orders (created_at);
create index if not exists idx_order_items_order on public.order_items (order_id);
create index if not exists idx_logs_created on public.logs (created_at);
create index if not exists idx_products_active on public.products (active);