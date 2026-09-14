<!-- upgrade-policy: managed-block. Edits made inside this BEGIN/END block are regenerated and lost on the next tapps_upgrade — put project-specific customizations below the END marker instead, where they survive every upgrade untouched. -->
<!-- BEGIN: tapps-skill-asset tapps-wayfind/assets/map-template.md v3.12.78 -->
# Wayfind map template

Paste into the Linear parent issue body when charting. Open tickets are **not**
listed here — they are open children found by query.

```markdown
## Destination

<what reaching the end of this map looks like — one or two lines>

## Notes

<domain; skills every session should consult; standing preferences>

## Decisions so far

<!-- one line per closed ticket: name-link + one-line gist -->

- [<closed ticket title>](url) — <gist of the answer>

## Not yet specified

<!-- in-scope fog too dim to ticket yet; graduates as the frontier advances -->

## Out of scope

<!-- past the destination; never graduates -->
```

### Child ticket body

```markdown
## Question

<the decision or investigation this ticket resolves — one session sized>
```

Optional below the Question (keep short): context links, blockers already
expressed as Linear relations, asset pointers.
<!-- END: tapps-skill-asset -->
