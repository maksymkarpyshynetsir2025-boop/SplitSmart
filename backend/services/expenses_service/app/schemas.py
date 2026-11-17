from pydantic import BaseModel
from typing import List

class TransactionInput(BaseModel):
    debtor_id: int
    creditor_id: int
    amount: float

class OptimizationRequest(BaseModel):
    transactions: List[TransactionInput]

from typing import List

class ExpenseSplitCreate(BaseModel):
    user_id: int
    owed_amount: float

class ExpenseCreate(BaseModel):
    group_id: int
    payer_id: int
    amount: float
    description: str
    splits: List[ExpenseSplitCreate]

class ExpenseResponse(BaseModel):
    id: int
    group_id: int
    payer_id: int
    amount: float
    description: str

    class Config:
        from_attributes = True