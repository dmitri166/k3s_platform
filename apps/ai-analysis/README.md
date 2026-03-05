# AI Analysis – K3s Cluster Insights via Groq

Automatically collects Prometheus metrics and Loki logs from the K3s cluster,
sends them to **Groq AI** for analysis, and saves a structured Markdown
health report to a PersistentVolume. Runs daily via a Kubernetes CronJob managed
by ArgoCD.

---

## How It Works

```
Prometheus ──┐
             ├──► analyze.py ──► Groq API ──► /reports/YYYY-MM-DD.md
Loki ────────┘
```

1. `analyze.py` queries Prometheus (CPU, memory, pod restarts, PVC usage, API latency)
2. `analyze.py` queries Loki (errors, warnings, OOMKilled, CrashLoopBackOff events)
3. Data is sent to `llama3-70b-8192` with a structured SRE-grade prompt
4. A Markdown report + raw JSON are saved to `/reports/` (backed by a PVC)

---

## Prerequisites

- K3s cluster with `kube-prometheus-stack` and `loki-stack` running
- `kubectl` access to the cluster
- Docker (for building the image)
- `GROQ_API_KEY` – already in the project

---

## Deployment Steps

### 1. Create the Kubernetes Secret (one-time)
```bash
cd apps/ai-analysis/k8s
chmod +x create-secret.sh
./create-secret.sh
```

### 2. Build & Load the Docker Image

**Option A – Local k3s (no registry needed)**
```bash
cd apps/ai-analysis
docker build -t ai-analysis:latest .
docker save ai-analysis:latest | k3s ctr images import -
```

**Option B – Docker Hub**
```bash
docker build -t <your-dockerhub-user>/ai-analysis:latest .
docker push <your-dockerhub-user>/ai-analysis:latest
# Then update image: in k8s/cronjob.yaml
```

### 3. ArgoCD sync
`ai-analysis` is already added to the `k3s-platform-git-apps` ApplicationSet.
After pushing to Git:
```bash
# ArgoCD will auto-sync within ~3 minutes, or force it:
argocd app sync ai-analysis
```

### 4. Run a manual test job
```bash
kubectl create job --from=cronjob/ai-analysis ai-analysis-manual -n ai-analysis
kubectl logs -l job-name=ai-analysis-manual -n ai-analysis -f
```

### 5. Read the report
```bash
# Exec into a debug pod that mounts the PVC, or:
kubectl run report-reader --image=busybox -n ai-analysis --rm -it \
  --overrides='{"spec":{"volumes":[{"name":"r","persistentVolumeClaim":{"claimName":"ai-analysis-reports"}}],"containers":[{"name":"c","image":"busybox","command":["sh"],"volumeMounts":[{"name":"r","mountPath":"/reports"}]}]}}' \
  -- ls -la /reports/
```

---

## Configuration

All settings are in `k8s/configmap.yaml` (non-sensitive) and `k8s/create-secret.sh` (API key).

| Variable | Default | Description |
|---|---|---|
| `PROMETHEUS_URL` | `http://kube-prometheus-stack-prometheus.monitoring.svc:9090` | Prometheus API |
| `LOKI_URL` | `http://loki.monitoring.svc:3100` | Loki API |
| `GROQ_MODEL` | `llama3-70b-8192` | Groq model name |
| `GROQ_MAX_RPM` | `10` | Max API calls per minute |
| `LOOKBACK_HOURS` | `24` | Hours of data to analyse |
| `REPORT_DIR` | `/reports` | Report output directory |
| `REPORT_RETENTION_DAYS` | `30` | Days before old reports are deleted |

---

## File Structure

```
apps/ai-analysis/
├── Dockerfile            # Python 3.11 slim, non-root
├── requirements.txt      # Python dependencies
├── config.py             # Env-var driven configuration
├── analyze.py            # Main pipeline script
├── README.md             # This file
└── k8s/
    ├── namespace.yaml    # ai-analysis namespace
    ├── rbac.yaml         # ServiceAccount + ClusterRole (read-only)
    ├── pvc.yaml          # 5Gi PVC for reports (local-path)
    ├── configmap.yaml    # Non-sensitive config
    ├── cronjob.yaml      # Daily CronJob (06:00 UTC)
    └── create-secret.ps1 # Creates groq-api-key Secret (not in Git)
```
