#!/usr/bin/env python3
"""Generate EMS5G Scalability & Capacity Monitoring Grafana Dashboard JSON."""
import json

# ── Helpers ──────────────────────────────────────────────────────────────────
_pid = 0
def pid():
    global _pid; _pid += 1; return _pid

def ds():
    return {"type": "prometheus", "uid": "${DS_PROMETHEUS}"}

def ts_panel(title, targets, unit, y, w=12, h=8, x=0, desc="", stack=False, legendMode="table"):
    p = {
        "id": pid(), "type": "timeseries", "title": title, "description": desc,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": ds(),
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "axisBorderShow": False, "axisCenteredZero": False,
                    "axisLabel": "", "axisPlacement": "auto",
                    "barAlignment": 0, "drawStyle": "line", "fillOpacity": 10,
                    "gradientMode": "opacity", "lineInterpolation": "smooth",
                    "lineWidth": 2, "pointSize": 5, "showPoints": "never",
                    "spanNulls": True,
                    "stacking": {"group": "A", "mode": "normal" if stack else "none"},
                    "thresholdsStyle": {"mode": "off"}
                },
                "unit": unit,
                "thresholds": {"mode": "absolute", "steps": [
                    {"color": "green", "value": None}, {"color": "red", "value": 80}
                ]}
            }, "overrides": []
        },
        "options": {
            "legend": {"calcs": ["mean","max","lastNotNull"], "displayMode": legendMode, "placement": "bottom", "showLegend": True},
            "tooltip": {"mode": "multi", "sort": "desc"}
        },
        "targets": [{"datasource": ds(), "expr": t["expr"], "legendFormat": t.get("legend","{{pod}}"),
                      "refId": chr(65+i), "editorMode": "code", "range": True,
                      "interval": "", "intervalFactor": 1}
                     for i, t in enumerate(targets)]
    }
    return p

def stat_panel(title, targets, unit, y, w=4, h=4, x=0, color="green", desc="", thresholds=None):
    th = thresholds or [{"color": "green", "value": None}, {"color": "orange", "value": 70}, {"color": "red", "value": 85}]
    return {
        "id": pid(), "type": "stat", "title": title, "description": desc,
        "gridPos": {"h": h, "w": w, "x": x, "y": y}, "datasource": ds(),
        "fieldConfig": {
            "defaults": {"unit": unit, "color": {"mode": "thresholds"},
                         "thresholds": {"mode": "absolute", "steps": th},
                         "mappings": []}, "overrides": []},
        "options": {"colorMode": "background", "graphMode": "area", "justifyMode": "auto",
                    "orientation": "auto", "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                    "textMode": "auto", "wideLayout": True},
        "targets": [{"datasource": ds(), "expr": t["expr"], "legendFormat": t.get("legend",""),
                      "refId": chr(65+i), "instant": True} for i, t in enumerate(targets)]
    }

def gauge_panel(title, targets, unit, y, w=6, h=5, x=0, desc=""):
    return {
        "id": pid(), "type": "gauge", "title": title, "description": desc,
        "gridPos": {"h": h, "w": w, "x": x, "y": y}, "datasource": ds(),
        "fieldConfig": {
            "defaults": {"unit": unit, "min": 0, "max": 100,
                         "color": {"mode": "continuous-GrYlRd"},
                         "thresholds": {"mode": "absolute", "steps": [
                             {"color": "green", "value": None}, {"color": "yellow", "value": 60},
                             {"color": "orange", "value": 75}, {"color": "red", "value": 90}]}},
            "overrides": []},
        "options": {"showThresholdLabels": False, "showThresholdMarkers": True,
                    "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}},
        "targets": [{"datasource": ds(), "expr": t["expr"], "legendFormat": t.get("legend",""),
                      "refId": chr(65+i), "instant": True} for i, t in enumerate(targets)]
    }

def bar_gauge(title, targets, unit, y, w=12, h=8, x=0, desc="", orient="horizontal"):
    return {
        "id": pid(), "type": "bargauge", "title": title, "description": desc,
        "gridPos": {"h": h, "w": w, "x": x, "y": y}, "datasource": ds(),
        "fieldConfig": {
            "defaults": {"unit": unit, "color": {"mode": "continuous-BlYlRd"},
                         "thresholds": {"mode": "absolute", "steps": [
                             {"color": "green", "value": None}, {"color": "red", "value": 80}]}},
            "overrides": []},
        "options": {"displayMode": "gradient", "minVizHeight": 10, "minVizWidth": 0,
                    "orientation": orient, "showUnfilled": True, "valueMode": "color",
                    "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}},
        "targets": [{"datasource": ds(), "expr": t["expr"], "legendFormat": t.get("legend","{{pod}}"),
                      "refId": chr(65+i), "instant": True} for i, t in enumerate(targets)]
    }

def table_panel(title, targets, y, w=24, h=8, x=0, desc=""):
    return {
        "id": pid(), "type": "table", "title": title, "description": desc,
        "gridPos": {"h": h, "w": w, "x": x, "y": y}, "datasource": ds(),
        "fieldConfig": {"defaults": {"color": {"mode": "thresholds"},
                        "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]}}, "overrides": []},
        "options": {"showHeader": True, "sortBy": [{"displayName": "Value", "desc": True}],
                    "cellHeight": "sm", "footer": {"show": False}},
        "targets": [{"datasource": ds(), "expr": t["expr"], "legendFormat": t.get("legend",""),
                      "refId": chr(65+i), "instant": True, "format": "table"} for i, t in enumerate(targets)],
        "transformations": [{"id": "organize", "options": {}}]
    }

def row_panel(title, y, collapsed=True, panels=None):
    return {
        "id": pid(), "type": "row", "title": title,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": y},
        "collapsed": collapsed, "panels": panels or []
    }

NS = '${namespace}'
POD = '${pod}'
SVC = '${service}'

# ── TEMPLATE VARIABLES ──────────────────────────────────────────────────────
templating = {"list": [
    {"name": "DS_PROMETHEUS", "type": "datasource", "query": "prometheus",
     "current": {}, "hide": 0, "includeAll": False, "multi": False, "options": [],
     "refresh": 1, "regex": "", "skipUrlSync": False},
    {"name": "namespace", "type": "query", "query": "label_values(kube_pod_info, namespace)",
     "datasource": ds(), "current": {"selected": True, "text": "ems5g", "value": "ems5g"},
     "hide": 0, "includeAll": False, "multi": False, "refresh": 2, "regex": "", "sort": 1},
    {"name": "pod", "type": "query", "query": f'label_values(container_cpu_usage_seconds_total{{namespace="${NS}", container!="", container!="POD"}}, pod)',
     "datasource": ds(), "current": {}, "hide": 0, "includeAll": True, "multi": True,
     "refresh": 2, "regex": "", "sort": 1, "allValue": ".*"},
    {"name": "service", "type": "query",
     "query": f'label_values(kube_deployment_labels{{namespace="${NS}"}}, deployment)',
     "datasource": ds(), "current": {}, "hide": 0, "includeAll": True, "multi": True,
     "refresh": 2, "regex": "", "sort": 1, "allValue": ".*"},
    {"name": "node", "type": "query", "query": "label_values(kube_node_info, node)",
     "datasource": ds(), "current": {}, "hide": 0, "includeAll": True, "multi": True,
     "refresh": 2, "regex": "", "sort": 1},
    {"name": "interval", "type": "interval", "query": "1m,5m,10m,30m,1h",
     "current": {"selected": True, "text": "5m", "value": "5m"},
     "hide": 0, "auto": False, "auto_count": 30, "auto_min": "10s"}
]}

# ── OVERVIEW PANELS (always visible) ────────────────────────────────────────
overview = [
    stat_panel("Running Pods", [{"expr": f'count(kube_pod_status_phase{{namespace="{NS}", phase="Running"}} == 1)'}],
               "short", 0, w=4, x=0, thresholds=[{"color":"green","value":None}]),
    stat_panel("Total CPU Usage (cores)", [{"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", container!="", container!="POD"}}[$interval]))'}],
               "short", 0, w=4, x=4, thresholds=[{"color":"blue","value":None}]),
    stat_panel("Total Memory Usage", [{"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", container!="", container!="POD"}})'}],
               "bytes", 0, w=4, x=8, thresholds=[{"color":"purple","value":None}]),
    stat_panel("Total Disk Usage", [{"expr": f'sum(container_fs_usage_bytes{{namespace="{NS}", container!=""}})'}],
               "bytes", 0, w=4, x=12, thresholds=[{"color":"orange","value":None}]),
    stat_panel("Pod Restarts (1h)", [{"expr": f'sum(increase(kube_pod_container_status_restarts_total{{namespace="{NS}"}}[1h]))'}],
               "short", 0, w=4, x=16, thresholds=[{"color":"green","value":None},{"color":"orange","value":1},{"color":"red","value":5}]),
    stat_panel("OOMKilled (24h)", [{"expr": f'sum(increase(kube_pod_container_status_last_terminated_reason{{namespace="{NS}", reason="OOMKilled"}}[24h])) OR vector(0)'}],
               "short", 0, w=4, x=20, thresholds=[{"color":"green","value":None},{"color":"red","value":1}]),
    gauge_panel("Namespace CPU Utilization %", [{"expr": f'100 * sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", container!="", container!="POD"}}[$interval])) / sum(kube_pod_container_resource_limits{{namespace="{NS}", resource="cpu"}})'}],
                "percent", 4, w=8, x=0),
    gauge_panel("Namespace Memory Utilization %", [{"expr": f'100 * sum(container_memory_working_set_bytes{{namespace="{NS}", container!="", container!="POD"}}) / sum(kube_pod_container_resource_limits{{namespace="{NS}", resource="memory"}})'}],
                "percent", 4, w=8, x=8),
    gauge_panel("Node CPU Utilization %", [{"expr": '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'}],
                "percent", 4, w=8, x=16),
]

# ── CPU USAGE ────────────────────────────────────────────────────────────────
cpu_panels = [
    ts_panel("CPU Usage by Pod (cores)", [
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"{POD}", container!="", container!="POD"}}[$interval])) by (pod)', "legend": "{{pod}}"}
    ], "short", 1, w=12, x=0, desc="CPU cores consumed per pod"),
    ts_panel("CPU Usage vs Limits", [
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"{POD}", container!="", container!="POD"}}[$interval])) by (pod)', "legend": "usage: {{pod}}"},
        {"expr": f'sum(kube_pod_container_resource_limits{{namespace="{NS}", pod=~"{POD}", resource="cpu"}}) by (pod)', "legend": "limit: {{pod}}"}
    ], "short", 1, w=12, x=12, desc="CPU usage vs configured limits"),
    ts_panel("CPU Utilization % by Pod", [
        {"expr": f'100 * sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"{POD}", container!="", container!="POD"}}[$interval])) by (pod) / sum(kube_pod_container_resource_limits{{namespace="{NS}", pod=~"{POD}", resource="cpu"}}) by (pod)', "legend": "{{pod}}"}
    ], "percentunit", 9, w=12, x=0, desc="CPU usage as percentage of limit"),
    ts_panel("CPU Throttling by Pod", [
        {"expr": f'sum(rate(container_cpu_cfs_throttled_seconds_total{{namespace="{NS}", pod=~"{POD}", container!=""}}[$interval])) by (pod)', "legend": "{{pod}}"}
    ], "s", 9, w=12, x=12, desc="CPU CFS throttle duration - high values indicate CPU starvation"),
    bar_gauge("Top 10 CPU Consumers", [
        {"expr": f'topk(10, sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", container!="", container!="POD"}}[$interval])) by (pod))', "legend": "{{pod}}"}
    ], "short", 17, w=12, x=0, desc="Top 10 pods by CPU usage"),
    ts_panel("CPU Requests vs Usage", [
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"{POD}", container!="", container!="POD"}}[$interval])) by (pod)', "legend": "usage: {{pod}}"},
        {"expr": f'sum(kube_pod_container_resource_requests{{namespace="{NS}", pod=~"{POD}", resource="cpu"}}) by (pod)', "legend": "request: {{pod}}"}
    ], "short", 17, w=12, x=12, desc="CPU requests vs actual usage - helps with right-sizing"),
]

# ── MEMORY USAGE ─────────────────────────────────────────────────────────────
mem_panels = [
    ts_panel("Memory Usage by Pod (Working Set)", [
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"{POD}", container!="", container!="POD"}}) by (pod)', "legend": "{{pod}}"}
    ], "bytes", 1, w=12, x=0, desc="Working set memory per pod"),
    ts_panel("Memory Usage vs Limits", [
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"{POD}", container!="", container!="POD"}}) by (pod)', "legend": "usage: {{pod}}"},
        {"expr": f'sum(kube_pod_container_resource_limits{{namespace="{NS}", pod=~"{POD}", resource="memory"}}) by (pod)', "legend": "limit: {{pod}}"}
    ], "bytes", 1, w=12, x=12, desc="Memory working set vs configured limits"),
    ts_panel("Memory Utilization % by Pod", [
        {"expr": f'100 * sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"{POD}", container!="", container!="POD"}}) by (pod) / sum(kube_pod_container_resource_limits{{namespace="{NS}", pod=~"{POD}", resource="memory"}}) by (pod)', "legend": "{{pod}}"}
    ], "percent", 9, w=12, x=0, desc="Memory as percentage of limit - alerts should fire >85%"),
    ts_panel("Memory RSS vs Cache", [
        {"expr": f'sum(container_memory_rss{{namespace="{NS}", pod=~"{POD}", container!=""}}) by (pod)', "legend": "RSS: {{pod}}"},
        {"expr": f'sum(container_memory_cache{{namespace="{NS}", pod=~"{POD}", container!=""}}) by (pod)', "legend": "Cache: {{pod}}"}
    ], "bytes", 9, w=12, x=12, desc="RSS (non-reclaimable) vs Cache (reclaimable) memory"),
    bar_gauge("Top 10 Memory Consumers", [
        {"expr": f'topk(10, sum(container_memory_working_set_bytes{{namespace="{NS}", container!="", container!="POD"}}) by (pod))', "legend": "{{pod}}"}
    ], "bytes", 17, w=12, x=0),
    ts_panel("Memory Requests vs Usage", [
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"{POD}", container!="", container!="POD"}}) by (pod)', "legend": "usage: {{pod}}"},
        {"expr": f'sum(kube_pod_container_resource_requests{{namespace="{NS}", pod=~"{POD}", resource="memory"}}) by (pod)', "legend": "request: {{pod}}"}
    ], "bytes", 17, w=12, x=12, desc="Memory requests vs actual usage for capacity planning"),
]

# ── DISK USAGE ───────────────────────────────────────────────────────────────
disk_panels = [
    ts_panel("Container Filesystem Usage by Pod", [
        {"expr": f'sum(container_fs_usage_bytes{{namespace="{NS}", pod=~"{POD}", container!=""}}) by (pod)', "legend": "{{pod}}"}
    ], "bytes", 1, w=12, x=0, desc="Filesystem bytes used inside each container"),
    ts_panel("Container FS Usage % of Limit", [
        {"expr": f'sum(container_fs_usage_bytes{{namespace="{NS}", pod=~"{POD}", container!=""}}) by (pod) / sum(container_fs_limit_bytes{{namespace="{NS}", pod=~"{POD}", container!=""}}) by (pod) * 100', "legend": "{{pod}}"}
    ], "percent", 1, w=12, x=12, desc="Filesystem usage as percentage of filesystem limit"),
    ts_panel("PV Usage (kubelet_volume_stats)", [
        {"expr": f'kubelet_volume_stats_used_bytes{{namespace="{NS}"}}', "legend": "{{persistentvolumeclaim}}"}
    ], "bytes", 9, w=12, x=0, desc="Persistent Volume usage by PVC"),
    ts_panel("PV Available vs Capacity", [
        {"expr": f'kubelet_volume_stats_capacity_bytes{{namespace="{NS}"}}', "legend": "capacity: {{persistentvolumeclaim}}"},
        {"expr": f'kubelet_volume_stats_used_bytes{{namespace="{NS}"}}', "legend": "used: {{persistentvolumeclaim}}"}
    ], "bytes", 9, w=12, x=12, desc="PV capacity vs actual usage"),
    bar_gauge("Top 10 Disk Consumers", [
        {"expr": f'topk(10, sum(container_fs_usage_bytes{{namespace="{NS}", container!=""}}) by (pod))', "legend": "{{pod}}"}
    ], "bytes", 17, w=12, x=0),
    ts_panel("Node Disk I/O", [
        {"expr": 'rate(node_disk_read_bytes_total[5m])', "legend": "read: {{device}}"},
        {"expr": 'rate(node_disk_written_bytes_total[5m])', "legend": "write: {{device}}"}
    ], "Bps", 17, w=12, x=12, desc="Node-level disk read/write throughput"),
]

# ── DATABASES ────────────────────────────────────────────────────────────────
db_panels = [
    # PostgreSQL
    ts_panel("PostgreSQL — Tuples Inserted/s", [
        {"expr": f'rate(pg_stat_database_tup_inserted{{namespace="{NS}"}}[$interval])', "legend": "{{datname}}"}
    ], "ops", 1, w=8, x=0, desc="Rate of tuples inserted per database"),
    ts_panel("PostgreSQL — Tuples Updated/s", [
        {"expr": f'rate(pg_stat_database_tup_updated{{namespace="{NS}"}}[$interval])', "legend": "{{datname}}"}
    ], "ops", 1, w=8, x=8, desc="Rate of tuples updated per database"),
    ts_panel("PostgreSQL — Tuples Deleted/s", [
        {"expr": f'rate(pg_stat_database_tup_deleted{{namespace="{NS}"}}[$interval])', "legend": "{{datname}}"}
    ], "ops", 1, w=8, x=16, desc="Rate of tuples deleted per database"),
    ts_panel("PostgreSQL — Active Connections", [
        {"expr": f'pg_stat_database_numbackends{{namespace="{NS}"}}', "legend": "{{datname}}"}
    ], "short", 9, w=8, x=0, desc="Active backend connections per database"),
    ts_panel("PostgreSQL — Database Size", [
        {"expr": f'pg_database_size_bytes{{namespace="{NS}"}}', "legend": "{{datname}}"}
    ], "bytes", 9, w=8, x=8, desc="Total size of each database"),
    ts_panel("PostgreSQL — Transactions/s", [
        {"expr": f'rate(pg_stat_database_xact_commit{{namespace="{NS}"}}[$interval])', "legend": "commit: {{datname}}"},
        {"expr": f'rate(pg_stat_database_xact_rollback{{namespace="{NS}"}}[$interval])', "legend": "rollback: {{datname}}"}
    ], "ops", 9, w=8, x=16, desc="Commit and rollback transaction rates"),
    # Cassandra
    ts_panel("Cassandra — Client Read Latency", [
        {"expr": f'cassandra_client_request_latency{{namespace="{NS}", request_type="read"}}', "legend": "p{{quantile}} read"},
        {"expr": f'cassandra_clientrequest_latency_seconds{{namespace="{NS}", scope="Read"}}', "legend": "read: {{quantile}}"}
    ], "s", 17, w=8, x=0, desc="Client read request latency (try both metric name conventions)"),
    ts_panel("Cassandra — Client Write Latency", [
        {"expr": f'cassandra_client_request_latency{{namespace="{NS}", request_type="write"}}', "legend": "p{{quantile}} write"},
        {"expr": f'cassandra_clientrequest_latency_seconds{{namespace="{NS}", scope="Write"}}', "legend": "write: {{quantile}}"}
    ], "s", 17, w=8, x=8, desc="Client write request latency"),
    ts_panel("Cassandra — Pending Compactions & Connections", [
        {"expr": f'cassandra_compaction_pendingtasks{{namespace="{NS}"}}', "legend": "pending compactions"},
        {"expr": f'cassandra_client_connected_native_clients{{namespace="{NS}"}}', "legend": "native clients"}
    ], "short", 17, w=8, x=16, desc="Pending compaction tasks and connected clients"),
    # Kafka
    ts_panel("Kafka — Messages In/s", [
        {"expr": f'sum(rate(kafka_server_brokertopicmetrics_messagesinpersec_count{{namespace="{NS}"}}[$interval])) by (topic)', "legend": "{{topic}}"},
    ], "ops", 25, w=8, x=0, desc="Kafka message ingestion rate per topic"),
    ts_panel("Kafka — Consumer Lag", [
        {"expr": f'kafka_consumergroup_lag{{namespace="{NS}"}}', "legend": "{{consumergroup}}-{{topic}}"}
    ], "short", 25, w=8, x=8, desc="Consumer group lag - high lag indicates consumers can't keep up"),
    ts_panel("Kafka — Log Size", [
        {"expr": f'sum(kafka_log_log_size{{namespace="{NS}"}}) by (topic)', "legend": "{{topic}}"}
    ], "bytes", 25, w=8, x=16, desc="Kafka log segment size per topic"),
]

# ── PODS ─────────────────────────────────────────────────────────────────────
pod_panels = [
    ts_panel("Pod Restarts Over Time", [
        {"expr": f'increase(kube_pod_container_status_restarts_total{{namespace="{NS}"}}[$interval])', "legend": "{{pod}} / {{container}}"}
    ], "short", 1, w=12, x=0, desc="Container restart count increases"),
    ts_panel("Pod CPU vs Memory Scatter (Usage)", [
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", container!="", container!="POD"}}[$interval])) by (pod)', "legend": "cpu: {{pod}}"},
    ], "short", 1, w=12, x=12, desc="CPU usage trends per pod"),
    stat_panel("Pods Not Ready", [
        {"expr": f'count(kube_pod_status_ready{{namespace="{NS}", condition="true"}} == 0) OR vector(0)'}
    ], "short", 9, w=6, x=0, thresholds=[{"color":"green","value":None},{"color":"red","value":1}]),
    stat_panel("CrashLoopBackOff", [
        {"expr": f'count(kube_pod_container_status_waiting_reason{{namespace="{NS}", reason="CrashLoopBackOff"}} == 1) OR vector(0)'}
    ], "short", 9, w=6, x=6, thresholds=[{"color":"green","value":None},{"color":"red","value":1}]),
    stat_panel("Pods Pending", [
        {"expr": f'count(kube_pod_status_phase{{namespace="{NS}", phase="Pending"}} == 1) OR vector(0)'}
    ], "short", 9, w=6, x=12, thresholds=[{"color":"green","value":None},{"color":"orange","value":1}]),
    stat_panel("Evicted Pods (24h)", [
        {"expr": f'count(kube_pod_status_reason{{namespace="{NS}", reason="Evicted"}} == 1) OR vector(0)'}
    ], "short", 9, w=6, x=18, thresholds=[{"color":"green","value":None},{"color":"red","value":1}]),
    ts_panel("Container Ready State", [
        {"expr": f'kube_pod_container_status_ready{{namespace="{NS}"}}', "legend": "{{pod}}/{{container}}"}
    ], "short", 13, w=12, x=0, desc="1 = ready, 0 = not ready"),
    ts_panel("Container Network Receive/Transmit", [
        {"expr": f'sum(rate(container_network_receive_bytes_total{{namespace="{NS}", pod=~"{POD}"}}[$interval])) by (pod)', "legend": "rx: {{pod}}"},
        {"expr": f'sum(rate(container_network_transmit_bytes_total{{namespace="{NS}", pod=~"{POD}"}}[$interval])) by (pod)', "legend": "tx: {{pod}}"}
    ], "Bps", 13, w=12, x=12, desc="Network I/O per pod"),
]

# ── PER SERVICE ──────────────────────────────────────────────────────────────
svc_panels = [
    ts_panel("CPU Usage by Service (Deployment)", [
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", container!="", container!="POD"}}[$interval])) by (pod) * on(pod) group_left(owner_name) label_replace(kube_pod_owner{{namespace="{NS}", owner_kind="ReplicaSet"}}, "pod", "$1", "pod", "(.*)")', "legend": "{{owner_name}}"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"irmas-.*", container!="", container!="POD"}}[$interval])) by (pod)', "legend": "{{pod}}"}
    ], "short", 1, w=12, x=0, desc="Aggregate CPU usage per deployment/service"),
    ts_panel("Memory Usage by Service (Deployment)", [
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"irmas-.*", container!="", container!="POD"}}) by (pod)', "legend": "{{pod}}"},
    ], "bytes", 1, w=12, x=12, desc="Aggregate memory usage per deployment/service"),
    ts_panel("IRMAS Services — CPU Breakdown", [
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"irmas-cmservice.*", container!=""}}[$interval]))', "legend": "cmservice"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"irmas-fmservice.*", container!=""}}[$interval]))', "legend": "fmservice"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"irmas-pmservice.*", container!=""}}[$interval]))', "legend": "pmservice"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"irmas-guiservice.*", container!=""}}[$interval]))', "legend": "guiservice"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"irmas-managementservice.*", container!=""}}[$interval]))', "legend": "managementservice"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"irmas-nbiservice.*", container!=""}}[$interval]))', "legend": "nbiservice"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"irmas-netconfservice.*", container!=""}}[$interval]))', "legend": "netconfservice"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"irmas-idmservice.*", container!=""}}[$interval]))', "legend": "idmservice"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"irmas-fileservice.*", container!=""}}[$interval]))', "legend": "fileservice"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"irmas-reportservice.*", container!=""}}[$interval]))', "legend": "reportservice"},
    ], "short", 9, w=12, x=0, desc="Individual IRMAS service CPU usage"),
    ts_panel("IRMAS Services — Memory Breakdown", [
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"irmas-cmservice.*", container!=""}}) ', "legend": "cmservice"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"irmas-fmservice.*", container!=""}}) ', "legend": "fmservice"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"irmas-pmservice.*", container!=""}}) ', "legend": "pmservice"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"irmas-guiservice.*", container!=""}}) ', "legend": "guiservice"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"irmas-managementservice.*", container!=""}}) ', "legend": "managementservice"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"irmas-nbiservice.*", container!=""}}) ', "legend": "nbiservice"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"irmas-netconfservice.*", container!=""}}) ', "legend": "netconfservice"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"irmas-idmservice.*", container!=""}}) ', "legend": "idmservice"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"irmas-fileservice.*", container!=""}}) ', "legend": "fileservice"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"irmas-reportservice.*", container!=""}}) ', "legend": "reportservice"},
    ], "bytes", 9, w=12, x=12, desc="Individual IRMAS service memory usage"),
    ts_panel("Infrastructure Services — CPU", [
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"cassandra-.*", container!=""}}[$interval]))', "legend": "cassandra"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"postgresql-.*", container!=""}}[$interval]))', "legend": "postgresql"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"kafka-.*", container!=""}}[$interval]))', "legend": "kafka"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"keycloak-.*", container!=""}}[$interval]))', "legend": "keycloak"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"nginx-ingress.*", container!=""}}[$interval]))', "legend": "nginx-ingress"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"grafana-.*", container!=""}}[$interval]))', "legend": "grafana"},
        {"expr": f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NS}", pod=~"fluentd-.*", container!=""}}[$interval]))', "legend": "fluentd"},
    ], "short", 17, w=12, x=0, desc="Infrastructure and middleware CPU usage"),
    ts_panel("Infrastructure Services — Memory", [
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"cassandra-.*", container!=""}})', "legend": "cassandra"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"postgresql-.*", container!=""}})', "legend": "postgresql"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"kafka-.*", container!=""}})', "legend": "kafka"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"keycloak-.*", container!=""}})', "legend": "keycloak"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"nginx-ingress.*", container!=""}})', "legend": "nginx-ingress"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"grafana-.*", container!=""}})', "legend": "grafana"},
        {"expr": f'sum(container_memory_working_set_bytes{{namespace="{NS}", pod=~"fluentd-.*", container!=""}})', "legend": "fluentd"},
    ], "bytes", 17, w=12, x=12, desc="Infrastructure and middleware memory usage"),
]

# ── LOGGING / FLUENTD ────────────────────────────────────────────────────────
log_panels = [
    ts_panel("Fluentd — Log Records Output Rate", [
        {"expr": f'sum(rate(fluentd_output_status_num_records_total{{namespace="{NS}"}}[$interval])) by (hostname)', "legend": "{{hostname}}"},
        {"expr": f'sum(rate(fluentd_output_status_num_records_total{{namespace="{NS}"}}[$interval]))', "legend": "total"}
    ], "ops", 1, w=12, x=0, desc="Rate of log records emitted by Fluentd"),
    ts_panel("Fluentd — Buffer Queue Length", [
        {"expr": f'fluentd_output_status_buffer_queue_length{{namespace="{NS}"}}', "legend": "{{hostname}}-{{plugin_id}}"}
    ], "short", 1, w=12, x=12, desc="Buffer queue length — high values indicate output bottleneck"),
    ts_panel("Fluentd — Retry Count", [
        {"expr": f'increase(fluentd_output_status_retry_count{{namespace="{NS}"}}[$interval])', "legend": "{{hostname}}-{{plugin_id}}"}
    ], "short", 9, w=12, x=0, desc="Output retry count — sustained retries indicate destination issues"),
    ts_panel("Fluentd — Emit Records vs Flush Time", [
        {"expr": f'rate(fluentd_output_status_emit_records{{namespace="{NS}"}}[$interval])', "legend": "emit: {{hostname}}"},
        {"expr": f'fluentd_output_status_flush_time_count{{namespace="{NS}"}}', "legend": "flush: {{hostname}}"}
    ], "short", 9, w=12, x=12, desc="Emit rate and flush time tracking"),
    ts_panel("Fluentd — Buffer Total Bytes", [
        {"expr": f'fluentd_output_status_buffer_total_bytes{{namespace="{NS}"}}', "legend": "{{hostname}}-{{plugin_id}}"}
    ], "bytes", 17, w=12, x=0, desc="Total buffer size in bytes"),
    ts_panel("Container Log Generation (stderr + stdout)", [
        {"expr": f'sum(rate(container_log_logged_bytes_total{{namespace="{NS}", pod=~"{POD}"}}[$interval])) by (pod)', "legend": "{{pod}}"}
    ], "Bps", 17, w=12, x=12, desc="Container log output rate by pod (if metric available)"),
]

# ── ASSEMBLE DASHBOARD ──────────────────────────────────────────────────────
panels = []
# Overview (always visible)
panels.extend(overview)
y = 9
# Collapsible rows
sections = [
    ("📊 CPU Usage", cpu_panels),
    ("🧠 Memory Usage", mem_panels),
    ("💾 Disk Usage", disk_panels),
    ("🗄️ Databases (PostgreSQL / Cassandra / Kafka)", db_panels),
    ("🔲 Pods Health & Status", pod_panels),
    ("⚙️ Per Service Breakdown", svc_panels),
    ("📝 Logging & Fluentd", log_panels),
]
for title, section_panels in sections:
    panels.append(row_panel(title, y, collapsed=True, panels=section_panels))
    y += 1

dashboard = {
    "id": None,
    "uid": "ems5g-scalability-500cells",
    "title": "EMS5G — Scalability & Capacity Dashboard (500 Cells)",
    "description": "Comprehensive monitoring dashboard for EMS5G Non-Multi-Tenant scalability testing up to 500 cells. Tracks CPU, Memory, Disk, Databases, Pod health, per-service metrics, and Fluentd logging across all services.",
    "tags": ["ems5g", "scalability", "capacity", "500-cells", "kubernetes", "prometheus"],
    "timezone": "browser",
    "schemaVersion": 39,
    "version": 1,
    "refresh": "30s",
    "editable": True,
    "fiscalYearStartMonth": 0,
    "graphTooltip": 1,
    "style": "dark",
    "time": {"from": "now-6h", "to": "now"},
    "timepicker": {
        "refresh_intervals": ["5s","10s","30s","1m","5m","15m","30m","1h","2h","1d"],
        "time_options": ["5m","15m","1h","6h","12h","24h","2d","7d","30d"]
    },
    "templating": templating,
    "annotations": {"list": [
        {"builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"},
         "enable": True, "hide": True, "iconColor": "rgba(0, 211, 255, 1)",
         "name": "Annotations & Alerts", "type": "dashboard"}
    ]},
    "panels": panels,
    "links": [
        {"title": "Node Exporter Full", "type": "link", "url": "/d/rYdddlPWk/node-exporter-full",
         "icon": "external link", "targetBlank": True, "tooltip": "Full Node Exporter Dashboard"},
        {"title": "Kubernetes Cluster", "type": "link", "url": "/d/6417/kubernetes-cluster-monitoring",
         "icon": "external link", "targetBlank": True, "tooltip": "K8s Cluster Overview"},
    ],
    "__inputs": [{"name": "DS_PROMETHEUS", "label": "Prometheus", "description": "",
                  "type": "datasource", "pluginId": "prometheus", "pluginName": "Prometheus"}],
    "__requires": [
        {"type": "grafana", "id": "grafana", "name": "Grafana", "version": "9.0.0"},
        {"type": "datasource", "id": "prometheus", "name": "Prometheus", "version": "1.0.0"},
        {"type": "panel", "id": "timeseries", "name": "Time series", "version": ""},
        {"type": "panel", "id": "stat", "name": "Stat", "version": ""},
        {"type": "panel", "id": "gauge", "name": "Gauge", "version": ""},
        {"type": "panel", "id": "bargauge", "name": "Bar gauge", "version": ""},
        {"type": "panel", "id": "table", "name": "Table", "version": ""}
    ]
}

# Write output
with open("/Users/ankit/dashboard-grafana/ems5g-scalability-dashboard.json", "w") as f:
    json.dump(dashboard, f, indent=2)

print("✅ Dashboard JSON generated: ems5g-scalability-dashboard.json")
print(f"   Total panels: {_pid}")
print(f"   Sections: {len(sections)}")
print(f"   Template variables: {len(templating['list'])}")
