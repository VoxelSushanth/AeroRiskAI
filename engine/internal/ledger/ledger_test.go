package ledger

import (
	"testing"

	"github.com/aerorisk/engine/pkg/financial"
)

func TestLedger_CreateAccount(t *testing.T) {
	l := NewLedger()

	err := l.CreateAccount(1, financial.NewQuantity(1000))
	if err != nil {
		t.Fatalf("failed to create account: %v", err)
	}

	balance, err := l.GetBalance(1)
	if err != nil {
		t.Fatalf("failed to get balance: %v", err)
	}

	if balance != 1000 {
		t.Errorf("expected balance 1000, got %d", balance)
	}
}

func TestLedger_Deposit(t *testing.T) {
	l := NewLedger()
	l.CreateAccount(1, financial.NewQuantity(1000))

	err := l.Deposit(1, financial.NewQuantity(500))
	if err != nil {
		t.Fatalf("failed to deposit: %v", err)
	}

	balance, err := l.GetBalance(1)
	if err != nil {
		t.Fatalf("failed to get balance: %v", err)
	}

	if balance != 1500 {
		t.Errorf("expected balance 1500, got %d", balance)
	}
}

func TestLedger_Withdraw(t *testing.T) {
	l := NewLedger()
	l.CreateAccount(1, financial.NewQuantity(1000))

	err := l.Withdraw(1, financial.NewQuantity(300))
	if err != nil {
		t.Fatalf("failed to withdraw: %v", err)
	}

	balance, err := l.GetBalance(1)
	if err != nil {
		t.Fatalf("failed to get balance: %v", err)
	}

	if balance != 700 {
		t.Errorf("expected balance 700, got %d", balance)
	}
}

func TestLedger_Withdraw_InsufficientFunds(t *testing.T) {
	l := NewLedger()
	l.CreateAccount(1, financial.NewQuantity(100))

	err := l.Withdraw(1, financial.NewQuantity(200))
	if err != ErrInsufficientFunds {
		t.Errorf("expected ErrInsufficientFunds, got %v", err)
	}
}

func TestLedger_Transfer(t *testing.T) {
	l := NewLedger()
	l.CreateAccount(1, financial.NewQuantity(1000))
	l.CreateAccount(2, financial.NewQuantity(500))

	err := l.Transfer(1, 2, financial.NewQuantity(200))
	if err != nil {
		t.Fatalf("failed to transfer: %v", err)
	}

	balance1, _ := l.GetBalance(1)
	balance2, _ := l.GetBalance(2)

	if balance1 != 800 {
		t.Errorf("expected balance1 800, got %d", balance1)
	}

	if balance2 != 700 {
		t.Errorf("expected balance2 700, got %d", balance2)
	}
}

func TestLedger_GetTransactions(t *testing.T) {
	l := NewLedger()
	l.CreateAccount(1, financial.NewQuantity(1000))
	l.Deposit(1, financial.NewQuantity(500))
	l.Withdraw(1, financial.NewQuantity(200))

	txns := l.GetTransactions(1)
	if len(txns) != 3 {
		t.Errorf("expected 3 transactions, got %d", len(txns))
	}
}
