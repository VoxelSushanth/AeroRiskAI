package ledger

import "errors"

var (
	ErrAccountExists       = errors.New("account already exists")
	ErrAccountNotFound     = errors.New("account not found")
	ErrInsufficientFunds   = errors.New("insufficient funds")
	ErrInvalidAmount       = errors.New("invalid amount")
	ErrSettlementNotFound  = errors.New("settlement not found")
)
