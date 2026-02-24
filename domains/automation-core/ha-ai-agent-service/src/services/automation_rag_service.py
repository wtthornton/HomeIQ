"""
Automation RAG Service

Epic: HomeIQ Automation Improvements, Story 5
Epic: Reusable Pattern Framework, Story 1 (refactored to extend RAGContextService)

Retrieves automation patterns from corpus (Super Bowl guide, etc.) when user
prompt matches sports/team tracker keywords.
"""

from pathlib import Path
import logging

from homeiq_patterns import RAGContextService

logger = logging.getLogger(__name__)

# Keywords that indicate sports/team tracker automation intent.
# Covers all ha-teamtracker leagues: NFL, NBA, MLB, NHL, MLS, NCAA, PGA, UFC, EPL, F1, etc.
SPORTS_KEYWORDS = (
    # Integration
    "team tracker", "teamtracker",
    # Major US leagues
    "nfl", "nba", "mlb", "nhl", "mls", "ncaa",
    # College / alternate leagues
    "ncaaf", "ncaam", "ncaaw", "wnba", "xfl",
    # International / other sports
    "pga", "golf", "ufc", "mma", "nwsl", "epl", "f1", "irl", "atp", "wta",
    "afl", "world cup", "premier league", "champions league", "march madness",
    # Sport names
    "football", "basketball", "baseball", "hockey", "soccer", "tennis",
    "volleyball", "racing", "formula 1",
    # Events
    "super bowl", "superbowl", "game day", "kickoff", "playoff", "playoffs",
    "championship", "finals",
    # Game flow — "score" replaced with multi-word to avoid "credit score" false positive
    "scores a", "game over", "winner", "quarter", "period", "halftime",
    "possession", "when team scores", "when my team scores",
    # Sport-specific scoring
    "touchdown", "field goal", "goal", "home run", "run", "basket",
    "inning", "strikeout", "match", "hat trick", "birdie", "eagle",
    "fight", "knockout", "lap", "pole position",
    # Lights / automation intent
    "sports lights", "game lights", "score flash", "team colors", "team_colors",
)


class AutomationRAGService(RAGContextService):
    """
    Retrieves automation context from RAG corpus (Super Bowl guide excerpts)
    when user prompt matches sports/team tracker keywords.

    Extends RAGContextService with sports-specific keyword list and corpus.
    """

    name = "Sports/Team Tracker"
    keywords = SPORTS_KEYWORDS
    min_score = 0.3  # Higher threshold — large keyword list needs specificity
    corpus_path = Path(__file__).parent.parent / "data" / "superbowl_guide_excerpts.md"

    def __init__(self) -> None:
        super().__init__()

    # --- Backward-compatible methods ---

    def _matches_sports_intent(self, user_prompt: str) -> bool:
        """Check if user prompt indicates sports/team tracker automation intent."""
        return self.detect_intent(user_prompt)

    def _load_corpus(self) -> str:
        """Load corpus from bundled file."""
        return self.load_corpus()

    async def get_automation_context(self, user_prompt: str) -> str:
        """
        Get RAG context for automation generation when sports keywords detected.

        Backward-compatible wrapper around RAGContextService.get_context().

        Args:
            user_prompt: User message to match

        Returns:
            Corpus excerpts or empty string if no match
        """
        return await self.get_context(user_prompt)

    def format_context(self, corpus: str) -> str:
        """Format sports corpus with domain-specific header."""
        return (
            f"\n---\n\nAUTOMATION RAG CONTEXT (Sports/Team Tracker patterns):\n"
            f"Use these proven patterns when generating sports automations:\n\n"
            f"{corpus}\n\n---\n"
        )
