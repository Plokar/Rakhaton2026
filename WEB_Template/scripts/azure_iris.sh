#!/usr/bin/env bash
# ACI demo instance (synthetic data only). Credentials enter through the environment.
set +x
set -euo pipefail

: "${AZURE_RESOURCE_GROUP:?Set AZURE_RESOURCE_GROUP}"
: "${AZURE_LOCATION:?Set AZURE_LOCATION (e.g. westeurope)}"
: "${IRIS_PASSWORD:?Set IRIS_PASSWORD in the environment}"
export AZURE_CONTAINER_NAME="${AZURE_CONTAINER_NAME:-mdt-iris}"
export IRIS_IMAGE="${IRIS_IMAGE:-intersystems/irishealth-community:2026.2}"
command -v az >/dev/null
command -v python3 >/dev/null

# Stream the deployment document: no local password files and no secret in process arguments.
# az output is suppressed because the submitted manifest contains a base64-encoded secret.
python3 - <<'PY' | az container create --resource-group "$AZURE_RESOURCE_GROUP" --file /dev/stdin --only-show-errors --output none
import base64
import json
import os

after_start = '''#!/bin/sh
set -eu
iris session IRIS -U %SYS <<'OBJECTSCRIPT'
set properties("Enabled")=1,properties("AutheEnabled")=48
set status=##class(Security.Services).Modify("%Service_CallIn",.properties)
if $SYSTEM.Status.IsError(status) do $SYSTEM.Status.DisplayError(status) halt 1
do ##class(Security.Users).UnExpireUserPasswords("*")
halt
OBJECTSCRIPT
'''

def encoded(text):
    return base64.b64encode(text.encode("utf-8")).decode("ascii")

ports = [{"port": p, "protocol": "TCP"} for p in (1972, 52773)]
print(json.dumps({
    "apiVersion": "2021-10-01", "type": "Microsoft.ContainerInstance/containerGroups",
    "name": os.environ["AZURE_CONTAINER_NAME"], "location": os.environ["AZURE_LOCATION"],
    "properties": {
        "osType": "Linux", "restartPolicy": "Always",
        "containers": [{"name": "iris", "properties": {
            "image": os.environ["IRIS_IMAGE"],
            "command": ["/iris-main", "--password-file", "/run/iris-secrets/password",
                        "-a", "sh /run/iris-secrets/after-start.sh"],
            "ports": ports, "resources": {"requests": {"cpu": 2, "memoryInGB": 4}},
            "volumeMounts": [{"name": "iris-secrets", "mountPath": "/run/iris-secrets", "readOnly": True}],
        }}],
        "ipAddress": {"type": "Public", "ports": ports},
        "volumes": [{"name": "iris-secrets", "secret": {
            "password": encoded(os.environ["IRIS_PASSWORD"]), "after-start.sh": encoded(after_start),
        }}],
    },
}))
PY

az container show --resource-group "$AZURE_RESOURCE_GROUP" --name "$AZURE_CONTAINER_NAME" \
    --query ipAddress.ip --output tsv --only-show-errors
