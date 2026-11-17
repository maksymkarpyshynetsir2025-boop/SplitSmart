from fastapi import FastAPI, Depends, HTTPException
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.debt_optimizer import simplify_debts, Transaction

models.Base.metadata.create_all(bind=models.engine)

app = FastAPI(
    title="SplitSmart Expenses Service",
    description="Microservice for calculating and optimizing shared expenses."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

@app.get("/api/v1/expenses/group/{group_id}", response_model=List[schemas.ExpenseResponse])
def read_expenses(group_id: int, db: Session = Depends(get_db)):
    expenses = crud.get_expenses_by_group(db, group_id=group_id)
    return expenses

@app.delete("/api/v1/expenses/{expense_id}")
def remove_expense(expense_id: int, db: Session = Depends(get_db)):
    success = crud.delete_expense(db, expense_id=expense_id)
    if not success:
        raise HTTPException(status_code=404, detail="Витрату не знайдено")
    return {"message": "Витрату успішно видалено"}

@app.get("/api/v1/balances/{group_id}")
def read_balances(group_id: int, db: Session = Depends(get_db)):
    balances = crud.get_group_balances(db, group_id=group_id)
    return {"group_id": group_id, "balances": balances}