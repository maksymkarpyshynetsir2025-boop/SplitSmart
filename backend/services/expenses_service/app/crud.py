from sqlalchemy.orm import Session
from app import models

def create_expense(db: Session, group_id: int, payer_id: int, amount: float, description: str, splits: list[dict]):
    db_expense = models.Expense(
        group_id=group_id,
        payer_id=payer_id,
        amount=amount,
        description=description
    )
    db.add(db_expense)
    db.commit()
    
    db.refresh(db_expense) 

    for split in splits:
        db_split = models.ExpenseSplit(
            expense_id=db_expense.id,
            user_id=split["user_id"],
            owed_amount=split["owed_amount"]
        )
        db.add(db_split)
    
    db.commit()
    db.refresh(db_expense)
    
    return db_expense

def get_group_expenses(db: Session, group_id: int):
    return db.query(models.Expense).filter(models.Expense.group_id == group_id).all()

def delete_expense(db: Session, expense_id: int):
    expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if expense:
        db.delete(expense)
        db.commit()
        return True
    return False

def get_group_balances(db: Session, group_id: int):
    expenses = db.query(models.Expense).filter(models.Expense.group_id == group_id).all()
    
    balances = {}
    
    for expense in expenses:
        if expense.payer_id not in balances:
            balances[expense.payer_id] = 0.0
        balances[expense.payer_id] += expense.amount
        
        for split in expense.splits:
            if split.user_id not in balances:
                balances[split.user_id] = 0.0
            balances[split.user_id] -= split.owed_amount
            
    return [{"user_id": user, "balance": round(bal, 2)} for user, bal in balances.items()]