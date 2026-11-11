"""Build the public API reference from zoded's api/openapi.yaml.

    uv run --with pyyaml scripts/public_openapi.py ../zoded/api/openapi.yaml

Writes api-reference/openapi.yaml (only the routes an API key uses, against
https://api.zode.dev) and replaces the endpoint groups of the "API reference"
tab in docs.json. Run it again whenever the spec in zoded changes.
"""

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# (group, [(METHOD, path, sidebar title)]) in the order the sidebar shows them.
GROUPS = [
    ("Sandboxes", [
        ("GET", "/v1/sandboxes", "List sandboxes"),
        ("POST", "/v1/sandboxes", "Create a sandbox"),
        ("GET", "/v1/sandboxes/{id}", "Get a sandbox"),
        ("DELETE", "/v1/sandboxes/{id}", "Delete a sandbox"),
        ("POST", "/v1/sandboxes/{id}/fork", "Fork a sandbox"),
        ("POST", "/v1/sandboxes/{id}/stop", "Stop a sandbox"),
        ("POST", "/v1/sandboxes/{id}/start", "Start a sandbox"),
        ("GET", "/v1/concurrency", "Running sandboxes"),
    ]),
    ("Commands", [
        ("POST", "/v1/sandboxes/{id}/exec", "Run a command"),
        ("GET", "/v1/sandboxes/{id}/attach", "Open a session (WebSocket)"),
    ]),
    ("Browser and desktop", [
        ("PATCH", "/v1/sandboxes/{id}/features", "Switch browser or desktop"),
        ("GET", "/v1/sandboxes/{id}/browser", "Get a CDP endpoint"),
        ("GET", "/v1/sandboxes/{id}/desktop", "Get the desktop size"),
        ("GET", "/v1/sandboxes/{id}/desktop/screenshot", "Take a screenshot"),
        ("POST", "/v1/sandboxes/{id}/desktop/actions", "Click, type, press keys"),
        ("POST", "/v1/sandboxes/{id}/desktop/session", "Get a live view URL"),
    ]),
    ("Snapshots", [
        ("GET", "/v1/snapshots", "List snapshots"),
        ("POST", "/v1/snapshots", "Take a snapshot"),
        ("POST", "/v1/snapshots/{id}/restore", "Restore a snapshot"),
        ("DELETE", "/v1/snapshots/{id}", "Delete a snapshot"),
    ]),
    ("Images", [
        ("GET", "/v1/images", "List images"),
        ("POST", "/v1/images", "Build an image"),
        ("GET", "/v1/images/{id}", "Get an image"),
        ("GET", "/v1/images/{id}/logs", "Read a build log"),
        ("DELETE", "/v1/images/{id}", "Delete an image"),
    ]),
    ("Environments", [
        ("GET", "/v1/environments", "List environments"),
        ("POST", "/v1/environments", "Create an environment"),
        ("DELETE", "/v1/environments/{id}", "Delete an environment"),
        ("GET", "/v1/environments/{id}/variables", "List variables"),
        ("PUT", "/v1/environments/{id}/variables/{name}", "Set a variable"),
        ("DELETE", "/v1/environments/{id}/variables/{name}", "Delete a variable"),
        ("GET", "/v1/environments/{id}/secrets", "List secrets"),
        ("PUT", "/v1/environments/{id}/secrets/{name}", "Set a secret"),
        ("DELETE", "/v1/environments/{id}/secrets/{name}", "Delete a secret"),
    ]),
    ("Flight recorder", [
        ("GET", "/v1/sandboxes/{id}/timeline", "Read the timeline"),
        ("GET", "/v1/sandboxes/{id}/stats", "Summarize a window"),
    ]),
    ("Attestation", [
        ("GET", "/v1/sandboxes/{id}/attestation", "Attest a sandbox's host"),
        ("GET", "/v1/regions/{region}/attestation", "Attest a region"),
    ]),
    ("Agents", [
        ("GET", "/v1/agents", "List harnesses and keys"),
        ("POST", "/v1/agents/credentials", "Connect a provider key"),
        ("DELETE", "/v1/agents/credentials/{provider}", "Disconnect a provider key"),
        ("PATCH", "/v1/agents/settings", "Set default harness and models"),
    ]),
    ("Proxying", [
        ("GET", "/v1/proxying", "Get keys, breaker and caps"),
        ("POST", "/v1/proxying/keys", "Add a workspace key"),
        ("DELETE", "/v1/proxying/keys/{key}", "Remove a workspace key"),
        ("POST", "/v1/proxying/keys/order", "Set failover order"),
        ("PATCH", "/v1/proxying/settings", "Change breaker and caps"),
    ]),
    ("Webhooks", [
        ("GET", "/v1/webhooks", "List endpoints"),
        ("POST", "/v1/webhooks", "Add an endpoint"),
        ("GET", "/v1/webhooks/{id}", "Get an endpoint"),
        ("PATCH", "/v1/webhooks/{id}", "Change an endpoint"),
        ("DELETE", "/v1/webhooks/{id}", "Remove an endpoint"),
        ("POST", "/v1/webhooks/{id}/rotate-secret", "Rotate the signing secret"),
        ("POST", "/v1/webhooks/{id}/test", "Send a test event"),
        ("GET", "/v1/webhooks/{id}/deliveries", "List deliveries"),
        ("POST", "/v1/webhooks/{id}/deliveries/{delivery_id}/resend", "Resend a delivery"),
    ]),
    ("OpenTelemetry", [
        ("GET", "/v1/otel", "Get export settings"),
        ("PATCH", "/v1/otel", "Change export settings"),
        ("DELETE", "/v1/otel", "Stop export"),
        ("POST", "/v1/otel/test", "Send a test record"),
    ]),
    ("Alerts", [
        ("GET", "/v1/alerts", "Get alert settings"),
        ("PATCH", "/v1/alerts", "Set the time zone"),
        ("GET", "/v1/alerts/channels", "List channels"),
        ("POST", "/v1/alerts/channels", "Add a channel"),
        ("PATCH", "/v1/alerts/channels/{id}", "Change a channel"),
        ("DELETE", "/v1/alerts/channels/{id}", "Delete a channel"),
        ("POST", "/v1/alerts/channels/{id}/test", "Test a channel"),
        ("GET", "/v1/alerts/rules", "List rules"),
        ("POST", "/v1/alerts/rules", "Add a rule"),
        ("PATCH", "/v1/alerts/rules/{id}", "Change a rule"),
        ("DELETE", "/v1/alerts/rules/{id}", "Delete a rule"),
        ("GET", "/v1/alerts/deliveries", "List deliveries"),
    ]),
    ("CI", [
        ("GET", "/v1/ci", "Get CI setup"),
        ("GET", "/v1/ci/jobs", "List CI jobs"),
        ("PATCH", "/v1/ci/settings", "Set the monthly cap"),
    ]),
    ("Usage and billing", [
        ("GET", "/v1/usage", "Get usage"),
        ("GET", "/v1/usage.csv", "Export usage as CSV"),
        ("GET", "/v1/billing", "Get billing"),
        ("PATCH", "/v1/billing", "Change caps and billing"),
        ("GET", "/v1/billing/invoices", "List invoices"),
    ]),
    ("Workspace", [
        ("GET", "/v1/whoami", "Who am I"),
        ("GET", "/v1/org", "Get the workspace"),
        ("PATCH", "/v1/org", "Change the workspace"),
        ("GET", "/v1/members", "List members"),
        ("PATCH", "/v1/members/{id}", "Change a member's role"),
        ("DELETE", "/v1/members/{id}", "Remove a member"),
        ("GET", "/v1/invites", "List invites"),
        ("POST", "/v1/invites", "Invite someone"),
        ("POST", "/v1/invites/{id}/resend", "Resend an invite"),
        ("DELETE", "/v1/invites/{id}", "Revoke an invite"),
        ("GET", "/v1/tokens", "List API keys"),
        ("POST", "/v1/tokens", "Create an API key"),
        ("DELETE", "/v1/tokens/{id}", "Revoke an API key"),
        ("GET", "/v1/audit", "Read the audit log"),
        ("GET", "/v1/audit.csv", "Export the audit log"),
    ]),
    ("Platform", [
        ("GET", "/v1/status", "Service status"),
    ]),
]

# Parenthesised pointers into the zoded repo mean nothing to a reader.
SEE_REF = re.compile(r"\s*[Ss]ee `?(?:docs|internal|cmd)/[^\s`]+`?(?:\.(?=\s|$))?")
REPO_REF = re.compile(r"\s*\((?:see |contract: )?`?(?:docs|internal|cmd)/[^)]*\)")
INLINE_REF = re.compile(r"`?(?:docs|internal)/[A-Za-z0-9_./-]+`?")
METHODS = ("get", "post", "put", "patch", "delete")


def clean(text):
    if not isinstance(text, str):
        return text
    text = SEE_REF.sub("", text)
    text = REPO_REF.sub("", text)
    text = INLINE_REF.sub("", text)
    text = text.replace("The WebRTC desktop is on.", "The Linux desktop is on.")
    # API keys carry their workspace; the X-Zode-Org header is for console sessions.
    text = text.replace("`org_required` (session without X-Zode-Org), or a bad request.", "A bad request.")
    text = text.replace("`org_required` (session without X-Zode-Org).", "A bad request.")
    text = text.replace("`org_required`, or a bad request.", "A bad request.")
    text = text.replace(" or `org_required`", "")
    text = text.replace(" (an older zoded)", "")
    # One of the sizes is named `default`, and it is not what an empty body gets.
    text = text.replace("An empty body creates a default sandbox.", "An empty body creates a `small` sandbox.")
    text = re.sub(r"\s*\(zoded[^)]*\)", "", text)
    text = text.replace("zoded", "the control plane")
    return text


def refs(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str):
                out.add(v)
            else:
                refs(v, out)
    elif isinstance(node, list):
        for v in node:
            refs(v, out)


SESSION_ONLY = {"#/components/parameters/OrgHeader", "#/components/parameters/CSRFHeader"}


def drop_org_header(params):
    return [p for p in params if p.get("$ref") not in SESSION_ONLY]


def main(src):
    spec = yaml.safe_load(Path(src).read_text())
    keep = {(m.lower(), p): (group, title) for group, ops in GROUPS for m, p, title in ops}

    paths = {}
    for path, item in spec["paths"].items():
        out = {}
        for key, val in item.items():
            if key == "parameters":
                continue
            if key in METHODS and (key, path) in keep:
                group, title = keep[(key, path)]
                op = dict(val)
                summary = op.get("summary", "")
                desc = op.get("description", "")
                op["summary"] = title
                if summary.rstrip(".").lower() == title.lower():
                    summary = ""
                op["description"] = clean((summary + ".\n\n" + desc).strip() if summary else desc)
                op["tags"] = [group]
                if "parameters" in op:
                    op["parameters"] = drop_org_header(op["parameters"])
                    if not op["parameters"]:
                        del op["parameters"]
                if op.get("security") not in ([], None):
                    op["security"] = [{"bearerAuth": []}]
                out[key] = op
        if out:
            if "parameters" in item:
                params = drop_org_header(item["parameters"])
                if params:
                    out["parameters"] = params
            paths[path] = out

    missing = [f"{m} {p}" for (m, p) in keep if p not in paths or m not in paths[p]]
    if missing:
        sys.exit("not in the spec: " + ", ".join(missing))

    comps = spec["components"]
    schemes = comps.get("securitySchemes", {})
    comps["securitySchemes"] = {"bearerAuth": schemes["bearerAuth"]}
    comps["securitySchemes"]["bearerAuth"]["description"] = (
        "An API key (`zode_tok_...`). Create one in the console under Settings, API keys, or with `zode login`."
    )
    for name in ("OrgHeader", "CSRFHeader"):
        comps.get("parameters", {}).pop(name, None)

    # The spec describes any server's regions; the hosted API has one.
    for schema in ("CreateSandboxRequest", "CreateImageRequest"):
        props = comps["schemas"].get(schema, {}).get("properties", {})
        if "region" in props:
            props["region"] = {"type": "string", "enum": ["eu-central"], "default": "eu-central",
                               "description": "`eu-central` is the only region today; more will be added."}

    # Keep only the components the public routes reach.
    used, todo = set(), set()
    refs(paths, todo)
    while todo:
        r = todo.pop()
        if r in used:
            continue
        used.add(r)
        _, _, kind, name = r.split("/", 3)
        refs(comps[kind][name], todo)
    for kind in ("schemas", "parameters", "responses"):
        if kind in comps:
            comps[kind] = {k: v for k, v in comps[kind].items() if f"#/components/{kind}/{k}" in used}

    def walk(node):
        if isinstance(node, dict):
            return {k: (clean(v) if k == "description" else walk(v)) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    public = {
        "openapi": spec["openapi"],
        "info": {
            "title": "Zode API",
            "version": spec["info"]["version"],
            "description": "Sandboxes for coding agents. Every route takes an API key as a bearer token.",
        },
        "servers": [{"url": "https://api.zode.dev"}],
        "security": [{"bearerAuth": []}],
        "tags": [{"name": g} for g, _ in GROUPS],
        "paths": walk(paths),
        "components": walk(comps),
    }
    out = ROOT / "api-reference" / "openapi.yaml"
    out.write_text(yaml.safe_dump(public, sort_keys=False, allow_unicode=True, width=100))

    docs = json.loads((ROOT / "docs.json").read_text())
    for tab in docs["navigation"]["tabs"]:
        if tab["tab"] == "API reference":
            intro = [g for g in tab["groups"] if "openapi" not in g]
            tab["groups"] = intro + [
                {"group": g, "openapi": "api-reference/openapi.yaml", "pages": [f"{m} {p}" for m, p, _ in ops]}
                for g, ops in GROUPS
            ]
    (ROOT / "docs.json").write_text(json.dumps(docs, indent=2) + "\n")
    print(f"{sum(len(o) for _, o in GROUPS)} operations, {len(paths)} paths -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../zoded/api/openapi.yaml")
