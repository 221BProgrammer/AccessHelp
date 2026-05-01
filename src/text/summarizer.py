# src/text/summarizer.py
import re

# Fix 4: wrap model load in try/except so missing internet / first-run
# doesn't crash the entire app at import time.
try:
    from transformers import pipeline as _hf_pipeline
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    _TRANSFORMERS_AVAILABLE = False


class TextSummarizer:
    """
    Summarises text using facebook/bart-large-cnn.

    BUG FIXES
    ---------
    1. min_length > effective input length caused BART to crash.
       min_length is now always capped to half the input token estimate.
    2. Chunking was done by character count (500 chars) but BART's hard
       limit is 1024 tokens.  ~4 chars ≈ 1 token, so 500 chars ≈ 125
       tokens — far too small, causing hundreds of tiny summaries.
       Chunk size raised to 3000 chars (~750 tokens) which fits safely
       within BART's 1024-token window.
    3. Final summarisation step had a fixed min_length=60 that could
       exceed the actual combined summary length, causing a crash.
       min_length is now computed dynamically.
    4. Model load failure (no internet, missing package) now falls back
       to an extractive summariser instead of crashing the whole app.
    """

    # Safe chunk size: ~3000 chars ≈ 750 tokens, well within BART's 1024 limit
    _CHUNK_CHARS = 3000
    # Minimum chunk length worth summarising (very short chunks produce noise)
    _MIN_CHUNK_CHARS = 100

    def __init__(self):
        self.summarizer = None
        self._load_model()

    def _load_model(self):
        """Load BART model — silently fall back if unavailable."""
        if not _TRANSFORMERS_AVAILABLE:
            print("⚠️ transformers not installed — using extractive fallback.")
            print("   Run: pip install transformers torch")
            return
        try:
            self.summarizer = _hf_pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
            )
            print("✅ Summariser model loaded.")
        except Exception as e:
            print(f"⚠️ Could not load summariser model: {e}")
            print("   Using extractive fallback instead.")
            self.summarizer = None

    # ── Text cleaning ─────────────────────────────────────────────────────────

    def clean_text(self, text: str) -> str:
        """Fix run-together words from PDF extraction and normalise whitespace."""
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    # ── Safe summarisation helper ─────────────────────────────────────────────

    def _safe_summarise(self, text: str, max_length: int = 130) -> str:
        """
        Summarise a single chunk safely.

        Fix 1 & 3: dynamically compute min_length so it never exceeds
        half the estimated token count of the input.
        """
        # Rough estimate: 1 token ≈ 4 characters
        estimated_tokens = max(1, len(text) // 4)
        # min_length must be < max_length and < estimated_tokens
        safe_min = min(30, max_length - 1, estimated_tokens // 2)
        safe_min = max(1, safe_min)   # never below 1

        result = self.summarizer(
            text,
            max_length=max_length,
            min_length=safe_min,
            do_sample=False,
            truncation=True,          # silently truncate if over token limit
        )
        return result[0]["summary_text"]

    # ── Extractive fallback ───────────────────────────────────────────────────

    @staticmethod
    def _extractive_summary(text: str, max_sentences: int = 5) -> str:
        """
        Simple extractive fallback: return the first N sentences.
        Used when the BART model is unavailable.
        """
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        chosen = sentences[:max_sentences]
        return " ".join(chosen) if chosen else text[:500]

    # ── Public API ────────────────────────────────────────────────────────────

    def summarize(self, text: str) -> str:
        """
        Summarise text of any length.

        Falls back to extractive summary if BART is not available.
        """
        text = self.clean_text(text)

        if not text:
            return "⚠️ No text provided to summarise."

        # Fix 4: graceful fallback when model unavailable
        if self.summarizer is None:
            return self._extractive_summary(text)

        try:
            # Fix 2: chunk by _CHUNK_CHARS (~750 tokens) not 500 chars
            chunks = [
                text[i: i + self._CHUNK_CHARS]
                for i in range(0, len(text), self._CHUNK_CHARS)
            ]

            # Step 1: summarise each chunk individually
            chunk_summaries = []
            for chunk in chunks:
                if len(chunk.strip()) >= self._MIN_CHUNK_CHARS:
                    chunk_summaries.append(self._safe_summarise(chunk, max_length=120))

            if not chunk_summaries:
                return self._extractive_summary(text)

            combined = " ".join(chunk_summaries)

            # Step 2: final summarisation of the combined summaries
            # Fix 3: only run if combined is long enough to be worth summarising
            if len(combined) > self._MIN_CHUNK_CHARS:
                return self._safe_summarise(combined, max_length=150)

            return combined

        except Exception as e:
            print(f"Summariser error: {e} — falling back to extractive summary.")
            return self._extractive_summary(text)