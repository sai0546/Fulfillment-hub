# Business rules

## Order lifecycle

`RECEIVED → READY_TO_PICK → PICKING → PICKED → PACKED → STAGED → SHIPPED`

`AWAITING_STOCK` becomes `READY_TO_PICK` only when a related transfer is received and Main has enough stock. An exception can block work. API actions reject invalid transitions.

## Inventory

- Quantity is tracked by SKU and warehouse.
- Picking decrements Main inventory only after SKU, variant, and quantity match.
- A transfer request does not change balances. Receiving it atomically decrements Secondary and increments Main.
- A transfer cannot be received if its source balance is insufficient.
- Orders with insufficient stock cannot be picked.

## Picking and packing

- The submitted SKU and variant must exactly match the order line.
- Pick quantity must equal the outstanding quantity for that line.
- Packing is available after all lines have been verified.
- Packing creates a unique package and simulated shipping label.

## Staging and courier

- A packed package needs a staging location before courier pickup.
- Pickup confirmation changes the order to SHIPPED and writes an event.
- Courier and tracking values are sample/simulated data.

## Exceptions

- Issues have an ID, related order when applicable, description, owner, status, and timestamps.
- Resolving an exception is recorded. A blocked order returns to pick queue only when stock is available; otherwise it remains blocked pending a stock action.
