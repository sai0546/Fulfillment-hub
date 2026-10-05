# Test plan

This plan defines the scenarios to run before extending or deploying the demo.

## Business logic

1. Seed is idempotent: restarting with a populated database does not duplicate orders.
2. Order with enough Main stock starts READY_TO_PICK; short Main and sufficient Secondary starts AWAITING_STOCK; insufficient combined stock opens an exception.
3. Wrong SKU, wrong variant, wrong quantity, or insufficient Main stock leaves inventory and pick state unchanged.
4. Correct pick decrements Main once; duplicate pick is rejected.
5. Partial picking cannot be packed; complete picking can be packed once.
6. Transfer request leaves balances unchanged; receipt moves exact units atomically; insufficient source balance rejects receipt.
7. Related order becomes pickable only after transfer receipt provides enough Main stock.
8. Staging requires PACKED; pickup requires STAGED and records SHIPPED plus an event.
9. Resolving an issue does not unblock an order if inventory is still short.

## API checks

- Invalid identifiers return 404; invalid states and business conflicts return 409/422 with useful detail.
- Search and status/priority filtering return only matching orders.
- Order details include ordered lines and chronological events.

## Browser walkthrough

- Run API and Vite concurrently, complete the acceptance walkthrough in `README.md`, refresh between actions, and confirm state remains correct.
- Check narrow viewport layout and empty/loading/error states.

