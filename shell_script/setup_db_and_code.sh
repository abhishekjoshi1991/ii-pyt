#!/bin/bash 

# clone the backend codebase from Git
echo "#########################################" 
echo "Cloning Python codebase from Git"
SCRIPT_DIR="/home/imai"
echo "Current working directory: $(pwd)"
echo "#########################################" 

# Check if the directory exists
if [ ! -d "$SCRIPT_DIR" ]; then
    echo "Directory $SCRIPT_DIR does not exist. Creating it..."
    mkdir -p "$SCRIPT_DIR"  # Create the directory if it does not exist
else
    echo "Directory $SCRIPT_DIR already exists. Deleting it..."
    rm -rf "$SCRIPT_DIR"  # Delete the directory and its contents
    echo "Creating directory $SCRIPT_DIR..."
    mkdir -p "$SCRIPT_DIR"  # Create the directory if it does not exist
fi  

cd "$SCRIPT_DIR"
echo "Changed to directory: $(pwd)"
echo "Please enter git repo link to clone backend (Python) codebase:..."
read repolink

getrepo() {
    echo "Getting Repo, Please wait!"
    git clone $repolink .
}

getrepo


# clone the imai webapp frontend codebase from Git
echo "#########################################" 
echo "Cloning imai webapp frontend codebase from Git"
SCRIPT_DIR2="/home/imai_webapp_frontend"
echo "Current working directory: $(pwd)"
echo "#########################################" 

# Check if the directory exists
if [ ! -d "$SCRIPT_DIR2" ]; then
    echo "Directory $SCRIPT_DIR2 does not exist. Creating it..."
    mkdir -p "$SCRIPT_DIR2"  # Create the directory if it does not exist
else
    echo "Directory $SCRIPT_DIR2 already exists. Deleting it..."
    rm -rf "$SCRIPT_DIR2"  # Delete the directory and its contents
    echo "Creating directory $SCRIPT_DIR2..."
    mkdir -p "$SCRIPT_DIR2"  # Create the directory if it does not exist
fi  

cd "$SCRIPT_DIR2"
echo "Changed to directory: $(pwd)"
echo "Please enter git repo link to clone frontend codebase:..."
read repolinkfrontend

getrepofrontend() {
    echo "Getting Repo, Please wait!"
    git clone $repolinkfrontend .
}

getrepofrontend


# clone the imai webapp backend codebase from Git
echo "#########################################" 
echo "Cloning imai webapp backend codebase from Git"
SCRIPT_DIR3="/home/imai_webapp_backend"
echo "Current working directory: $(pwd)"
echo "#########################################" 

# Check if the directory exists
if [ ! -d "$SCRIPT_DIR3" ]; then
    echo "Directory $SCRIPT_DIR3 does not exist. Creating it..."
    mkdir -p "$SCRIPT_DIR3"  # Create the directory if it does not exist
else
    echo "Directory $SCRIPT_DIR3 already exists. Deleting it..."
    rm -rf "$SCRIPT_DIR3"  # Delete the directory and its contents
    echo "Creating directory $SCRIPT_DIR3..."
    mkdir -p "$SCRIPT_DIR3"  # Create the directory if it does not exist
fi  

cd "$SCRIPT_DIR3"
echo "Changed to directory: $(pwd)"
echo "Please enter git repo link to clone backend codebase:..."
read repolinkbackend

getrepobackend() {
    echo "Getting Repo, Please wait!"
    git clone $repolinkbackend .
}

getrepobackend

# Setup the database
# MySQL connection details
echo "#########################################" 
echo "Setting up the Database"
echo "#########################################" 

MYSQL_CMD="sudo mysql"
MYSQL_USER="imai"
read -s -p "Enter MySQL password you want to set: " MYSQL_PASSWORD
echo

chmod -R 777 "$SCRIPT_DIR" "$SCRIPT_DIR2" "$SCRIPT_DIR3"

# Database details
DATABASE_NAME_1="imai"
SQL_FILE_1="$SCRIPT_DIR/database/imai.sql"
DATABASE_NAME_2="redmine"
SQL_FILE_2="$SCRIPT_DIR/database/redmine.sql"

# Function to create MySQL user and grant privileges
setup_mysql_user() {
    echo "Creating MySQL user $MYSQL_USER and granting privileges..."
    echo "CREATE USER IF NOT EXISTS '$MYSQL_USER'@'localhost' IDENTIFIED BY '$MYSQL_PASSWORD';
    GRANT ALL PRIVILEGES ON *.* TO '$MYSQL_USER'@'localhost' WITH GRANT OPTION;
    FLUSH PRIVILEGES;" | $MYSQL_CMD

    if [ $? -ne 0 ]; then
        echo "Error creating MySQL user or granting privileges."
        exit 1
    fi
}

# Function to create database and execute SQL file
setup_database() {
    local db_name=$1
    local sql_file=$2
    
    echo "Creating database $db_name (if not exists)..."
    echo "CREATE DATABASE IF NOT EXISTS $db_name;" | $MYSQL_CMD

    if [ $? -ne 0 ]; then
        echo "Error creating database $db_name."
        return 1
    fi
    
    echo "Executing SQL file to set up database schema and data for $db_name..."
    mysql -u $MYSQL_USER -p$MYSQL_PASSWORD $db_name < $sql_file

    if [ $? -ne 0 ]; then
        echo "Error executing SQL file for $db_name."
        return 1
    fi
    echo "Database setup completed for $db_name."
}

# Setup MySQL user
setup_mysql_user

# Setup first database
if ! setup_database $DATABASE_NAME_1 $SQL_FILE_1; then
    echo "Failed to set up database $DATABASE_NAME_1. Exiting."
    exit 1
fi

# Setup second database
if ! setup_database $DATABASE_NAME_2 $SQL_FILE_2; then
    echo "Failed to set up database $DATABASE_NAME_2. Exiting."
    exit 1
fi

echo "All database setups completed."

sudo reboot
