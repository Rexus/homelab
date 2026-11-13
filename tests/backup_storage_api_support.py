"""Loopback API fixture for native kubernetes.core modules; no cluster or mounted storage."""

import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from urllib.parse import urlsplit
import uuid


class BackupStorageAPI:
    resources = {
        "namespaces": ("Namespace", False, "v1"),
        "persistentvolumes": ("PersistentVolume", False, "v1"),
        "persistentvolumeclaims": ("PersistentVolumeClaim", True, "v1"),
        "csidrivers": ("CSIDriver", False, "storage.k8s.io/v1"),
    }

    def __init__(self):
        self.objects = {}
        self.mutations = []
        self.requests = []
        self.put({"apiVersion": "storage.k8s.io/v1", "kind": "CSIDriver",
                  "metadata": {"name": "nfs.csi.k8s.io"}, "spec": {}})
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, body, status=200):
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                path = urlsplit(self.path).path
                fixture.requests.append(("GET", path))
                if path == "/version":
                    return self.reply({"major": "1", "minor": "34", "gitVersion": "v1.34.0"})
                if path == "/api":
                    return self.reply({"apiVersion": "v1", "kind": "APIVersions", "versions": ["v1"]})
                if path == "/apis":
                    version = {"groupVersion": "storage.k8s.io/v1", "version": "v1"}
                    return self.reply({"apiVersion": "v1", "kind": "APIGroupList", "groups": [
                        {"name": "storage.k8s.io", "versions": [version], "preferredVersion": version}]})
                if path in ("/api/v1", "/apis/storage.k8s.io/v1"):
                    api = "v1" if path == "/api/v1" else "storage.k8s.io/v1"
                    return self.reply({"apiVersion": "v1", "kind": "APIResourceList", "groupVersion": api,
                        "resources": [{"name": name, "kind": kind, "namespaced": namespaced,
                                       "verbs": ["get", "list", "create", "patch"]}
                                      for name, (kind, namespaced, group) in fixture.resources.items() if group == api]})
                key = fixture.key(path)
                if key in fixture.objects:
                    return self.reply(fixture.objects[key])
                if key and key[2] is None:
                    kind = fixture.resources[key[0]][0]
                    items = [value for (resource, namespace, _), value in fixture.objects.items()
                             if resource == key[0] and namespace == key[1]]
                    return self.reply({"apiVersion": fixture.resources[key[0]][2], "kind": kind + "List",
                                       "metadata": {"resourceVersion": "1"}, "items": items})
                return self.reply({"apiVersion": "v1", "kind": "Status", "reason": "NotFound",
                                   "message": "fixture resource absent", "code": 404}, 404)

            def do_POST(self):
                fixture.requests.append(("POST", urlsplit(self.path).path))
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fixture.mutations.append(("POST", urlsplit(self.path).path, copy.deepcopy(body)))
                fixture.put(body)
                if body["kind"] == "PersistentVolumeClaim":
                    pv = fixture.objects[("persistentvolumes", "", body["spec"]["volumeName"])]
                    pv["spec"]["claimRef"]["uid"] = body["metadata"]["uid"]
                    pv["status"] = {"phase": "Bound"}
                return self.reply(body, 201)

            def do_PATCH(self):
                fixture.mutations.append(("PATCH", self.path, None))
                return self.reply({"kind": "Status", "code": 405}, 405)

            do_DELETE = do_PATCH
            do_PUT = do_PATCH

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def put(self, obj):
        resource = next(name for name, (kind, _, _) in self.resources.items() if kind == obj["kind"])
        csi = obj.get("spec", {}).get("csi", {})
        if csi.get("readOnly") is False:
            csi.pop("readOnly")  # Native API serialization omits this false default.
        obj["metadata"].setdefault("uid", str(uuid.uuid4()))
        obj["metadata"].setdefault("resourceVersion", "1")
        if obj["kind"] in ("Namespace", "PersistentVolume", "PersistentVolumeClaim"):
            phase = {"Namespace": "Active", "PersistentVolume": "Available", "PersistentVolumeClaim": "Bound"}
            obj.setdefault("status", {"phase": phase[obj["kind"]]})
        self.objects[(resource, obj["metadata"].get("namespace", ""), obj["metadata"]["name"])] = obj

    @staticmethod
    def key(path):
        parts = path.split("/")[3:] if path.startswith("/api/") else path.split("/")[4:]
        namespace = ""
        if len(parts) >= 3 and parts[0] == "namespaces":
            namespace, parts = parts[1], parts[2:]
        return (parts[0], namespace, parts[1] if len(parts) > 1 else None) if parts else None

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def kubeconfig(self):
        return {"apiVersion": "v1", "kind": "Config", "current-context": "offline",
                "clusters": [{"name": "fixture", "cluster": {
                    "server": f"http://127.0.0.1:{self.server.server_port}"}}],
                "contexts": [{"name": "offline", "context": {"cluster": "fixture", "user": "offline"}}],
                "users": [{"name": "offline", "user": {}}]}
