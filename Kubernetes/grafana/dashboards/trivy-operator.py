#!/usr/bin/env python3
"""Generates trivy-operator.json from Trivy Operator's metrics. Edit here, then:

    python3 trivy-operator.py > trivy-operator.json

Vulnerability metrics are per workload container, so an image run by two
workloads is reported twice. Totals take max() per image first to count each
image once.
"""
import json
DS = {"type": "prometheus", "uid": "${datasource}"}
panels = []
pid = [0]
def nid():
    pid[0] += 1
    return pid[0]

GOOD, WARN, BAD = "green", "orange", "red"
ZERO_GOOD = lambda bad=BAD: [{"color": GOOD, "value": None}, {"color": bad, "value": 1}]

def stat(title, expr, x, w, thresholds=None, desc=""):
    return {
        "type": "stat", "title": title, "description": desc, "id": nid(), "datasource": DS,
        "gridPos": {"h": 4, "w": w, "x": x, "y": 0},
        "targets": [{"refId": "A", "expr": expr, "instant": True}],
        "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                    "colorMode": "background" if thresholds else "none", "graphMode": "none",
                    "textMode": "value", "justifyMode": "center", "orientation": "auto"},
        "fieldConfig": {"defaults": {"unit": "none",
                        "thresholds": {"mode": "absolute", "steps": thresholds or [{"color": "text", "value": None}]},
                        "color": {"mode": "thresholds"}}, "overrides": []},
    }

def ts(title, targets, x, y, w, desc=""):
    return {"type": "timeseries", "title": title, "description": desc, "id": nid(), "datasource": DS,
            "gridPos": {"h": 8, "w": w, "x": x, "y": y},
            "targets": [{"refId": chr(65 + i), "expr": e, "legendFormat": l} for i, (e, l) in enumerate(targets)],
            "options": {"legend": {"displayMode": "table", "placement": "bottom", "showLegend": True,
                                   "calcs": ["lastNotNull", "max"]},
                        "tooltip": {"mode": "multi", "sort": "desc"}},
            "fieldConfig": {"defaults": {"unit": "none", "min": 0, "decimals": 0,
                            "custom": {"lineWidth": 2, "fillOpacity": 0, "showPoints": "never",
                                       "spanNulls": True, "axisBorderShow": False},
                            "color": {"mode": "palette-classic"}}, "overrides": []}}

def table(title, targets, x, y, w, fields, rename=None, sort=None, colored=(), h=10, desc=""):
    """targets: [(expr, value column name)]. Several targets are merged on their labels."""
    overrides = [{"matcher": {"id": "byName", "options": f}, "properties": [
                     {"id": "custom.cellOptions", "value": {"type": "color-background", "mode": "basic"}},
                     {"id": "thresholds", "value": {"mode": "absolute", "steps": ZERO_GOOD(c)}}]}
                 for f, c in colored]
    rename = dict(rename or {})
    trans = []
    if len(targets) > 1:
        trans.append({"id": "merge", "options": {}})
    for i, (_, name) in enumerate(targets):
        rename[f"Value #{chr(65 + i)}" if len(targets) > 1 else "Value"] = name
    trans.append({"id": "organize", "options": {
        "includeByName": {f: True for f in fields + [k for k in rename if rename[k] in fields]},
        "renameByName": rename,
        "indexByName": {f: i for i, f in enumerate(fields)}}})
    return {"type": "table", "title": title, "description": desc, "id": nid(), "datasource": DS,
            "gridPos": {"h": h, "w": w, "x": x, "y": y},
            "targets": [{"refId": chr(65 + i), "expr": e, "instant": True, "format": "table"}
                        for i, (e, _) in enumerate(targets)],
            "transformations": trans,
            "options": {"showHeader": True, "cellHeight": "sm",
                        "sortBy": [{"displayName": sort or fields[-1], "desc": True}]},
            "fieldConfig": {"defaults": {"custom": {"align": "left"}}, "overrides": overrides}}

def row(title, y):
    return {"type": "row", "title": title, "id": nid(), "collapsed": False,
            "gridPos": {"h": 1, "w": 24, "x": 0, "y": y}, "panels": []}

IMG = "image_registry, image_repository, image_tag"
def vulns(sev, by=IMG):
    """Vulnerabilities of one severity, one series per image (deduplicated across workloads)."""
    return f'max by ({by}) (trivy_image_vulnerabilities{{severity="{sev}"}})'

# --- headline tiles
panels += [
    stat("Critical vulnerabilities", f"sum({vulns('Critical')}) or vector(0)", 0, 4, ZERO_GOOD(),
         desc="Critical CVEs across all running images, each image counted once."),
    stat("High vulnerabilities", f"sum({vulns('High')}) or vector(0)", 4, 4, ZERO_GOOD(WARN),
         desc="High CVEs across all running images, each image counted once."),
    stat("Images with a critical CVE", f"count({vulns('Critical')} > 0) or vector(0)", 8, 4, ZERO_GOOD(),
         desc="Distinct running images with at least one critical CVE."),
    stat("Fixable critical CVEs",
         f'count(max by (vuln_id, {IMG}) (trivy_vulnerability_id{{severity="Critical", fixed_version!=""}})) or vector(0)',
         12, 4, ZERO_GOOD(),
         desc="Critical CVEs that have a fixed package version upstream: an image upgrade or rebuild clears them."),
    stat("Exposed secrets", "sum(max by (" + IMG + ") (trivy_image_exposedsecrets)) or vector(0)", 16, 4, ZERO_GOOD(),
         desc="Credentials, keys or tokens found baked into image layers."),
    stat("Critical misconfigurations",
         'sum(trivy_resource_configaudits{severity="Critical"}) or vector(0)', 20, 4, ZERO_GOOD(),
         desc="Critical config-audit findings on workloads, Services and other resources."),
]

y = 4
panels.append(row("Vulnerabilities", y)); y += 1
panels += [
    ts("Vulnerabilities over time",
       [(f"sum({vulns('Critical')})", "critical"), (f"sum({vulns('High')})", "high"),
        (f"sum({vulns('Medium')})", "medium")],
       0, y, 12, desc="Each image counted once. Drops follow image upgrades; jumps follow new CVE disclosures."),
    ts("Critical and high by namespace",
       [('sum by (namespace) (trivy_image_vulnerabilities{severity=~"Critical|High"})', "{{namespace}}")],
       12, y, 12, desc="Per workload container, so an image run in several places counts in each namespace."),
]
y += 8
panels.append(table(
    "Images by vulnerability count",
    [(vulns(s, "namespace, " + IMG), s) for s in ("Critical", "High", "Medium", "Low")],
    0, y, 24, ["namespace", "image_registry", "image_repository", "image_tag", "Critical", "High", "Medium", "Low"],
    rename={"image_registry": "registry", "image_repository": "image", "image_tag": "tag"},
    sort="Critical", colored=[("Critical", BAD), ("High", WARN)], h=12,
    desc="Every running image and its CVE count by severity. Upgrade from the top."))
y += 12
panels.append(table(
    "Critical and high CVEs",
    [('max by (vuln_id, severity, vuln_title, resource, installed_version, fixed_version, image_repository, image_tag)'
      ' (trivy_vulnerability_id{severity=~"Critical|High"})', "score")],
    0, y, 24, ["severity", "vuln_id", "resource", "installed_version", "fixed_version",
               "image_repository", "image_tag", "vuln_title"],
    rename={"resource": "package", "installed_version": "installed", "fixed_version": "fixed in",
            "image_repository": "image", "image_tag": "tag", "vuln_title": "title"},
    sort="severity", h=12,
    desc="One row per CVE per image. An empty 'fixed in' means no upstream fix yet."))
y += 12

panels.append(row("Configuration, RBAC and secrets", y)); y += 1
panels += [
    table("Misconfigurations by resource",
          [(f'sum by (namespace, resource_kind, resource_name) (trivy_resource_configaudits{{severity="{s}"}})', s)
           for s in ("Critical", "High", "Medium")],
          0, y, 12, ["namespace", "resource_kind", "resource_name", "Critical", "High", "Medium"],
          rename={"resource_kind": "kind", "resource_name": "name"},
          sort="Critical", colored=[("Critical", BAD), ("High", WARN)],
          desc="Config-audit findings per resource (running as root, no limits, writable root FS, ...). "
               "kubectl get configauditreports -A for details."),
    table("RBAC findings by role",
          [('sum by (namespace, resource_kind, resource_name) (trivy_role_rbacassessments{severity=~"Critical|High"})'
            ' or sum by (resource_kind, resource_name) (trivy_clusterrole_clusterrbacassessments{severity=~"Critical|High"})',
            "critical + high")],
          12, y, 12, ["namespace", "resource_kind", "resource_name", "critical + high"],
          rename={"resource_kind": "kind", "resource_name": "name"}, colored=[("critical + high", WARN)],
          desc="Roles and ClusterRoles granting risky permissions (secrets access, wildcard verbs, exec, ...)."),
]
y += 10
panels.append(table(
    "Exposed secrets by image",
    [("sum by (namespace, " + IMG + ") (trivy_image_exposedsecrets) > 0", "secrets")],
    0, y, 24, ["namespace", "image_registry", "image_repository", "image_tag", "secrets"],
    rename={"image_registry": "registry", "image_repository": "image", "image_tag": "tag"},
    colored=[("secrets", BAD)], h=6,
    desc="Images with credentials in their layers. Empty is good. kubectl get exposedsecretreports -A for details."))

dash = {
    "uid": "trivy-operator", "title": "Trivy Operator", "tags": ["homelab", "security"],
    "timezone": "browser", "schemaVersion": 39, "version": 1, "editable": True,
    "refresh": "5m", "time": {"from": "now-7d", "to": "now"},
    "description": "Vulnerabilities, misconfigurations, RBAC risks and exposed secrets in running workloads.",
    "templating": {"list": [{"name": "datasource", "label": "Data source", "type": "datasource",
                             "query": "prometheus", "current": {"text": "Prometheus", "value": "prometheus"},
                             "hide": 0}]},
    "annotations": {"list": []}, "links": [], "panels": panels,
}
print(json.dumps(dash, indent=2))
