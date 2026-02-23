---
name: email-responder
description: Reads customer emails from /Needs_Action/ (written by Gmail Watcher), classifies them by type (order query, complaint, refund request, shipping question), drafts a professional reply, and creates a HITL approval file in /Pending_Approval/. Use when EMAIL_*.md files appear in /Needs_Action/, when asked to "draft email replies", "respond to customer emails", or "handle customer messages". Never sends emails autonomously — always creates an approval file first.
---

# Email Responder

## Overview

Classifies incoming customer emails, drafts context-aware replies using Company_Handbook.md tone rules, and writes approval files to /Pending_Approval/ for human review before any email is sent.

## Workflow

1. Read all `EMAIL_*.md` files in `/Needs_Action/`
2. For each email: classify type and draft reply
3. Write approval file to `/Pending_Approval/`
4. Move processed email file to `/Done/`
5. Update Dashboard.md (pending approvals count)

## Email Classification

| Type | Trigger Keywords | Reply Tone |
|------|-----------------|------------|
| `order_query` | order status, tracking, where is, when will | Informative, reassuring |
| `complaint` | wrong item, broken, damaged, not happy, terrible | Apologetic, solution-focused |
| `refund_request` | refund, return, money back, cancel | Empathetic, process-clear |
| `shipping_query` | shipping, delivery, address, dispatch | Helpful, specific |
| `general` | anything else | Friendly, professional |

## Drafting Rules

Always read `Company_Handbook.md` before drafting. Key rules:
- Tone: friendly, professional, concise (under 150 words)
- Sign off as: "[Store Name] Team"
- For complaints: always acknowledge first, then offer solution
- For refunds: explain the process, do NOT promise refund autonomously — mark as HITL
- Never include order details you cannot verify from vault files

## Output: Approval File

Write to `/Pending_Approval/EMAIL_REPLY_<timestamp>.md`:

```markdown
---
type: email_reply_approval
action: send_email
original_email_id: <source file name>
to: customer@example.com
subject: Re: Your Order #1001
created: 2026-02-21T10:30:00
expires: 2026-02-22T10:30:00
status: pending
classification: order_query
---

## Drafted Reply

Dear [Customer Name],

Thank you for reaching out! Your order #1001 is currently being prepared
for dispatch and should ship within 24 hours. You will receive a tracking
email once it's on its way.

Feel free to contact us if you need anything else.

Best regards,
[Store Name] Team

---
## To Approve
Move this file to `/Approved/` — the approval watcher will send the email.

## To Edit
Edit the reply above, then move to `/Approved/`.

## To Reject
Move this file to `/Rejected/`.
```

## Error Handling

- Missing customer email address in source file: write `ESCALATE_no_email_<timestamp>.md` to `/Needs_Action/`
- Complaint requiring refund > $50: always HITL, add `requires_manager_review: true` to frontmatter
- Expired approval (> 24h): write `EXPIRED_<filename>` to `/Done/` without sending

## References

- `references/reply_templates.md` — reply templates by classification type
