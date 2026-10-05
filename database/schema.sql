-- Logical schema. SQLAlchemy creates the runtime tables on API startup.
CREATE TABLE orders (id TEXT PRIMARY KEY, customer TEXT NOT NULL, channel TEXT NOT NULL, priority TEXT NOT NULL, deadline DATETIME NOT NULL, status TEXT NOT NULL, courier TEXT NOT NULL, tracking TEXT NOT NULL, created_at DATETIME NOT NULL);
CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(id), sku TEXT NOT NULL, name TEXT NOT NULL, variant TEXT NOT NULL, quantity INTEGER NOT NULL, picked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE inventory (id INTEGER PRIMARY KEY, sku TEXT NOT NULL, name TEXT NOT NULL, variant TEXT NOT NULL, warehouse TEXT NOT NULL, quantity INTEGER NOT NULL, location TEXT NOT NULL, UNIQUE(sku, warehouse));
CREATE TABLE transfers (id TEXT PRIMARY KEY, sku TEXT NOT NULL, quantity INTEGER NOT NULL, source TEXT NOT NULL, destination TEXT NOT NULL, order_id TEXT REFERENCES orders(id), status TEXT NOT NULL, created_at DATETIME NOT NULL, received_at DATETIME);
CREATE TABLE exceptions (id TEXT PRIMARY KEY, order_id TEXT REFERENCES orders(id), title TEXT NOT NULL, description TEXT NOT NULL, owner TEXT NOT NULL, status TEXT NOT NULL, created_at DATETIME NOT NULL, resolved_at DATETIME);
CREATE TABLE events (id INTEGER PRIMARY KEY, order_id TEXT REFERENCES orders(id), action TEXT NOT NULL, detail TEXT NOT NULL, created_at DATETIME NOT NULL);
