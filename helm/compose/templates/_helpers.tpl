{{/*
Expand the name of the chart.
*/}}
{{- define "scd-reporting.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to every resource.
*/}}
{{- define "scd-reporting.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "scd-reporting.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels – pass the component name as the second argument via a dict.
Usage: {{ include "scd-reporting.selectorLabels" (dict "root" . "component" "web") }}
*/}}
{{- define "scd-reporting.selectorLabels" -}}
app.kubernetes.io/name: {{ include "scd-reporting.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/*
Construct the DATABASE_URL from db values.
*/}}
{{- define "scd-reporting.databaseUrl" -}}
{{- printf "postgres://%s:%s@db:5432/%s" .Values.db.user .Values.db.password .Values.db.name }}
{{- end }}
