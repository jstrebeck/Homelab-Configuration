#!/usr/bin/env python3
"""Generates homelab-overview.json. Edit here, then:

    python3 homelab-overview.py > homelab-overview.json
"""
import json
DS = {"type": "prometheus", "uid": "${datasource}"}
panels = []
pid = [0]
def nid():
    pid[0] += 1
    return pid[0]

def stat(title, expr, x, w, unit="none", mappings=None, thresholds=None, desc="", decimals=None, legend=""):
    p = {
        "type": "stat", "title": title, "description": desc, "id": nid(), "datasource": DS,
        "gridPos": {"h": 4, "w": w, "x": x, "y": 0},
        "targets": [{"refId": "A", "expr": expr, "instant": True, "legendFormat": legend}],
        "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                    "colorMode": "background" if thresholds else "none", "graphMode": "none",
                    "textMode": "value", "justifyMode": "center", "orientation": "auto"},
        "fieldConfig": {"defaults": {"unit": unit, "mappings": mappings or [],
                        "thresholds": {"mode": "absolute", "steps": thresholds or [{"color": "text", "value": None}]},
                        "color": {"mode": "thresholds"}}, "overrides": []},
    }
    if decimals is not None:
        p["fieldConfig"]["defaults"]["decimals"] = decimals
    return p

def ts(title, targets, x, y, w, unit, desc="", maxv=None, stack=False):
    d = {"unit": unit, "min": 0,
         "custom": {"lineWidth": 2, "fillOpacity": 10 if stack else 0, "showPoints": "never",
                    "spanNulls": True, "axisBorderShow": False, "gradientMode": "none",
                    "stacking": {"mode": "normal" if stack else "none", "group": "A"}},
         "color": {"mode": "palette-classic"}}
    if maxv is not None:
        d["max"] = maxv
    return {"type": "timeseries", "title": title, "description": desc, "id": nid(), "datasource": DS,
            "gridPos": {"h": 8, "w": w, "x": x, "y": y},
            "targets": [{"refId": chr(65 + i), "expr": e, "legendFormat": l} for i, (e, l) in enumerate(targets)],
            "options": {"legend": {"displayMode": "table", "placement": "bottom", "showLegend": True,
                                   "calcs": ["lastNotNull", "max"]},
                        "tooltip": {"mode": "multi", "sort": "desc"}},
            "fieldConfig": {"defaults": d, "overrides": []}}

def row(title, y):
    return {"type": "row", "title": title, "id": nid(), "collapsed": False,
            "gridPos": {"h": 1, "w": 24, "x": 0, "y": y}, "panels": []}

GOOD, WARN, BAD = "green", "orange", "red"

# --- headline tiles
panels += [
    stat("Nodes ready", 'sum(kube_node_status_condition{condition="Ready",status="true"}) or vector(0)', 0, 4,
         thresholds=[{"color": BAD, "value": None}, {"color": GOOD, "value": 4}],
         desc="Nodes reporting Ready. The cluster has 4."),
    stat("Ceph health", "max(ceph_health_status)", 4, 4,
         mappings=[{"type": "value", "options": {
             "0": {"text": "HEALTH_OK", "color": GOOD, "index": 0},
             "1": {"text": "HEALTH_WARN", "color": WARN, "index": 1},
             "2": {"text": "HEALTH_ERR", "color": BAD, "index": 2}}},
             {"type": "special", "options": {"match": "null", "result": {"text": "No data", "color": "text", "index": 3}}}],
         thresholds=[{"color": GOOD, "value": None}, {"color": WARN, "value": 1}, {"color": BAD, "value": 2}],
         desc="Overall Ceph status from the mgr. See the Ceph Cluster dashboard for the reason."),
    stat("Ceph capacity used", "sum(ceph_cluster_total_used_bytes) / sum(ceph_cluster_total_bytes)", 8, 4,
         unit="percentunit", decimals=1,
         thresholds=[{"color": GOOD, "value": None}, {"color": WARN, "value": 0.7}, {"color": BAD, "value": 0.85}],
         desc="Raw capacity used across all OSDs (3x replicated, so usable space is about a third)."),
    stat("Argo CD apps synced",
         'count(argocd_app_info{sync_status="Synced"}) or vector(0)', 12, 4,
         desc="Applications whose live state matches Git."),
    stat("Argo CD apps not healthy",
         'count(argocd_app_info{health_status!="Healthy"}) or vector(0)', 16, 4,
         thresholds=[{"color": GOOD, "value": None}, {"color": WARN, "value": 1}],
         desc="Applications reporting Degraded, Progressing, Missing or Unknown."),
    stat("Alerts firing",
         'count(ALERTS{alertstate="firing",severity=~"warning|critical"}) or vector(0)', 20, 4,
         thresholds=[{"color": GOOD, "value": None}, {"color": WARN, "value": 1}],
         desc="Warning and critical alerts currently firing (Watchdog and info alerts excluded)."),
]

y = 4
panels.append(row("Nodes", y)); y += 1
panels += [
    ts("CPU used by node",
       [('(1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[$__rate_interval]))) * on (instance) group_left (nodename) node_uname_info', "{{nodename}}")],
       0, y, 12, "percentunit", maxv=1, desc="Share of all cores busy, per node."),
    ts("Memory used by node",
       [("(1 - sum by (instance) (node_memory_MemAvailable_bytes) / sum by (instance) (node_memory_MemTotal_bytes)) * on (instance) group_left (nodename) node_uname_info", "{{nodename}}")],
       12, y, 12, "percentunit", maxv=1, desc="Memory not available to new workloads, per node."),
]
y += 8
panels.append(row("Storage (Rook-Ceph)", y)); y += 1
panels += [
    ts("Ceph raw capacity used",
       [("sum(ceph_cluster_total_used_bytes)", "used"), ("sum(ceph_cluster_total_bytes)", "total")],
       0, y, 8, "bytes"),
    ts("Ceph client throughput",
       [("sum(rate(ceph_pool_rd_bytes[$__rate_interval]))", "read"),
        ("sum(rate(ceph_pool_wr_bytes[$__rate_interval]))", "write")],
       8, y, 8, "Bps"),
    ts("Ceph client IOPS",
       [("sum(rate(ceph_pool_rd[$__rate_interval]))", "read"),
        ("sum(rate(ceph_pool_wr[$__rate_interval]))", "write")],
       16, y, 8, "iops"),
]
y += 8
panels.append(row("Delivery and workloads", y)); y += 1

def table(title, expr, x, w, fields, mappings_by_field=None, desc=""):
    overrides = []
    for f, m in (mappings_by_field or {}).items():
        overrides.append({"matcher": {"id": "byName", "options": f}, "properties": [
            {"id": "mappings", "value": m},
            {"id": "custom.cellOptions", "value": {"type": "color-text"}}]})
    return {"type": "table", "title": title, "description": desc, "id": nid(), "datasource": DS,
            "gridPos": {"h": 10, "w": w, "x": x, "y": y},
            "targets": [{"refId": "A", "expr": expr, "instant": True, "format": "table"}],
            "transformations": [{"id": "organize", "options": {
                "includeByName": {f: True for f in fields},
                "indexByName": {f: i for i, f in enumerate(fields)}}}],
            "options": {"showHeader": True, "cellHeight": "sm",
                        "sortBy": [{"displayName": fields[0], "desc": False}]},
            "fieldConfig": {"defaults": {"custom": {"align": "left"}}, "overrides": overrides}}

status_map = lambda good, warn, bad: [{"type": "value", "options": {
    **{k: {"color": GOOD, "index": 0} for k in good},
    **{k: {"color": WARN, "index": 1} for k in warn},
    **{k: {"color": BAD, "index": 2} for k in bad}}}]

panels += [
    table("Argo CD applications", "argocd_app_info", 0, 12,
          ["name", "project", "sync_status", "health_status"],
          {"sync_status": status_map(["Synced"], ["OutOfSync", "Unknown"], []),
           "health_status": status_map(["Healthy"], ["Progressing", "Suspended", "Missing", "Unknown"], ["Degraded"])},
          desc="Every Application Argo CD manages, from argocd_app_info."),
    table("Workloads with unavailable replicas",
          "kube_deployment_status_replicas_unavailable > 0 or kube_statefulset_status_replicas - kube_statefulset_status_replicas_ready > 0",
          12, 12, ["namespace", "deployment", "statefulset", "Value"],
          desc="Deployments and StatefulSets missing ready replicas. Empty is good."),
]

dash = {
    "uid": "homelab-overview", "title": "Homelab overview", "tags": ["homelab"],
    "timezone": "browser", "schemaVersion": 39, "version": 1, "editable": True,
    "refresh": "1m", "time": {"from": "now-24h", "to": "now"},
    "description": "Cluster, storage and GitOps health at a glance.",
    "templating": {"list": [{"name": "datasource", "label": "Data source", "type": "datasource",
                             "query": "prometheus", "current": {"text": "Prometheus", "value": "prometheus"},
                             "hide": 0}]},
    "annotations": {"list": []}, "links": [], "panels": panels,
}
print(json.dumps(dash, indent=2))
