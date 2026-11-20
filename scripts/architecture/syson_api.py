"""SysON 2026.11 snapshot transport; no model merge or destructive operations."""

import io
import json
import uuid
import zipfile
from urllib.parse import urlsplit

import requests


def checked_url(url):
    """Reject credentials before a server or receipt URL can be sent or persisted."""
    try:
        parsed = urlsplit(url)
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("SysON URLs must not contain userinfo")
        if "?" in url or "#" in url:
            raise ValueError("SysON base URLs must not contain a query or fragment")
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.port == 0:
            raise ValueError("Invalid SysON URL")
    except (TypeError, AttributeError, ValueError):
        # Parser exceptions can include the original URL; never echo credential-bearing input.
        raise ValueError("Use an HTTP(S) SysON URL without userinfo, query, or fragment") from None
    return url.rstrip("/")


def objects(value):
    """Walk Sirius JSON objects, keeping persistence IDs distinct from elementId."""
    if isinstance(value, dict):
        if "eClass" in value and "id" in value:
            yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


class SysON:
    def __init__(self, url):
        self.url = checked_url(url)
        self.session = requests.Session()

    def request(self, method, path, **kwargs):
        response = self.session.request(method, self.url + path, timeout=(10, 300), **kwargs)
        response.raise_for_status()
        return response

    def graphql(self, query, variables=None):
        result = self.request("POST", "/api/graphql", json={
            "query": query, "variables": variables or {},
        }).json()
        if result.get("errors"):
            raise ValueError("SysON GraphQL: " + json.dumps(result["errors"]))
        return result["data"]

    def mutate(self, operation, input_type, values, result_fields=""):
        result = self.graphql(
            f"mutation($input:{input_type}!){{{operation}(input:$input){{__typename "
            f"{result_fields} ... on ErrorPayload{{messages{{body level}}}}}}}}",
            {"input": {"id": str(uuid.uuid4()), **values}},
        )[operation]
        if result["__typename"] == "ErrorPayload":
            raise ValueError(json.dumps(result["messages"]))
        return result

    def projects(self):
        return self.request("GET", "/api/rest/projects").json()

    def create_project(self, name):
        if any(p["name"] == name for p in self.projects()):
            raise ValueError("Project name already exists; inspect it or choose another --name: " + name)
        return self.request("POST", "/api/rest/projects", params={"name": name}).json()["@id"]

    def context(self, project):
        result = self.graphql(
            "query($id:ID!){viewer{project(projectId:$id){currentEditingContext{id}}}}",
            {"id": project},
        )["viewer"]["project"]
        if not result or not result["currentEditingContext"]:
            raise ValueError("SysON project has no editing context: " + project)
        return result["currentEditingContext"]["id"]

    def upload(self, context, path):
        operations = {
            "query": "mutation($input:UploadDocumentInput!){uploadDocument(input:$input){"
            "__typename ... on UploadDocumentSuccessPayload{report} "
            "... on ErrorPayload{messages{body level}}}}",
            "variables": {"input": {"id": str(uuid.uuid4()), "editingContextId": context,
                                    "file": None, "readOnly": False}},
        }
        with path.open("rb") as stream:
            data = self.request("POST", "/api/graphql/upload", data={
                "operations": json.dumps(operations), "map": json.dumps({"0": "variables.file"}),
            }, files={"0": ("homelab.sysml", stream, "text/plain")}).json()
        if data.get("errors"):
            raise ValueError(json.dumps(data["errors"]))
        payload = data["data"]["uploadDocument"]
        if payload["__typename"] != "UploadDocumentSuccessPayload" or payload.get("report"):
            raise ValueError("Import was not clean: " + json.dumps(payload))
        return payload

    def archive(self, project, output):
        content = self.request("GET", "/api/projects/" + project).content
        output.write_bytes(content)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = {name: json.loads(archive.read(name)) for name in archive.namelist()
                       if name.endswith(".json")}
        manifest = next(v for k, v in entries.items() if k.endswith("/manifest.json"))
        model = [obj for name, data in entries.items() if "/documents/" in name
                 for obj in objects(data)]
        diagrams = {v["id"]: v["representation"] for k, v in entries.items()
                    if "/representations/" in k}
        return manifest, model, diagrams

    def elements(self, project):
        commits = self.request("GET", f"/api/rest/projects/{project}/commits").json()
        if len(commits) != 1:
            raise ValueError("This adapter expects SysON's single-current-commit API")
        path = f"/api/rest/projects/{project}/commits/{commits[0]['@id']}/elements"
        response = self.request("GET", path)
        if response.headers.get("Link"):
            raise ValueError("Paginated element response is not supported by this version profile")
        return response.json()

    def representation(self, context, object_id, name, description_label="General View"):
        data = self.graphql(
            "query($c:ID!,$o:ID!){viewer{editingContext(editingContextId:$c){"
            "representationDescriptions(objectId:$o){edges{node{id label}}}}}}",
            {"c": context, "o": object_id},
        )["viewer"]["editingContext"]["representationDescriptions"]["edges"]
        descriptions = [e["node"]["id"] for e in data if e["node"]["label"] == description_label]
        if len(descriptions) != 1:
            raise ValueError("Expected one representation description: " + description_label)
        return self.mutate("createRepresentation", "CreateRepresentationInput", {
            "editingContextId": context, "objectId": object_id,
            "representationDescriptionId": descriptions[0], "representationName": name,
        }, "... on CreateRepresentationSuccessPayload{representation{id label}} ")["representation"]

    def layout(self, context, diagram, boxes, *, details=None, handles=None):
        nodes = []
        positions = {n['id']: boxes[n['targetObjectId']] for n in diagram['nodes'] if n['targetObjectId'] in boxes}
        positions.update(details or {})
        for identity, (x, y, width, height) in positions.items():
            nodes.append({"id": identity, "position": {"x": x, "y": y},
                          "size": {"width": width, "height": height}, "resizedByUser": True,
                          "movedByUser": True, "handleLayoutData": (handles or {}).get(identity, []),
                          "minComputedSize": {"width": 0, "height": 0}})
        self.mutate("layoutDiagram", "LayoutDiagramInput", {
            "editingContextId": context, "representationId": diagram["id"],
            # Any other cause with a fresh request ID is silently ignored by Sirius.
            "cause": "layout", "diagramLayoutData": {
                "nodeLayoutData": nodes, "edgeLayoutData": [], "labelLayoutData": [],
                "autoLayoutState": "DEACTIVATE",
            },
        })

    def hide_details(self, context, representation, ids, *, hide=True):
        if ids:
            self.mutate("hideDiagramElement", "HideDiagramElementInput", {
                "editingContextId": context, "representationId": representation,
                "elementIds": ids, "hide": hide,
            })

    def export_text(self, context, document):
        return self.request("GET", f"/api/editingcontexts/{context}/documents/{document}",
                            headers={"Accept": "text/html"}).content
