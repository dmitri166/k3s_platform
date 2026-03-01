# Troubleshooting Guide

This guide provides solutions to common issues that may occur when working with the Talos on-premises platform.

## Quick Reference

### Common Issues and Solutions

| Issue | Solution | Command |
|-------|----------|---------|
| VMs not starting | Check Multipass status | `multipass list` |
| Cluster not accessible | Check kubeconfig | `kubectl get nodes` |
| Services not accessible | Check MetalLB | `kubectl get svc -n metallb-system` |
| ArgoCD not syncing | Check ArgoCD status | `argocd app list` |
| Applications not deploying | Check ArgoCD apps | `kubectl get applications -n argocd` |

## Infrastructure Issues

### Multipass VM Issues

#### VMs Not Starting
```bash
# Check Multipass status
multipass list

# Check Multipass daemon
multipass status

# Restart Multipass daemon
multipass stop --all
multipass start --all

# Delete and recreate VMs
multipass delete vm-name --purge
multipass launch --name vm-name --cpus 2 --memory 2G --disk 20G
```

#### VM Network Issues
```bash
# Check VM network configuration
multipass info vm-name

# Check bridged network
multipass exec vm-name -- ip addr show

# Restart network in VM
multipass exec vm-name -- sudo systemctl restart networking
```

### Terraform Issues

#### Terraform State Issues
```bash
# Check Terraform state
terraform state list

# Refresh state
terraform refresh

# Fix corrupted state
terraform force-unlock LOCK_ID

# Reset state (last resort)
terraform state rm RESOURCE_NAME
```

#### Resource Creation Failures
```bash
# Check Terraform plan
terraform plan

# Apply with detailed output
terraform apply -detailed-exitcode

# Debug specific resource
terraform apply -target=RESOURCE_TYPE.RESOURCE_NAME
```

## Cluster Issues

### Kubernetes Cluster Issues

#### Cluster Not Accessible
```bash
# Check kubeconfig
kubectl config view

# Test cluster connectivity
kubectl cluster-info

# Check nodes
kubectl get nodes -o wide

# Check system pods
kubectl get pods -n kube-system
```

#### Nodes Not Ready
```bash
# Check node status
kubectl describe node NODE_NAME

# Check kubelet logs
multipass exec vm-name -- sudo journalctl -u kubelet

# Check Talos status
talosctl health -n NODE_IP

# Restart kubelet
multipass exec vm-name -- sudo systemctl restart kubelet
```

#### Pod Issues
```bash
# Check pod status
kubectl get pods -A

# Describe pod
kubectl describe pod POD_NAME -n NAMESPACE

# Check pod logs
kubectl logs POD_NAME -n NAMESPACE

# Get events
kubectl get events -n NAMESPACE --sort-by=.metadata.creationTimestamp
```

## Service Issues

### MetalLB Issues

#### LoadBalancer Not Working
```bash
# Check MetalLB pods
kubectl get pods -n metallb-system

# Check MetalLB config
kubectl get configmap config -n metallb-system -o yaml

# Check MetalLB logs
kubectl logs -n metallb-system -l app.kubernetes.io/name=metallb

# Check IP allocation
kubectl get svc -A | grep LoadBalancer
```

#### IP Address Conflicts
```bash
# Check IP pool configuration
kubectl get configmap config -n metallb-system -o yaml

# Update IP pool
kubectl edit configmap config -n metallb-system

# Restart MetalLB
kubectl rollout restart deployment/metallb-controller -n metallb-system
```

### Ingress Issues

#### Ingress Not Working
```bash
# Check Ingress controller
kubectl get pods -n ingress-nginx

# Check Ingress service
kubectl get svc -n ingress-nginx

# Check Ingress configuration
kubectl get ingress -A

# Test Ingress
curl -H "Host: example.com" http://INGRESS_IP
```

#### Certificate Issues
```bash
# Check cert-manager
kubectl get pods -n cert-manager

# Check certificate status
kubectl get certificates -A

# Check certificate requests
kubectl get certificaterequests -A

# Describe certificate
kubectl describe certificate CERT_NAME -n NAMESPACE
```

## Application Issues

### ArgoCD Issues

#### ArgoCD Not Syncing
```bash
# Check ArgoCD server
kubectl get pods -n argocd

# Check ArgoCD applications
argocd app list

# Sync specific application
argocd app sync APP_NAME

# Force sync
argocd app sync APP_NAME --force

# Check application details
argocd app get APP_NAME
```

#### ArgoCD Login Issues
```bash
# Get ArgoCD password
kubectl get secret argocd-admin-password -n argocd -o jsonpath='{.data.password}' | base64 -d

# Get ArgoCD server IP
kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Login to ArgoCD
argocd login SERVER_IP --insecure --username admin --password PASSWORD
```

#### Application Deployment Failures
```bash
# Check application status
kubectl get applications -n argocd

# Check application events
kubectl describe application APP_NAME -n argocd

# Check application logs
kubectl logs -n argocd deployment/argocd-application-controller

# Sync with debug
argocd app sync APP_NAME --debug
```

### Monitoring Issues

#### Prometheus Issues
```bash
# Check Prometheus pods
kubectl get pods -n monitoring -l app.kubernetes.io/name=prometheus

# Check Prometheus configuration
kubectl get configmap prometheus-config -n monitoring -o yaml

# Check Prometheus targets
kubectl port-forward svc/prometheus-server 9090 -n monitoring
# Access http://localhost:9090/targets
```

#### Grafana Issues
```bash
# Check Grafana pods
kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana

# Check Grafana configuration
kubectl get configmap grafana-config -n monitoring -o yaml

# Access Grafana
kubectl port-forward svc/grafana 3000 -n monitoring
# Access http://localhost:3000
```

#### Loki Issues
```bash
# Check Loki pods
kubectl get pods -n monitoring -l app.kubernetes.io/name=loki

# Check Loki configuration
kubectl get configmap loki-config -n monitoring -o yaml

# Check Promtail logs
kubectl logs -n monitoring -l app.kubernetes.io/name=promtail
```

## Security Issues

### Vault Issues
```bash
# Check Vault pods
kubectl get pods -n vault

# Check Vault status
kubectl exec -n vault deployment/vault -- vault status

# Unseal Vault
kubectl exec -n vault deployment/vault -- vault operator unseal

# Check Vault logs
kubectl logs -n vault deployment/vault
```

### OPA Gatekeeper Issues
```bash
# Check Gatekeeper pods
kubectl get pods -n gatekeeper-system

# Check Gatekeeper constraints
kubectl get constraints -A

# Check Gatekeeper config
kubectl get configmap config -n gatekeeper-system -o yaml

# Test policy enforcement
kubectl run test-pod --image=nginx --dry-run=client -o yaml | kubectl apply -f -
```

### Falco Issues
```bash
# Check Falco pods
kubectl get pods -n falco

# Check Falco events
kubectl logs -n falco deployment/falco

# Test Falco rules
kubectl run test-pod --image=nginx --rm -it -- /bin/bash
```

## Backup Issues

### Velero Issues
```bash
# Check Velero pods
kubectl get pods -n velero

# Check Velero backups
velero get backups

# Check Velero schedule
velero get schedule

# Test backup
velero backup test-backup --wait

# Test restore
velero restore test-restore --from-backup test-backup --wait
```

## Performance Issues

### Resource Issues
```bash
# Check resource usage
kubectl top nodes
kubectl top pods -A

# Check resource quotas
kubectl get resourcequota -A

# Check limit ranges
kubectl get limitrange -A

# Describe resource issues
kubectl describe node NODE_NAME
```

### Network Issues
```bash
# Check network policies
kubectl get networkpolicy -A

# Test pod connectivity
kubectl exec POD_NAME -- ping TARGET_POD

# Check DNS resolution
kubectl exec POD_NAME -- nslookup kubernetes.default.svc.cluster.local

# Check service connectivity
kubectl exec POD_NAME -- curl SERVICE_NAME.NAMESPACE.svc.cluster.local
```

## Debugging Tools

### Health Check Script
```bash
# Run comprehensive health check
./scripts/utils/check-health.ps1

# Run with verbose output
./scripts/utils/check-health.ps1 -Verbose

# Wait for recovery
./scripts/utils/check-health.ps1 -Wait
```

### Service URLs Script
```bash
# Get all service URLs
./scripts/utils/get-urls.ps1

# Test service accessibility
./scripts/utils/get-urls.ps1 -Test

# Verbose output
./scripts/utils/get-urls.ps1 -Verbose
```

### Cluster Diagnostics
```bash
# Full cluster status
kubectl get all -A

# Cluster events
kubectl get events -A --sort-by=.metadata.creationTimestamp

# Resource usage
kubectl describe nodes
kubectl top nodes
kubectl top pods -A
```

## Common Error Messages

### Terraform Errors

#### "Error: resource already exists"
```bash
# Import existing resource
terraform import RESOURCE_TYPE.RESOURCE_NAME RESOURCE_ID

# Remove from state
terraform state rm RESOURCE_TYPE.RESOURCE_NAME

# Force recreate
terraform taint RESOURCE_TYPE.RESOURCE_NAME
terraform apply
```

#### "Error: timeout while waiting for state to lock"
```bash
# Force unlock
terraform force-unlock LOCK_ID

# Check for other processes
ps aux | grep terraform

# Kill terraform processes
pkill -f terraform
```

### Kubernetes Errors

#### "Error: connection refused"
```bash
# Check kubeconfig
kubectl config view

# Test connectivity
kubectl cluster-info

# Check API server
kubectl get endpoints kubernetes
```

#### "Error: pod has unbound immediate PersistentVolumeClaims"
```bash
# Check PVC status
kubectl get pvc -A

# Check storage classes
kubectl get storageclass

# Describe PVC
kubectl describe pvc PVC_NAME -n NAMESPACE
```

## Recovery Procedures

### Complete Cluster Recovery
```bash
# 1. Destroy cluster
./scripts/destroy-cluster.ps1

# 2. Clean up remaining resources
multipass delete --all --purge

# 3. Recreate cluster
./scripts/create-cluster.ps1
```

### Application Recovery
```bash
# 1. Sync ArgoCD applications
argocd app sync --all

# 2. Wait for applications to be healthy
./scripts/utils/check-health.ps1 -Wait

# 3. Verify service access
./scripts/utils/get-urls.ps1 -Test
```

### Data Recovery
```bash
# 1. Restore from backup
velero restore from-backup BACKUP_NAME --wait

# 2. Verify restore
velero get restores

# 3. Check application status
kubectl get pods -A
```

## Getting Help

### Logs and Debugging
```bash
# Enable verbose logging
export TALOSCTL_DEBUG=true

# Check system logs
journalctl -u multipassd

# Check Terraform logs
terraform plan -detailed-exitcode

# Check Kubernetes events
kubectl get events -A --sort-by=.metadata.creationTimestamp
```

### Community Resources
- [Talos Documentation](https://www.talos.dev/docs/v1.7/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [ArgoCD Documentation](https://argoproj.github.io/argo-cd/)
- [Terraform Documentation](https://www.terraform.io/docs/)

### Support Channels
- GitHub Issues: Report bugs and feature requests
- Community Forums: Get help from other users
- Documentation: Check existing documentation
- Troubleshooting: Use this guide for common issues

## Prevention Tips

### Regular Maintenance
- Run health checks regularly
- Monitor resource usage
- Keep backups updated
- Review logs for issues
- Update configurations as needed

### Best Practices
- Use version control for all changes
- Test changes in development first
- Monitor system performance
- Document custom configurations
- Plan for disaster recovery

### Monitoring Setup
- Set up alerting for critical services
- Monitor resource usage
- Track application performance
- Log important events
- Review metrics regularly
