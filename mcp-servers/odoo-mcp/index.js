#!/usr/bin/env node
/**
 * Odoo MCP Server — AI Employee Vault
 * Connects to Odoo.com (cloud) via XML-RPC API
 * Tools: create_sale_order, create_invoice, get_financial_summary,
 *        update_inventory, search_products, get_sale_orders
 */

require("dotenv").config({ path: "E:/AI_Employee_Vault/.env" });
const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const { CallToolRequestSchema, ListToolsRequestSchema } = require("@modelcontextprotocol/sdk/types.js");
const xmlrpc = require("xmlrpc");
const https = require("https");
const url = require("url");

// ── Config ────────────────────────────────────────────────────────────────────
const ODOO_URL      = process.env.ODOO_URL      || "";
const ODOO_DB       = process.env.ODOO_DB       || "";
const ODOO_USERNAME = process.env.ODOO_USERNAME || "";
const ODOO_API_KEY  = process.env.ODOO_API_KEY  || "";

// ── Odoo XML-RPC Client ───────────────────────────────────────────────────────
function makeClient(path) {
  const parsed = url.parse(ODOO_URL);
  const opts = {
    host: parsed.hostname,
    path: path,
    port: parsed.port || (parsed.protocol === "https:" ? 443 : 80),
  };
  return parsed.protocol === "https:"
    ? xmlrpc.createSecureClient(opts)
    : xmlrpc.createClient(opts);
}

function callRpc(path, method, params) {
  return new Promise((resolve, reject) => {
    const client = makeClient(path);
    client.methodCall(method, params, (err, val) => {
      if (err) reject(err);
      else resolve(val);
    });
  });
}

async function authenticate() {
  const uid = await callRpc("/xmlrpc/2/common", "authenticate", [
    ODOO_DB, ODOO_USERNAME, ODOO_API_KEY, {},
  ]);
  if (!uid) throw new Error("Odoo authentication failed — check credentials");
  return uid;
}

async function execute(model, method, args = [], kwargs = {}) {
  const uid = await authenticate();
  return callRpc("/xmlrpc/2/object", "execute_kw", [
    ODOO_DB, uid, ODOO_API_KEY, model, method, args, kwargs,
  ]);
}

// ── Tool Implementations ──────────────────────────────────────────────────────

async function searchProducts({ query = "", limit = 10 }) {
  const domain = query ? [["name", "ilike", query]] : [];
  const products = await execute("product.product", "search_read", [domain], {
    fields: ["id", "name", "list_price", "qty_available", "default_code"],
    limit,
  });
  return products;
}

async function getSaleOrders({ limit = 20, state = "all" }) {
  const domain = state === "all" ? [] : [["state", "=", state]];
  const orders = await execute("sale.order", "search_read", [domain], {
    fields: ["id", "name", "partner_id", "amount_total", "state", "date_order"],
    limit,
    order: "date_order desc",
  });
  return orders;
}

async function createSaleOrder({ customer_name, customer_email, order_ref, lines, note = "" }) {
  // Find or create customer
  let partnerIds = await execute("res.partner", "search", [[["email", "=", customer_email]]]);
  let partnerId;
  if (partnerIds.length > 0) {
    partnerId = partnerIds[0];
  } else {
    partnerId = await execute("res.partner", "create", [{
      name: customer_name,
      email: customer_email,
    }]);
  }

  // Build order lines
  const orderLines = lines.map(line => [0, 0, {
    name: line.description || line.product_name,
    product_uom_qty: line.quantity || 1,
    price_unit: line.unit_price || 0,
  }]);

  const orderId = await execute("sale.order", "create", [{
    partner_id: partnerId,
    client_order_ref: order_ref || "",
    note: note,
    order_line: orderLines,
  }]);

  return { order_id: orderId, partner_id: partnerId };
}

async function createInvoice({ sale_order_id }) {
  // Confirm the sale order first if in draft
  const [order] = await execute("sale.order", "read", [[sale_order_id]], {
    fields: ["state", "name"],
  });

  if (order.state === "draft" || order.state === "sent") {
    await execute("sale.order", "action_confirm", [[sale_order_id]]);
  }

  // Create invoice from sale order
  const invoiceContext = { active_ids: [sale_order_id], active_model: "sale.order" };
  const invoiceWizardId = await execute("sale.advance.payment.inv", "create", [{}], {
    context: invoiceContext,
  });
  await execute("sale.advance.payment.inv", "create_invoices", [[invoiceWizardId]], {
    context: invoiceContext,
  });

  // Get the created invoice
  const invoices = await execute("account.move", "search_read",
    [[["invoice_origin", "like", order.name]]],
    { fields: ["id", "name", "amount_total", "state", "invoice_date"], limit: 1 }
  );

  return invoices[0] || { message: "Invoice created but could not retrieve details" };
}

async function getFinancialSummary({ period = "this_month" }) {
  const today = new Date();
  let dateFrom, dateTo;

  if (period === "this_month") {
    dateFrom = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split("T")[0];
    dateTo   = today.toISOString().split("T")[0];
  } else if (period === "last_month") {
    const first = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    const last  = new Date(today.getFullYear(), today.getMonth(), 0);
    dateFrom = first.toISOString().split("T")[0];
    dateTo   = last.toISOString().split("T")[0];
  } else {
    // this_year
    dateFrom = `${today.getFullYear()}-01-01`;
    dateTo   = today.toISOString().split("T")[0];
  }

  // Get posted invoices (revenue)
  const invoices = await execute("account.move", "search_read",
    [[
      ["move_type", "=", "out_invoice"],
      ["state", "=", "posted"],
      ["invoice_date", ">=", dateFrom],
      ["invoice_date", "<=", dateTo],
    ]],
    { fields: ["name", "amount_total", "invoice_date", "partner_id"] }
  );

  const totalRevenue = invoices.reduce((s, i) => s + i.amount_total, 0);
  const orderCount   = invoices.length;

  // Get unpaid invoices
  const unpaid = await execute("account.move", "search_read",
    [[
      ["move_type", "=", "out_invoice"],
      ["payment_state", "in", ["not_paid", "partial"]],
      ["state", "=", "posted"],
    ]],
    { fields: ["name", "amount_residual", "partner_id"] }
  );
  const totalOutstanding = unpaid.reduce((s, i) => s + i.amount_residual, 0);

  return {
    period,
    date_from: dateFrom,
    date_to: dateTo,
    total_revenue: totalRevenue,
    invoice_count: orderCount,
    outstanding_receivables: totalOutstanding,
    invoices: invoices.slice(0, 5), // top 5 for preview
  };
}

async function updateInventory({ product_id, new_quantity, location = "WH/Stock" }) {
  // Find stock location
  const locations = await execute("stock.location", "search_read",
    [[["complete_name", "ilike", location], ["usage", "=", "internal"]]],
    { fields: ["id", "complete_name"], limit: 1 }
  );
  if (!locations.length) throw new Error(`Location '${location}' not found`);
  const locationId = locations[0].id;

  // Create inventory adjustment
  const inventoryId = await execute("stock.quant", "create", [{
    product_id: product_id,
    location_id: locationId,
    inventory_quantity: new_quantity,
  }]);

  await execute("stock.quant", "action_apply_inventory", [[inventoryId]]);

  return { product_id, new_quantity, location: locations[0].complete_name };
}

// ── MCP Server ────────────────────────────────────────────────────────────────
const server = new Server(
  { name: "odoo-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "search_products",
      description: "Search products in Odoo inventory",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string", description: "Product name to search (empty = all)" },
          limit: { type: "number", description: "Max results (default 10)" },
        },
      },
    },
    {
      name: "get_sale_orders",
      description: "Get recent sales orders from Odoo",
      inputSchema: {
        type: "object",
        properties: {
          limit: { type: "number", description: "Number of orders to return (default 20)" },
          state: {
            type: "string",
            enum: ["all", "draft", "sale", "done", "cancel"],
            description: "Filter by order state",
          },
        },
      },
    },
    {
      name: "create_sale_order",
      description: "Create a new sales order in Odoo from a Shopify order",
      inputSchema: {
        type: "object",
        required: ["customer_name", "customer_email", "lines"],
        properties: {
          customer_name:  { type: "string" },
          customer_email: { type: "string" },
          order_ref:      { type: "string", description: "Shopify order number e.g. #1001" },
          note:           { type: "string" },
          lines: {
            type: "array",
            items: {
              type: "object",
              properties: {
                product_name: { type: "string" },
                description:  { type: "string" },
                quantity:     { type: "number" },
                unit_price:   { type: "number" },
              },
            },
          },
        },
      },
    },
    {
      name: "create_invoice",
      description: "Create and confirm an invoice from an existing Odoo sale order",
      inputSchema: {
        type: "object",
        required: ["sale_order_id"],
        properties: {
          sale_order_id: { type: "number", description: "Odoo sale order ID" },
        },
      },
    },
    {
      name: "get_financial_summary",
      description: "Get revenue, invoice count, and outstanding receivables from Odoo",
      inputSchema: {
        type: "object",
        properties: {
          period: {
            type: "string",
            enum: ["this_month", "last_month", "this_year"],
            description: "Reporting period (default: this_month)",
          },
        },
      },
    },
    {
      name: "update_inventory",
      description: "Update product stock quantity in Odoo warehouse",
      inputSchema: {
        type: "object",
        required: ["product_id", "new_quantity"],
        properties: {
          product_id:   { type: "number", description: "Odoo product ID" },
          new_quantity: { type: "number", description: "New stock quantity" },
          location:     { type: "string", description: "Warehouse location (default: WH/Stock)" },
        },
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (!ODOO_URL || !ODOO_DB || !ODOO_USERNAME || !ODOO_API_KEY) {
    return {
      content: [{ type: "text", text: "❌ Odoo credentials not configured. Set ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_API_KEY in .env" }],
      isError: true,
    };
  }

  try {
    let result;
    switch (name) {
      case "search_products":      result = await searchProducts(args);           break;
      case "get_sale_orders":      result = await getSaleOrders(args);            break;
      case "create_sale_order":    result = await createSaleOrder(args);          break;
      case "create_invoice":       result = await createInvoice(args);            break;
      case "get_financial_summary": result = await getFinancialSummary(args);     break;
      case "update_inventory":     result = await updateInventory(args);          break;
      default:
        return { content: [{ type: "text", text: `Unknown tool: ${name}` }], isError: true };
    }
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  } catch (err) {
    return { content: [{ type: "text", text: `Error: ${err.message}` }], isError: true };
  }
});

const transport = new StdioServerTransport();
server.connect(transport).then(() => {
  process.stderr.write("Odoo MCP server running\n");
});
