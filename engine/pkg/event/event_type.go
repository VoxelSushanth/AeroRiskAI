package event

type EventType int

const (
EventTypeUnknown EventType = iota
EventTypeOrderNew
EventTypeOrderCancel
EventTypeOrderModify
EventTypeTrade
EventTypeSettlement
EventTypeRiskDecision
EventTypeAudit
)

func (e EventType) String() string {
switch e {
case EventTypeOrderNew:
return "ORDER_NEW"
case EventTypeOrderCancel:
return "ORDER_CANCEL"
case EventTypeOrderModify:
return "ORDER_MODIFY"
case EventTypeTrade:
return "TRADE"
case EventTypeSettlement:
return "SETTLEMENT"
case EventTypeRiskDecision:
return "RISK_DECISION"
case EventTypeAudit:
return "AUDIT"
default:
return "UNKNOWN"
}
}
