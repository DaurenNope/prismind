# Structured Output for Specialized Agents

This document describes the structured JSON output format used by the Analyst and Skeptic agents.

## Overview

Both `AnalystAgent` and `SkepticAgent` return structured JSON responses with validated fields and graceful error handling. This ensures consistent data formats and reliable parsing.

## AnalystAgent Output

### Structure

```json
{
  "summary": "2-3 sentence summary of the content",
  "entities": ["entity1", "entity2", "..."],
  "value_score": 7.5,
  "key_concepts": ["concept1", "concept2", "..."],
  "category": "technology|science|business|...",
  "sentiment": "positive|negative|neutral",
  "raw_response": "Original AI response text"
}
```

### Field Descriptions

- **summary** (string): A concise 2-3 sentence summary of the analyzed content
- **entities** (array): List of extracted entities (people, organizations, technologies)
- **value_score** (float): Score from 0.0 to 10.0 indicating content value/novelty
  - Automatically clamped to 0-10 range if outside bounds
- **key_concepts** (array): List of main concepts or topics identified
- **category** (string): Content category classification
- **sentiment** (string): One of "positive", "negative", or "neutral"
  - Automatically normalized if invalid value provided
- **raw_response** (string): Original AI response for debugging/fallback

### Validation

- `value_score` is automatically clamped to 0.0-10.0 range
- `entities` and `key_concepts` are always returned as lists (converted if needed)
- `sentiment` is normalized to valid values ("positive", "negative", "neutral")
- Invalid sentiment values default to "neutral"

### Error Handling

If JSON parsing fails, the agent returns a fallback structure:

```json
{
  "summary": "First 200 chars of raw response",
  "entities": [],
  "value_score": 0.0,
  "key_concepts": [],
  "category": "unknown",
  "sentiment": "neutral",
  "error": "JSON parse error: ...",
  "raw_response": "Full raw response text"
}
```

## SkepticAgent Output

### Structure

```json
{
  "verdict": "verified|questionable|false|unverified",
  "trust_score": 7.5,
  "concerns": ["concern1", "concern2", "..."],
  "reasoning": "Brief explanation of the verdict",
  "raw_response": "Original AI response text"
}
```

### Field Descriptions

- **verdict** (string): Verification result
  - "verified": Claims appear to be true
  - "questionable": Claims need verification
  - "false": Claims appear to be false
  - "unverified": Cannot determine veracity
  - Automatically normalized to "unknown" if invalid
- **trust_score** (float): Score from 0.0 to 10.0 indicating trustworthiness
  - Automatically clamped to 0-10 range if outside bounds
- **concerns** (array): List of potential issues, fallacies, or red flags
- **reasoning** (string): Brief explanation of the verification decision
- **raw_response** (string): Original AI response for debugging/fallback

### Validation

- `trust_score` is automatically clamped to 0.0-10.0 range
- `concerns` is always returned as a list (converted if needed)
- `verdict` is normalized to valid values
- Invalid verdict values default to "unknown"

### Error Handling

If JSON parsing fails, the agent returns a fallback structure:

```json
{
  "verdict": "error",
  "trust_score": 0.0,
  "concerns": [],
  "reasoning": "",
  "error": "JSON parse error: ...",
  "raw_response": "Full raw response text"
}
```

## JSON Extraction

Both agents handle JSON extraction from various response formats:

1. **Plain JSON**: Direct JSON string
2. **Markdown code blocks**: Extracts JSON from ````json` blocks
3. **Generic code blocks**: Extracts JSON from ```` blocks
4. **Regex fallback**: Uses regex to find JSON objects in text

## Usage Examples

### AnalystAgent

```python
from src.agents.specialized.analyst_agent import AnalystAgent

agent = AnalystAgent()
post = {"content": "Your content here"}
result = await agent._analyze_content(post)

print(f"Summary: {result['summary']}")
print(f"Value Score: {result['value_score']}")
print(f"Entities: {result['entities']}")
```

### SkepticAgent

```python
from src.agents.specialized.skeptic_agent import SkepticAgent

agent = SkepticAgent()
verification = await agent._verify_claims("Text to verify")

print(f"Verdict: {verification['verdict']}")
print(f"Trust Score: {verification['trust_score']}")
print(f"Concerns: {verification['concerns']}")
```

## Metrics Tracking

Both agents automatically track metrics:

- **AnalystAgent**: `analysis_count`, `last_analysis_time`, `analysis_duration`
- **SkepticAgent**: `verification_count`, `last_verification_time`, `verification_duration`

Access metrics via:
```python
agent.metrics["analysis_count"]  # or verification_count
```

## Health Checks

Both agents provide enhanced health checks:

```python
health = await agent.health_check()
# Returns base health + agent-specific metrics:
# - model_available
# - last_analysis/last_verification
# - analysis_count/verification_count
```

## Testing

Comprehensive tests are available in:
- `tests/test_specialized_agents_structured_output.py`

Run tests with:
```bash
pytest tests/test_specialized_agents_structured_output.py -v
```

## Best Practices

1. **Always check for errors**: Look for `"error"` key in responses
2. **Use raw_response for debugging**: When parsing fails, check `raw_response`
3. **Validate scores**: Scores are auto-clamped, but verify ranges in your code
4. **Handle empty lists**: Entities, concepts, and concerns may be empty arrays
5. **Check model availability**: Use health checks to verify model is initialized

## Troubleshooting

### JSON Parse Errors

If you see JSON parse errors:
1. Check `raw_response` to see what the AI actually returned
2. Verify the AI model is properly configured
3. Check logs for detailed error messages

### Invalid Scores

Scores are automatically clamped, but if you see unexpected values:
1. Check the `raw_response` to see original AI output
2. Verify the prompt is requesting numeric scores
3. Review agent logs for warnings

### Missing Fields

If fields are missing:
1. Check for `"error"` key in response
2. Verify model is initialized (check health)
3. Review fallback structure documentation above

