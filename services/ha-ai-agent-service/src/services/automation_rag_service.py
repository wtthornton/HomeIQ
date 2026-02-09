"""
Automation RAG Service

Epic: HomeIQ Automation Improvements, Story 5
Retrieves automation patterns from corpus (Super Bowl guide, etc.) when user
prompt matches sports/team tracker keywords.
"""

import logging
from pathlib import Path

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
    # Game flow
    "score", "game over", "winner", "quarter", "period", "halftime",
    "possession", "when team scores", "when my team scores",
    # Sport-specific scoring
    "touchdown", "field goal", "goal", "home run", "run", "basket",
    "inning", "strikeout", "match", "hat trick", "birdie", "eagle",
    "fight", "knockout", "lap", "pole position",
    # Lights / automation intent
    "sports lights", "game lights", "score flash", "team colors", "team_colors",
)


class AutomationRAGService:
    """
    Retrieves automation context from RAG corpus (Super Bowl guide excerpts)
    when user prompt matches sports/team tracker keywords.
    """

    def __init__(self) -> None:
        self._corpus: str | None = None
        # Generic Team Tracker patterns (Super Bowl is one example)
        self._corpus_path = Path(__file__).parent.parent / "data" / "superbowl_guide_excerpts.md"

    def _load_corpus(self) -> str:
        """Load corpus from bundled file."""
        if self._corpus is not None:
            return self._corpus
        try:
            self._corpus = self._corpus_path.read_text(encoding="utf-8")
            logger.debug(f"Loaded automation RAG corpus ({len(self._corpus)} chars)")
        except Exception as e:
            logger.warning(f"Could not load automation RAG corpus: {e}")
            self._corpus = ""
        return self._corpus

    def _matches_sports_intent(self, user_prompt: str) -> bool:
        """Check if user prompt indicates sports/team tracker automation intent."""
        lower = user_prompt.lower()
        return any(kw in lower for kw in SPORTS_KEYWORDS)

    async def get_automation_context(self, user_prompt: str) -> str:
        """
        Get RAG context for automation generation when sports keywords detected.

        Args:
            user_prompt: User message to match

        Returns:
            Corpus excerpts or empty string if no match
        """
        if not self._matches_sports_intent(user_prompt):
            return ""
        corpus = self._load_corpus()
        if not corpus:
            return ""
        return (
            f"\n---\n\nAUTOMATION RAG CONTEXT (Sports/Team Tracker patterns):\n"
            f"Use these proven patterns when generating sports automations:\n\n"
            f"{corpus}\n\n---\n"
        )
