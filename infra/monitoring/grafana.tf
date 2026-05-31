# ==========================================
# Grafana Cloud Data Sources
# ==========================================

# Cloud Monitoring (stackdriver) data source
# monitoring-reader SA の JSON key で認証
resource "grafana_data_source" "cloud_monitoring" {
  name = "GCP Cloud Monitoring"
  type = "stackdriver"

  json_data_encoded = jsonencode({
    authenticationType = "jwt"
    defaultProject     = var.project_id
    tokenUri           = "https://oauth2.googleapis.com/token"
    clientEmail        = google_service_account.monitoring_reader.email
    privateKeyPath     = ""
  })

  secure_json_data_encoded = jsonencode({
    privateKey = jsondecode(base64decode(google_service_account_key.monitoring_reader.private_key)).private_key
  })
}

# Grafana Cloud Loki data source
resource "grafana_data_source" "loki" {
  name = "Grafana Cloud Loki"
  type = "loki"
  url  = var.loki_url

  basic_auth_enabled  = true
  basic_auth_username = var.loki_username

  secure_json_data_encoded = jsonencode({
    basicAuthPassword = var.loki_password
  })
}

# ==========================================
# Dashboard フォルダ
# ==========================================
resource "grafana_folder" "cloud_run" {
  title = "Cloud Run"
}

# ==========================================
# Cloud Run Service ダッシュボード
# ==========================================
resource "grafana_dashboard" "cloud_run_service" {
  folder = grafana_folder.cloud_run.id

  config_json = jsonencode({
    title       = "Cloud Run Service - ${var.cloud_run_service_name}"
    description = "バックエンド API のメトリクスとエラーログ"
    tags        = ["cloud-run", "backend", var.environment]
    refresh     = "1m"
    time = {
      from = "now-3h"
      to   = "now"
    }
    panels = [
      # Row: メトリクス
      {
        id      = 1
        type    = "row"
        title   = "メトリクス"
        gridPos = { h = 1, w = 24, x = 0, y = 0 }
      },
      # Instance Count
      {
        id    = 2
        type  = "timeseries"
        title = "インスタンス数"
        gridPos = { h = 8, w = 12, x = 0, y = 1 }
        datasource = { type = "stackdriver", uid = grafana_data_source.cloud_monitoring.uid }
        targets = [
          {
            refId      = "A"
            metricType = "run.googleapis.com/container/instance_count"
            filters = [
              "resource.labels.service_name", "=", var.cloud_run_service_name
            ]
            aliasBy   = "インスタンス数"
            groupBys  = []
            crossSeriesReducer = "REDUCE_SUM"
            perSeriesAligner   = "ALIGN_MEAN"
            alignmentPeriod    = "60s"
          }
        ]
        fieldConfig = {
          defaults = {
            unit  = "short"
            color = { mode = "palette-classic" }
          }
        }
      },
      # Request Count
      {
        id    = 3
        type  = "timeseries"
        title = "リクエスト数 (status_code 別)"
        gridPos = { h = 8, w = 12, x = 12, y = 1 }
        datasource = { type = "stackdriver", uid = grafana_data_source.cloud_monitoring.uid }
        targets = [
          {
            refId      = "A"
            metricType = "run.googleapis.com/request_count"
            filters = [
              "resource.labels.service_name", "=", var.cloud_run_service_name
            ]
            aliasBy            = "{{metric.labels.response_code_class}}"
            groupBys           = ["metric.labels.response_code_class"]
            crossSeriesReducer = "REDUCE_SUM"
            perSeriesAligner   = "ALIGN_RATE"
            alignmentPeriod    = "60s"
          }
        ]
        fieldConfig = {
          defaults = {
            unit  = "reqps"
            color = { mode = "palette-classic" }
          }
        }
      },
      # Request Latency
      {
        id    = 4
        type  = "timeseries"
        title = "レイテンシ (P50 / P95 / P99)"
        gridPos = { h = 8, w = 12, x = 0, y = 9 }
        datasource = { type = "stackdriver", uid = grafana_data_source.cloud_monitoring.uid }
        targets = [
          {
            refId      = "P50"
            metricType = "run.googleapis.com/request_latencies"
            filters = [
              "resource.labels.service_name", "=", var.cloud_run_service_name
            ]
            aliasBy            = "P50"
            groupBys           = []
            crossSeriesReducer = "REDUCE_PERCENTILE_50"
            perSeriesAligner   = "ALIGN_DELTA"
            alignmentPeriod    = "60s"
          },
          {
            refId      = "P95"
            metricType = "run.googleapis.com/request_latencies"
            filters = [
              "resource.labels.service_name", "=", var.cloud_run_service_name
            ]
            aliasBy            = "P95"
            groupBys           = []
            crossSeriesReducer = "REDUCE_PERCENTILE_95"
            perSeriesAligner   = "ALIGN_DELTA"
            alignmentPeriod    = "60s"
          },
          {
            refId      = "P99"
            metricType = "run.googleapis.com/request_latencies"
            filters = [
              "resource.labels.service_name", "=", var.cloud_run_service_name
            ]
            aliasBy            = "P99"
            groupBys           = []
            crossSeriesReducer = "REDUCE_PERCENTILE_99"
            perSeriesAligner   = "ALIGN_DELTA"
            alignmentPeriod    = "60s"
          }
        ]
        fieldConfig = {
          defaults = {
            unit  = "ms"
            color = { mode = "palette-classic" }
          }
        }
      },
      # CPU / Memory Utilization
      {
        id    = 5
        type  = "timeseries"
        title = "CPU / Memory 使用率"
        gridPos = { h = 8, w = 12, x = 12, y = 9 }
        datasource = { type = "stackdriver", uid = grafana_data_source.cloud_monitoring.uid }
        targets = [
          {
            refId      = "CPU"
            metricType = "run.googleapis.com/container/cpu/utilizations"
            filters = [
              "resource.labels.service_name", "=", var.cloud_run_service_name
            ]
            aliasBy            = "CPU 使用率"
            groupBys           = []
            crossSeriesReducer = "REDUCE_MEAN"
            perSeriesAligner   = "ALIGN_MEAN"
            alignmentPeriod    = "60s"
          },
          {
            refId      = "MEM"
            metricType = "run.googleapis.com/container/memory/utilizations"
            filters = [
              "resource.labels.service_name", "=", var.cloud_run_service_name
            ]
            aliasBy            = "Memory 使用率"
            groupBys           = []
            crossSeriesReducer = "REDUCE_MEAN"
            perSeriesAligner   = "ALIGN_MEAN"
            alignmentPeriod    = "60s"
          }
        ]
        fieldConfig = {
          defaults = {
            unit = "percentunit"
            min  = 0
            max  = 1
            color = { mode = "palette-classic" }
          }
        }
      },
      # Row: ログ
      {
        id      = 10
        type    = "row"
        title   = "ログ"
        gridPos = { h = 1, w = 24, x = 0, y = 17 }
      },
      # エラー・警告ログ
      {
        id    = 11
        type  = "logs"
        title = "エラー / 警告ログ"
        gridPos = { h = 10, w = 24, x = 0, y = 18 }
        datasource = { type = "loki", uid = grafana_data_source.loki.uid }
        targets = [
          {
            refId = "A"
            expr  = "{env=\"${var.environment}\", resource_type=\"cloud_run_revision\"} | json | severity =~ `ERROR|WARNING|CRITICAL`"
          }
        ]
        options = {
          showTime      = true
          showLabels    = false
          wrapLogMessage = true
          sortOrder     = "Descending"
        }
      },
      # 非200 アクセスログ
      {
        id    = 12
        type  = "logs"
        title = "非 200 アクセスログ (4xx / 5xx)"
        gridPos = { h = 10, w = 24, x = 0, y = 28 }
        datasource = { type = "loki", uid = grafana_data_source.loki.uid }
        targets = [
          {
            refId = "A"
            expr  = "{env=\"${var.environment}\", resource_type=\"cloud_run_revision\"} | json | httpRequest_status != `` | httpRequest_status != `200`"
          }
        ]
        options = {
          showTime      = true
          showLabels    = false
          wrapLogMessage = true
          sortOrder     = "Descending"
        }
      }
    ]
    schemaVersion = 38
  })
}

# ==========================================
# Cloud Run Job ダッシュボード
# ==========================================
resource "grafana_dashboard" "cloud_run_job" {
  folder = grafana_folder.cloud_run.id

  config_json = jsonencode({
    title       = "Cloud Run Job - ${var.cloud_run_job_name}"
    description = "バッチジョブのメトリクスと例外ログ"
    tags        = ["cloud-run", "batch", var.environment]
    refresh     = "5m"
    time = {
      from = "now-24h"
      to   = "now"
    }
    panels = [
      # Row: メトリクス
      {
        id      = 1
        type    = "row"
        title   = "メトリクス"
        gridPos = { h = 1, w = 24, x = 0, y = 0 }
      },
      # タスク完了数（成功）
      {
        id    = 2
        type  = "timeseries"
        title = "タスク完了数 (成功 / 失敗)"
        gridPos = { h = 8, w = 12, x = 0, y = 1 }
        datasource = { type = "stackdriver", uid = grafana_data_source.cloud_monitoring.uid }
        targets = [
          {
            refId      = "SUCCESS"
            metricType = "run.googleapis.com/job/completed_task_attempt_count"
            filters = [
              "resource.labels.job_name", "=", var.cloud_run_job_name,
              "metric.labels.result", "=", "succeeded"
            ]
            aliasBy            = "成功"
            groupBys           = []
            crossSeriesReducer = "REDUCE_SUM"
            perSeriesAligner   = "ALIGN_DELTA"
            alignmentPeriod    = "300s"
          },
          {
            refId      = "FAILED"
            metricType = "run.googleapis.com/job/completed_task_attempt_count"
            filters = [
              "resource.labels.job_name", "=", var.cloud_run_job_name,
              "metric.labels.result", "=", "failed"
            ]
            aliasBy            = "失敗"
            groupBys           = []
            crossSeriesReducer = "REDUCE_SUM"
            perSeriesAligner   = "ALIGN_DELTA"
            alignmentPeriod    = "300s"
          }
        ]
        fieldConfig = {
          defaults = {
            unit  = "short"
            color = { mode = "palette-classic" }
          }
          overrides = [
            {
              matcher = { id = "byName", options = "失敗" }
              properties = [
                { id = "color", value = { mode = "fixed", fixedColor = "red" } }
              ]
            }
          ]
        }
      },
      # タスク失敗数 (stat)
      {
        id    = 3
        type  = "stat"
        title = "直近 24h のタスク失敗数"
        gridPos = { h = 8, w = 12, x = 12, y = 1 }
        datasource = { type = "stackdriver", uid = grafana_data_source.cloud_monitoring.uid }
        targets = [
          {
            refId      = "A"
            metricType = "run.googleapis.com/job/completed_task_attempt_count"
            filters = [
              "resource.labels.job_name", "=", var.cloud_run_job_name,
              "metric.labels.result", "=", "failed"
            ]
            aliasBy            = "失敗数"
            groupBys           = []
            crossSeriesReducer = "REDUCE_SUM"
            perSeriesAligner   = "ALIGN_DELTA"
            alignmentPeriod    = "86400s"
          }
        ]
        options = {
          colorMode  = "background"
          reduceOptions = { calcs = ["sum"] }
        }
        fieldConfig = {
          defaults = {
            unit = "short"
            thresholds = {
              mode = "absolute"
              steps = [
                { color = "green", value = null },
                { color = "red", value = 1 }
              ]
            }
          }
        }
      },
      # Row: ログ
      {
        id      = 10
        type    = "row"
        title   = "ログ"
        gridPos = { h = 1, w = 24, x = 0, y = 9 }
      },
      # バッチ例外ログ
      {
        id    = 11
        type  = "logs"
        title = "例外 / エラーログ"
        gridPos = { h = 12, w = 24, x = 0, y = 10 }
        datasource = { type = "loki", uid = grafana_data_source.loki.uid }
        targets = [
          {
            refId = "A"
            expr  = "{env=\"${var.environment}\", resource_type=\"cloud_run_job\"} | json | severity =~ `ERROR|CRITICAL|EMERGENCY`"
          }
        ]
        options = {
          showTime      = true
          showLabels    = false
          wrapLogMessage = true
          sortOrder     = "Descending"
        }
      }
    ]
    schemaVersion = 38
  })
}
