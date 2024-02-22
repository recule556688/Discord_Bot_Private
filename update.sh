#!/bin/bash

# Define the image and container names
IMAGE_NAME="getkarma/discord-bot-private"
CONTAINER_NAME="discord-bot-private"

# Function to pull the latest Docker image
pull_image() {
    echo "Pulling latest Docker image from the registry..."
    if docker pull $IMAGE_NAME; then
        echo "Successfully pulled latest Docker image."
    else
        echo "Failed to pull latest Docker image."
        exit 1
    fi
}

# Function to stop and remove the running Docker container
remove_container() {
    echo "Stopping and removing the running Docker container..."
    if docker stop $CONTAINER_NAME && docker rm $CONTAINER_NAME; then
        echo "Successfully stopped and removed the Docker container."
    else
        echo "Failed to stop and remove the Docker container."
        exit 1
    fi
}

# Function to run the latest Docker image
run_image() {
    echo "Running latest Docker image..."
    if docker run -d --name $CONTAINER_NAME $IMAGE_NAME; then
        echo "Successfully started new Docker container."
    else
        echo "Failed to start new Docker container."
        exit 1
    fi
}

# Main script execution
echo "Starting update script..."
pull_image
remove_container
run_image
echo "Update script finished."
