# Specialized Agents Enhancement Documentation

## Overview

This document describes the enhancements made to the specialized agents (Analyst, Skeptic, and Historian) to improve structured output parsing, error handling, and reliability.

## Changes Summary

### 1. Base Specialized Agent (`base_specialized.py`)

#### Retry Logic
- Added `tenacity` library for automatic retry with exponential backoff
- Implemented `@retry` decorator on `process()` method
- Retry configuration:
  - Maximum 3 attempts
  - Exponential backoff: multiplier=1, min=2s, max=10s
- Separated implementation logic into `_process_impl()` method for better error handling

#### Error Handling
- All exceptions are logged with full traceback
- Errors are re-raised after retries are exhausted
- Status tracking and metrics updated on failures

### 2. Analyst Agent (`analyst_agent.py`)

#### Structured JSON Output
The agent now returns a consistent JSON structure:

```json
{
  "summary": "2-3 sentence summary",
  "entities": ["entity1", "entity2"],
  "value_score": 0-10,
  "key_concepts": ["concept1", "concept2"],
  "category": "category name",
  "sentiment": "positive|negative|neutral",
  "raw_response": "original AI response"
}
```

#### Features
- **JSON Extraction**: Handles markdown code blocks and plain JSON responses
- **Validation**: Ensures all required fields are present with defaults
- **Error Handling**: Graceful fallback on JSON parse errors
- **Type Safety**: Converts value_score to float, ensures lists are arrays

#### Error Scenarios
1. **No Model Available**: Returns structured error response
2. **No Content**: Returns error message
3. **JSON Parse Error**: Falls back to basic extraction with error flag
4. **API Exception**: Catches and logs with structured error response

### 3. Skeptic Agent (`skeptic_agent.py`)

#### Structured JSON Output
The agent returns a consistent verification structure:

```json
{
  "verdict": "verified|questionable|false",
  "trust_score": 0-10,
  "concerns": ["concern1", "concern2"],
  "reasoning": "brief explanation",
  "raw_response": "original AI response"
}
```

#### Features
- **Markdown Handling**: Extracts JSON from code blocks (```json or ```)
- **Regex Extraction**: Falls back to regex if markdown parsing fails
- **Type Conversion**: Ensures trust_score is float
- **Error Recovery**: Returns structured error response on failures

#### Error Scenarios
1. **No Model Available**: Returns "AI unavailable" verdict
2. **JSON Parse Error**: Returns "error" verdict with error details
3. **API Exception**: Catches and logs with error verdict

### 4. Historian Agent (`historian_agent.py`)

#### Structured JSON Output
The agent returns structured historical context:

```json
{
  "context": "formatted context string",
  "relevant_memories": [
    {
      "content": "memory content",
      "type": "fact|event|insight",
      "source_id": "source identifier",
      "metadata": {}
    }
  ],
  "match_count": 5,
  "query": "original query"
}
```

#### Features
- **Memory Integration**: Uses VectorMemory for semantic search
- **Structured Results**: Formats memories with metadata
- **Error Handling**: Handles memory search failures gracefully
- **Empty Results**: Returns structured response even when no matches found

#### Error Scenarios
1. **No Query**: Returns error in structured format
2. **Memory Search Failure**: Catches exceptions and returns error response
3. **Empty Results**: Returns structured response with match_count=0

## Implementation Details

### JSON Parsing Strategy

All agents use a multi-step JSON extraction approach:

1. **Markdown Detection**: Check for ```json or ``` code blocks
2. **Regex Extraction**: Use regex to find JSON objects in text
3. **Direct Parsing**: Attempt to parse the cleaned text directly
4. **Fallback**: Return structured error response if all methods fail

### Error Response Format

All agents follow a consistent error response format:

```python
{
    "error": "Error message",
    # ... other fields with defaults
    "raw_response": "original response if available"
}
```

### Retry Logic Flow

```
process() [with @retry decorator]
  └─> _process_impl()
       ├─> Success → Return result
       └─> Exception → Retry (up to 3 times)
            └─> All retries exhausted → Raise exception
```

## Testing

Comprehensive test suite in `tests/agents/test_specialized_agents.py`:

### Test Coverage
- ✅ Agent initialization
- ✅ Structured output parsing
- ✅ JSON extraction from markdown
- ✅ Error handling scenarios
- ✅ Retry logic
- ✅ Output structure validation
- ✅ No model scenarios
- ✅ Empty input handling

### Running Tests

```bash
pytest tests/agents/test_specialized_agents.py -v
```

## Dependencies

### New Dependency
- **tenacity==8.2.3**: Retry library for robust error handling

### Existing Dependencies
- `google-generativeai`: For Gemini AI integration
- `langchain`: For message handling
- `json`, `re`: For JSON parsing and extraction

## Migration Guide

### Before
```python
# Old: Simple text response
result = await agent._analyze_content(post)
summary = result.get("summary", "")  # Could be raw text
```

### After
```python
# New: Structured JSON response
result = await agent._analyze_content(post)
summary = result["summary"]  # Always a string
entities = result["entities"]  # Always a list
value_score = result["value_score"]  # Always a float
```

### Breaking Changes
- **Analyst Agent**: `_analyze_content()` now always returns structured dict
- **Skeptic Agent**: `_verify_claims()` now always returns structured dict
- **Historian Agent**: `_process_impl()` now returns structured historical context

### Backward Compatibility
- All agents maintain the same method signatures
- Error responses include `raw_response` field for debugging
- Default values ensure fields are always present

## Best Practices

### Using Structured Output

1. **Always check for errors**:
   ```python
   if "error" in result:
       logger.error(f"Agent error: {result['error']}")
   ```

2. **Use type hints**:
   ```python
   value_score: float = result.get("value_score", 0.0)
   entities: List[str] = result.get("entities", [])
   ```

3. **Handle empty results**:
   ```python
   if not result.get("entities"):
       # Handle empty entities
   ```

### Error Handling

1. **Log errors with context**:
   ```python
   if "error" in result:
       logger.error(f"Agent {agent.agent_name} failed: {result['error']}")
   ```

2. **Use retry logic**:
   - The base class handles retries automatically
   - Don't implement custom retry logic in subclasses

3. **Monitor metrics**:
   - Check `agent.metrics` for execution statistics
   - Monitor `tasks_failed` vs `tasks_completed`

## Performance Considerations

### Retry Overhead
- Maximum retry delay: 10 seconds
- Maximum total retry time: ~20 seconds (2s + 4s + 10s)
- Consider timeout settings in calling code

### JSON Parsing
- Regex extraction is O(n) where n is response length
- Markdown parsing is O(n) for string operations
- Both are fast for typical response sizes (<10KB)

## Future Enhancements

1. **Pydantic Models**: Replace dict returns with Pydantic models for type safety
2. **Structured Output API**: Use Gemini's structured output feature when available
3. **Caching**: Cache parsed JSON structures to avoid re-parsing
4. **Metrics**: Add parsing success/failure metrics
5. **Validation**: Add schema validation for JSON responses

## Troubleshooting

### Common Issues

1. **JSON Parse Errors**
   - Check `raw_response` field for actual AI response
   - Verify AI model is returning valid JSON
   - Check prompt formatting

2. **Retry Exhaustion**
   - Check network connectivity
   - Verify API keys are valid
   - Check rate limits

3. **Empty Results**
   - Verify input content is not empty
   - Check model initialization
   - Review error logs

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger("src.agents.specialized").setLevel(logging.DEBUG)
```

## References

- [Tenacity Documentation](https://tenacity.readthedocs.io/)
- [Google Generative AI Documentation](https://ai.google.dev/docs)
- [LangChain Documentation](https://python.langchain.com/)

