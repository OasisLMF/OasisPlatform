{{/*
Expand the name of the chart.
*/}}
{{- define "h.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "h.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "h.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "h.labels" -}}
helm.sh/chart: {{ include "h.chart" . }}
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
app.kubernetes.io/name: {{ include "h.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
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
{{- if eq .Values.databases.oasis_db.type "mysql" }}
- name: OASIS_SERVER_DB_ENGINE
  value: django.db.backends.mysql
{{- else }}
- name: OASIS_SERVER_DB_ENGINE
  value: django.db.backends.postgresql_psycopg2
{{- end }}
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
Oasis server API envs
*/}}
{{- define "h.serverApiVars" }}
- name: API_IP
  valueFrom:
    configMapKeyRef:
      name: {{ .Values.oasisServer.name }}
      key: host
- name: API_HOST
  valueFrom:
    configMapKeyRef:
      name: {{ .Values.oasisServer.name }}
      key: host
- name: API_PORT
  valueFrom:
    configMapKeyRef:
      name: {{ .Values.oasisServer.name }}
      key: port
{{- end }}

{{/*
Init container to wait for a service to become available (tcp check only)
*/}}
{{- define "h.initTcpAvailabilityCheck" -}}
{{- $root := (index . 0) -}}
- name: init-tcp-wait
  image: {{ $root.Values.images.init.image }}:{{ $root.Values.images.init.version }}
  command: ['sh', '-c', "
    {{- range $s := slice . 1 -}}
        until nc -zw 3 {{ $s.name }} {{ $s.port }}; do echo 'waiting for service {{ $s.name }}...'; sleep 1; done;
    {{- end -}}
    echo available"]
{{- end -}}

{{- define "h.password" -}}
{{- $secretName := (index . 0) -}}
{{- $name := (index . 1) -}}
{{- $root := (index . 2) -}}
{{- $password := (index . 3) -}}
{{- $missingMessage := (index . 4) -}}

{{- if or $root.Release.IsInstall (not (lookup "v1" "Secret" $root.Release.Namespace $secretName)) -}}
    {{- if $root.Values.generatePasswords -}}
        {{- randAlphaNum 20 | b64enc -}}
    {{- else -}}
        {{ required $missingMessage $password | b64enc }}
    {{- end -}}
{{- else -}}
    {{- index (lookup "v1" "Secret" $root.Release.Namespace $secretName).data $name -}}
{{- end -}}

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
