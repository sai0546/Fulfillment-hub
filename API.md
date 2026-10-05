# API reference

Base URL: `http://localhost:8000/api`. JSON responses; validation/business conflicts return 4xx with a human-readable detail.

| Method | Path | Purpose |
|---|---|---|
| GET | `/overview` | Dashboard metrics and deadline queue |
| GET | `/orders` | Order list; optional `status`, `priority`, `q` filters |
| GET | `/orders/{id}` | Order, lines, and event history |
| POST | `/orders` | Create order; checks stock and sets initial state |
| GET | `/inventory` | SKU balances by warehouse |
| GET | `/transfers` | Internal stock transfer list |
| POST | `/transfers` | Request Secondary → Main transfer |
| POST | `/transfers/{id}/receive` | Receive transfer and update balances |
| GET | `/exceptions` | Exception log |
| POST | `/exceptions` | Record issue and block related order |
| POST | `/exceptions/{id}/resolve` | Resolve and conditionally unblock order |
| POST | `/orders/{id}/pick` | Verify and pick one order line |
| POST | `/orders/{id}/pack` | Pack fully picked order |
| POST | `/orders/{id}/stage` | Assign staging bay |
| POST | `/orders/{id}/pickup` | Confirm courier handover |

### Example payloads

```json
{"customer":"Asha Rao","channel":"Website","priority":"HIGH","deadline":"2026-10-05T15:00:00","courier":"Delhivery","items":[{"sku":"WM-101","quantity":1}]}
```

```json
{"sku":"KB-205","variant":"Brown switch","quantity":2,"order_id":"ORD-2082"}
```

```json
{"sku":"KB-205","variant":"Brown switch","quantity":3}
```

