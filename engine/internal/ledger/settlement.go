package ledger

import "time"

type Settlement struct {
	ID            uint64    `json:"id"`
	TradeID       uint64    `json:"trade_id"`
	BuyerAccount  uint64    `json:"buyer_account"`
	SellerAccount uint64    `json:"seller_account"`
	Amount        int64     `json:"amount"`
	Status        string    `json:"status"`
	CreatedAt     time.Time `json:"created_at"`
	SettledAt     time.Time `json:"settled_at"`
}

type SettlementEngine struct {
	settlements map[uint64]*Settlement
	nextID      uint64
}

func NewSettlementEngine() *SettlementEngine {
	return &SettlementEngine{
		settlements: make(map[uint64]*Settlement),
	}
}

func (se *SettlementEngine) CreateSettlement(tradeID, buyerAccount, sellerAccount uint64, amount int64) *Settlement {
	se.nextID++
	settlement := &Settlement{
		ID:            se.nextID,
		TradeID:       tradeID,
		BuyerAccount:  buyerAccount,
		SellerAccount: sellerAccount,
		Amount:        amount,
		Status:        "PENDING",
		CreatedAt:     time.Now(),
	}
	se.settlements[settlement.ID] = settlement
	return settlement
}

func (se *SettlementEngine) Settle(settlementID uint64) error {
	settlement, exists := se.settlements[settlementID]
	if !exists {
		return ErrSettlementNotFound
	}

	settlement.Status = "SETTLED"
	settlement.SettledAt = time.Now()
	return nil
}

func (se *SettlementEngine) GetSettlement(id uint64) (*Settlement, error) {
	settlement, exists := se.settlements[id]
	if !exists {
		return nil, ErrSettlementNotFound
	}
	return settlement, nil
}
