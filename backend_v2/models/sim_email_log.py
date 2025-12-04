from __future__ import annotations

from datetime import datetime
from sqlmodel import SQLModel, Field


class SimEmailLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    lead_id: int = Field(index=True)
    day_index: int = Field(default=1)

    # "assistant" means AI → client, "client" if you later log replies
    direction: str = Field(default="assistant")

    subject: str = Field(default="")
    body: str = Field(default="")

    created_at: datetime = Field(default_factory=datetime.utcnow)
