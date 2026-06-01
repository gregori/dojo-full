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

# Install containerd
dnf install -y dnf-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
dnf install -y containerd.io

# Configure containerd
mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml
sed -i 's/SystemdCgroup = .*/SystemdCgroup = true/' /etc/containerd/config.toml
systemctl enable --now containerd

# Add Kubernetes repo
cat >> /etc/yum.repos.d/kubernetes.repo <<EOF
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.34:/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.34:/rpm/repodata/repomd.xml.key
exclude=kubelet kubeadm kubectl cri-tools
EOF

# Install kubeadm, kubelet, kubectl
dnf install -y kubelet kubeadm kubectl --disableexcludes=kubernetes
systemctl enable kubelet

# Pull kubeadm images
kubeadm config images pull

touch /home/opc/.k8s_provisioned
