# Talos On-Premises Platform

A production-ready on-premises Kubernetes platform built with Talos OS, optimized for laptop development while maintaining enterprise-grade features.

## Overview

This project provides a complete Kubernetes platform that mirrors cloud-native EKS functionality but runs entirely on-premises using Talos OS. It's designed for development, testing, and learning while following production best practices.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Host Machine (16GB RAM)                   │
├─────────────────────────────────────────────────────────────┤
│  Multipass VMs (10GB RAM, 10 CPU cores total)               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│  │   cp1   │ │   cp2   │ │   cp3   │ │worker1  │ │worker2  │ │
│  │ 2GB RAM │ │ 2GB RAM │ │ 2GB RAM │ │ 2GB RAM │ │ 2GB RAM │ │
│  │ 2 CPU   │ │ 2 CPU   │ │ 2 CPU   │ │ 2 CPU   │ │ 2 CPU   │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Features

### Infrastructure
- **Talos OS**: Minimalist, secure, immutable Kubernetes operating system
- **Multipass**: Lightweight VM management for local development
- **Terraform**: Infrastructure as Code for reproducible deployments
- **MetalLB**: LoadBalancer implementation for on-premises environments
- **High Availability**: 3-node control plane with 2 worker nodes

### Platform Services
- **ArgoCD**: GitOps continuous delivery
- **NGINX Ingress**: Traffic routing and load balancing
- **Cert-Manager**: Automated certificate management
- **Vault OSS**: Production-grade secrets management
- **External Secrets**: Kubernetes secrets synchronization

### Monitoring & Observability
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Loki**: Log aggregation and querying
- **Alert management**: Proactive monitoring

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

- **Multipass**: VM management
- **Terraform**: Infrastructure as Code
- **Helm**: Kubernetes package manager
- **Talosctl**: Talos cluster management
- **kubectl**: Kubernetes CLI
- **Python 3.12+**: Scripting support
- **PowerShell**: Windows automation

### Installation

1. **Clone the repository**:
   ```bash
   cd D:\talos_platform
   git init
   git add .
   git commit -m "Initial commit: Talos platform infrastructure"
   ```

2. **Initialize Terraform**:
   ```bash
   terraform init
   ```

3. **Deploy the platform**:
   ```bash
   terraform apply -auto-approve
   ```

### Access Services

After deployment, access the services at:

- **ArgoCD**: http://192.168.1.240
- **Applications**: http://192.168.1.241
- **Grafana**: http://192.168.1.242
- **Prometheus**: http://192.168.1.243
- **Vault**: http://192.168.1.244

### Get Credentials

```bash
# Get ArgoCD admin password
terraform output -raw argocd_admin_password

# Get cluster kubeconfig
talosctl kubeconfig > ~/.kube/config-talos
export KUBECONFIG=~/.kube/config-talos
```

## Architecture Details

### Network Configuration

```
Network: 192.168.1.0/24
├── Host: 192.168.1.100
├── Multipass VMs: 192.168.1.101-192.168.1.105
└── MetalLB Pool: 192.168.1.240-192.168.1.250
    ├── ArgoCD: 192.168.1.240
    ├── Ingress: 192.168.1.241
    ├── Grafana: 192.168.1.242
    ├── Prometheus: 192.168.1.243
    └── Vault: 192.168.1.244
```

### Resource Allocation

| Component | RAM | CPU | Purpose |
|-----------|-----|-----|---------|
| cp1 | 2GB | 2 | Control plane + Vault |
| cp2 | 2GB | 2 | Control plane |
| cp3 | 2GB | 2 | Control plane |
| worker1 | 2GB | 2 | Applications |
| worker2 | 2GB | 2 | Applications |
| Host | 6GB | 2 | System reserve |

## GitOps Workflow

This platform uses ArgoCD for GitOps deployment:

1. **Infrastructure**: Managed by Terraform
2. **Applications**: Managed by ArgoCD from Git
3. **Updates**: Push to Git triggers automatic deployment
4. **Rollback**: Git-based rollback capabilities

### Application Structure

```
apps/
├── ingress-nginx/          # Ingress controller
├── cert-manager/           # Certificate management
├── kube-prometheus-stack/  # Monitoring stack
├── loki-stack/            # Logging stack
├── opa-gatekeeper/        # Policy enforcement
├── falco/                 # Runtime security
├── velero/                # Backup/restore
├── vault/                 # Secrets management
└── external-secrets/      # Secrets synchronization
```

## Security

### Multi-Layered Security

1. **Infrastructure Security**:
   - Talos OS immutable system
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
- **AlertManager**: Alert management

### Monitoring Targets

- Cluster health and performance
- Application metrics
- Infrastructure metrics
- Security events
- Business metrics

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
- **ArgoCD**: Application deployment and management
- **Automated testing**: Health checks and validation
- **Security scanning**: Code and infrastructure scanning

## Troubleshooting

### Common Issues

1. **VM startup issues**: Check Multipass status
2. **Cluster bootstrap**: Verify Talos configuration
3. **Service access**: Check MetalLB and networking
4. **Application deployment**: Check ArgoCD status

### Debug Commands

```bash
# Check VM status
multipass list

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
```

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
