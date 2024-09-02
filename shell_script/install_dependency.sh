#!/bin/bash 

echo "Installing Python..."

# Update package lists 
sudo apt-get update 

# Install dependencies 
sudo apt-get install -y libssl-dev openssl make gcc 
sudo apt-get install -y build-essential zlib1g-dev libffi-dev libssl-dev 
sudo apt-get install libbz2-dev libncurses5-dev libgdbm-dev libgdbm-compat-dev liblzma-dev libsqlite3-dev tk-dev uuid-dev libreadline-dev

# Change to /opt directory 
cd /opt

# Download Python source 
sudo wget https://www.python.org/ftp/python/3.10.4/Python-3.10.4.tgz 

# Extract the archive 
sudo tar xzvf Python-3.10.4.tgz 

# Change to Python directory 
cd Python-3.10.4 

# Configure the build 
sudo ./configure

# Build Python 
sudo make

# Install Python 
sudo make install 
sudo ln -fs /opt/Python-3.10.4/Python/usr/bin/python3.10 

# Check if Python 3.10 is installed 
if command -v python3.10 &>/dev/null; then 
    echo "#########################################" 
    echo "Python 3.10.4 has been successfully installed." 
    python3 --version 
    echo "Python installation completed." 
    echo "#########################################" 
else
    echo "Python 3.10.4 installation failed." 
    exit 1
fi

# Install MySQL Server 
echo "Installing MySQL Server..." 
sudo apt update 
sudo apt install -y mysql-server 
sudo systemctl start mysql.service 

# Check MySQL version 
if mysql -V &>/dev/null; then 
    echo "#########################################" 
    echo "MySQL has been successfully installed." 
    mysql -V 
    echo "MySQL installation completed." 
    echo "#########################################" 
else 
    echo "MySQL installation failed." 
    exit 1 
fi 


# Install Docker 
echo "Installing Docker..." 
sudo apt update 
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common 
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add - 
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable" 
apt-cache policy docker-ce 

sudo apt install -y docker-ce 
sudo systemctl start docker 
sudo systemctl enable docker 

# Check Docker version 
if docker --version &>/dev/null; then 
    echo "#########################################" 
    echo "Docker has been successfully installed." 
    docker --version 
    echo "Docker installation completed." 
    echo "#########################################" 
else 
    echo "Docker installation failed." 
    exit 1 
fi

# Install Docker Compose 
echo "Installing Docker Compose..." 
sudo apt install -y docker-compose 

# Check Docker Compose version 
if docker-compose --version &>/dev/null; then 
    echo "#########################################" 
    echo "Docker Compose has been successfully installed." 
    docker-compose --version 
    echo "Docker Compose installation completed." 
    echo "#########################################" 
else 
    echo "Docker Compose installation failed." 
    exit 1 
fi 

# Install nvidia driver 
echo "Installing nvidia drivers..." 
echo "Installing build essentials and NVIDIA driver..."
sudo apt-get update 
sudo apt install -y build-essential
sudo apt install -y linux-headers-$(uname -r)
sudo apt install -y nvidia-driver-535

# Reboot is typically required after NVIDIA driver installation
echo "#########################################" 
echo "NVIDIA driver installation completed."
echo "A system reboot is required for the NVIDIA driver to take effect."
echo "After rebooting, you can check the driver status with 'nvidia-smi' command. If command returns
'NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver. Make sure that the latest NVIDIA driver is installed and running' then
check if you have configured GPU properly."
echo "#########################################" 


# Create docker-compose.yaml file
SCRIPT_DIR="/home"
echo "Current working directory: $(pwd)"

cd "$SCRIPT_DIR"
echo "Changed to directory: $(pwd)"
echo "Creating docker-compose.yaml file..."

cat << EOF > docker-compose.yaml
services:
  weaviate:
    image: semitechnologies/weaviate:1.21.1
    restart: on-failure:0
    ports:
     - "8080:8080"
    environment:
      QUERY_DEFAULTS_LIMIT: 2000
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: "./data"
      ENABLE_MODULES: text2vec-transformers
      DEFAULT_VECTORIZER_MODULE: text2vec-transformers
      TRANSFORMERS_INFERENCE_API: http://t2v-transformers:8080
      CLUSTER_HOSTNAME: 'node1'
  t2v-transformers:
    image: semitechnologies/transformers-inference:sentence-transformers-paraphrase-multilingual-MiniLM-L12-v2-latest
    restart: always
    environment:
      ENABLE_CUDA: 0 # set to 1 to enable
EOF

echo "docker-compose.yaml file created."

# Start Docker containers
echo "#########################################" 
echo "Starting Docker containers..."
sudo docker compose up -d
echo "Docker containers started. You can check their status with 'sudo docker ps'."
echo "#########################################" 

# Install node js
echo "Installing Node JS..."

# Navigate to the home directory
cd ~

# Download the NodeSource setup script for Node.js 20.x
curl -sL https://deb.nodesource.com/setup_20.x -o /tmp/nodesource_setup.sh

# Run the setup script
sudo bash /tmp/nodesource_setup.sh

# Install Node.js
sudo apt install -y nodejs

# Check if Node.js was installed successfully
if command -v node &> /dev/null
then
    echo "#########################################" 
    echo "Node.js is installed successfully."
    echo "Node.js version: $(node -v)"
    echo "#########################################" 
else
    echo "Node.js installation failed."
    exit 1
fi

# Check if npm was installed successfully
if command -v npm &> /dev/null
then
    echo "#########################################" 
    echo "npm is installed successfully."
    echo "npm version: $(npm -v)"
    echo "#########################################" 

else
    echo "npm installation failed."
    exit 1
fi
echo "All installations (Python, MySQL, Docker, Docker Compose and Node JS) completed successfully." 
echo "rebooting system"
sudo reboot
