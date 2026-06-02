#!/bin/bash
set -euo pipefail

# Disable firewalld for Kubernetes
systemctl disable --now firewalld || true

# Configure sysctl for Kubernetes
cat >> /etc/sysctl.d/k8s.conf <<EOF
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1
EOF
sysctl --system

# Disable swap
swapoff -a
sed -i '/ swap /d' /etc/fstab || true

# Get public IP from OCI metadata
PUBLIC_IP=$(curl -s -H 'Authorization: Bearer Oracle' http://169.254.169.254/opc/v1/instance/ | grep -o '"publicIp":"[^"]*"' | cut -d'"' -f4 || echo "")
if [ -z "$PUBLIC_IP" ]; then
  PUBLIC_IP=""
fi

# Remove broken Kubernetes repo (pkgs.k8s.io returns 403 for ARM)
rm -f /etc/yum.repos.d/kubernetes.repo || true

# Install k3s (lightweight Kubernetes, bundles containerd + CNI + kubelet)
# Using v1.29.x (last version that fully supports cgroup v1 on Oracle Linux 8)
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_VERSION="v1.29.14+k3s1" \
  K3S_KUBECONFIG_MODE="644" \
  INSTALL_K3S_SKIP_SELINUX_RPM=true \
  sh -s - \
    --flannel-backend=host-gw \
    --write-kubeconfig-mode=644 \
    ${PUBLIC_IP:+--tls-san=$PUBLIC_IP}

touch /home/opc/.k8s_provisioned
