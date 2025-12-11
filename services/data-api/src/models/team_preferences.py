"""
User Team Preferences Model
Epic 11 Story 11.5: Team Persistence Implementation

Stores user-selected NFL and NHL teams for sports monitoring.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class TeamPreferences(Base):
    """
    User team preferences for sports monitoring.
    
    Stores NFL and NHL team selections per user.
    """
    __tablename__ = "user_team_preferences"
    
    user_id: Mapped[str] = mapped_column(String(50), primary_key=True, comment="User identifier (default: 'default')")
    nfl_teams: Mapped[list[str]] = mapped_column(JSON, default=list, comment="List of NFL team IDs")
    nhl_teams: Mapped[list[str]] = mapped_column(JSON, default=list, comment="List of NHL team IDs")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="Creation timestamp")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Last update timestamp")
    
    def __repr__(self) -> str:
        return f"<TeamPreferences(user_id={self.user_id}, nfl_teams={len(self.nfl_teams)}, nhl_teams={len(self.nhl_teams)})>"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "user_id": self.user_id,
            "nfl_teams": self.nfl_teams,
            "nhl_teams": self.nhl_teams,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

