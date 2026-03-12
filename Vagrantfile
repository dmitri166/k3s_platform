# Vagrantfile for K3s Platform - HA Kubernetes Cluster
Vagrant.configure("2") do |config|
  config.vm.boot_timeout = ENV.fetch("VM_BOOT_TIMEOUT", "1200").to_i
  
  cluster_name   = ENV.fetch("CLUSTER_NAME", "k3s-platform")
  vm_box         = ENV.fetch("VM_BOX", "ubuntu/jammy64")
  k3s_version    = ENV.fetch("K3S_VERSION", "v1.34.4+k3s1")
  network_prefix = ENV.fetch("K3S_NET_PREFIX", "192.168.56")
  network_mode   = ENV.fetch("K3S_NETWORK_MODE", "bridged").downcase
  hostonly_adapter = ENV["HOSTONLY_ADAPTER"]
  bridge_adapter = ENV["BRIDGE_ADAPTER"]

  if network_mode == "hostonly"
    if hostonly_adapter.nil? || hostonly_adapter.strip.empty?
      raise <<~MSG
        HOSTONLY_ADAPTER is not set.
        Run deployment via scripts/k3s-deploy.ps1 (recommended), or set HOSTONLY_ADAPTER explicitly.
      MSG
    end

    begin
      hostonlyifs_raw = `VBoxManage list hostonlyifs 2>&1`
    rescue StandardError => e
      raise "Failed to query VirtualBox host-only adapters: #{e.message}"
    end

    adapter_names = hostonlyifs_raw.scan(/^Name:\s+(.+)$/).flatten
    unless adapter_names.include?(hostonly_adapter)
      raise <<~MSG
        HOSTONLY_ADAPTER '#{hostonly_adapter}' was not found in VirtualBox host-only adapters.
        Available adapters: #{adapter_names.empty? ? "(none)" : adapter_names.join(", ")}
        Run scripts/preflight-network.ps1 and use scripts/k3s-deploy.ps1.
      MSG
    end
  elsif network_mode == "bridged"
    if bridge_adapter.nil? || bridge_adapter.strip.empty?
      raise <<~MSG
        BRIDGE_ADAPTER is not set for bridged networking.
        Set BRIDGE_ADAPTER to your host NIC name, for example:
        BRIDGE_ADAPTER="Intel(R) Ethernet Controller" or BRIDGE_ADAPTER="Wi-Fi"
      MSG
    end
  else
    raise "K3S_NETWORK_MODE must be either 'bridged' or 'hostonly'."
  end
  cp_memory      = ENV.fetch("CP_MEMORY_MB", "2560")
  cp_cpus        = ENV.fetch("CP_CPUS", "2")
  worker_memory  = ENV.fetch("WORKER_MEMORY_MB", "3072")
  worker_cpus    = ENV.fetch("WORKER_CPUS", "2")

  cp_ip = ->(i) { "#{network_prefix}.#{100 + i}" }
  worker_ip = ->(i) { "#{network_prefix}.#{102 + i}" }

  config.vm.box = vm_box
  config.vm.synced_folder ".", "/vagrant"
  config.vm.synced_folder "./scripts", "/vagrant/scripts", type: "virtualbox"

  # Prefer ephemeral keys over static insecure credentials.
  config.ssh.insert_key = true
  config.ssh.verify_host_key = false

  # Common provisioning script
  common_provision = <<-SHELL
    set -euo pipefail
    export DEBIAN_FRONTEND=noninteractive

    apt-get update
    apt-get install -y curl wget gnupg software-properties-common ca-certificates netcat-openbsd docker.io

    # Start Docker
    systemctl start docker
    systemctl enable docker

    # Disable swap (Kubernetes requirement)
    swapoff -a
    sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

    # Enable kernel modules
    cat <<EOF >/etc/modules-load.d/k8s.conf
br_netfilter
overlay
EOF

    modprobe br_netfilter
    modprobe overlay

    # Set sysctl params required for Kubernetes networking.
    cat <<EOF >/etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

    sysctl --system >/dev/null
  SHELL

  # Control Plane Nodes (2-node HA)
  (1..2).each do |i|
    config.vm.define "cp#{i}" do |cp|
      cp.vm.hostname = "cp#{i}"
      if network_mode == "bridged"
        cp.vm.network "public_network", ip: cp_ip.call(i), bridge: bridge_adapter
      else
        cp.vm.network "private_network", ip: cp_ip.call(i), virtualbox__hostonly: hostonly_adapter
      end
      if i == 1
        # Stable host access path for local tooling (kubectl/Terraform).
        cp.vm.network "forwarded_port", guest: 6443, host: 64430, host_ip: "127.0.0.1", auto_correct: true
      end
      cp.vm.provider "virtualbox" do |vb|
        vb.name = "#{cluster_name}-cp#{i}"
        vb.memory = cp_memory
        vb.cpus = cp_cpus
        vb.gui = false
        # Required for MetalLB L2 VIP announcements on host-only networks.
        vb.customize ["modifyvm", :id, "--nicpromisc2", "allow-all"]
      end

      cp.vm.provision "shell", inline: common_provision

      cp.vm.provision "shell", inline: <<-SHELL
        set -euo pipefail
        export INSTALL_K3S_VERSION="#{k3s_version}"
        NODE_IP="#{cp_ip.call(i)}"
        K3S_IFACE=$(ip -o -4 addr show | grep -F "#{network_prefix}." | awk '{print $2; exit}')
        [ -n "$K3S_IFACE" ] || { echo "failed to detect private interface for #{network_prefix}.0/24"; ip -o -4 addr show; exit 1; }

        if [ #{i} -eq 1 ]; then
          rm -f /vagrant/scripts/k3s-token.txt

          curl -sfL https://get.k3s.io | sh -s - server \
            --cluster-init \
            --tls-san #{cp_ip.call(1)} \
            --tls-san #{cp_ip.call(2)} \
            --tls-san 127.0.0.1 \
            --tls-san localhost \
            --node-ip "$NODE_IP" \
            --advertise-address "$NODE_IP" \
            --flannel-iface "$K3S_IFACE" \
            --write-kubeconfig-mode 644 \
            --disable servicelb \
            --disable traefik \
            --node-taint node-role.kubernetes.io/control-plane=true:NoSchedule

          # Share token for joining members.
          cat /var/lib/rancher/k3s/server/node-token >/vagrant/scripts/k3s-token.txt
        else
          # Wait until bootstrap token appears.
          for n in $(seq 1 90); do
            if [ -s /vagrant/scripts/k3s-token.txt ]; then
              break
            fi
            sleep 2
          done
          [ -s /vagrant/scripts/k3s-token.txt ] || { echo "k3s token not found"; exit 1; }

          # Wait until cp1 API port is reachable.
          for n in $(seq 1 90); do
            if nc -z #{cp_ip.call(1)} 6443; then
              break
            fi
            sleep 2
          done

          K3S_TOKEN=$(cat /vagrant/scripts/k3s-token.txt)
          curl -sfL https://get.k3s.io | sh -s - server \
            --server https://#{cp_ip.call(1)}:6443 \
            --token "$K3S_TOKEN" \
            --tls-san #{cp_ip.call(i)} \
            --tls-san 127.0.0.1 \
            --tls-san localhost \
            --node-ip "$NODE_IP" \
            --advertise-address "$NODE_IP" \
            --flannel-iface "$K3S_IFACE" \
            --disable servicelb \
            --disable traefik \
            --node-taint node-role.kubernetes.io/control-plane=true:NoSchedule
        fi
      SHELL
    end
  end

  # Worker Nodes (2 nodes)
  (1..2).each do |i|
    config.vm.define "worker#{i}" do |worker|
      worker.vm.hostname = "worker#{i}"
      if network_mode == "bridged"
        worker.vm.network "public_network", ip: worker_ip.call(i), bridge: bridge_adapter
      else
        worker.vm.network "private_network", ip: worker_ip.call(i), virtualbox__hostonly: hostonly_adapter
      end
      worker.vm.provider "virtualbox" do |vb|
        vb.name = "#{cluster_name}-worker#{i}"
        vb.memory = worker_memory
        vb.cpus = worker_cpus
        vb.gui = false
        # Required for MetalLB L2 VIP announcements on host-only networks.
        vb.customize ["modifyvm", :id, "--nicpromisc2", "allow-all"]
      end

      worker.vm.provision "shell", inline: common_provision

      worker.vm.provision "shell", inline: <<-SHELL
        set -euo pipefail
        export INSTALL_K3S_VERSION="#{k3s_version}"
        NODE_IP="#{worker_ip.call(i)}"
        K3S_IFACE=$(ip -o -4 addr show | grep -F "#{network_prefix}." | awk '{print $2; exit}')
        [ -n "$K3S_IFACE" ] || { echo "failed to detect private interface for #{network_prefix}.0/24"; ip -o -4 addr show; exit 1; }

        # Wait for shared bootstrap token and cp1 API availability.
        for n in $(seq 1 90); do
          if [ -s /vagrant/scripts/k3s-token.txt ] && nc -z #{cp_ip.call(1)} 6443; then
            break
          fi
          sleep 2
        done
        [ -s /vagrant/scripts/k3s-token.txt ] || { echo "k3s token not found"; exit 1; }

        K3S_TOKEN=$(cat /vagrant/scripts/k3s-token.txt)
        curl -sfL https://get.k3s.io | sh -s - agent \
          --server https://#{cp_ip.call(1)}:6443 \
          --node-ip "$NODE_IP" \
          --flannel-iface "$K3S_IFACE" \
          --token "$K3S_TOKEN"
      SHELL
    end
  end
end
