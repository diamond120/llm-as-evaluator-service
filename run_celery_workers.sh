#!/bin/bash -e

# Parse command line arguments for concurrency and processes per queue
while getopts c:p: flag
do
    case "${flag}" in
        c) concurrency=${OPTARG};;
        p) processes_per_queue=${OPTARG};;
    esac
done

# Set default values if not provided
concurrency=${concurrency:-20}
processes_per_queue=${processes_per_queue:-5}

# Start Celery workers for each queue with specified concurrency and logging
queues=("db_fetch_queue" "evaluation_stage2_queue" "process_queue" "evaluation_queue" "saving_queue" "webhook_queue" "logging_queue")

# Ensure logs directory exists
mkdir -p logs

# Function to start workers
start_workers() {
    echo "Starting workers..."
    for queue in "${queues[@]}"; do
        for ((i=1; i<=processes_per_queue; i++)); do
            log_file="logs/log_${queue}_${i}.out"
            echo "Starting worker for queue $queue, process $i, logging to $log_file"
            # Redirect both stdout and stderr to the log file and also to the terminal
            poetry run celery -A workers.celery_worker worker --queues=$queue -l debug -E -P gevent --concurrency=$concurrency -n worker_${queue}_${i} > >(tee -a "$log_file") 2>&1 &
        done
    done
    echo "Workers started..."
}

# Function to stop workers
stop_workers() {
    echo "Stopping all Celery workers..."
    pids=$(pgrep -f 'celery -A workers.celery_worker')
    if [ -n "$pids" ]; then
        echo "Killing PIDs: $pids"
        kill -9 $pids
        echo "Done killing workers."
    else
        echo "No Celery workers found."
    fi
}

# Trap Ctrl+C (SIGINT) and stop workers
trap stop_workers SIGINT

# Start the workers
start_workers

# Wait indefinitely to keep the script running
while true; do
    sleep 1
done
