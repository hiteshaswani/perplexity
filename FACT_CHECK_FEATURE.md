# Fact-Checking Feature

## Overview

A robust fact-checking layer has been added to the validation pipeline that verifies the accuracy of generated answers against source material.

## Architecture

The system now has a **three-phase pipeline**:

1. **Initial Research** (`initial_research()`)
   - Generate search queries
   - Search web
   - Crawl pages (HTTP + RSS fallback)
   - Summarize content
   - Generate initial answer

2. **Validation & Follow-up** (`validation_and_followup()`)
   - Check answer completeness
   - Search for missing topics if needed
   - Regenerate answer if incomplete

3. **Fact-Checking** (integrated into phase 2)
   - Verify claims against sources
   - Classify as: accurate, unsupported, contradicted, or exaggerated
   - Assign accuracy score (0-100)
   - Provide verdict

## Implementation Details

### Core Functions (in `ai.py`)

#### `extract_json(text: str) -> dict`
Safely extracts JSON from LLM response, handling malformed output gracefully.

#### `validate_schema(result: dict) -> dict`
Ensures fact-check results have all required fields with proper defaults:
- `accuracy_score`: 0-100
- `accurate_claims`: list of verified claims
- `unsupported_claims`: claims not found in sources
- `contradicted_claims`: claims that conflict with sources
- `issues`: list of problems found
- `verdict`: accurate | mostly_accurate | partially_accurate | inaccurate

#### `fact_check_answer(answer: str, sources: list) -> dict`
Main fact-checking function with:
- **Source limiting**: Uses max 6 sources to avoid context overflow
- **Retry logic**: 2 attempts with deterministic temperature=0
- **Extended context**: 4096 tokens for thorough analysis
- **Graceful fallback**: Returns safe default on failure

### Configuration

```python
MAX_SOURCES = 6          # Limit sources for fact-checking
MAX_RETRIES = 2          # Retry attempts on failure
TEMPERATURE = 0          # Deterministic for consistency
CONTEXT_SIZE = 4096      # Extended context window
```

## Fact-Check Classifications

### ✅ Accurate
Claims clearly supported by sources with evidence.

### ⚠️ Unsupported
Claims not present in the provided sources. May be true but unverified.

### ❌ Contradicted
Claims that directly conflict with information in sources.

### 📝 Exaggerated
Claims that overstate or misrepresent what sources actually say.

## Output Format

Results include a `fact_check` field:

```json
{
  "query": "...",
  "sources": [...],
  "answer": "...",
  "validation": {...},
  "fact_check": {
    "accuracy_score": 95,
    "accurate_claims": [
      "Su-30 MKI introduced in 2002",
      "Aircraft has thrust vectoring"
    ],
    "unsupported_claims": [],
    "contradicted_claims": [],
    "issues": [],
    "verdict": "accurate"
  }
}
```

## Verdicts

- **accurate**: All major claims supported by sources (score typically 90-100)
- **mostly_accurate**: Most claims supported with minor issues (score 70-89)
- **partially_accurate**: Significant unsupported/contradicted claims (score 40-69)
- **inaccurate**: Many contradictions or unsupported claims (score 0-39)

## Display

The `pretty_print()` function now shows fact-check results:

```
============================================================
🔬 FACT CHECK
============================================================
✅ ACCURATE (Score: 95/100)
```

For issues:

```
============================================================
🔬 FACT CHECK
============================================================
⚠️ PARTIALLY ACCURATE (Score: 65/100)

⚠️  Unsupported claims (2):
   • Claim about feature X
   • Statement about capability Y

📝 Issues (1):
   • Some dates are approximate
```

## Error Handling

- **Retry logic**: 2 attempts if LLM fails to respond
- **JSON extraction**: Handles malformed responses gracefully
- **Schema validation**: Ensures all required fields present
- **Fallback**: Returns safe default with `verdict: "unknown"` on failure

## Benefits

1. **Accuracy verification**: Ensures answers are grounded in sources
2. **Transparency**: Shows which claims are supported vs unsupported
3. **Quality control**: Flags hallucinations and contradictions
4. **User confidence**: Provides accuracy scores for reliability assessment
5. **Debugging**: Helps identify weak sources or gaps in research

## Testing

Test with queries that have verifiable facts:

```bash
# Simple factual query
python app_simple.py "What is the capital of France and when was the Eiffel Tower built?"

# Complex technical query
python app_simple.py "Write an article on Su-30 MKI capabilities and modernization"

# Check result.json for fact_check field
cat result.json | grep -A 10 "fact_check"
```

## Performance

- **Additional time**: ~3-5 seconds per query
- **Context usage**: Limited to 6 sources (4096 tokens)
- **Deterministic**: Temperature=0 ensures consistent results
- **Retry overhead**: Max 2 attempts (6-10 seconds worst case)

## Future Enhancements

- [ ] Cross-reference external fact-checking databases
- [ ] Source credibility scoring
- [ ] Confidence levels for individual claims
- [ ] Automatic correction of minor inaccuracies
- [ ] Citation mapping (which source supports which claim)
