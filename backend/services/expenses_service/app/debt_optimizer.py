from typing import List, Dict, Tuple
from collections import defaultdict

class Transaction:
    def __init__(self, debtor_id: int, creditor_id: int, amount: float):
        self.debtor_id = debtor_id
        self.creditor_id = creditor_id
        self.amount = round(amount, 2)

    def __repr__(self):
        return f"User {self.debtor_id} owes User {self.creditor_id} {self.amount}"

def simplify_debts(transactions: List[Transaction]) -> List[Transaction]:
    """
    Використ. жадібний підхід для зведення загальних балансів.
    """
    balances = defaultdict(float)
    
    for t in transactions:
        balances[t.debtor_id] -= t.amount
        balances[t.creditor_id] += t.amount

    debtors = []
    creditors = []

    for user_id, balance in balances.items():
        if balance < -0.01:
            debtors.append([user_id, abs(balance)])
        elif balance > 0.01:
            creditors.append([user_id, balance])

    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)

    optimized_transactions = []
    
    i, j = 0, 0
    
    while i < len(debtors) and j < len(creditors):
        debtor_id, debt_amount = debtors[i]
        creditor_id, credit_amount = creditors[j]
        
        settled_amount = min(debt_amount, credit_amount)
        
        optimized_transactions.append(Transaction(debtor_id, creditor_id, settled_amount))
        
        debtors[i][1] -= settled_amount
        creditors[j][1] -= settled_amount
        
        if debtors[i][1] < 0.01:
            i += 1
            
        if creditors[j][1] < 0.01:
            j += 1
            
    return optimized_transactions

if __name__ == "__main__":
    raw_debts = [
        Transaction(1, 2, 100),
        Transaction(2, 3, 100),
        Transaction(3, 4, 100),
    ]
    
    print("До оптимізації (3 перекази):", raw_debts)
    optimized = simplify_debts(raw_debts)
    print("Після оптимізації (1 переказ):", optimized)