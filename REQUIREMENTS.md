# Requirements

## Goal

Replace shared spreadsheets and folders with a clear, fast fulfillment workspace suitable for a small office and warehouse team.

## MVP users

- Office: review/create orders, set priority and ship-by time, watch stock and exceptions.
- Warehouse: follow pick tasks, verify SKU/variant/quantity, pack, assign staging bay, confirm pickup.
- Supervisor: view overall flow and resolve issues.

## MVP capabilities

1. Dashboard with open workload, urgent deadlines, stage counts, and open exceptions.
2. Searchable order queue with priority, channel, courier, item, deadline, and lifecycle status.
3. Per-warehouse inventory for a Main and Secondary warehouse.
4. Requested and received internal stock transfers, with auditable inventory changes.
5. Guided pick and exact SKU/variant/quantity verification.
6. Packing, generated demo package/label/tracking references, staging bay, and courier pickup.
7. Exceptions with owner, open/resolved state, related order, and notes.
8. Persistent records and event history through an API/database.

## Sample environment

Local single-user app; simulated marketplaces and couriers; sample Indian customer names, rupee currency, and two warehouses. No external account credentials are needed.

## Non-goals for this take-home

Live marketplace/courier integration, barcode device support, multi-tenant hosting, login/permissions, billing, returns, and production-grade reporting.

## Acceptance walkthrough

- Transfer 2 of the 12 secondary keyboards to cover the ORD-2082 shortfall; balances update and order becomes READY_TO_PICK.
- Wrong SKU or variant cannot be recorded as a pick.
- Correct complete pick allows packing, then staging with a location, then pickup to SHIPPED.
- Order view and dashboard reflect mutations after a page refresh.
- Exception has owner, status, order link, and resolution history.
