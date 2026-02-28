#!/usr/bin/env python3
"""
Sync Shopify order summaries from /Inbox/ to Odoo via XML-RPC.
Runs after order-reader skill processes a CSV.
"""

import os, json, glob, xmlrpc.client, datetime
from pathlib import Path

VAULT = Path("E:/AI_Employee_Vault")

def load_env():
    env = {}
    for line in open(VAULT / ".env", encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env

def odoo_connect(env):
    url     = env["ODOO_URL"].rstrip("/")
    db      = env["ODOO_DB"]
    user    = env["ODOO_USERNAME"]
    api_key = env["ODOO_API_KEY"]

    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid    = common.authenticate(db, user, api_key, {})
    if not uid:
        raise RuntimeError("Odoo authentication failed")

    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    return models, db, uid, api_key

def execute(models, db, uid, api_key, model, method, args=[], kwargs={}):
    return models.execute_kw(db, uid, api_key, model, method, args, kwargs)

def get_or_create_partner(models, db, uid, api_key, name, email):
    ids = execute(models, db, uid, api_key, "res.partner", "search",
                  [[["email", "=", email]]])
    if ids:
        return ids[0]
    return execute(models, db, uid, api_key, "res.partner", "create",
                   [{"name": name, "email": email}])

def sync_order(models, db, uid, api_key, order: dict) -> dict:
    """Push one order dict to Odoo. Returns {order_id, invoice_id}."""
    partner_id = get_or_create_partner(
        models, db, uid, api_key,
        order.get("customer_name", "Unknown"),
        order.get("customer_email", "unknown@example.com"),
    )

    lines = []
    for item in order.get("line_items", []):
        lines.append([0, 0, {
            "name": item.get("name", item.get("product_name", "Item")),
            "product_uom_qty": item.get("quantity", 1),
            "price_unit": item.get("price", item.get("unit_price", 0)),
        }])

    order_id = execute(models, db, uid, api_key, "sale.order", "create", [{
        "partner_id": partner_id,
        "client_order_ref": order.get("order_number", ""),
        "note": order.get("note", "Imported from Shopify"),
        "order_line": lines,
    }])

    # Confirm order
    execute(models, db, uid, api_key, "sale.order", "action_confirm", [[order_id]])

    # Create invoice
    wizard_id = execute(models, db, uid, api_key, "sale.advance.payment.inv", "create",
                        [{}], {"context": {"active_ids": [order_id], "active_model": "sale.order"}})
    execute(models, db, uid, api_key, "sale.advance.payment.inv", "create_invoices",
            [[wizard_id]], {"context": {"active_ids": [order_id], "active_model": "sale.order"}})

    return {"order_id": order_id, "partner_id": partner_id}

def get_financial_summary(models, db, uid, api_key):
    today = datetime.date.today()
    date_from = today.replace(day=1).isoformat()
    date_to   = today.isoformat()

    invoices = execute(models, db, uid, api_key, "account.move", "search_read",
        [[["move_type","=","out_invoice"],["state","=","posted"],
          ["invoice_date",">=",date_from],["invoice_date","<=",date_to]]],
        {"fields": ["amount_total"]})

    revenue = sum(i["amount_total"] for i in invoices)
    return {"period": f"{date_from} to {date_to}", "total_revenue": revenue, "invoice_count": len(invoices)}

def main():
    env = load_env()
    if not all(env.get(k) for k in ["ODOO_URL","ODOO_DB","ODOO_USERNAME","ODOO_API_KEY"]):
        print("[!] Odoo credentials not configured in .env — skipping sync")
        return

    models, db, uid, api_key = odoo_connect(env)
    print(f"[*] Connected to Odoo: {env['ODOO_URL']}")

    # Find order summaries in Inbox/
    inbox_files = glob.glob(str(VAULT / "Inbox" / "ORDER_*.md"))
    if not inbox_files:
        print("[*] No order summaries found in /Inbox/ — nothing to sync")
        return

    log = {"timestamp": datetime.datetime.now().isoformat(),
           "orders_synced": 0, "invoices_created": 0, "errors": []}

    for fpath in inbox_files:
        try:
            # Parse basic fields from markdown (order_reader format)
            content = open(fpath, encoding="utf-8").read()
            # Extract JSON block if present
            import re
            m = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if m:
                order = json.loads(m.group(1))
            else:
                print(f"[!] No JSON in {fpath} — skipping")
                continue

            result = sync_order(models, db, uid, api_key, order)
            print(f"[OK] Synced {order.get('order_number','?')} → Odoo order #{result['order_id']}")
            log["orders_synced"] += 1
            log["invoices_created"] += 1

        except Exception as e:
            print(f"[!] Error syncing {fpath}: {e}")
            log["errors"].append({"file": fpath, "error": str(e)})

    # Financial summary
    try:
        log["financial_summary"] = get_financial_summary(models, db, uid, api_key)
        print(f"[*] MTD Revenue: ${log['financial_summary']['total_revenue']:.2f}")
    except Exception as e:
        print(f"[!] Could not get financial summary: {e}")

    # Write log
    log_path = VAULT / "Logs" / f"odoo_sync_{datetime.date.today()}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)
    print(f"[*] Log written: {log_path}")

if __name__ == "__main__":
    main()
