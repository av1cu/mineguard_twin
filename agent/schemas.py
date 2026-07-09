from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ProposedAction(BaseModel):
    type: str
    route_id: Optional[str] = None
    equipment_id: Optional[str] = None
    driver_id: Optional[str] = None
    reason: Optional[str] = None
    label: Optional[str] = None


class AgentToolCallTrace(BaseModel):
    tool: str
    args: Dict[str, Any] = {}
    result_preview: str = ""


class AgentChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class AgentChatResponse(BaseModel):
    answer: str
    proposed_actions: List[ProposedAction] = []
    trace: List[AgentToolCallTrace] = []
    session_id: str = "default"


class WhatIfRequest(BaseModel):
    question: str
    session_id: str = "whatif"


class ShiftReportResponse(BaseModel):
    report: str
    generated_at: str
    proposed_actions: List[ProposedAction] = []
    trace: List[AgentToolCallTrace] = []
