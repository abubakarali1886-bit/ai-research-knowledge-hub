from app.services.summarization_service import SummarizationService


def test_clean_summary_response_removes_reasoning_and_preamble():
    response = """<think>
I need to explain the report before writing its summary.
</think>
Here is the summary:
# RESEARCH SUMMARY

### 1. Executive Summary
Dollar use declined.
"""

    cleaned = SummarizationService._clean_summary_response(response)

    assert cleaned.startswith("# RESEARCH SUMMARY")
    assert "I need to" not in cleaned
    assert "Here is the summary" not in cleaned
    assert "Dollar use declined." in cleaned


def test_clean_summary_response_removes_unclosed_reasoning_block():
    response = "# RESEARCH SUMMARY\n<think>unfinished private reasoning"

    assert SummarizationService._clean_summary_response(response) == "# RESEARCH SUMMARY"


def test_summarization_uses_a_dedicated_model(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "deepseek-r1:1.5b")
    monkeypatch.delenv("SUMMARY_LLM_MODEL", raising=False)

    assert SummarizationService().model == "qwen3.5:0.8b"