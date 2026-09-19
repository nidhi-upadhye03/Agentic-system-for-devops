{{/*
Expand the name of the chart.
*/}}
{{- define "ai-system.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ai-system.fullname" -}}
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
{{- define "ai-system.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ai-system.labels" -}}
helm.sh/chart: {{ include "ai-system.chart" . }}
{{ include "ai-system.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: ai-system
environment: {{ .Values.global.environment }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ai-system.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ai-system.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ai-system.serviceAccountName" -}}
{{- if .Values.rbac.serviceAccount.create }}
{{- default (include "ai-system.fullname" .) .Values.rbac.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.rbac.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
LLM Service labels
*/}}
{{- define "ai-system.llmService.labels" -}}
{{ include "ai-system.labels" . }}
app.kubernetes.io/component: llm-service
{{- end }}

{{/*
LLM Service selector labels
*/}}
{{- define "ai-system.llmService.selectorLabels" -}}
{{ include "ai-system.selectorLabels" . }}
app.kubernetes.io/component: llm-service
{{- end }}

{{/*
Worker labels
*/}}
{{- define "ai-system.worker.labels" -}}
{{ include "ai-system.labels" . }}
app.kubernetes.io/component: worker
{{- end }}

{{/*
Worker selector labels
*/}}
{{- define "ai-system.worker.selectorLabels" -}}
{{ include "ai-system.selectorLabels" . }}
app.kubernetes.io/component: worker
{{- end }}

{{/*
Approval Backend labels
*/}}
{{- define "ai-system.approvalBackend.labels" -}}
{{ include "ai-system.labels" . }}
app.kubernetes.io/component: approval-backend
{{- end }}

{{/*
Approval Backend selector labels
*/}}
{{- define "ai-system.approvalBackend.selectorLabels" -}}
{{ include "ai-system.selectorLabels" . }}
app.kubernetes.io/component: approval-backend
{{- end }}

{{/*
Approval Frontend labels
*/}}
{{- define "ai-system.approvalFrontend.labels" -}}
{{ include "ai-system.labels" . }}
app.kubernetes.io/component: approval-frontend
{{- end }}

{{/*
Approval Frontend selector labels
*/}}
{{- define "ai-system.approvalFrontend.selectorLabels" -}}
{{ include "ai-system.selectorLabels" . }}
app.kubernetes.io/component: approval-frontend
{{- end }}

{{/*
RabbitMQ labels
*/}}
{{- define "ai-system.rabbitmq.labels" -}}
{{ include "ai-system.labels" . }}
app.kubernetes.io/component: rabbitmq
{{- end }}

{{/*
RabbitMQ selector labels
*/}}
{{- define "ai-system.rabbitmq.selectorLabels" -}}
{{ include "ai-system.selectorLabels" . }}
app.kubernetes.io/component: rabbitmq
{{- end }}

{{/*
PostgreSQL labels
*/}}
{{- define "ai-system.postgresql.labels" -}}
{{ include "ai-system.labels" . }}
app.kubernetes.io/component: postgresql
{{- end }}

{{/*
PostgreSQL selector labels
*/}}
{{- define "ai-system.postgresql.selectorLabels" -}}
{{ include "ai-system.selectorLabels" . }}
app.kubernetes.io/component: postgresql
{{- end }}

{{/*
Redis labels
*/}}
{{- define "ai-system.redis.labels" -}}
{{ include "ai-system.labels" . }}
app.kubernetes.io/component: redis
{{- end }}

{{/*
Redis selector labels
*/}}
{{- define "ai-system.redis.selectorLabels" -}}
{{ include "ai-system.selectorLabels" . }}
app.kubernetes.io/component: redis
{{- end }}

{{/*
Return the proper image name
*/}}
{{- define "ai-system.image" -}}
{{- $tag := .tag | default .root.Chart.AppVersion -}}
{{- printf "%s:%s" .repository $tag -}}
{{- end }}

{{/*
Return image pull policy
*/}}
{{- define "ai-system.imagePullPolicy" -}}
{{- .Values.global.imagePullPolicy | default "IfNotPresent" -}}
{{- end }}

{{/*
Return the namespace
*/}}
{{- define "ai-system.namespace" -}}
{{- .Values.global.namespace | default .Release.Namespace -}}
{{- end }}

{{/*
Return the proper Docker Image Registry Secret Names
*/}}
{{- define "ai-system.imagePullSecrets" -}}
{{- if .Values.global.imagePullSecrets }}
imagePullSecrets:
{{- range .Values.global.imagePullSecrets }}
  - name: {{ . }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create environment variables from configmap
*/}}
{{- define "ai-system.envFrom.configMap" -}}
- configMapRef:
    name: {{ include "ai-system.fullname" . }}-config
{{- end }}

{{/*
Create environment variables from secrets
*/}}
{{- define "ai-system.envFrom.secrets" -}}
- secretRef:
    name: {{ include "ai-system.fullname" . }}-secrets
{{- end }}

{{/*
Return the database connection string
*/}}
{{- define "ai-system.databaseUrl" -}}
{{- printf "postgresql://%s:%s@%s:%d/%s" .Values.postgresql.auth.username .Values.postgresql.auth.password .Values.postgresql.name (int .Values.postgresql.service.port) .Values.postgresql.auth.database -}}
{{- end }}

{{/*
Return the Redis connection string
*/}}
{{- define "ai-system.redisUrl" -}}
{{- if .Values.redis.auth.enabled -}}
{{- printf "redis://:%s@%s:%d/0" .Values.redis.auth.password .Values.redis.name (int .Values.redis.service.port) -}}
{{- else -}}
{{- printf "redis://%s:%d/0" .Values.redis.name (int .Values.redis.service.port) -}}
{{- end -}}
{{- end }}

{{/*
Return the RabbitMQ connection string
*/}}
{{- define "ai-system.rabbitmqUrl" -}}
{{- printf "amqp://%s:%s@%s:%d/" .Values.rabbitmq.auth.username .Values.rabbitmq.auth.password .Values.rabbitmq.name (int .Values.rabbitmq.service.ports.amqp) -}}
{{- end }}
