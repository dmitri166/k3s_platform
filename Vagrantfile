# Vagrantfile for K3s Platform - HA Kubernetes Cluster
Vagrant.configure("2") do |config|
  
  config.vm.box = "ubuntu/jammy64"
  config.vm.synced_folder ".", "/vagrant", disabled: true
  config.vm.synced_folder "./scripts", "/vagrant/scripts", type: "virtualbox"
  
  config.ssh.insert_key = false
  config.ssh.verify_host_key = false
  
  # Common provisioning script
  $common_provision = <<-SHELL
    # Update system
    apt-get update && apt-get upgrade -y
    
    # Install required packages
    apt-get install -y curl wget gnupg software-properties-common
    
    # Disable swap (Kubernetes requirement)
    swapoff -a
    sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
    
    # Enable kernel modules
    cat <<EOF | tee /etc/modules-load.d/k8s.conf
br_netfilter
overlay
EOF
    
    modprobe br_netfilter
    modprobe overlay
    
    # Set sysctl params
    cat <<EOF | tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
    
    sysctl --system
    
    # Create k3s user
    useradd -m -s /bin/bash k3s
    echo 'k3s:k3s123' | chpasswd
    usermod -aG sudo k3s
    
    # Configure SSH for k3s user
    mkdir -p /home/k3s/.ssh
    chmod 700 /home/k3s/.ssh
    chown k3s:k3s /home/k3s/.ssh
    
    echo "PasswordAuthentication yes" > /etc/ssh/sshd_config.d/99-password.conf
    echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config.d/99-password.conf
    systemctl restart ssh
  SHELL
  
  # Control Plane Nodes (3-node HA)
  (1..3).each do |i|
    config.vm.define "cp#{i}" do |cp|
      cp.vm.hostname = "cp#{i}"
      cp.vm.network "private_network", ip: "192.168.56.#{100 + i}"
      cp.vm.provider "virtualbox" do |vb|
        vb.name = "k3s-platform-cp#{i}"
        vb.memory = "2048"
        vb.cpus = "2"
        vb.gui = false
      end
      
      # Provision control plane
      cp.vm.provision "shell", inline: $common_provision
      
      cp.vm.provision "shell", inline: <<-SHELL
        # Install K3s server
        if [ #{i} -eq 1 ]; then
          # First control plane node (initialize cluster)
          curl -sfL https://get.k3s.io | sh -s - server \
            --cluster-init \
            --tls-san 192.168.56.101 \
            --tls-san 192.168.56.102 \
            --tls-san 192.168.56.103 \
            --write-kubeconfig-mode 644
            
          # Get cluster token for other nodes
          cat /var/lib/rancher/k3s/server/node-token > /vagrant/scripts/k3s-token.txt
          
          echo "=== K3s Control Plane #{i} Ready ==="
          echo "IP: 192.168.56.#{100 + i}"
          echo "Role: Control Plane (Cluster Init)"
          echo "=============================="
        else
          # Additional control plane nodes
          sleep 30  # Wait for first node to be ready
          
          # Get token from shared file
          K3S_TOKEN=$(cat /vagrant/scripts/k3s-token.txt)
          
          curl -sfL https://get.k3s.io | sh -s - server \
            --server https://192.168.56.101:6443 \
            --token $K3S_TOKEN \
            --tls-san 192.168.56.#{100 + i}
          
          echo "=== K3s Control Plane #{i} Ready ==="
          echo "IP: 192.168.56.#{100 + i}"
          echo "Role: Control Plane (Joined)"
          echo "=============================="
        fi
      SHELL
    end
  end
  
  # Worker Nodes (2 nodes)
  (1..2).each do |i|
    config.vm.define "worker#{i}" do |worker|
      worker.vm.hostname = "worker#{i}"
      worker.vm.network "private_network", ip: "192.168.56.#{103 + i}"
      worker.vm.provider "virtualbox" do |vb|
        vb.name = "k3s-platform-worker#{i}"
        vb.memory = "1536"
        vb.cpus = "1"
        vb.gui = false
      end
      
      # Provision worker
      worker.vm.provision "shell", inline: $common_provision
      
      worker.vm.provision "shell", inline: <<-SHELL
        # Wait for control plane to be ready
        sleep 60
        
        # Get token from shared file
        K3S_TOKEN=$(cat /vagrant/scripts/k3s-token.txt)
        
        # Install K3s agent
        curl -sfL https://get.k3s.io | sh -s - agent \
          --server https://192.168.56.101:6443 \
          --token $K3S_TOKEN
        
        echo "=== K3s Worker #{i} Ready ==="
        echo "IP: 192.168.56.#{103 + i}"
        echo "Role: Worker Node"
        echo "=========================="
      SHELL
    end
  end
  
end
