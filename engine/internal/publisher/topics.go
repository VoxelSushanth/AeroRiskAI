package publisher

const (
TopicOrders       = "aerorisk.orders"
TopicTrades       = "aerorisk.trades"
TopicRiskDecision = "aerorisk.risk.decisions"
TopicAuditLog     = "aerorisk.audit.log"
TopicMarketData   = "aerorisk.market.data"
)

type Topics struct {
Orders       string
Trades       string
RiskDecisions string
AuditLog     string
MarketData   string
}

func NewTopics() *Topics {
return &Topics{
Orders:        TopicOrders,
Trades:        TopicTrades,
RiskDecisions: TopicRiskDecision,
AuditLog:      TopicAuditLog,
MarketData:    TopicMarketData,
}
}
