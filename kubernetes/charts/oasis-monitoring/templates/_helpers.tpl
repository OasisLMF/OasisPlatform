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
Annotations to set worker deployment behaviours like auto scaling rules
*/}}
{{- define "h.workerDeploymentAnnotations" -}}
{{- range $k, $v := .autoScaling }}
oasislmf-autoscaling/{{ $k | kebabcase }}: {{ $v | quote }}
{{- end }}
{{- end }}

{{/*
Variables for a broker client
*/}}
{{- define "h.brokerVars" }}
- name: CELERY_BROKER_URL
  valueFrom:
    configMapKeyRef:
      name: {{ .Values.databases.broker.name }}
      key: uri
{{- end }}

{{/*
Init container to wait for a service to become available (tcp check only) based on host:port from secret
*/}}
{{- define "h.initTcpAvailabilityCheckBySecret" -}}
{{- $root := (index . 0) -}}
- name: init-tcp-wait-by-secret
  image: {{ $root.Values.monitoringImages.init.image }}:{{ $root.Values.monitoringImages.init.version }}
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
