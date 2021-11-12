#!/bin/bash

set -e

cat << EOF | kubectl apply -f -
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

while ! kubectl get pods host-volume-shell | grep Running | grep "1/1"; do
  sleep 1
  echo -n .
done

echo
echo "Host volume mount point is /mnt/host/"
echo

kubectl exec -it host-volume-shell -- bash
kubectl delete pod --grace-period=2 host-volume-shell
kubectl delete pvc host-pv-claim
kubectl delete pv host-pv
