---
name: agentic-surface
description: Use when building, probing, or auditing the machine-readable surface of a storefront — UCP profile, MCP cart/checkout/catalog endpoints, agentic-catalog eligibility, product route shape, or agent identity. Carries dated protocol cutovers.
version: 1.0.0
verified_at: 2026-08-01
expires: 2026-11-01
allowed_tools: ""
---
# Agentic surface

**Dated knowledge.** Verified 2026-08-01 against the platform's own changelog, its
agent documentation, its Catalog requirements pages, and two developer-forum
threads carrying staff answers. Re-verify by **2026-11-01**.

This surface moves faster than any other in the kit — **two tool removals already
happened on schedule** in the four months before this pack was written. A protocol
cutover held only in a chat transcript is precisely the failure that dated packs
exist to prevent, so every date below carries its consequence, not just its fact.

An auditor reading this pack past its `expires` date must say so in its findings
rather than silently trusting stale endpoints.

## 1. The cutover calendar

| Date | Event | Consequence |
|---|---|---|
| **2026-04-22** | Storefront Catalog MCP migrated to UCP | legacy tool names accepted through 2026-06-15 |
| **2026-06-15** | legacy catalog tool names **removed** | `search_*` / `lookup_*` no longer resolve; use `search_catalog` / `lookup_catalog` |
| **2026-06-24** | cart tools deprecated in favour of UCP Cart MCP | **the cutover happened here** — the new path is live from this date |
| **2026-08-31** | legacy `get_cart` / `update_cart` on `/api/mcp` **removed** | a consumer still on the old path stops working entirely |

**Read that table carefully, because the obvious misreading is expensive.**
2026-08-31 is a **removal** date, not a migration date. The migration opened on
2026-06-24 and the new endpoint is live now. There is nothing to wait for, and a
plan that schedules work "before the cutover" has already missed it.

Two removals landing on their announced dates is the evidence that matters here:
on this platform, deprecation notices are not advisory.

## 2. Endpoints, and which one needs a credential

| Server | Path | Tools | Auth |
|---|---|---|---|
| Cart MCP | `/api/ucp/mcp` on the shop domain | `create_cart`, `get_cart`, `update_cart`, `cancel_cart` | **none** |
| Checkout MCP | `/api/ucp/mcp` on the shop domain | `create_checkout`, `get_checkout`, `update_checkout`, `complete_checkout`, `cancel_checkout` | **OAuth bearer token** |
| Catalog MCP | `/api/ucp/mcp` on the shop domain | `search_catalog`, `lookup_catalog`, `get_product` | none |
| Legacy Storefront MCP | `/api/mcp` on the shop domain | policy/FAQ search survives; the two cart tools die 2026-08-31 | none |

**The auth asymmetry is a trap.** Cart and Catalog need no credential, so it is
natural to conclude the whole UCP path is credential-free. **Checkout MCP requires a
real bearer token.** A design built on "no credentials anywhere in this path" works
all the way through browsing and cart assembly and then fails at the one step that
moves money.

Contract details: JSON-RPC 2.0; every request carries `meta["ucp-agent"].profile`, a
URL to the calling agent's profile JSON. The three destructive operations —
`cancel_cart`, `complete_checkout`, `cancel_checkout` — additionally require
`meta["idempotency-key"]` as a UUID. Capability `dev.ucp.shopping.cart`, dated
version `2026-04-08`.

**`update_cart` has PUT semantics.** Each call replaces the full cart state; it is
not a patch. A caller that sends only the changed line silently discards the rest of
the cart.

## 3. Who serves the UCP profile — not us

The platform **generates** the business profile when agentic storefronts are enabled
and serves it at `{shop-subdomain}/.well-known/ucp` and on the managed checkout
domain. Platform staff answered this directly in the developer forums
(2026-01-29, updated 2026-07-27): there is *"not currently a supported way to edit or
replace that profile"*, and a consumer **should not host, proxy, or redirect it** —
including on a custom domain.

**So the correct posture on this platform is verify-and-report, never publish.** A
storefront may build an entirely independent implementation on its own
infrastructure, but it is *additional to* the managed endpoint, not a replacement.

Two consequences for anyone writing a profile-related contract:

- A **404 on the custom domain is expected**, not a defect. An audit that scores it
  red is wrong.
- Self-publishing belongs only to **non-platform storefronts**, and every place it
  appears must name the platform it applies to.

## 4. Catalog eligibility

Store level: the paid-plan floor or above; **not password-protected**; sells to
customers in the United States; **Terms of service, Privacy policy, and Return and
refund policy all completed**; the merchant has accepted the agentic-storefront
supplemental terms. Account standing additionally requires genuine sales history,
prompt fulfilment, low chargebacks, and identity verification.

Product level: a title and **at least one image**; price **greater than zero** —
free products are excluded outright; published to a storefront sales channel; an
identifiable product URL; not unlisted; not hidden from search engines.

Three notes that are easy to get wrong:

1. **The policy pages are an eligibility gate, not just a legal obligation.** A store
   missing them is invisible to every agentic channel regardless of its catalog.
2. **Development stores can never qualify** — they are permanently password-protected,
   so they fail the password gate rather than a named exclusion. Watch for records
   claiming a separate "trial store" rule; no such rule is published.
3. **Eligibility is earned by trading, not provisioned.** No freshly created store
   qualifies at birth. A factory can stamp everything else; it cannot stamp standing.
   Any plan promising "repo to agent-ready store in one session" is overclaiming — say
   so rather than designing around it.

## 5. The product route is a hard requirement

A headless storefront **must** use the expected route format to be included in the
agentic catalog. The standard is **`/products/<handle>`** with the platform's product
handle verbatim. A storefront using a different structure must provide a
**server-side 3XX redirect** from the expected path — client-side redirection does
not satisfy it.

**Do not localize or prefix the canonical product path.** A prettier URL is fine as
long as the canonical one still resolves.

**The catalog is fed from the platform's own product records, not by crawling
storefront HTML.** So structured data and sitemaps do **not** gate agentic-catalog
inclusion — they serve general search crawlers, which is a separate pipeline over the
same canonical product record. Conflating the two leads to auditing the wrong artifact.

## 6. Agent identity and rate limits

Higher rate limits for automated traffic are documented as reachable through
**RFC 9421 HTTP Message Signatures** (Web Bot Auth), which lets a well-behaved agent
identify itself cryptographically rather than being treated as anonymous traffic.

**Carried knowledge, not re-fetched this pass.** The RFC itself is stable, but the
platform-side mechanism for registering a signing key and the limits actually granted
were not verified on 2026-08-01. Treat the direction as sound and **re-verify the
specifics before building against them**; do not quote a limit number from this pack.

## 7. What a headless storefront owes agents

| Artifact | Status |
|---|---|
| the `/products/<handle>` route | **required** |
| product published to a storefront channel | **required** |
| `/.well-known/ucp` on the storefront domain | **do not build** — platform-managed |
| an MCP endpoint on the storefront domain | **do not build** — platform-managed |
| product feed | not required for the agentic catalog; still required for shopping-ad surfaces |
| `sitemap.xml`, `robots.txt` | the framework generates both |
| canonical URL | recommended |
| product structured data | recommended; effectively required for merchant listings on general search |
| `/llms.txt`, `/agents.md` | **must be hand-built on headless** — the platform's defaults are theme templates and a headless storefront renders none of them, so all such paths 404 |

**Non-production preview deployments are served a disallow-all robots file by
design.** Never diagnose agent visibility against a preview URL — an absence there
proves nothing.

## 8. Audit behaviour

An audit of this surface is never "compliant" as one flag. Classify per item, the
same discipline the disclosure-matrix and compliance packs use.

- **Treat pack expiry as blocking.** Past `expires`, report the staleness as a finding
  in its own right before reporting anything else.
- **A 404 for the profile on a custom domain is a PASS.** So is an empty agentic
  catalog for a store that has never traded. Classify correct-empty against
  broken-empty before scoring anything red.
- **Name the date and the source** for every protocol claim, so a reader can tell a
  current fact from a carried one.
- **Never assert a limit, endpoint, or tool name from memory.** Two tool families were
  renamed and removed within four months of this pack being written.
