# Odoo XML-RPC API Reference

## Connection

```python
import xmlrpc.client

url     = "https://yourcompany.odoo.com"
db      = "yourcompany"
username= "you@email.com"
api_key = "your-odoo-api-key"

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid    = common.authenticate(db, username, api_key, {})

models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
```

## Getting API Key

1. In Odoo: **Settings → Technical → API Keys**
2. Click **New** → name it "AI Employee"
3. Copy the key (shown once)

## Key Models

| Model | Purpose |
|-------|---------|
| `res.partner` | Customers / contacts |
| `sale.order` | Sales orders |
| `account.move` | Invoices (move_type='out_invoice') |
| `product.product` | Products with variants |
| `product.template` | Product templates |
| `stock.quant` | Inventory quantities |
| `stock.location` | Warehouse locations |

## Common Operations

```python
# Search
ids = models.execute_kw(db, uid, api_key,
    'sale.order', 'search',
    [[['state', '=', 'sale']]])

# Read
records = models.execute_kw(db, uid, api_key,
    'sale.order', 'read',
    [ids], {'fields': ['name', 'amount_total']})

# Create
new_id = models.execute_kw(db, uid, api_key,
    'res.partner', 'create',
    [{'name': 'Jane', 'email': 'jane@test.com'}])

# Write (update)
models.execute_kw(db, uid, api_key,
    'sale.order', 'write',
    [[new_id], {'note': 'Updated'}])
```

## Sale Order States
- `draft` → Quotation
- `sent` → Quotation Sent
- `sale` → Sales Order (confirmed)
- `done` → Locked
- `cancel` → Cancelled

## Invoice States (account.move)
- `draft` → Draft
- `posted` → Posted/Confirmed
- `cancel` → Cancelled
- `payment_state`: `not_paid`, `partial`, `paid`, `reversed`

## Required User Access Rights
For full AI Employee integration, the Odoo user needs:
- Sales → User or Manager
- Accounting → Billing or Accountant
- Inventory → User or Manager
