# AI Observability – K3s Cluster Insights via Groq

Automatically collects Prometheus metrics, Loki logs, Tempo traces, and Kubernetes events from the K3s cluster, performs local anomaly detection, sends data to **Groq AI** for Root Cause Analysis (RCA), generates reports, and sends alerts to Slack. Runs continuously as a Deployment managed by ArgoCD, with a Slack SocketMode bot for ad-hoc queries.

---

## How It Works

```
Prometheus ──┐
            ├──► main.py ──► Anomaly Detection ──► Groq API ──► RCA Reports
Loki ────────┘                                      │
Tempo ───────┐                                      ├──► Slack Alerts
K8s Events ──┘                                      └──► Grafana Annotations
```

1. Collectors query Prometheus, Loki, Tempo, and Kubernetes API for metrics, logs, traces, and events.
2. Anomaly Detection engine identifies spikes using statistical methods (Z-score, moving averages).
3. If anomalies detected, data is sent to `llama-3.3-70b-versatile` with a structured RCA prompt.
4. Markdown reports and raw JSON are saved to `/reports/` (backed by a PVC).
5. Proactive alerts sent to Slack channel.
6. Slack bot listens for @mentions for ad-hoc queries.
7. Annotations pushed to Grafana for incident markers.

---

## Prerequisites

- K3s cluster with `kube-prometheus-stack`, `loki-stack`, `tempo`, and `opentelemetry-collector` running
- `kubectl` access to the cluster
- Docker (for building the image)
- API keys: `GROQ_API_KEY`, `SLACK_APP_TOKEN`, `SLACK_BOT_TOKEN`, `GRAFANA_API_KEY`

---

## Deployment Steps

### 1. Create the Kubernetes Secret (one-time)
```bash
cd apps/ai-observability/k8s
.\create-secret.ps1
```

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

### 3. Deploy via ArgoCD
The application is already added to `argocd/bootstrap/applicationset.yaml` under `k3s-platform-git-apps`.
ArgoCD will automatically deploy it to the `ai-observability` namespace.

### 4. Verify Deployment
```bash
kubectl get pods -n ai-observability
kubectl logs -n ai-observability deployment/ai-observability
```

---

## Configuration

Environment variables (via ConfigMap and Secret):
- `PROMETHEUS_URL`, `LOKI_URL`, `TEMPO_URL`, `GRAFANA_URL`
- `GROQ_API_KEY`, `SLACK_APP_TOKEN`, `SLACK_BOT_TOKEN`, `GRAFANA_API_KEY`
- `LOOKBACK_HOURS`, `REPORT_DIR`, `SLACK_CHANNEL`

---

## Testing

To test anomaly detection:
1. Intentionally spike CPU: `kubectl run stress --image=polinux/stress -- stress --cpu 4 --timeout 300`
2. Kill a pod: `kubectl delete pod <pod-name>`
3. Check logs: `kubectl logs -n ai-observability deployment/ai-observability`
4. Verify RCA report in `/reports/` and Slack alerts.
