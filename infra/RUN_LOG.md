# Faultline Autonomous Run Log

- Phase 1.1: Tested FAULTLINE_EXTRACT_OVERFLOW_MODEL=gemini:gemini-3.5-flash; active cache hits dropped from 220 to 125 (gpt-oss-20b entries omitted by candidates chain), so reverted .env per instruction to preserve 220 cached sources.
- Phase 1.2: Added FAULTLINE_EXTRACT_FALLBACK_MODEL as 3rd candidate and translated response_format in llm.py (commit 7b02421); confirmed check_cache.py restored 220 of 933.
- Phase 1.3: Tested 20-source slice on scratch_gem with workers 2; sources extracted, but resolve_entities failed with JSONDecodeError (Gemini output truncated at token limit, returning unterminated JSON string); git reverted fix commit (0a89828), cleaned .env and deleted scratch_gem per step 3 instructions.
