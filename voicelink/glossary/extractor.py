"""DSPy modules for technical term extraction and explanation."""

from dataclasses import dataclass
from typing import Optional

try:
    import dspy
except ImportError:
    dspy = None


def _check_dspy():
    """Check if DSPy is available."""
    if dspy is None:
        raise ImportError(
            "DSPy library required. Install with: pip install voicelink[glossary]"
        )


# DSPy Signatures
class ExtractTermsSignature(dspy.Signature if dspy else object):
    """Extract technical terms and jargon from a transcript."""

    transcript: str = dspy.InputField(
        desc="The transcript text to analyze"
    ) if dspy else ""
    context: str = dspy.InputField(
        desc="Optional context about the domain or topic", default=""
    ) if dspy else ""
    terms: list[str] = dspy.OutputField(
        desc="List of technical terms, acronyms, and domain-specific jargon found in the transcript"
    ) if dspy else []


class ExplainTermSignature(dspy.Signature if dspy else object):
    """Generate an explanation for a technical term."""

    term: str = dspy.InputField(
        desc="The technical term to explain"
    ) if dspy else ""
    context: str = dspy.InputField(
        desc="Context from the transcript where the term was used"
    ) if dspy else ""
    domain: str = dspy.InputField(
        desc="The domain or field the term belongs to", default=""
    ) if dspy else ""
    explanation: str = dspy.OutputField(
        desc="Clear, concise explanation of the term suitable for a glossary"
    ) if dspy else ""
    related_terms: list[str] = dspy.OutputField(
        desc="Related terms that might also need explanation", default=[]
    ) if dspy else []


class CategorizeTermSignature(dspy.Signature if dspy else object):
    """Categorize a technical term."""

    term: str = dspy.InputField(desc="The technical term") if dspy else ""
    explanation: str = dspy.InputField(desc="The term's explanation") if dspy else ""
    category: str = dspy.OutputField(
        desc="Category for the term (e.g., 'Programming', 'Networking', 'Database', 'Security', 'General')"
    ) if dspy else ""


# DSPy Modules
class TermExtractor(dspy.Module if dspy else object):
    """Extract technical terms from a transcript using Chain of Thought."""

    def __init__(self):
        _check_dspy()
        super().__init__()
        self.extract = dspy.ChainOfThought(ExtractTermsSignature)

    def forward(self, transcript: str, context: str = "") -> list[str]:
        """Extract terms from transcript.

        Args:
            transcript: The transcript text.
            context: Optional domain context.

        Returns:
            List of extracted technical terms.
        """
        result = self.extract(transcript=transcript, context=context)
        return result.terms if hasattr(result, "terms") else []


class TermExplainer(dspy.Module if dspy else object):
    """Generate explanations for technical terms using Chain of Thought."""

    def __init__(self):
        _check_dspy()
        super().__init__()
        self.explain = dspy.ChainOfThought(ExplainTermSignature)
        self.categorize = dspy.Predict(CategorizeTermSignature)

    def forward(
        self, term: str, context: str = "", domain: str = ""
    ) -> dict:
        """Explain a technical term.

        Args:
            term: The term to explain.
            context: Context where the term appeared.
            domain: Domain/field of the term.

        Returns:
            Dictionary with explanation and metadata.
        """
        # Get explanation
        explanation_result = self.explain(term=term, context=context, domain=domain)

        explanation = getattr(explanation_result, "explanation", "")
        related = getattr(explanation_result, "related_terms", [])

        # Get category
        category_result = self.categorize(term=term, explanation=explanation)
        category = getattr(category_result, "category", "General")

        return {
            "term": term,
            "explanation": explanation,
            "category": category,
            "related_terms": related,
        }


class GlossaryCompiler(dspy.Module if dspy else object):
    """Complete glossary compilation pipeline."""

    def __init__(self, max_terms: int = 50):
        """Initialize the glossary compiler.

        Args:
            max_terms: Maximum number of terms to extract.
        """
        _check_dspy()
        super().__init__()
        self.extractor = TermExtractor()
        self.explainer = TermExplainer()
        self.max_terms = max_terms

    def forward(
        self, transcript: str, context: str = "", domain: str = ""
    ) -> list[dict]:
        """Compile a glossary from a transcript.

        Args:
            transcript: The transcript text.
            context: Optional context about the content.
            domain: Domain/field of the content.

        Returns:
            List of term dictionaries with explanations.
        """
        # Extract terms
        terms = self.extractor(transcript=transcript, context=context)

        # Limit terms
        terms = terms[: self.max_terms]

        # Explain each term
        glossary = []
        for term in terms:
            # Find context snippet for the term
            term_context = self._find_context(transcript, term)

            entry = self.explainer(term=term, context=term_context, domain=domain)
            glossary.append(entry)

        return glossary

    def _find_context(self, transcript: str, term: str, window: int = 200) -> str:
        """Find context snippet around a term in the transcript.

        Args:
            transcript: Full transcript.
            term: Term to find context for.
            window: Character window around the term.

        Returns:
            Context snippet.
        """
        term_lower = term.lower()
        transcript_lower = transcript.lower()

        idx = transcript_lower.find(term_lower)
        if idx == -1:
            return ""

        start = max(0, idx - window // 2)
        end = min(len(transcript), idx + len(term) + window // 2)

        context = transcript[start:end]

        # Clean up partial words at boundaries
        if start > 0:
            space_idx = context.find(" ")
            if space_idx != -1 and space_idx < 20:
                context = context[space_idx + 1 :]

        if end < len(transcript):
            space_idx = context.rfind(" ")
            if space_idx != -1 and len(context) - space_idx < 20:
                context = context[:space_idx]

        return f"...{context}..."


def setup_dspy(api_key: str, model: str = "gpt-4o") -> None:
    """Configure DSPy with OpenAI.

    Args:
        api_key: OpenAI API key.
        model: Model to use.
    """
    _check_dspy()

    lm = dspy.LM(f"openai/{model}", api_key=api_key)
    dspy.configure(lm=lm)
