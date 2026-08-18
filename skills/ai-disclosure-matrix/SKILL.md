---
name: ai-disclosure-matrix
description: Use when deciding whether an AI-generated or AI-assisted asset requires disclosure on a given channel, and by what mechanism.
version: 1.0.0
verified_at: 2026-07-28
expires: 2026-10-28
allowed_tools: ""
---
# AI disclosure matrix

**Dated knowledge.** Verified 2026-07-28; re-verify by 2026-10-28. Regimes in
this area change on short notice and one has a hard compliance date inside this
window. A judge reading this pack past its expiry must say so in its findings.

Disclosure is a **per-channel classification**. A single global "this is AI"
flag is always wrong somewhere — the regimes disagree about what counts, who
must label, and by what mechanism.

## The distinction every decision turns on

| Asset class | General treatment |
| --- | --- |
| AI-**assisted text** (captions, product copy, scripts) | Usually exempt from media-labeling rules |
| **Synthetic media** depicting realistic people, places, or events | Labeling required on most surfaces |
| AI-generated imagery of the **product itself** | Depends on whether it misrepresents physical characteristics |
| Assistive edits (background removal, colour correction) | Generally permitted; some marketplaces still count it |

## Per-channel decisions

| Channel | Text | Synthetic media | Mechanism |
| --- | --- | --- | --- |
| Instagram / Facebook | Not required | Required | Platform toggle + preserved provenance metadata; platform also auto-detects |
| TikTok | Exempt | Required | Platform toggle; auto-detection from provenance metadata |
| YouTube | Exempt | Required | Altered-content disclosure at upload |
| Threads | Not required | Required | Same regime as its parent platform |
| Pinterest | Not required | Required | Provenance metadata |
| Own storefront (EU-facing) | Machine-readable marking obligation applies to synthetic media | Required | Embedded provenance + on-page notice |
| Marketplaces | Varies — some require an explicit attribution field even for assistive edits | Required | Per-marketplace field; assume stricter until verified |
| Paid ads (any platform) | Not required | Required | Platform toggle; undisclosed AI is a top rejection category |

**A platform's own toggle satisfies that platform and nothing else.** It never
discharges a jurisdiction's obligation, and at least one platform says so
explicitly in its own policy.

## Provenance metadata

Generated media carries an embedded provenance signature. **Re-encoding strips
it silently** — a naive transcode between formats or a resize can drop it.

Rule: verify the signature is present on the final asset, not the source. A
missing signature on a generated asset is a blocking finding requiring
re-export. It is never fixed by adding a caption.

## The hard prohibition — no disclosure fixes this

A synthetic person delivering a **first-person customer experience** — a
testimonial, a review, an endorsement, "I bought this and…" — is a fabricated
consumer testimonial. It is prohibited outright, carries per-violation
penalties, and **is not made compliant by any label**.

Blocked on every channel. The asset must be re-cut without the testimonial
framing. Aspirational and second-person copy is unaffected.

## Judge behaviour

1. Emit a distinct decision per destination channel, with channel-specific
   rationale. One verdict repeated is a sign the classification was not done.
2. Echo this pack's version and `verified_at`. Past `expires`, add a finding.
3. Fail closed on an unknown channel or an unreadable asset.
4. Name the requirement; never opine that something is legal. This pack is
   operational guidance, not legal advice.
