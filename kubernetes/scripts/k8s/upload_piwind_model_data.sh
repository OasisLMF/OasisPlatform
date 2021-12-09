#!/bin/bash

set -e

PWP=$1
MODEL_PATHS="meta-data/model_settings.json oasislmf.json model_data/ keys_data/ tests/"
OPTIONAL_MODEL_FILES="meta-data/chunking_configuration.json meta-data/scaling_configuration.json"
OASIS_CLUSTER_NAMESPACE="${OASIS_CLUSTER_NAMESPACE:-default}"

if [ -z "$PWP" ] || ! [ -d "$PWP" ]; then
  echo "Usage: $0 <piwind git path>"
  exit
fi

for file in $MODEL_PATHS; do
  file="${PWP}/$file"
  if ! [ -f "$file" ] && ! [ -d "$file" ]; then
    echo "Missing expected file: $file"
    exit 1
  fi
  echo "Found file: $file"
done

for file in $OPTIONAL_MODEL_FILES; do
  file="${PWP}/$file"
  if [ -f "$file" ] && ! [ -d "$file" ]; then
    echo "Found optional file: $file"
  fi
done

echo "Creating volume and pods..."

cat << EOF | kubectl apply -n "$OASIS_CLUSTER_NAMESPACE" -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: host-data-volume
spec:
  storageClassName: manual
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteMany
  hostPath:
    path: /data/
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: host-data-volume-claim
spec:
  volumeName: host-data-volume
  storageClassName: manual
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: host-data-volume-pod
spec:
  containers:
    - image: nginx
      name: nginx
      volumeMounts:
        - name: shared-fs-persistent-storage
          mountPath: /mnt/host
  volumes:
    - name: shared-fs-persistent-storage
      persistentVolumeClaim:
        claimName: host-data-volume-claim
---
EOF

echo -n "Waiting for pod to be created."
while ! kubectl get pods -n "$OASIS_CLUSTER_NAMESPACE" host-data-volume-pod | grep Running | grep -q "1/1"; do
  sleep 1
  echo -n .
done

echo " done"
echo -n "Uploading files..."

kubectl exec -n "$OASIS_CLUSTER_NAMESPACE" host-data-volume-pod -- mkdir -p /mnt/host/model-data/piwind/

for file in $MODEL_PATHS; do
  file=${PWP}/$file
  kubectl cp -n "$OASIS_CLUSTER_NAMESPACE" "${file}" host-data-volume-pod:/mnt/host/model-data/piwind/
  echo -n .
done

for file in $OPTIONAL_MODEL_FILES; do
  file=${PWP}/$file
  if [ -f "$file" ] && ! [ -d "$file" ]; then
    kubectl cp -n "$OASIS_CLUSTER_NAMESPACE" "${file}" host-data-volume-pod:/mnt/host/model-data/piwind/
  fi
  echo -n .
done

echo " done"
echo "Cleaning up..."

kubectl delete pod -n "$OASIS_CLUSTER_NAMESPACE" --grace-period=2 host-data-volume-pod; kubectl delete pvc host-data-volume-claim; kubectl delete pv host-data-volume

echo "All done"

