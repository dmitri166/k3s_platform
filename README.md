# K3s On-Premises Platform

A production-ready on-premises Kubernetes platform built with K3s, optimized for laptop development while maintaining enterprise-grade features.

## Overview

This project provides a complete Kubernetes platform that mirrors cloud-native EKS functionality but runs entirely on-premises using K3s. It's designed for development, testing, and learning while following production best practices.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Host Machine (16GB RAM)                   │
├─────────────────────────────────────────────────────────────┤
│  VirtualBox VMs (11GB RAM, 8 CPU cores total)               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │   cp1   │ │   cp2   │ │worker1  │ │worker2  │           │
│  │ 2.5GB RAM│ │ 2.5GB RAM│ │ 3GB RAM │ │ 3GB RAM │           │
│  │ 2 CPU   │ │ 2 CPU   │ │ 2 CPU   │ │ 2 CPU   │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## Features

### Infrastructure
- **K3s**: Lightweight, certified Kubernetes distribution
- **VirtualBox**: VM management for local development
- **Vagrant**: Infrastructure automation and reproducibility
- **Terraform**: Infrastructure as Code for platform services
- **MetalLB**: LoadBalancer implementation for on-premises environments
- **High Availability**: 2-node control plane with 2 worker nodes

### Platform Services
- **ArgoCD**: GitOps continuous delivery
- **NGINX Ingress**: Traffic routing and load balancing
- **Cert-Manager**: Automated certificate management
- **Vault OSS**: Production-grade secrets management
- **External Secrets**: Kubernetes secrets synchronization
- **MinIO**: Object storage for AI workloads

### Monitoring & Observability
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Loki**: Log aggregation and querying
- **Tempo**: Distributed tracing
- **OpenTelemetry Collector**: Telemetry data collection
- **Alert management**: Proactive monitoring
- **AI Observability**: Groq-powered root cause analysis

### Security
- **OPA Gatekeeper**: Policy enforcement and admission control
- **Falco**: Runtime security monitoring
- **Network policies**: Pod-to-pod communication control
- **RBAC**: Role-based access control

### Backup & Recovery
- **Velero**: Cluster backup and disaster recovery
- **Automated backups**: Scheduled backup policies
- **Restore procedures**: Disaster recovery workflows

## Quick Start

### Prerequisites

Ensure you have the following tools installed:

- **VirtualBox**: VM management
- **Vagrant**: Infrastructure automation
- **Terraform**: Infrastructure as Code
- **kubectl**: Kubernetes CLI
- **PowerShell**: Windows automation

### Installation

1. **Run host networking preflight (Windows, Admin PowerShell)**:
   ```powershell
   .\scripts\preflight-network.ps1
   ```

2. **Deploy K3s cluster**:
   ```powershell
   .\scripts\k3s-deploy.ps1
   ```
   For host-only networking:
   ```powershell
   $env:K3S_NETWORK_MODE="hostonly"
   .\scripts\k3s-deploy.ps1
   ```
   For bridged networking:
   ```powershell
   $env:K3S_NETWORK_MODE="bridged"
   $env:BRIDGE_ADAPTER="Wi-Fi"
   .\scripts\k3s-deploy.ps1
   ```
3. **Deploy platform services**:
   
   ```bash
   cd terraform
   terraform init
   terraform apply -target='module.metallb.kubernetes_namespace.metallb' -auto-approve
   terraform apply -target='module.metallb.helm_release.metallb' -auto-approve
   terraform apply
   ```

4. **Bootstrap ArgoCD applications (GitOps apps of apps)**:
   ```powershell
   .\scripts\bootstrap-argocd-apps.ps1
   ```

5. **Verify deployment**:
   ```powershell
   .\scripts\final-verification.ps1
   ```

### Access Services

After deployment, access the services at:

- **ArgoCD**: http://192.168.56.245
- **Applications**: http://192.168.56.241
- **Grafana**: http://192.168.56.242
- **Prometheus**: http://192.168.56.243
- **Vault**: http://192.168.56.244
- **Alertmanager**: http://192.168.56.246
- **Loki**: http://192.168.56.247
- **MinIO**: http://192.168.56.248

### Get Credentials

```bash
# Get ArgoCD initial admin password
terraform output -raw argocd_initial_admin_password_command

# Access cluster via kubectl
export KUBECONFIG=~/.kube/config-k3s
kubectl get nodes
```

## Architecture Details

### Network Configuration

```
Network: 192.168.56.0/24
├── Host: 192.168.56.1
├── Control Plane:
│   ├── cp1: 192.168.56.101
│   └── cp2: 192.168.56.102
└── Workers:
    ├── worker1: 192.168.56.103
    └── worker2: 192.168.56.104
```

### LoadBalancer IP Pool

```
MetalLB IP Range: 192.168.56.240-192.168.56.250
├── ArgoCD: 192.168.56.245
├── Ingress: 192.168.56.241
├── Grafana: 192.168.56.242
├── Prometheus: 192.168.56.243
└── Vault: 192.168.56.244
```

### Resource Allocation

| Node Type | RAM | CPU | Purpose |
|-----------|-----|-----|---------|
| Control Plane | 2.5GB | 2 | HA etcd + API server |
| Workers | 3GB | 2 | Application workloads |
| **Total** | **11GB** | **8** | **Complete platform** |

## Taint Configuration

Control plane nodes are tainted with `node-role.kubernetes.io/control-plane=true:NoSchedule`
via Terraform configuration to prevent workloads from running on them. This ensures:
- Control planes have dedicated resources for Kubernetes operations
- Better resource isolation between control plane and workloads
- Improved performance and stability
- Predictable resource allocation

## Application Distribution

- **Control Planes**: Cert Manager, Vault (critical components)
- **Workers**: AI Observability, Monitoring, Ingress, External Secrets, Falco, Velero

## GitOps Workflow

This platform uses ArgoCD for GitOps deployment:

1. **Infrastructure**: Managed by Terraform
2. **Applications**: Managed by ArgoCD from Git
3. **Updates**: Push to Git triggers automatic deployment
4. **Rollback**: Git-based rollback capabilities

### Application Structure

```
apps/
├── namespaces/              # Namespace definitions
├── minio/                   # Object storage
├── ingress-nginx/           # Ingress controller
├── cert-manager/            # Certificate management
├── kube-prometheus-stack/   # Monitoring stack
├── loki-stack/             # Logging stack
├── tempo/                  # Distributed tracing
├── opentelemetry-collector/ # OpenTelemetry collection
├── opa-gatekeeper/         # Policy enforcement
├── falco/                  # Runtime security
├── velero/                 # Backup/restore
├── vault/                  # Secrets management
├── external-secrets/       # Secrets synchronization
└── ai-observability/       # AI-powered observability
```

## Security

### Multi-Layered Security

1. **Infrastructure Security**:
   - Hardened host OS baseline
   - Network segmentation
   - Firewall rules

2. **Kubernetes Security**:
   - RBAC configuration
   - Network policies
   - Pod security standards
   - Admission controllers

3. **Application Security**:
   - Secrets encryption
   - TLS configuration
   - Runtime monitoring
   - Vulnerability scanning

### Security Components

- **OPA Gatekeeper**: Policy enforcement
- **Falco**: Runtime security monitoring
- **Vault OSS**: Secrets management
- **Network policies**: Traffic control
- **RBAC**: Access control

## Monitoring

### Observability Stack

- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards
- **Loki**: Log aggregation
- **Tempo**: Distributed tracing
- **OpenTelemetry Collector**: Telemetry data collection
- **AlertManager**: Alert management
- **AI Observability**: Groq-powered RCA and anomaly detection

### Monitoring Targets

- Cluster health and performance
- Application metrics
- Infrastructure metrics
- Security events
- Business metrics
- Distributed traces
- AI-powered anomaly detection and root cause analysis

## Backup & Recovery

### Backup Strategy

- **Cluster backup**: Velero cluster backups
- **Namespace backup**: Application-specific backups
- **Persistent volumes**: Data backup
- **Configuration**: Git-based configuration backup

### Recovery Procedures

1. **Cluster recovery**: Complete cluster restore
2. **Application recovery**: Individual application restore
3. **Data recovery**: Persistent volume restore
4. **Configuration recovery**: Git-based configuration restore

## Development Workflow

### Local Development

1. **Make changes** to application configurations
2. **Push to Git** to trigger ArgoCD deployment
3. **Monitor deployment** through ArgoCD UI
4. **Test changes** in the local environment

### CI/CD Integration

- **GitHub Actions**: Infrastructure validation and deployment
- **Trivy (CI)**: Filesystem, secrets, and IaC security scanning on PR/push
- **ArgoCD**: Application deployment and management
- **Automated testing**: Health checks and validation
- **Security scanning**: Code and infrastructure scanning

### Trivy Security Scanning

- CI workflow runs Trivy on every relevant PR/push:
  - `fs` scan for vulnerabilities and secrets
  - `config` scan for Terraform/Kubernetes misconfigurations
- Policy: pipeline fails on `HIGH`/`CRITICAL`.
- Findings are uploaded as SARIF to GitHub Security tab.
- Optional later: deploy Trivy Operator in-cluster (higher runtime resource usage).

## Troubleshooting

### Common Issues

1. **VM startup issues**: Check Multipass status
2. **Cluster bootstrap**: Verify K3s configuration
3. **Service access**: Check MetalLB and networking
4. **Application deployment**: Check ArgoCD status
5. **Host cannot reach 192.168.56.x**: Run `.\scripts\preflight-network.ps1` and reload VMs (`vagrant reload`)
6. **Temporary UI access workaround**: `kubectl -n argocd port-forward svc/argocd-server 8080:80` then open `http://localhost:8080`

### Debug Commands

```bash
# Check VM status
vagrant status

# Check cluster nodes
kubectl get nodes

# Check ArgoCD applications
kubectl get applications -n argocd

# Check service status
kubectl get svc -A

# Check pod logs
kubectl logs -n <namespace> <pod-name>
```

### Health Checks

```bash
# Run comprehensive health check
.\scripts\utils\check-health.ps1

# Get service URLs
.\scripts\utils\get-urls.ps1

# Run final verification
.\scripts\final-verification.ps1
```

## AI Observability

### Overview

The platform includes an AI-powered observability system that automatically:
- Collects metrics from Prometheus, logs from Loki, traces from Tempo
- Performs real-time anomaly detection using statistical methods
- Sends data to Groq AI for root cause analysis
- Generates detailed RCA reports and saves them to persistent storage
- Sends proactive alerts to Slack with incident summaries
- Provides a Slack bot for ad-hoc queries and analysis
- Creates Grafana annotations for incident tracking

### Components

- **Collectors**: Gather metrics, logs, traces, and Kubernetes events
- **Anomaly Detection Engine**: Statistical analysis using Z-score and moving averages
- **Groq Integration**: Uses `llama-3.3-70b-versatile` for intelligent analysis
- **Report Generation**: Markdown and JSON reports stored in PVC
- **Slack Integration**: Proactive alerts and interactive bot
- **Grafana Integration**: Automatic incident annotations

### Access

- **Reports**: Available in `/reports/` directory within the AI observability pod
- **Slack Bot**: Interact via @mentions in configured Slack channel
- **Grafana**: View annotations and incident markers on dashboards

## Resource Optimization

### Disabled Services

For laptop resource optimization, these services are disabled:

- **Backstage**: Saves ~512MB RAM
- **Kubecost**: Saves ~500MB RAM
- **LitmusChaos**: Saves ~300MB RAM

### Optimized Services

- **Vault OSS**: Resource-optimized configuration
- **ArgoCD**: Resource limits and requests
- **Prometheus**: Resource tuning for laptop
- **Grafana**: Memory optimization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test in the local environment
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

1. Check the [troubleshooting guide](docs/troubleshooting.md)
2. Review the [architecture documentation](docs/architecture.md)
3. Check the [security documentation](docs/security.md)
4. Review the [monitoring setup](docs/monitoring.md)

## Version History

- **v1.0.0**: Initial release with complete platform
- **v1.1.0**: Added enhanced monitoring
- **v1.2.0**: Security enhancements
- **v1.3.0**: Resource optimization

---

**Note**: This platform is designed for development and testing. For production use, consider additional security hardening, monitoring, and backup strategies.

## Taint Configuration Details

Control plane nodes are tainted with `node-role.kubernetes.io/control-plane=true:NoSchedule` via Terraform configuration. This ensures:
- Control planes have dedicated resources for Kubernetes operations
- Better resource isolation between control plane and workloads
- Improved performance and stability
- Predictable resource allocation

Applications that need to run on workers must include tolerations:
```yaml
tolerations:
- key: "node-role.kubernetes.io/control-plane"
  operator: "Exists"
  effect: "NoSchedule"
```

## Resource Allocation Summary

- **Control Planes**: 2.5GB RAM, 2 CPUs each (5GB total)
- **Workers**: 3GB RAM, 2 CPUs each (6GB total)
- **Total**: 11GB RAM, 8 CPUs
- **Host RAM available**: 5GB

This configuration provides optimal performance for AI/ML workloads while maintaining system stability.