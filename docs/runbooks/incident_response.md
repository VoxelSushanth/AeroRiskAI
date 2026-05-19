# Incident Response Runbook

## Overview

This runbook provides step-by-step procedures for responding to incidents in the AeroRisk AI platform. All incidents should be logged in the incident tracking system and post-mortems conducted for Severity 1 and 2 incidents.

## Incident Severity Levels

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| **SEV-1** | Critical - System down, data loss | <5 minutes | Complete outage, fraud breach |
| **SEV-2** | High - Major degradation | <15 minutes | >50% latency increase, partial outage |
| **SEV-3** | Medium - Minor issues | <1 hour | Elevated error rates, single component failure |
| **SEV-4** | Low - Non-urgent | <24 hours | Cosmetic issues, minor bugs |

## On-Call Rotation

**Primary On-Call**: [Link to PagerDuty/OpsGenie]
**Secondary On-Call**: [Contact Info]
**Escalation Path**: Primary → Secondary → Engineering Manager → CTO

## Communication Channels

- **Incident War Room**: Slack #incidents
- **Status Page**: status.aerorisk.ai
- **Customer Comms**: [Template Link]
- **Executive Updates**: Every 30 minutes for SEV-1

---

## Incident Playbooks

### PLAYBOOK 1: High Latency (>1ms p99)

**Severity**: SEV-2

**Symptoms**:
- Order processing latency exceeds 1ms p99
- Customer complaints about slow executions
- Grafana alert: `engine_order_latency_ns > 1000000`

**Immediate Actions**:

1. **Assess Scope** (2 minutes)
   ```bash
   # Check current latency
   curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.99,rate(engine_order_latency_ns_bucket[5m]))'
   
   # Check throughput
   curl -s http://localhost:9090/api/v1/query?query='rate(engine_orders_processed_total[5m])'
   ```

2. **Check Recent Deployments** (1 minute)
   ```bash
   # Check recent deployments
   kubectl get deployments -n aerorisk --sort-by='.metadata.creationTimestamp'
   
   # Review deployment logs
   kubectl logs -n aerorisk deploy/engine -c engine --tail=100
   ```

3. **Scale if Needed** (2 minutes)
   ```bash
   # Scale engine horizontally
   kubectl scale deployment engine --replicas=5 -n aerorisk
   
   # Verify scaling
   kubectl get pods -n aerorisk -l app=engine
   ```

4. **Enable Circuit Breakers** (if latency persists)
   ```bash
   # Manually open circuit breaker
   redis-cli SET circuit_breaker:manual OPEN EX 300
   ```

**Root Cause Analysis**:
- [ ] Check GC pauses
- [ ] Review CPU saturation
- [ ] Check network connectivity
- [ ] Analyze recent code changes
- [ ] Review database query performance

**Resolution Verification**:
```bash
# Verify latency returned to normal
curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.99,rate(engine_order_latency_ns_bucket[5m]))'
# Expected: <500000 (500μs)
```

---

### PLAYBOOK 2: Fraud Detection Failure

**Severity**: SEV-1

**Symptoms**:
- Suspicious trades not flagged
- Anomaly detection pipeline not processing events
- Kafka consumer lag increasing

**Immediate Actions**:

1. **Stop Trading** (IMMEDIATE)
   ```bash
   # Open all circuit breakers
   redis-cli MSET circuit_breaker:AAPL OPEN circuit_breaker:GOOGL OPEN circuit_breaker:MSFT OPEN
   redis-cli EXPIRE circuit_breaker:AAPL 3600
   redis-cli EXPIRE circuit_breaker:GOOGL 3600
   redis-cli EXPIRE circuit_breaker:MSFT 3600
   
   # Notify trading desk
   # Call: +1-XXX-XXX-XXXX (Trading Desk)
   ```

2. **Preserve Evidence** (5 minutes)
   ```bash
   # Export recent events
   docker exec aerorisk-kafka kafka-console-consumer \
     --bootstrap-server localhost:9092 \
     --topic aerorisk.orders \
     --from-beginning \
     --timeout-ms 60000 > /tmp/evidence_orders.json
   
   # Export AI decisions
   kubectl logs -n aerorisk deploy/ai-guardrail --tail=10000 > /tmp/evidence_decisions.log
   ```

3. **Restart AI Pipeline** (5 minutes)
   ```bash
   # Rolling restart of AI guardrail
   kubectl rollout restart deployment ai-guardrail -n aerorisk
   
   # Monitor restart
   kubectl rollout status deployment ai-guardrail -n aerorisk
   ```

4. **Manual Review Queue** 
   ```bash
   # Flag all recent transactions for review
   psql -h postgres -U aerorisk -d aerorisk -c \
     "UPDATE transactions SET review_status='PENDING_MANUAL' WHERE created_at > NOW() - INTERVAL '1 hour'"
   ```

**Root Cause Analysis**:
- [ ] Review anomaly detection models
- [ ] Check model drift
- [ ] Verify feature engineering pipeline
- [ ] Review training data quality
- [ ] Check for adversarial patterns

**Regulatory Notification**:
- [ ] Legal team notified
- [ ] Compliance officer briefed
- [ ] Regulatory filing prepared (if required)

---

### PLAYBOOK 3: Data Corruption

**Severity**: SEV-1

**Symptoms**:
- Ledger imbalance detected
- Account balances incorrect
- Audit trail inconsistencies

**Immediate Actions**:

1. **Freeze All Operations** (IMMEDIATE)
   ```bash
   # Set system to maintenance mode
   redis-cli SET system_mode MAINTENANCE
   
   # Reject all new orders
   kubectl patch deployment gateway -n aerorisk --type='json' \
     -p='[{"op": "replace", "path": "/spec/template/metadata/labels/maintenance", "value": "true"}]'
   ```

2. **Snapshot Current State** (10 minutes)
   ```bash
   # Backup Redis
   docker exec aerorisk-redis redis-cli BGSAVE
   docker cp aerorisk-redis:/data/dump.rdb /tmp/redis-backup-$(date +%Y%m%d-%H%M%S).rdb
   
   # Backup PostgreSQL
   docker exec aerorisk-postgres pg_dump -U aerorisk aerorisk > \
     /tmp/postgres-backup-$(date +%Y%m%d-%H%M%S).sql
   ```

3. **Identify Corruption Point** (15 minutes)
   ```bash
   # Run integrity checks
   python scripts/check_ledger_integrity.py --from=2024-01-01 --to=$(date +%Y-%m-%d)
   
   # Compare with audit logs
   python scripts/reconcile_audit_trail.py
   ```

4. **Prepare Rollback** (if needed)
   ```bash
   # Identify last known good state
   # Restore from backup
   cat /tmp/postgres-backup-YYYYMMDD.sql | docker exec -i aerorisk-postgres psql -U aerorisk -d aerorisk
   ```

**Root Cause Analysis**:
- [ ] Review recent deployments
- [ ] Check for race conditions
- [ ] Analyze transaction logs
- [ ] Review concurrent access patterns
- [ ] Check for hardware issues

**Customer Communication**:
- [ ] Prepare customer notification
- [ ] Update status page
- [ ] Prepare FAQ document

---

### PLAYBOOK 4: Kafka/Redpanda Outage

**Severity**: SEV-2

**Symptoms**:
- Producer errors in logs
- Consumer lag increasing
- Events not being processed

**Immediate Actions**:

1. **Check Cluster Health** (2 minutes)
   ```bash
   # Check broker status
   docker exec aerorisk-kafka kafka-broker-api-versions --bootstrap-server localhost:9092
   
   # Check topic status
   docker exec aerorisk-kafka kafka-topics --bootstrap-server localhost:9092 --describe
   ```

2. **Restart Brokers** (5 minutes)
   ```bash
   # Rolling restart
   kubectl rollout restart statefulset kafka -n aerorisk
   
   # Monitor recovery
   watch kubectl get pods -n aerorisk -l app=kafka
   ```

3. **Clear Backlog** (if needed)
   ```bash
   # Reset consumer offsets (careful!)
   docker exec aerorisk-kafka kafka-consumer-groups \
     --bootstrap-server localhost:9092 \
     --group ai-guardrail \
     --reset-offsets \
     --to-latest \
     --execute
   ```

**Root Cause Analysis**:
- [ ] Check disk space
- [ ] Review network connectivity
- [ ] Analyze broker logs
- [ ] Check Zookeeper health
- [ ] Review resource limits

---

### PLAYBOOK 5: Redis Outage

**Severity**: SEV-2

**Symptoms**:
- Cache misses increasing
- Circuit breaker state lost
- Account state errors

**Immediate Actions**:

1. **Check Redis Status** (1 minute)
   ```bash
   docker exec aerorisk-redis redis-cli PING
   docker exec aerorisk-redis redis-cli INFO
   ```

2. **Restart Redis** (3 minutes)
   ```bash
   kubectl rollout restart statefulset redis -n aerorisk
   ```

3. **Rebuild Cache** (if needed)
   ```bash
   # Rebuild account state cache
   python scripts/rebuild_account_cache.py
   ```

**Root Cause Analysis**:
- [ ] Check memory usage
- [ ] Review eviction policies
- [ ] Analyze connection pool
- [ ] Check persistence settings

---

## Post-Incident Process

### Immediate Post-Incident (Within 24 Hours)

1. **Send Incident Summary**
   - Timeline of events
   - Impact assessment
   - Resolution steps taken

2. **Schedule Blameless Post-Mortem**
   - Within 48 hours for SEV-1/2
   - Include all stakeholders
   - Focus on systems, not individuals

### Post-Mortem Document Template

```markdown
# Incident Post-Mortem: [INCIDENT-ID]

## Summary
[Brief description]

## Impact
- Duration: X minutes
- Affected users: X%
- Financial impact: $X (if applicable)

## Timeline
- HH:MM - Incident started
- HH:MM - Detected
- HH:MM - Response initiated
- HH:MM - Mitigation applied
- HH:MM - Resolved

## Root Cause
[Technical explanation]

## Contributing Factors
[List factors]

## Action Items
| Item | Owner | Due Date | Status |
|------|-------|----------|--------|
| Fix bug | @name | YYYY-MM-DD | TODO |
| Add monitoring | @name | YYYY-MM-DD | TODO |
| Update runbook | @name | YYYY-MM-DD | TODO |

## Lessons Learned
- What went well
- What could be improved
- Where we got lucky
```

### Follow-Up

1. **Track Action Items**
   - Create Jira tickets
   - Assign owners
   - Set deadlines

2. **Update Documentation**
   - Revise runbooks
   - Update architecture docs
   - Add new alerts

3. **Share Learnings**
   - Present at engineering all-hands
   - Update training materials
   - Share with industry (if appropriate)

---

## Emergency Contacts

| Role | Name | Phone | Email |
|------|------|-------|-------|
| Primary On-Call | [Name] | [Phone] | [Email] |
| Secondary On-Call | [Name] | [Phone] | [Email] |
| Engineering Manager | [Name] | [Phone] | [Email] |
| CTO | [Name] | [Phone] | [Email] |
| Legal Counsel | [Name] | [Phone] | [Email] |
| Compliance Officer | [Name] | [Phone] | [Email] |
| AWS Support | - | 1-800-XXX-XXXX | - |

---

## Tools & Access

### Monitoring
- Grafana: http://grafana.aerorisk.ai
- Prometheus: http://prometheus.aerorisk.ai
- Jaeger: http://jaeger.aerorisk.ai

### Infrastructure
- Kubernetes: `kubectl --context=aerorisk-prod`
- Redis: `redis-cli -h redis.aerorisk.ai`
- PostgreSQL: `psql -h postgres.aerorisk.ai -U aerorisk`

### Logs
- Kibana: http://kibana.aerorisk.ai
- CloudWatch: https://console.aws.amazon.com/cloudwatch

### Deployment
- ArgoCD: https://argocd.aerorisk.ai
- GitHub Actions: https://github.com/aerorisk/aerorisk-ai/actions

---

## Appendix: Useful Commands

### Quick Diagnostics

```bash
# Check all pods
kubectl get pods -n aerorisk -o wide

# Check recent events
kubectl get events -n aerorisk --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods -n aerorisk

# Check persistent volumes
kubectl get pv,pvc -n aerorisk
```

### Log Queries

```bash
# Last 100 lines from all engine pods
kubectl logs -n aerorisk -l app=engine --tail=100

# Search for errors
kubectl logs -n aerorisk -l app=engine | grep -i error

# Follow logs in real-time
kubectl logs -n aerorisk -l app=engine -f
```

### Database Queries

```sql
-- Check recent incidents
SELECT * FROM incident_reports ORDER BY created_at DESC LIMIT 10;

-- Check transaction volume
SELECT DATE_TRUNC('hour', created_at) as hour, COUNT(*) 
FROM transactions 
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY 1 ORDER BY 1;

-- Check ledger balance
SELECT account_id, SUM(amount) as balance 
FROM ledger_entries 
GROUP BY account_id 
HAVING SUM(amount) != 0;
```
