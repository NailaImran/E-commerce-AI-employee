# Shopify Order Export — Column Reference

Standard columns in a Shopify Orders CSV export (Admin > Orders > Export).

## Core Order Fields
| Column | Description | Example |
|--------|-------------|---------|
| Name | Order number | #1001 |
| Email | Customer email | jane@example.com |
| Financial Status | Payment state | paid / pending / refunded / voided |
| Fulfillment Status | Shipping state | fulfilled / unfulfilled / partial |
| Currency | 3-letter code | USD / PKR / GBP |
| Subtotal | Before shipping/tax | 45.00 |
| Shipping | Shipping cost | 5.00 |
| Taxes | Tax amount | 4.50 |
| Total | Final amount | 54.50 |
| Discount Code | Applied coupon | SUMMER10 |
| Discount Amount | Discount value | 5.00 |
| Created at | ISO timestamp | 2026-02-21T10:30:00+05:00 |
| Notes | Customer notes | "Please gift wrap" |

## Line Item Fields (one row per item)
| Column | Description |
|--------|-------------|
| Lineitem name | Product name |
| Lineitem quantity | Qty ordered |
| Lineitem price | Unit price |
| Lineitem compare at price | Original price (if on sale) |
| Lineitem sku | Product SKU |
| Lineitem requires shipping | true/false |
| Lineitem taxable | true/false |
| Lineitem fulfillment status | Per-item fulfillment |

## Shipping Address Fields
| Column | Description |
|--------|-------------|
| Shipping Name | Recipient name |
| Shipping Street | Street address |
| Shipping Address1 | Address line 1 |
| Shipping Address2 | Address line 2 |
| Shipping Company | Company name |
| Shipping City | City |
| Shipping Zip | Postal code |
| Shipping Province | State/Province |
| Shipping Country | Country name |
| Shipping Phone | Phone number |

## Billing Address Fields
Same as Shipping with "Billing" prefix.

## Payment Fields
| Column | Description |
|--------|-------------|
| Payment Method | e.g. Credit Card, COD |
| Payment Reference | Transaction ID |

## Notes
- Multi-item orders appear as multiple rows with the same `Name`
- The parser groups rows by `Name` to count items per order
- Empty `Email` may indicate a draft or POS order
