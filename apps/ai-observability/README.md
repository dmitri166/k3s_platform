# AI Observability – K3s Cluster Insights via Groq

Automatically collects Prometheus metrics, Loki logs, Tempo traces, and Kubernetes events from the K3s cluster, performs local anomaly detection, sends data to **Groq AI** for Root Cause Analysis (RCA), generates reports, and sends alerts to Slack. Runs continuously as a Deployment managed by ArgoCD, with a Slack SocketMode bot for ad-hoc queries.

---

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Data Sources   │    │   AI Pipeline    │    │   Outputs       │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ Prometheus      │───▶│ Anomaly Detection│───▶│ Slack Alerts    │
│ Loki            │    │ Statistical      │    │ RCA Reports     │
│ Tempo           │    │ Analysis         │    │ Grafana Annot.  │
│ K8s Events      │    │ Groq AI RCA      │    │ JSON Data       │
│ OpenTelemetry   │    │ Report Gen       │    │ Slack Bot       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## How It Works

1. **Data Collection**: Collectors query Prometheus, Loki, Tempo, OpenTelemetry, and Kubernetes API for metrics, logs, traces, and events.
2. **Anomaly Detection**: Engine identifies spikes using statistical methods (Z-score, moving averages, threshold analysis).
3. **AI Analysis**: If anomalies detected, data is sent to `llama-3.3-70b-versatile` with a structured RCA prompt.
4. **Report Generation**: Markdown reports and raw JSON are saved to `/reports/` (backed by a PVC).
5. **Proactive Alerts**: Sent to Slack channel with incident summaries.
6. **Interactive Bot**: Slack bot listens for @mentions for ad-hoc queries.
7. **Grafana Integration**: Annotations pushed to Grafana for incident markers.

---

## Prerequisites

### Platform Requirements
- K3s cluster with the following components deployed via ArgoCD:
  - `kube-prometheus-stack` (Prometheus, Grafana, AlertManager)
  - `loki-stack` (Log aggregation)
  - `tempo` (Distributed tracing)
  - `opentelemetry-collector` (Telemetry collection)
  - `ingress-nginx` (For service access)
- `kubectl` access to the cluster
- Docker (for building the image)

### Required API Keys
- `GROQ_API_KEY`: Groq AI API key for RCA analysis
- `SLACK_APP_TOKEN`: Slack App-level token for Socket Mode
- `SLACK_BOT_TOKEN`: Slack Bot token for API access
- `GRAFANA_API_KEY`: Grafana API key for annotations

### Optional Configuration
- `MINIO_ACCESS_KEY`: For MinIO integration (if using object storage)
- `MINIO_SECRET_KEY`: For MinIO integration
- `VAULT_ADDR`: For Vault secrets management

---

## Deployment Steps

### 1. Create the Kubernetes Secret (one-time)
```powershell
cd apps/ai-observability/k8s
.\create-secret.ps1
```

This script creates a secret with all required API keys and configuration.

### 2. Build & Load the Docker Image

**Option A – Local k3s (no registry needed)**
```bash
cd apps/ai-observability
docker build -t ai-observability:latest .
docker save ai-observability:latest | k3s ctr images import -
```

**Option B – DockerHub or Registry**
```bash
cd apps/ai-observability
docker build -t your-registry/ai-observability:latest .
docker push your-registry/ai-observability:latest
```
Update `apps/ai-observability/k8s/deployment.yaml` with the correct image path.

**Option C – MinIO Registry (On-premises)**
```bash
cd apps/ai-observability
docker build -t 192.168.56.248:9000/ai-observability:latest .
docker push 192.168.56.248:9000/ai-observability:latest
```

### 3. Deploy via ArgoCD
The application is already added to `argocd/bootstrap/applicationset.yaml` under `k3s-platform-git-apps`.
ArgoCD will automatically deploy it to the `ai-observability` namespace.

### 4. Verify Deployment
```bash
kubectl get pods -n ai-observability
kubectl logs -n ai-observability deployment/ai-observability -f
kubectl get pvc -n ai-observability  # Verify report storage
```

---

## Configuration

### Environment Variables (ConfigMap)
- `PROMETHEUS_URL`: Prometheus server URL (default: http://prometheus.monitoring.svc.cluster.local:9090)
- `LOKI_URL`: Loki server URL (default: http://loki.monitoring.svc.cluster.local:3100)
- `TEMPO_URL`: Tempo server URL (default: http://tempo.monitoring.svc.cluster.local:3200)
- `GRAFANA_URL`: Grafana URL (default: http://grafana.monitoring.svc.cluster.local:3000)
- `LOOKBACK_HOURS`: Historical data lookback window (default: 24)
- `REPORT_DIR`: Report storage directory (default: /reports)
- `SLACK_CHANNEL`: Slack channel for alerts (default: #observability)
- `COLLECTION_INTERVAL`: Data collection interval in seconds (default: 60)
- `ANOMALY_THRESHOLD`: Z-score threshold for anomaly detection (default: 2.5)

### Environment Variables (Secret)
- `GROQ_API_KEY`: Groq AI API key
- `SLACK_APP_TOKEN`: Slack App-level token
- `SLACK_BOT_TOKEN`: Slack Bot token
- `GRAFANA_API_KEY`: Grafana API key
- `MINIO_ACCESS_KEY`: MinIO access key (optional)
- `MINIO_SECRET_KEY`: MinIO secret key (optional)
- `VAULT_ADDR`: Vault address (optional)

### Component Structure
```
ai-observability/
├── main.py              # Main orchestration logic
├── config.py            # Configuration management
├── slack_bot.py         # Slack bot implementation
├── analyzers/           # Anomaly detection modules
│   ├── prompt_builder.py # RCA prompt construction
│   └── statistical.py   # Statistical analysis
├── collectors/          # Data collection modules
│   ├── prometheus.py    # Metrics collection
│   ├── loki.py          # Log collection
│   ├── tempo.py         # Trace collection
│   ├── k8s_events.py    # Kubernetes events
│   └── opentelemetry.py # OTel data
├── reporters/           # Output modules
│   ├── slack.py         # Slack integration
│   └── grafana.py       # Grafana annotations
├── ai/                  # AI processing
│   └── groq_client.py   # Groq API client
└── k8s/                 # Kubernetes manifests
    ├── deployment.yaml  # Main deployment
    ├── configmap.yaml   # Configuration
    ├── pvc.yaml         # Report storage
    ├── rbac.yaml        # Permissions
    └── namespace.yaml   # Namespace
```

---

## Testing

### Anomaly Detection Testing
To test anomaly detection:
1. **CPU Stress Test**:
   ```bash
   kubectl run stress --image=polinux/stress --rm -i --tty -- stress --cpu 4 --timeout 300
   ```
2. **Pod Deletion**:
   ```bash
   kubectl delete pod <pod-name> -n <namespace>
   ```
3. **Memory Pressure**:
   ```bash
   kubectl run stress-mem --image=polinux/stress --rm -i --tty -- stress --vm 2 --vm-bytes 256M --timeout 300
   ```
4. **Network Issues**:
   ```bash
   kubectl run network-test --image=alpine --rm -i --tty -- sh -c 'while true; do wget -qO- http://httpbin.org/delay/1 > /dev/null; done'
   ```

### Verification Steps
1. **Check Logs**:
   ```bash
   kubectl logs -n ai-observability deployment/ai-observability -f
   ```
2. **Verify Reports**:
   ```bash
   kubectl exec -n ai-observability deployment/ai-observability -- ls -la /reports/
   kubectl exec -n ai-observability deployment/ai-observability -- cat /reports/latest-rca.md
   ```
3. **Check Slack Alerts**: Verify alerts in configured Slack channel
4. **Grafana Annotations**: Check Grafana for incident markers
5. **Slack Bot Testing**: Mention the bot in Slack with queries like:
   - `@ai-observability what happened in the last hour?`
   - `@ai-observability analyze pod failures`
   - `@ai-observability show recent anomalies`

### Performance Testing
```bash
# Load test with multiple stressors
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: load-test
spec:
  containers:
  - name: stress
    image: polinux/stress
    command: ["stress"]
    args: ["--cpu", "2", "--io", "2", "--vm", "1", "--vm-bytes", "128M", "--timeout", "300s"]
  restartPolicy: Never
EOF
```

## Troubleshooting

### Common Issues

1. **Pod Not Starting**:
   ```bash
   kubectl describe pod -n ai-observability
   kubectl get events -n ai-observability
   ```

2. **Missing API Keys**:
   ```bash
   kubectl get secret ai-observability-secrets -n ai-observability -o yaml
   # Re-run create-secret.ps1 if needed
   ```

3. **Network Connectivity**:
   ```bash
   kubectl exec -n ai-observability deployment/ai-observability -- wget -qO- http://prometheus.monitoring.svc.cluster.local:9090/api/v1/query?query=up
   ```

4. **Slack Bot Not Responding**:
   ```bash
   kubectl logs -n ai-observability deployment/ai-observability | grep slack
   # Verify SLACK_APP_TOKEN and SLACK_BOT_TOKEN
   ```

5. **No Reports Generated**:
   ```bash
   kubectl get pvc -n ai-observability
   kubectl exec -n ai-observability deployment/ai-observability -- df -h /reports
   ```

### Debug Mode
Enable debug logging by updating the ConfigMap:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ai-observability-config
data:
  LOG_LEVEL: "DEBUG"
  COLLECTION_INTERVAL: "30"  # More frequent for testing
```

### Manual Testing
```bash
# Test individual collectors
kubectl exec -n ai-observability deployment/ai-observability -- python -c "from collectors.prometheus import PrometheusCollector; print(PrometheusCollector().get_metrics())"

# Test anomaly detection
kubectl exec -n ai-observability deployment/ai-observability -- python -c "from analyzers.statistical import detect_anomalies; print(detect_anomalies([1,2,3,10,4,5]))"
```

---

## Integration Points

### Grafana Integration
- Automatic annotation creation for detected incidents
- Dashboard links in Slack alerts
- Historical anomaly visualization

### Slack Integration
- Proactive alerting with severity levels
- Interactive bot for ad-hoc analysis
- Threaded conversations for incident follow-up

### MinIO Integration (Optional)
- Long-term report storage
- Backup of RCA analysis
- Integration with external tools

### Vault Integration (Optional)
- Secure API key management
- Automatic secret rotation
- Centralized credential management

---

## Performance Considerations

- **Resource Requirements**: 500m CPU, 512Mi memory baseline
- **Storage**: 1Gi PVC for reports (auto-cleanup after 30 days)
- **Network**: ~10MB/hour data collection
- **API Limits**: Groq API rate limiting handled with exponential backoff

---

## Security Notes

- All API keys stored in Kubernetes secrets
- RBAC configured for minimal required permissions
- Network policies restrict egress traffic
- No sensitive data logged or exposed in reports
