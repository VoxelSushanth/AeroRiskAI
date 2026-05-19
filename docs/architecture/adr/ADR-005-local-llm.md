# ADR-005: Local LLM for Decision Orchestration

## Status
Accepted

## Context
The AI decision engine requires LLM inference for:
- Risk assessment synthesis
- Multi-factor decision making
- Natural language incident reports
- Explainable AI outputs

Regulatory requirements demand:
- Data never leaves our infrastructure
- Deterministic, reproducible outputs
- Full audit trail of prompts/responses
- Sub-100ms inference latency

## Decision
We will use self-hosted local LLMs instead of cloud APIs because:

### Advantages
- **Data Privacy**: No PII/sensitive data leaves infrastructure
- **Latency Control**: No network round-trip to external APIs
- **Cost Predictability**: Fixed infrastructure cost vs per-token pricing
- **Customization**: Fine-tuning on domain-specific data
- **Compliance**: Meets financial regulations (MiFID II, SOX)

### Model Selection
| Model | Parameters | VRAM | Use Case |
|-------|------------|------|----------|
| Mistral-7B-Instruct | 7B | 14GB | General orchestration |
| Llama-2-13B-Chat | 13B | 26GB | Complex reasoning |
| Phi-2 | 2.7B | 6GB | Fast path decisions |

### Inference Server
We will use Ollama/vLLM for serving:
- Continuous batching for throughput
- PagedAttention for memory efficiency
- OpenAI-compatible API for easy integration

### Configuration
```yaml
llm:
  provider: ollama
  model: mistral-7b-instruct
  base_url: http://ollama:11434
  max_tokens: 512
  temperature: 0.0  # Deterministic outputs
  top_p: 0.9
  timeout_ms: 100
  
quantization:
  type: int4  # Reduce VRAM requirements
  accuracy_loss: <2%
```

## Consequences

### Positive
- Full control over model lifecycle
- No vendor lock-in
- Meets regulatory requirements
- Predictable latency profile

### Negative
- Requires GPU infrastructure
- Model management overhead
- May need multiple models for different tasks
- Lower quality than largest cloud models

## Fallback Strategy
If local LLM fails or exceeds timeout:
1. Fall back to rule-based scoring
2. Flag for manual review
3. Log incident for model improvement
