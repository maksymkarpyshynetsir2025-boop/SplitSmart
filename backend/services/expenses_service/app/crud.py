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