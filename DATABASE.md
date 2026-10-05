# Database

SQLAlchemy models are created from the application on startup. SQLite is the zero-configuration default; `DATABASE_URL` can point to PostgreSQL.

## Entities

- `orders`: customer, channel, priority, deadline, state, courier, tracking.
- `order_items`: SKU, product/variant snapshot, ordered and picked quantities.
- `inventory`: SKU and warehouse balance plus pick location.
- `transfers`: source/destination, quantity, related order, lifecycle timestamps.
- `exceptions`: issue description, owner, related order, open/resolved state.
- `events`: append-only order/workflow activity with time and detail.

`database/schema.sql` shows the logical relational schema. Runtime initialization creates tables and inserts sample rows only when the order table is empty. Local file: `fulfillment.db` at the project root.

## Integrity notes

SKU and warehouse pairs are unique. Quantity columns are non-negative at the application boundary. Stock movement, transfer receipt, pick decrement, and event insertion share a database transaction.
