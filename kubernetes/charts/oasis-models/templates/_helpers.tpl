{{/*
Common labels
*/}}
{{- define "h.labels" -}}
helm.sh/chart: {{ .Chart.Name }}
{{ include "h.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "h.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Labels to identify worker pods and deployments
*/}}
{{- define "h.workerLabels" -}}
oasislmf/type: worker
oasislmf/supplier-id: {{ .supplierId | quote }}
oasislmf/model-id: {{ .modelId | quote }}
oasislmf/model-version-id: {{ .modelVersionId | quote }}
{{- end }}

{{/*
Annotations to set worker deployment behaviours like auto scaling rules
*/}}
{{- define "h.workerDeploymentAnnotations" -}}
{{- range $k, $v := .autoScaling }}
oasislmf-autoscaling/{{ $k | kebabcase }}: {{ $v | quote }}
{{- end }}
{{- end }}

{{/*
Persistent volume
*/}}
{{- define "h.createPersistentVolume" }}
apiVersion: v1
kind: PersistentVolume
metadata:
  name: {{ .name }}
  labels:
    type: local
spec:
  storageClassName: manual
  capacity:
    storage: {{ .storageCapacity }}
  accessModes:
    - ReadWriteMany
  hostPath:
    path: {{ .hostPath }}
{{- end }}

{{/*
Persistent volume claim
*/}}
{{- define "h.createPersistentVolumeClaim" }}
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ .name }}
spec:
  volumeName: {{ .name }}
  storageClassName: manual
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: {{ .storageCapacity }}
{{- end }}

{{/*
Variables for a DB client
*/}}
{{- define "h.oasisDbVars" }}
{{- $varName := index . 0 }}
{{- $name := index . 1 }}
- name: OASIS_{{ $varName }}_DB_HOST
  valueFrom:
    configMapKeyRef:
      name: {{ $name }}
      key: host
- name: OASIS_{{ $varName }}_DB_PORT
  valueFrom:
    configMapKeyRef:
      name: {{ $name }}
      key: port
- name: OASIS_{{ $varName }}_DB_NAME
  valueFrom:
    configMapKeyRef:
      name: {{ $name }}
      key: dbName
- name: OASIS_{{ $varName }}_DB_USER
  valueFrom:
    secretKeyRef:
      name: {{ $name }}
      key: user
- name: OASIS_{{ $varName }}_DB_PASS
  valueFrom:
    secretKeyRef:
      name: {{ $name }}
      key: password
{{- end }}

{{/*
Variables for a celery DB client
*/}}
{{- define "h.celeryDbVars" }}
{{- include "h.oasisDbVars" (list "CELERY" .Values.databases.celery_db.name) }}
- name: OASIS_CELERY_DB_ENGINE
  value: db+postgresql+psycopg2
{{- end }}

{{/*
Variables for a server DB client
*/}}
{{- define "h.serverDbVars" }}
{{- include "h.oasisDbVars" (list "SERVER" .Values.databases.oasis_db.name) }}
- name: OASIS_SERVER_DB_ENGINE
  value: django.db.backends.postgresql_psycopg2
{{- end }}

{{/*
Variables for a broker client
*/}}
{{- define "h.brokerVars" }}
- name: OASIS_CELERY_BROKER_URL
  valueFrom:
    configMapKeyRef:
      name: {{ .Values.databases.broker.name }}
      key: uri
{{- end }}

{{/*
Variables for a channel layer client
*/}}
{{- define "h.channelLayerVars" }}
- name: OASIS_SERVER_CHANNEL_LAYER_HOST
  value: channel-layer
- name: OASIS_INPUT_GENERATION_CONTROLLER_QUEUE
  value: task-controller
- name: OASIS_LOSSES_GENERATION_CONTROLLER_QUEUE
  value: task-controller
{{- end }}

{{/*
Oasis variables for a worker
*/}}
{{- define "h.modelEnvs" }}
- name: OASIS_MODEL_SUPPLIER_ID
  value: {{ .supplierId | quote}}
- name: OASIS_MODEL_ID
  value: {{ .modelId | quote }}
- name: OASIS_MODEL_VERSION_ID
  value: {{ .modelVersionId | quote }}
- name: OASIS_MEDIA_ROOT
  value: /shared-fs
- name: OASIS_DISABLE_WORKER_REG
  value: "True"
  {{- if .env }}
    {{- toYaml .env | nindent 0 }}
  {{- end }}
{{- end }}

{{/*
Oasis server client variables
*/}}
{{- define "h.oasisServerEnvs" }}
- name: OASIS_SERVER_HOST
  valueFrom:
    configMapKeyRef:
      name: {{ .Values.oasisServer.name }}
      key: host
- name: OASIS_SERVER_PORT
  valueFrom:
    configMapKeyRef:
      name: {{ .Values.oasisServer.name }}
      key: port
- name: OASIS_ADMIN_USER
  valueFrom:
    secretKeyRef:
      name: oasis-rest-service-account
      key: username
- name: OASIS_ADMIN_PASS
  valueFrom:
    secretKeyRef:
      name: oasis-rest-service-account
      key: password
{{- end }}

{{/*
Init container to wait for a service to become available (tcp check only) based on host:port from secret
*/}}
{{- define "h.initTcpAvailabilityCheckBySecret" -}}
{{- $root := (index . 0) -}}
- name: init-tcp-wait-by-secret
  image: {{ $root.Values.modelImages.init.image }}:{{ $root.Values.modelImages.init.version }}
  env:
    {{- range $index, $name := slice . 1 }}
    - name: SERVICE_NAME_{{ $index }}
      value: {{ $name }}
    - name: HOST_{{ $index }}
      valueFrom:
        configMapKeyRef:
          name: {{ $name }}
          key: host
    - name: PORT_{{ $index }}
      valueFrom:
        configMapKeyRef:
          name: {{ $name }}
          key: port
    {{- end }}
  command: ['sh', '-c', 'echo "Waiting for services:{{ range $index, $name := slice . 1 }} {{ $name }} {{- end }}";
    {{- range $index, $name := slice . 1 -}}
        until nc -zw 3 $HOST_{{ $index }} $PORT_{{ $index }}; do echo "waiting for service $SERVICE_NAME_{{ $index }}..."; sleep 1; done;
    {{- end -}}
    echo available']
{{- end -}}

{{/*
Set affinity if enabled
*/}}
{{- define "h.affinity" -}}
{{- if .Values.affinity }}
affinity:
  {{- toYaml .Values.affinity | nindent 2 }}
{{- end -}}
{{- end -}}
