package metrics

const (
LabelSideBuy  = "BUY"
LabelSideSell = "SELL"

LabelStatusAccepted   = "accepted"
LabelStatusRejected   = "rejected"
LabelStatusFilled     = "filled"
LabelStatusPartial    = "partial"
LabelStatusCancelled  = "cancelled"

LabelDecisionAllow      = "allow"
LabelDecisionFlag       = "flag"
LabelDecisionBlock      = "block"
LabelDecisionAdjustLimit = "adjust_limit"

LabelComponentGateway   = "gateway"
LabelComponentMatching  = "matching"
LabelComponentLedger    = "ledger"
LabelComponentPublisher = "publisher"
LabelComponentRisk      = "risk"
LabelComponentCache     = "cache"

LabelErrorValidation    = "validation"
LabelErrorAuthentication = "authentication"
LabelErrorAuthorization = "authorization"
LabelErrorTimeout       = "timeout"
LabelErrorInternal      = "internal"
LabelErrorCircuitBreak  = "circuit_break"
)
