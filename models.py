from pydantic import BaseModel

class UserAccountContext(BaseModel):
    customer_id: int
    name: str
    tier: str = "basic"


class InputGuardRailOutput(BaseModel):
    in_off_topic: bool
    reason: str

class HandoffData(BaseModel):
    agent_name: str
    issue_type: str
    issue_details: str
    reason: str