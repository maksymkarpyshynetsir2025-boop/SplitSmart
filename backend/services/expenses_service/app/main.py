from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.debt_optimizer import simplify_debts, Transaction

models.Base.metadata.create_all(bind=models.engine)

app = FastAPI(
    title="SplitSmart Expenses Service",
    description="Microservice for calculating and optimizing shared expenses."
)

def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()



@app.post("/api/v1/optimize-debts")
def optimize_debts(request: schemas.OptimizationRequest):
    raw_transactions = [
        Transaction(t.debtor_id, t.creditor_id, t.amount) 
        for t in request.transactions
    ]
    
    optimized = simplify_debts(raw_transactions)
    
    return {
        "original_count": len(raw_transactions),
        "optimized_count": len(optimized),
        "transactions": optimized
    }


@app.post("/api/v1/expenses/", response_model=schemas.ExpenseResponse)
def add_expense(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    splits_data = [{"user_id": split.user_id, "owed_amount": split.owed_amount} for split in expense.splits]
    
    return crud.create_expense(
        db=db,
        group_id=expense.group_id,
        payer_id=expense.payer_id,
        amount=expense.amount,
        description=expense.description,
        splits=splits_data
    )