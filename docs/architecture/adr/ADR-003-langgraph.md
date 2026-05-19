# ADR-003: LangGraph for Multi-Agent AI Pipeline

## Status
Accepted

## Context
The AI risk orchestration requires a multi-agent pipeline with:
- Deterministic execution paths for auditability
- State management across agent boundaries
- Conditional routing based on intermediate results
- Graceful error handling and timeouts

## Decision
We will use LangGraph instead of raw LangChain because:

### Advantages
- **Explicit State Machine**: Clear execution flow, auditable decisions
- **Cyclic Graphs**: Support for retry loops and refinement cycles
- **State Persistence**: Checkpointing for long-running workflows
- **Conditional Edges**: Dynamic routing based on agent outputs
- **Better Observability**: Built-in tracing of graph execution

### Graph Structure
```
                    ┌─────────────────┐
                    │   START         │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Agent 1:        │
                    │ Anomaly Detect  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
              ┌─────► Agent 2:        │◄─────┐
              │     │ RAG + Context   │      │
              │     └────────┬────────┘      │
              │              │               │
              │     ┌────────▼────────┐      │
              │     │ Risk < 0.3?     │──Yes─┤
              │     └────────┬────────┘      │
              │              │ No            │
              │     ┌────────▼────────┐      │
              └─────┤ Agent 3:        │◄─────┘
                    │ Orchestrator    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ END + Actions   │
                    └─────────────────┘
```

## Consequences

### Positive
- Clear separation of concerns between agents
- Audit trail of decision path
- Easy to add new agents or modify flow
- Built-in retry and timeout handling

### Negative
- Additional dependency (LangGraph)
- Learning curve for team
- Slight overhead vs raw async calls

## Implementation Notes
- All agents must be stateless functions
- State passed through TypedDict
- Timeout: 200ms total pipeline
- Each agent: <50ms budget
