#!/bin/bash

set -e

OASIS_CLUSTER_NAMESPACE="${OASIS_CLUSTER_NAMESPACE:-default}"

cat << EOF | kubectl apply -n "$OASIS_CLUSTER_NAMESPACE" -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: host-pv
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
  name: host-pv-claim
spec:
  volumeName: host-pv
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
  name: host-volume-shell
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
        claimName: host-pv-claim
---
EOF

while ! kubectl get pods -n "$OASIS_CLUSTER_NAMESPACE" host-volume-shell | grep Running | grep "1/1"; do
  sleep 1
  echo -n .
done

echo
echo "Host volume mount point is /mnt/host/"
echo

kubectl exec -it -n "$OASIS_CLUSTER_NAMESPACE" host-volume-shell -- bash
kubectl delete pod -n "$OASIS_CLUSTER_NAMESPACE" --grace-period=2 host-volume-shell
kubectl delete pvc -n "$OASIS_CLUSTER_NAMESPACE" host-pv-claim
kubectl delete pv -n "$OASIS_CLUSTER_NAMESPACE" host-pv
