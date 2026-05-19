package ledger

import (
	"sync"
	"time"

	"github.com/aerorisk/engine/pkg/financial"
)

type TransactionType int

const (
	TransactionTypeUnknown TransactionType = iota
	TransactionTypeDeposit
	TransactionTypeWithdrawal
	TransactionTypeTransfer
	TransactionTypeTrade
)

type Transaction struct {
	ID        uint64            `json:"id"`
	Type      TransactionType   `json:"type"`
	AccountID uint64            `json:"account_id"`
	Amount    financial.Quantity `json:"amount"`
	Balance   financial.Quantity `json:"balance"`
	Timestamp time.Time         `json:"timestamp"`
}

type Account struct {
	ID      uint64           `json:"id"`
	Balance financial.Quantity `json:"balance"`
	mu      sync.Mutex
}

type Ledger struct {
	accounts     map[uint64]*Account
	transactions []*Transaction
	mu           sync.RWMutex
	nextTxnID    uint64
}

func NewLedger() *Ledger {
	return &Ledger{
		accounts:     make(map[uint64]*Account),
		transactions: make([]*Transaction, 0),
	}
}

func (l *Ledger) CreateAccount(id uint64, initialBalance financial.Quantity) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	if _, exists := l.accounts[id]; exists {
		return ErrAccountExists
	}

	l.accounts[id] = &Account{
		ID:      id,
		Balance: initialBalance,
	}

	return nil
}

func (l *Ledger) GetBalance(accountID uint64) (financial.Quantity, error) {
	l.mu.RLock()
	defer l.mu.RUnlock()

	account, exists := l.accounts[accountID]
	if !exists {
		return 0, ErrAccountNotFound
	}

	return account.Balance, nil
}

func (l *Ledger) Deposit(accountID uint64, amount financial.Quantity) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	account, exists := l.accounts[accountID]
	if !exists {
		return ErrAccountNotFound
	}

	account.mu.Lock()
	account.Balance += amount
	account.mu.Unlock()

	l.recordTransaction(TransactionTypeDeposit, accountID, amount, account.Balance)
	return nil
}

func (l *Ledger) Withdraw(accountID uint64, amount financial.Quantity) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	account, exists := l.accounts[accountID]
	if !exists {
		return ErrAccountNotFound
	}

	account.mu.Lock()
	defer account.mu.Unlock()

	if account.Balance < amount {
		return ErrInsufficientFunds
	}

	account.Balance -= amount
	l.recordTransaction(TransactionTypeWithdrawal, accountID, amount, account.Balance)
	return nil
}

func (l *Ledger) Transfer(fromID, toID uint64, amount financial.Quantity) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	fromAccount, exists := l.accounts[fromID]
	if !exists {
		return ErrAccountNotFound
	}

	toAccount, exists := l.accounts[toID]
	if !exists {
		return ErrAccountNotFound
	}

	fromAccount.mu.Lock()
	defer fromAccount.mu.Unlock()

	if fromAccount.Balance < amount {
		return ErrInsufficientFunds
	}

	fromAccount.Balance -= amount
	toAccount.Balance += amount

	l.recordTransaction(TransactionTypeTransfer, fromID, -amount, fromAccount.Balance)
	l.recordTransaction(TransactionTypeTransfer, toID, amount, toAccount.Balance)

	return nil
}

func (l *Ledger) recordTransaction(txnType TransactionType, accountID uint64, amount financial.Quantity, balance financial.Quantity) {
	l.nextTxnID++
	txn := &Transaction{
		ID:        l.nextTxnID,
		Type:      txnType,
		AccountID: accountID,
		Amount:    amount,
		Balance:   balance,
		Timestamp: time.Now(),
	}
	l.transactions = append(l.transactions, txn)
}

func (l *Ledger) GetTransactions(accountID uint64) []*Transaction {
	l.mu.RLock()
	defer l.mu.RUnlock()

	var result []*Transaction
	for _, txn := range l.transactions {
		if txn.AccountID == accountID {
			result = append(result, txn)
		}
	}
	return result
}
