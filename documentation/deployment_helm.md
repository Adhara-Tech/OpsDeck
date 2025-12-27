# Helm Deployment Guide

This guide details how to deploy OpsDeck using Helm on a Kubernetes cluster.

## Prerequisites

- Kubernetes cluster (v1.19+)
- Helm 3.0+
- `kubectl` configured to talk to your cluster

## Chart Structure

You can find the helm chart in the "helm" folder. It has the following structure:

```
helm/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    └── pvc.yaml
```

## Installation Steps

### 1. Create a Namespace

```bash
kubectl create namespace opsdeck
```

### 2. Configure Secrets

Create a secret for sensitive environment variables, including the admin credentials:

```bash
kubectl create secret generic opsdeck-secrets \
  --from-literal=secret-key='your-super-secret-key-here' \
  --from-literal=admin-email='admin@yourcompany.com' \
  --from-literal=admin-password='YourSecurePassword123!' \
  -n opsdeck
```

> **Security Best Practice:** Always use strong, randomly generated passwords for production deployments. Consider using a secret management tool like HashiCorp Vault, AWS Secrets Manager, or Azure Key Vault for managing sensitive credentials.

### 3. Configure Persistent Storage (Optional)

OpsDeck supports persistent storage for three types of data:

1. **SQLite Database** (if using SQLite instead of PostgreSQL)
2. **Logs** (`/app/logs` folder)
3. **Attachments** (`/app/data/attachments` folder)

By default, all persistence is enabled in `values.yaml`. You can customize the storage sizes and classes:

```yaml
# values.yaml
database:
  type: sqlite
  sqlite:
    persistence:
      enabled: true
      size: 1Gi
      storageClass: ""  # Use default storage class

persistence:
  logs:
    enabled: true
    size: 500Mi
    storageClass: ""
    existingClaim: ""  # Optional: use an existing PVC
  
  attachments:
    enabled: true
    size: 5Gi
    storageClass: ""
    existingClaim: ""  # Optional: use an existing PVC
```

To disable persistence for any component, set `enabled: false` in the corresponding section.

### 4. Install the Chart

Navigate to the directory containing your chart and run:

```bash
helm upgrade --install opsdeck ./helm \
  --namespace opsdeck \
  --set image.tag=latest
```

## Deploying with ArgoCD

ArgoCD follows a GitOps pattern where the state of the cluster is defined in Git.

### Prerequisites

- ArgoCD installed in your cluster.
- A Git repository containing your Helm chart (or a reference to it).

### ArgoCD Application Manifest

Create a file named `application.yaml`. This manifest tells ArgoCD to sync the Helm chart from your repository to the Kubernetes cluster.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: opsdeck
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: 'https://github.com/pixelotes/OpsDeck.git'
    targetRevision: HEAD
    path: helm/
    helm:
      valueFiles:
        - values.yaml
      # You can also set values inline
      # parameters:
      #   - name: image.tag
      #     value: master
  destination:
    server: 'https://kubernetes.default.svc'
    namespace: opsdeck
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

### Apply the Manifest

Apply the manifest to your cluster to create the ArgoCD Application:

```bash
kubectl apply -f application.yaml
```

ArgoCD will now monitor the repository and automatically synchronize changes to the `opsdeck` namespace.
