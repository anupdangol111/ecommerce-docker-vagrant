CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    emoji       TEXT NOT NULL DEFAULT '📦'
);

CREATE TABLE IF NOT EXISTS orders (
    id             SERIAL PRIMARY KEY,
    customer_name  TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    total_cents    INTEGER NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    price_cents INTEGER NOT NULL
);

INSERT INTO products (name, description, price_cents, stock, emoji) VALUES
  ('Wireless Headphones', 'Over-ear, 30h battery',        5999, 25, '🎧'),
  ('Mechanical Keyboard', 'Hot-swappable, RGB',           8999, 15, '⌨️'),
  ('Smart Watch',         'Heart rate and GPS',          12999, 10, '⌚'),
  ('Backpack',            '20L, water resistant',         3999, 40, '🎒'),
  ('Coffee Mug',          'Ceramic, 350 ml',               899, 100,'☕'),
  ('Desk Lamp',           'LED, adjustable brightness',   2499, 30, '💡');
