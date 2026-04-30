# Dynamo CPython3 — Get ACC Project ID and Model GUID, then open the cloud document
# ─────────────────────────────────────────────────────────────────────────────────
# Inputs (wire String nodes in Dynamo):
#   IN[0]  3-legged OAuth token
#   IN[1]  Hub name          e.g. "Akryaz"
#   IN[2]  Project name      e.g. "Construction : Sample Project - Seaport Civic Center"
#   IN[3]  File path in ACC  e.g. "Project Files/Models/CloudeModelTest.rvt"
#
# Outputs:
#   OUT[0]  Project ID  (raw string, e.g. "b.3cbb0540-...")
#   OUT[1]  Item ID     (lineage URN)
#   OUT[2]  Model GUID  (Revit model GUID from version extension data)
#   OUT[3]  Opened Revit Document

import json
import urllib.request
import urllib.error

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import ModelPathUtils, OpenOptions
from System import Guid
from RevitServices.Persistence import DocumentManager

# IN is injected by Dynamo at runtime; fallback values let the script run standalone
_in = IN if "IN" in dir() else [  # type: ignore[name-defined]
    "your_3legged_token",
    "Akryaz",
    "Construction : Sample Project - Seaport Civic Center",
    "Project Files/Models/CloudeModelTest.rvt",
]
TOKEN        = "eyJhbGciOiJSUzI1NiIsImtpZCI6IlZiakZvUzhQU3lYODQyMV95dndvRUdRdFJEa19SUzI1NiIsInBpLmF0bSI6ImFzc2MifQ.eyJzY29wZSI6WyJkYXRhOnJlYWQiLCJkYXRhOndyaXRlIiwiZGF0YTpjcmVhdGUiLCJidWNrZXQ6cmVhZCIsImJ1Y2tldDpjcmVhdGUiLCJhY2NvdW50OnJlYWQiXSwiY2xpZW50X2lkIjoiM3NteWp0MFdtUzdMV1NLTUZ3UHl1NUY1TGxhcktHbWtMR1BPYXJRYzRibXJuZ2JnIiwiaXNzIjoiaHR0cHM6Ly9kZXZlbG9wZXIuYXBpLmF1dG9kZXNrLmNvbSIsImF1ZCI6Imh0dHBzOi8vYXV0b2Rlc2suY29tIiwianRpIjoiOXh5emU0UVNPWWg2WVVNN3Y4Q1ZUZ0I5ZmVCQTh1VEtEWnNQV2YwaGdsV1RPNFA3WTJvTXZZbEsxQTJPd3N5SCIsInVzZXJpZCI6IlRVSzlMRkJBWEdBWiIsImV4cCI6MTc3NzU2MDEwNn0.Mcjc61885IOURw59fUuFq6mhSzeUtzuVzd54ot96_kl7AjJFLZ_8eIyUR2zHDcO_LVUNq5SBvYv8ESro1rjjgSGZyD2FzMsVAzP7QbFirYC76QsYc-vT3esHg29KPM0HxhLtzybKdxTOGQqsEW5hptNdhhoIHgJa_cddUelmX_pIvCmrJsPkNuivR0fyGXrdaAUO3S7Cje-3p4MpCJnuzf_8cIB9INZiQ9fstPogZn1hfQihTWoxmADk1lzQekXYXms0UFRgBKqf7zCxjlpWkchBsLbv-PJUtxbVVlAg5DRfGJa0BkNnBvQYBHqUrg7si-QYzBAd5GoXh2CPtbC00g"
HUB_NAME     = "Akryaz"
PROJECT_NAME = "Construction : Sample Project - Seaport Civic Center"
FILE_PATH    = "Project Files/Models/CloudeModelTest.rvt"

BASE_URL = "https://developer.api.autodesk.com"


# ── HTTP helper ────────────────────────────────────────────────────────────────
def api_get(endpoint):
    req = urllib.request.Request(
        BASE_URL + endpoint,
        headers={"Authorization": "Bearer " + TOKEN}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())["data"]


# ── Paginated folder contents ──────────────────────────────────────────────────
def get_folder_contents(project_id, folder_id):
    url   = "{}/data/v1/projects/{}/folders/{}/contents?page[limit]=200".format(
            BASE_URL, project_id, folder_id)
    items = []
    while url:
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOKEN})
        with urllib.request.urlopen(req) as resp:
            body   = json.loads(resp.read().decode())
        items += body["data"]
        url    = body.get("links", {}).get("next", {}).get("href")
    return items


# ── Navigate folder tree ───────────────────────────────────────────────────────
def find_item(hub_id, project_id, file_path):
    parts       = file_path.strip("/").split("/")
    target_name = parts[-1]
    folder_path = parts[:-1]

    top_folders = api_get("/project/v1/hubs/{}/projects/{}/topFolders".format(hub_id, project_id))
    current     = next((f for f in top_folders if f["attributes"]["name"] == folder_path[0]), None)
    if not current:
        raise LookupError("Top-level folder not found: '{}'".format(folder_path[0]))

    for sub_name in folder_path[1:]:
        contents = get_folder_contents(project_id, current["id"])
        current  = next(
            (x for x in contents if x["type"] == "folders" and x["attributes"]["name"] == sub_name),
            None,
        )
        if not current:
            raise LookupError("Sub-folder not found: '{}'".format(sub_name))

    contents = get_folder_contents(project_id, current["id"])
    item     = next(
        (x for x in contents if x["type"] == "items" and x["attributes"]["displayName"] == target_name),
        None,
    )
    if not item:
        raise LookupError("File not found: '{}'".format(target_name))
    return item


# ── Main logic ─────────────────────────────────────────────────────────────────
try:
    # ── Resolve hub ──
    hubs   = api_get("/project/v1/hubs")
    hub    = next((h for h in hubs if h["attributes"]["name"] == HUB_NAME), None)
    if not hub:
        raise LookupError("Hub '{}' not found".format(HUB_NAME))
    hub_id = hub["id"]

    # ── Resolve project ──
    projects = api_get("/project/v1/hubs/{}/projects".format(hub_id))
    project  = next((p for p in projects if p["attributes"]["name"] == PROJECT_NAME), None)
    if not project:
        raise LookupError("Project '{}' not found".format(PROJECT_NAME))
    project_id = project["id"]

    # ── Resolve file item ──
    item    = find_item(hub_id, project_id, FILE_PATH)
    item_id = item["id"]

    # ── Get Revit model GUID from version extension data ──
    # extension.data.modelGuid is the actual GUID Revit uses — no decoding needed
    versions       = api_get("/data/v1/projects/{}/items/{}/versions".format(project_id, item_id))
    ext_data       = versions[0]["attributes"]["extension"]["data"]
    model_guid_str = ext_data["modelGuid"]
    proj_guid_str  = ext_data.get("projectGuid", project_id[2:])  # strip "b." fallback

    # ── Build cloud ModelPath and open document ──
    cloud_path = ModelPathUtils.ConvertCloudGUIDsToCloudPath(
        Guid(proj_guid_str), Guid(model_guid_str)
    )
    app = DocumentManager.Instance.CurrentUIApplication.Application
    doc = app.OpenDocumentFile(cloud_path, OpenOptions())

    OUT = [project_id, item_id, model_guid_str, doc]

except urllib.error.HTTPError as e:
    OUT = ["HTTP Error {}: {}".format(e.code, e.reason), None, None, None]
except LookupError as e:
    OUT = [str(e), None, None, None]
except Exception as e:
    OUT = ["Error: " + str(e), None, None, None]
