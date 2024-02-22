#!/bin/bash

# Define the image name
IMAGE_NAME="getkarma/discord-bot-private"
BOT_CONTAINER_NAME="discord-bot-private"

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo "Docker does not seem to be running, start it first and rerun the script"
        exit 1
    fi
}

# Function to pull the Docker image
pull_image() {
    echo "Pulling Docker image from the registry..."
    if docker pull $IMAGE_NAME; then
        echo "Successfully pulled Docker image."
    else
        echo "Failed to pull Docker image."
        exit 1
    fi
}

# Function to run the Docker image
run_image() {
    echo "Running Docker image..."
    if docker run -d --name $BOT_CONTAINER_NAME $IMAGE_NAME; then
        echo "Successfully started Docker container."
    else
        echo "Failed to start Docker container."
        exit 1
    fi
}

# Main script execution
echo "Starting deployment script..."
check_docker
pull_image
run_image
echo "Deployment script finished."