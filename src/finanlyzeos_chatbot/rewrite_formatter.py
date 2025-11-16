from __future__ import annotations

from typing import List


def rewrite_forecast_output(raw_text: str) -> str:
	"""
	Rewrite ANY ML forecast output into Finalyze/CBA's institutional format.
	Does NOT change any numbers, only improves wording, narrative, and structure.
	"""
	# Step 1: Remove debug logs or system messages
	cleaned: List[str] = []
	for line in (raw_text or "").split("\n"):
		ll = line.lower()
		if any(x in ll for x in [
			"processing timeline",
			"ms",
			"skip",
			"cache",
			"gathering",
			"compose",
			"ready",
			"finalising",
			"context"
		]):
			continue
		cleaned.append(line)
	cleaned_text = "\n".join(cleaned).strip()

	# Step 2: Apply the rewriting template (LLM will rewrite with this instruction)
	rewritten = f"""
Rewrite the following forecast output using the Finalyze/CBA institutional style:

Use this structure:

1. Executive Summary
2. Forecast Table
3. Growth Outlook
4. Key Business Drivers
5. Risk & Uncertainty
6. Model Explanation
7. Audit Trail

Rules:
- KEEP ALL NUMBERS EXACTLY THE SAME.
- Expand each section using full sentences.
- Improve narrative quality.
- Add company-specific business context.
- Add deeper financial interpretation.
- Remove any remaining fragments or debug text.

FORECAST TO REWRITE:

{cleaned_text}
"""
	return rewritten


