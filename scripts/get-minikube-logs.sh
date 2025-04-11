#!/bin/bash

# Set output directory
OUTPUT_DIR="oasis-kubelogs"

# Clean up or create the output directory
if [ -d "$OUTPUT_DIR" ]; then
    echo "Removing existing $OUTPUT_DIR directory..."
    rm -rf "$OUTPUT_DIR"
fi

echo "Creating $OUTPUT_DIR directory..."
mkdir -p "$OUTPUT_DIR"

# Step 1: List all pods and save to pod-list.txt inside the output directory
echo "Getting list of pods..."
kubectl get pods -o name > "$OUTPUT_DIR/pod-list.txt"
echo "Saved pod list to $OUTPUT_DIR/pod-list.txt"

# Step 2 & 3: For each pod, get logs and details
while read -r pod_line; do
    pod_name=$(echo "$pod_line" | cut -d'/' -f2)

    # Get pod status
    pod_status=$(kubectl get "$pod_line" -o jsonpath='{.status.phase}')

    if [ "$pod_status" == "Running" ]; then
        echo "Processing $pod_name..."

        # Get logs
        kubectl logs "$pod_line" > "$OUTPUT_DIR/${pod_name}.log"
        echo "  Saved logs to $OUTPUT_DIR/${pod_name}.log"

        # Get details
        kubectl describe "$pod_line" > "$OUTPUT_DIR/${pod_name}-details.log"
        echo "  Saved details to $OUTPUT_DIR/${pod_name}-details.log"
    else
        echo "Skipping $pod_name (Status: $pod_status)"
    fi
done < "$OUTPUT_DIR/pod-list.txt"

echo "All logs and details saved in $OUTPUT_DIR"
