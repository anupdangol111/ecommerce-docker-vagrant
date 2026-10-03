# -*- mode: ruby -*-
# E-commerce app: Nginx -> Flask API -> PostgreSQL + Redis
# VirtualBox VM provisioned by Vagrant; services run in Docker via Docker Compose.
Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"
  config.vm.hostname = "ecommerce"
  config.vm.boot_timeout = 600

  # Shop published on guest :8080 -> host :8081
  config.vm.network "forwarded_port", guest: 8080, host: 8081, host_ip: "127.0.0.1"
  config.vm.network "private_network", ip: "192.168.56.11"

  config.vm.synced_folder ".", "/vagrant"

  config.vm.provider "virtualbox" do |vb|
    vb.name = "ecommerce-docker"
    vb.memory = 2048
    vb.cpus = 2
    vb.gui = true
    vb.customize ["modifyvm", :id, "--uartmode1", "disconnected"]
  end

  config.vm.provision "shell", path: "scripts/provision.sh"

  config.vm.provision "shell", run: "always", inline: <<-SHELL
    cd /vagrant
    [ -f .env ] || cp .env.example .env
    docker compose up -d --build
  SHELL
end
