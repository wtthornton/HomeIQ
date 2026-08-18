---
name: site-compliance
description: Use when drafting, publishing, or auditing storefront pages (privacy policy, cookie banner, checkout price display, or any customer-facing page) for privacy, consent, accessibility, or price-display compliance.
version: 1.1.0
verified_at: 2026-08-01
expires: 2026-10-01
allowed_tools: ""
---
# Site compliance

**Dated knowledge.** Re-verified 2026-08-01 against primary regulator/vendor
sources; re-verify by 2026-10-01. The expiry was **shortened** from 2026-10-28
because two dates land just after it: the expected OJ citation of EN 301 549
V4.1.1 (~Oct 2026) and the AI Act Art. 50(2) grace-period expiry (2026-12-02). Every regime below is already in force —
none of this is "coming soon" — so a storefront live today is already
out of compliance wherever it fails these rules, not merely at risk. A judge
reading this pack past its `expires` date must say so in its findings rather
than silently trusting stale thresholds.

**Five** surfaces. A storefront-audit decision is never "compliant" as one flag —
classify per surface, the same discipline the disclosure-matrix pack uses for
AI-content labelling.

## 1. Privacy policy & terms of service

Baseline: California CCPA/CPRA (amendments effective 2023-01-01; source: CA
Attorney General, retrieved 2026-07-28).

- Applies to a for-profit business meeting **any** of: annual gross revenue
  > $25M; buys/sells/shares personal information of ≥100,000 CA
  residents/households; or derives ≥50% of annual revenue from selling
  personal information. A small storefront may be exempt on revenue/volume —
  check the threshold, don't assume coverage either way.
- A covered site's privacy policy must disclose: categories of personal
  information collected, the right to know, delete, correct, opt out of
  sale/share, and limit use of sensitive personal information, plus the
  non-discrimination guarantee.
- A covered site that sells or shares personal information must carry a
  **clear and conspicuous "Do Not Sell or Share My Personal Information"**
  link, reachable without forcing account creation.
- GDPR (EU-facing traffic) layers on top: lawful basis per processing
  purpose, data controller identity, and the same access/delete/portability
  rights — treat as the stricter baseline for any site with EU visitors,
  independent of the CCPA threshold test.

**Finding, not a rule:** neither CCPA nor GDPR is a single pass/fail toggle.
Audit each disclosure element and each right's fulfillment mechanism
separately.

## 2. Cookie consent & Google Consent Mode v2

Primary source: Google's own consent-mode documentation, retrieved
2026-07-28.

- Consent Mode v2 requires two consent signals beyond the original
  `ad_storage`/`analytics_storage`: **`ad_user_data`** (consent to send
  advertising-related user data to Google) and **`ad_personalization`**
  (consent for personalized advertising). Both take `granted`/`denied`.
- Scope: sites serving **EEA traffic** must collect and forward these
  signals to keep using Google Ads/Analytics tags for measurement,
  remarketing, and ad personalization on that traffic. Google's own
  documentation frames the consequence as degraded measurement and lost
  remarketing/personalization capability, not an outright tag block —
  **no single hard enforcement date was found in Google's own help content
  this pass; do not assert one without re-checking.**
- Underlying obligation this exists to satisfy: EU ePrivacy rules require
  **opt-in before non-essential cookies load** — the consent banner must
  gate script execution, not just record a preference after the fact.
- A storefront serving EU/EEA traffic needs both: (a) a pre-consent cookie
  gate, and (b) Consent Mode v2's two signals wired to that same gate state.
  Shipping one without the other is a partial implementation.

### Consent record-keeping (added 2026-08-01)

GDPR **Art. 7(1)** requires the controller to be able to **demonstrate** consent;
**Art. 5(2)** makes that an accountability duty. Per EDPB Guidelines 05/2020 and
ICO guidance, a record should capture **who** consented, **when**, **how** (the
mechanism), **what they were told** — the notice/banner version live at that
moment — and any **withdrawal**. No format is prescribed.

Retention: ICO says keep it as long as processing on that consent continues, then
per limitation periods. CNIL treats **6 months** as good practice for how long a
consent *choice* stays valid before re-asking. **Do not confuse that with CNIL's
13-month figure, which is the maximum lifetime of the tracking cookie itself, not
of the record.**

**Correction to a claim this project has repeated:** it is not true that Shopify's
native banner keeps *no* consent log. Shopify's changelog (2025-05-21) documents an
audit log of consent preferences from the **past 30 days**. The accurate statement
is that Shopify provides a **30-day, banner-scoped, undocumented-schema log with no
export API and no confirmed headless coverage** — the Admin GraphQL `consentPolicy`
returns shop-level regional config, not a per-visitor log. So the conclusion (a
headless template must build its own persistent, queryable consent-event store)
survives, but the reason is retention and scope, not absence.

**Headless specifics:** Shopify's banner does **not** render on Hydrogen
automatically — opt in via the analytics provider's consent config or sync a CMP
into the Customer Privacy API. Gate on `analyticsProcessingAllowed()`,
`marketingAllowed()`, `preferencesAllowed()`, `saleOfDataAllowed()`. Note that
`emailMarketingConsent` / `smsMarketingConsent` are **marketing** consent — a
different legal purpose, not cookie consent, and not interchangeable with it.

## 3. Accessibility — European Accessibility Act (EAA)

Primary source: Directive (EU) 2019/882, Article 2, via eur-lex.europa.eu,
retrieved 2026-07-28.

- **Application date: 2025-06-28** — exact text: "This Directive applies to
  ... products placed on the market after 28 June 2025" and "... services
  provided to consumers after 28 June 2025." That date is in the past
  relative to this pack's `verified_at` — **e-commerce is explicitly a
  covered service**, so any EU-facing storefront live today is already
  inside the compliance window, not approaching it.
- Covered services explicitly include e-commerce (alongside banking,
  e-books, telephony, audiovisual media, and passenger transport).
- Technical standard — **CORRECTED 2026-08-01, the earlier claim was wrong.**
  **No harmonised standard has been cited in the Official Journal for the EAA**,
  so there is currently **no formal presumption of conformity** under it.
  EN 301 549 V3.2.1 was harmonised for the *Web Accessibility Directive*
  2016/2102, a different instrument. Standardisation request M/587 is open;
  draft V4.1.0 went to public enquiry Nov 2025 and **V4.1.1, incorporating
  WCAG 2.2 Level AA**, is expected to be OJ-cited around Oct 2026 (industry
  estimate, not an official date).
- So EN 301 549 V3.2.1 / WCAG 2.1 AA is a **de facto reference only**. The AA
  level is right for today, but **build to WCAG 2.2 AA** — it has been a W3C
  Recommendation since 2023-10-05 and is what V4.1.1 will carry. WCAG 3.0 is a
  Working Draft, not before 2028.
- **US caution:** the DOJ's 2024 WCAG 2.1 AA rule is **ADA Title II, public
  sector only**. Title III has no DOJ regulation and no codified technical
  standard for private sites; WCAG AA is a de facto litigation benchmark
  (3,117 federal web-accessibility suits in 2025, up 27% year on year).
- Practical bar for an audit: keyboard navigability, sufficient colour
  contrast, alt text on informative images, form labels/error identification,
  and no content that relies on a single sense (colour-only status, audio
  without captions).

## 4. Price-display rules

Two independent, non-overlapping regimes — a storefront selling into both
must satisfy both.

**EU — Omnibus Directive "prior price" rule.** Primary source: Directive
(EU) 2019/2161, Article 2 (amending Directive 98/6/EC, new Article 6a), via
eur-lex.europa.eu, retrieved 2026-07-28.

- Exact rule: "Any announcement of a price reduction shall indicate the
  prior price applied by the trader for a determined period of time prior to
  the application of the price reduction."
- Prior price = **the lowest price applied by the trader in the 30 days**
  before the reduction — not the last list price, not an arbitrary "was"
  price. Member states may shorten the window for fast-perishable goods or
  goods on the market under 30 days, and may permit progressive-discount
  chains to reference the price before the *first* reduction.
- A storefront displaying a struck-through "was" price to an EU buyer must
  be able to show that "was" price was genuinely the 30-day low, not a
  marketing anchor.
- **Case C-330/23 (Verbraucherzentrale Baden-Wuerttemberg v Aldi Sued),
  judgment 26 September 2024 — added 2026-08-01, and it is controlling.** A
  **percentage** discount must be calculated against the Art. 6a 30-day-low
  prior price, not against the immediately preceding price. This applies to
  "price highlight" badges too, so a template rendering "-30%" from yesterday's
  price is non-compliant even where its struck-through figure is correct.

**US — drip pricing / all-in pricing.** Primary source: California SB 478,
via leginfo.legislature.ca.gov, retrieved 2026-07-28. Effective **2024-07-01**.

- Prohibits advertising, displaying, or offering a price that excludes
  mandatory fees or charges — the displayed price must be the true all-in
  price, excluding only taxes, government-imposed fees, and shipping.
  Applies broadly to consumer goods/services transactions, not one industry;
  named exceptions include vehicle rentals/leases/dealers, air transport,
  auctions, and food-delivery platforms listing restaurant prices.
- This is broader than the federal "Rule on Unfair or Deceptive Fees" (FTC,
  finalized Dec 2024), which — per general knowledge, **not independently
  **CONFIRMED 2026-08-01 against 16 CFR 464.1 via eCFR** — is scoped to
  live-event tickets and short-term lodging only. The final rule narrowed
  drastically from the 2023 NPRM, took effect 2025-05-12, and is actively
  enforced. **A storefront selling physical goods is out of federal scope as
  written.** This is no longer carried knowledge.

  **What actually binds a goods storefront is the state patchwork:** California
  SB 478 (2024-07-01), Minnesota (2025-01-01), Massachusetts (~Mar 2025),
  Virginia (2025-07-01), Colorado (2026-01-01), Connecticut (2026-07-01); NY and
  TN pending. **For a multi-store template, treat all-in pricing as the default
  rendering, not a per-state toggle** — and follow the federal section 464.2
  shape even where it does not bind: total price displayed more prominently than
  any other pricing information.
- Net effect for a storefront selling to California buyers: the everyday
  advertised/cart price must already be the all-in price. A separate,
  later-revealed "processing fee" or "handling fee" line is the exact
  pattern SB 478 targets.

## 5. AI transparency — EU AI Act Article 50

**Added 2026-08-01. This pack previously had no AI-transparency surface at all,
while asserting every regime it covers was already in force. Art. 50 becomes
enforceable 2026-08-02 — the omission was structural, not cosmetic.**

Regulation (EU) 2026/1744 ("Digital Omnibus on AI") is **enacted law** — OJ
2026-07-24, in force 2026-07-27. It postponed several high-risk obligations but
**Art. 50(1), (3) and (4) remain at 2026-08-02**. Its only Art. 50 change is a
grace period for **50(2)** (machine-readable marking) to **2026-12-02**, for
systems already on the market before 2026-08-02.

Who owes what — the distinction that decides our exposure:

- **50(1), on the PROVIDER** — a system interacting directly with people must
  inform them they are dealing with an AI system, unless obvious to a reasonably
  well-informed, observant and circumspect person in context.
- **50(2), on the PROVIDER** — synthetic audio/image/video/text output must be
  marked machine-readable and detectable, "as far as technically feasible".
- **50(4), on the DEPLOYER** — a deployer of a system generating or manipulating
  image/audio/video "constituting a deep fake shall disclose that the content has
  been artificially generated or manipulated".
- **50(5)** — disclosure must be clear and distinguishable, "at the latest at the
  time of the first interaction or exposure", and meet accessibility requirements.

**A merchant using a third-party image generator is a DEPLOYER, not a provider**
(Art. 3(3)/3(4)). The marking duty sits with the generator's vendor; the
disclosure duty sits with the store. Penalties, Art. 99(4): up to **EUR 15,000,000
or 3% of worldwide annual turnover**, whichever is higher.

**Whether an AI garment mockup is an Art. 50(4) deep fake is a LEGAL question this
pack must not answer.** Record the citations and stop. Art. 3(60) covers content
resembling existing persons, **objects**, places, entities or events that "would
falsely appear to a person to be authentic or truthful". Recital 134 says
"**appreciably** resembles" — a textual divergence from Art. 3(60)'s bare
"resembles" that counsel should see. Non-binding Guidelines on Art. 50 were adopted
2026-07-20; a voluntary Code of Practice on Transparency of AI-generated Content
was finalised June 2026.

**Explicit negative finding: no official EU guidance addresses product photography,
garment mockups, advertising imagery, or e-commerce.** Law-firm glosses exist. They
are interpretation, not Commission text, and a judge must not cite them as settled.

**No structured-data property discharges this.** JSON-LD and Art. 50 are unrelated;
disclosure cannot be satisfied through markup.

## Sources checked and not yet confirmed

- Etsy's own AI-disclosure and price-display policy pages returned HTTP 403
  to automated fetch this pass (same failure mode noted in the species'
  research doc, `docs/research/storefront-agent-research.md` §7.3 item 3) —
  still entirely secondary-sourced. Do not cite Etsy-specific numbers from
  this pack.
- FTC.gov returned HTTP 403 on every direct fetch attempt this pass (both
  the dot-com-disclosures guidance and the junk-fees consumer summary). The
  federal junk-fees scoping claim above is carried knowledge with an
  explicit caveat, not a fresh primary-source read.

## Audit behaviour (for a future site-compliance audit gene)

No gene in this kit consumes this pack yet — the species design doc named it
as a Phase 1 pool item, not a Phase 0 build. When an audit gene exists it
should:

1. Emit a distinct finding per surface (privacy policy, cookie consent,
   accessibility, price display) — never one aggregate compliant/non flag.
2. Treat this pack past its `expires` date as a blocking finding on its own,
   not a warning.
3. Name the specific regime and clause a finding is based on (e.g. "SB 478"
   or "EAA Art. 2"), never "may not be compliant."
4. Fail closed on a jurisdiction this pack does not cover — report it as
   unaudited, never assume the nearest covered regime applies.
5. Name the requirement; never opine that something is legal. This pack is
   operational guidance, not legal advice — same rule as `ai-disclosure-matrix`.
