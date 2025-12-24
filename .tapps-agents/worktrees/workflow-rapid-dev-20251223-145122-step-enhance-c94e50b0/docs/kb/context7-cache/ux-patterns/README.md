# UX/UI Design Patterns - Knowledge Base

This directory contains documented UX/UI design patterns that have been identified as preferred approaches for the HA Ingestor project. These patterns should be referenced and reused when building similar features.

## Available Patterns

### ✅ Service Visualization Patterns

#### [Health Dashboard Dependencies Tab Pattern](health-dashboard-dependencies-tab-pattern.md)
**Status:** Production-tested, User-approved  
**Source:** http://localhost:3000/ - Dependencies Tab  
**Component:** `ServiceDependencyGraph.tsx`

**Key Features:**
- Interactive dependency graph with click-to-highlight
- Hover tooltips with contextual information
- Layered architecture visualization (top-to-bottom data flow)
- Color-coded status indicators (🟢🟡🔴⚫)
- Icon-based service representation (emoji)
- Smooth scale animations on hover/select
- Dark mode support
- Responsive grid layouts
- Lightweight (pure React/CSS, no heavy graph libraries)

**Use For:**
- Service topology visualizations
- Data flow diagrams
- System architecture views
- Microservice dependency graphs
- Pipeline visualizations
- Infrastructure maps
- Integration status boards

**Complexity:** Medium  
**Reusability:** High  
**Maintenance:** Low

---

## Pattern Selection Guide

### When to Use Each Pattern

| Pattern | Best For | Avoid When |
|---------|----------|------------|
| **Dependencies Tab** | Service relationships, data flow, system topology | Simple lists, non-hierarchical data |

---

## Adding New Patterns

When documenting a new pattern, include:

1. **Overview** - What problem does it solve?
2. **Key Design Patterns** - What are the core UX/UI elements?
3. **Technical Implementation** - Technology stack and code structure
4. **Why This Pattern Works** - Strengths and use cases
5. **Reusable Components** - Code snippets for reuse
6. **Design Principles** - What makes it good design?
7. **Performance Considerations** - How to keep it fast
8. **Future Enhancements** - Ideas for improvement
9. **References** - Links to source code

## Pattern Status Indicators

- ✅ **Production-tested** - Live in production, verified by users
- 🧪 **Experimental** - In development or testing
- 📋 **Planned** - Documented but not yet implemented
- ⚠️ **Deprecated** - No longer recommended, use alternative

---

## Integration with Context7 KB

These patterns are stored in the Context7 KB cache and can be referenced by all BMAD agents when making UI/UX decisions. The patterns complement library-specific documentation from Context7 with project-specific design preferences.

### Querying Patterns

Use the following commands to access patterns:

```bash
*context7-kb-search "dependencies visualization"
*context7-kb-search "service graph"
*context7-kb-search "interactive visualization"
```

---

## Related Documentation

- [Health Dashboard README](../../../../services/health-dashboard/README.md)
- [Architecture Documentation](../../../architecture/)
- [Component Library](../../../../services/health-dashboard/src/components/)

---

**Last Updated:** 2025-10-12  
**Maintained By:** BMAD Agents  
**Location:** `docs/kb/context7-cache/ux-patterns/`

