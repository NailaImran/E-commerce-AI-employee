# Odoo Sync Skill

Sync Shopify orders to Odoo, create invoices, read financial reports, and update inventory.

## When to Use
- New Shopify order CSV processed → sync orders to Odoo
- Asked to "sync orders to Odoo", "create invoice", "check financials", "update stock"
- Weekly CEO briefing → include Odoo financial summary
- After order-reader skill runs → auto-push to Odoo

## Workflow

### 1. Sync Shopify Orders → Odoo
```
Read order summary from /Inbox/ or /Needs_Action/
For each order:
  → call odoo-mcp: create_sale_order
  → call odoo-mcp: create_invoice
  → log result to /Logs/odoo_sync_YYYY-MM-DD.json
```

### 2. Get Financial Summary
```
Call odoo-mcp: get_financial_summary { period: "this_month" }
Add to daily briefing / CEO report
```

### 3. Update Inventory
```
Call odoo-mcp: search_products { query: "product name" }
Get product_id from result
Call odoo-mcp: update_inventory { product_id, new_quantity }
```

## MCP Tool Reference

| Tool | Purpose |
|------|---------|
| `search_products` | Find product by name, get ID + stock |
| `get_sale_orders` | List recent orders in Odoo |
| `create_sale_order` | Push a Shopify order to Odoo |
| `create_invoice` | Invoice a confirmed sale order |
| `get_financial_summary` | Revenue, invoices, receivables |
| `update_inventory` | Set new stock quantity |

## Example: Sync One Shopify Order

```json
// 1. Create sale order
{
  "tool": "create_sale_order",
  "args": {
    "customer_name": "Jane Smith",
    "customer_email": "jane@email.com",
    "order_ref": "#1042",
    "lines": [
      { "product_name": "Blue Dress", "quantity": 1, "unit_price": 89.99 },
      { "product_name": "White Blouse", "quantity": 2, "unit_price": 45.00 }
    ]
  }
}

// 2. Create invoice (use order_id from step 1)
{
  "tool": "create_invoice",
  "args": { "sale_order_id": 42 }
}
```

## Logging

Always write results to `/Logs/odoo_sync_YYYY-MM-DD.json`:
```json
{
  "timestamp": "2026-02-28T10:00:00",
  "orders_synced": 3,
  "invoices_created": 3,
  "errors": [],
  "financial_summary": { "total_revenue": 450.00, "invoice_count": 3 }
}
```

## Error Handling
- `authentication failed` → credentials wrong, check .env
- `product not found` → create product in Odoo first, or use description-only line
- `access rights` → user needs Sales / Accounting / Inventory access in Odoo
