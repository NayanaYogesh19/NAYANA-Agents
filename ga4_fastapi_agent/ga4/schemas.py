from pydantic import BaseModel

from typing import List


class ReportRequest(BaseModel):

    property_id: str

    dimensions: List[str]

    metrics: List[str]

    start_date: str = "30daysAgo"

    end_date: str = "today"

    limit: int = 100