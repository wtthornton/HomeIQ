# Story AI4.4: Automation Chain Classification

**Epic:** AI-4 - N-Level Synergy Detection  
**Story Points:** 5  
**Priority:** Medium  
**Dependencies:** Story AI4.3 (Path Re-Ranking)

---

## Story Description

AS AN AI automation service  
I WANT TO classify automation chains by category and complexity  
SO THAT users can filter and prioritize suggestions

---

## Acceptance Criteria

### Must Have

1. **✅ Integrate flan-t5-small (INT8)**
   - Quantize via optimum-cli (80MB)
   - Classify into: energy, comfort, security, convenience
   - Target: 100ms per classification

2. **✅ Structured Prompt Engineering**
   - Use few-shot examples in prompt
   - Clear output format (single word category)
   - Fallback parsing with keyword detection

3. **✅ Complexity Assessment**
   - Easy: 2-hop, same area
   - Medium: 3-hop, same area OR 2-hop cross-area
   - Advanced: 4+ hops OR 3+ cross-area

---

## Technical Implementation (Context7 Best Practices)

```python
from optimum.intel.openvino import OVModelForSeq2SeqLM

class ChainClassifier:
    """
    Story AI4.4: Chain Classification
    Context7: Structured prompts + strict parsing
    """
    
    def __init__(self):
        # Export and quantize (INT8)
        self.model = OVModelForSeq2SeqLM.from_pretrained(
            "google/flan-t5-small",
            export=True,
            quantization_config={"bits": 8}
        )
    
    def classify(self, path):
        """Classify automation chain."""
        prompt = f"""Smart home automation classifier.

Chain: {self._to_description(path)}

Categories:
- energy: Power saving across devices
- comfort: Multi-room comfort
- security: Security sequences
- convenience: Complex automations

Examples:
- "Motion → Light → Thermostat" = comfort
- "Door → Lock → Alarm" = security

Category (one word):"""
        
        output = self.model.generate(prompt)
        return self._parse(output, path)
    
    def _parse(self, output, path):
        """Strict parsing with fallback."""
        valid = ['energy', 'comfort', 'security', 'convenience']
        
        if output in valid:
            return output
        
        # Keyword fallback
        if 'lock' in path or 'alarm' in path:
            return 'security'
        if 'climate' in path or 'fan' in path:
            return 'comfort'
        
        return 'convenience'
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Classification Accuracy | 75-80% |
| Inference Time | <100ms |
| Model Size | 80MB (INT8) |

---

**Created:** October 19, 2025  
**Status:** Proposed

