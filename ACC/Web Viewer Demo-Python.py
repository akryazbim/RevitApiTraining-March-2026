import requests
import base64
import time
import os

# =========================
# INPUTS
# =========================
CLIENT_ID = "3smyjt0WmS7LWSKMFwPyu5F5LlarKGmkLGPOarQc4bmrngbg"
CLIENT_SECRET = "RkFWBxLg7ZbGecac8AcwwTvaLovylEPmgzE0ITlm1r5I2sPGBO2e2cV4whnrDblT"
FILE_PATH = r"C:\Users\Akryazz\OneDrive\Documents\My Files\Revit Api Training\Python Revit API Training\Revit Models\2025\TestProject.rvt"
BUCKET_KEY = "aps-demo-bucket-april-2026-test"

APS_HOST = "https://developer.api.autodesk.com"

# =========================
# AUTH
# =========================
def get_token():
    url = f"{APS_HOST}/authentication/v2/token"
    data = {
        "grant_type": "client_credentials",
        "scope": "data:read data:write bucket:create bucket:read"
    }
    res = requests.post(url, data=data, auth=(CLIENT_ID, CLIENT_SECRET))
    return res.json()["access_token"]

# =========================
# CREATE BUCKET
# =========================
def create_bucket(token):
    url = f"{APS_HOST}/oss/v2/buckets"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "bucketKey": BUCKET_KEY,
        "policyKey": "transient"
    }
    requests.post(url, json=data, headers=headers)

# =========================
# GET SIGNED URL
# =========================
def get_signed_url(token, object_name):
    url = f"{APS_HOST}/oss/v2/buckets/{BUCKET_KEY}/objects/{object_name}/signeds3upload"
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(url, headers=headers).json()

    return res["urls"][0], res["uploadKey"]

# =========================
# UPLOAD TO S3
# =========================
def upload_to_s3(upload_url):
    with open(FILE_PATH, "rb") as f:
        file_data = f.read()

    res = requests.put(upload_url, data=file_data)

    print("Upload status:", res.status_code)
    etag = res.headers.get("ETag", "").strip('"')
    print("ETag:", etag)

    return etag

# =========================
# COMPLETE UPLOAD
# =========================
def complete_upload(token, object_name, upload_key, etag):
    url = f"{APS_HOST}/oss/v2/buckets/{BUCKET_KEY}/objects/{object_name}/signeds3upload"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    data = {
        "uploadKey": upload_key,
        "eTags": [etag]  
    }

    res = requests.post(url, json=data, headers=headers)

    result = res.json()
    print("Complete Upload Response:", res.text)

    if result.get("status") == "error":
        raise Exception(f"Complete upload failed: {result.get('reason')} — {result}")

    return result["objectId"]

# =========================
# ENCODE URN
# =========================
def encode_urn(object_id):
    return base64.b64encode(object_id.encode()).decode()

# =========================
# TRANSLATE
# =========================
def translate(token, urn):
    url = f"{APS_HOST}/modelderivative/v2/designdata/job"
    headers = {"Authorization": f"Bearer {token}"}

    data = {
        "input": {"urn": urn},
        "output": {
            "formats": [
                {"type": "svf", "views": ["2d", "3d"]}
            ]
        }
    }

    requests.post(url, json=data, headers=headers)

# =========================
# WAIT FOR TRANSLATION
# =========================
def wait_for_translation(token, urn):
    url = f"{APS_HOST}/modelderivative/v2/designdata/{urn}/manifest"
    headers = {"Authorization": f"Bearer {token}"}

    while True:
        res = requests.get(url, headers=headers).json()
        status = res.get("status")

        print("Status:", status)

        if status == "failed":
            print("ERROR:")
            print(res)
            break

        if status == "success":
            break

        time.sleep(5)

# =========================
# CREATE VIEWER HTML
# =========================
def create_html(urn, token):
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <script src="https://developer.api.autodesk.com/modelderivative/v2/viewers/7.*/viewer3D.min.js"></script>
  <link rel="stylesheet" href="https://developer.api.autodesk.com/modelderivative/v2/viewers/7.*/style.min.css">
  <style>
    html, body {{ margin: 0; height: 100%; }}
    #viewer {{ width: 100%; height: 100%; }}
  </style>
</head>
<body>
  <div id="viewer"></div>
  <script>
    const options = {{
      env: 'AutodeskProduction',
      accessToken: '{token}'
    }};

    Autodesk.Viewing.Initializer(options, function () {{
      const viewer = new Autodesk.Viewing.GuiViewer3D(document.getElementById('viewer'));
      viewer.start();

      Autodesk.Viewing.Document.load('urn:{urn}', function (doc) {{
        const defaultModel = doc.getRoot().getDefaultGeometry();
        viewer.loadDocumentNode(doc, defaultModel);
      }});
    }});
  </script>
</body>
</html>
"""
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viewer.html")
    with open(out_path, "w") as f:
        f.write(html)
    print("Saved to:", out_path)

# =========================
# MAIN
# =========================
def main():
    token = get_token()
    print("Token acquired")

    create_bucket(token)
    print("Bucket created")

    object_name = os.path.basename(FILE_PATH)

    upload_url, upload_key = get_signed_url(token, object_name)
    print("Got signed URL")

    etag = upload_to_s3(upload_url)
    print("Uploaded to S3")

    object_id = complete_upload(token, object_name, upload_key, etag)
    print("Upload completed")

    urn = encode_urn(object_id)
    print("URN:", urn)

    translate(token, urn)
    print("Translation started")

    wait_for_translation(token, urn)
    print("Translation finished")

    create_html(urn, token)
    print("viewer.html created → open in browser")

if __name__ == "__main__":
    main()