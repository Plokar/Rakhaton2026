"""ACI manifest construction without Azure, credentials or a running IRIS."""
import base64
import json
import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "azure_iris.sh"


def test_aci_manifest_secrets_bootstrap_and_ports(tmp_path):
    manifest = tmp_path / "manifest.json"
    az = tmp_path / "az"
    az.write_text('''#!/bin/sh
set -eu
if [ "$2" = create ]; then
    cat > "$TEST_MANIFEST"
else
    echo '<PUBLIC_IP>'
fi
''')
    az.chmod(0o700)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "TEST_MANIFEST": str(manifest),
           "AZURE_RESOURCE_GROUP": "test-group", "AZURE_LOCATION": "westeurope",
           "AZURE_CONTAINER_NAME": "test-iris", "IRIS_PASSWORD": "<placeholder>"}
    result = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "<PUBLIC_IP>" and "<placeholder>" not in result.stderr
    data = json.loads(manifest.read_text())
    assert data["name"] == "test-iris" and data["location"] == "westeurope"
    props = data["properties"]
    secrets = props["volumes"][0]["secret"]
    assert base64.b64decode(secrets["password"]).decode() == "<placeholder>"
    bootstrap = base64.b64decode(secrets["after-start.sh"]).decode()
    assert 'iris session IRIS -U %SYS' in bootstrap
    assert 'Security.Services).Modify("%Service_CallIn",.properties)' in bootstrap
    assert 'properties("Enabled")=1,properties("AutheEnabled")=48' in bootstrap
    assert 'Security.Users).UnExpireUserPasswords("*")' in bootstrap
    assert "<placeholder>" not in bootstrap
    container = props["containers"][0]["properties"]
    assert container["command"] == ["/iris-main", "--password-file", "/run/iris-secrets/password",
                                    "-a", "sh /run/iris-secrets/after-start.sh"]
    assert {p["port"] for p in container["ports"]} == {1972, 52773}
    assert props["ipAddress"]["ports"] == container["ports"]
    assert container["volumeMounts"][0]["readOnly"] is True


def test_aci_requires_password_before_invoking_azure(tmp_path):
    env = {**os.environ, "AZURE_RESOURCE_GROUP": "test-group", "AZURE_LOCATION": "westeurope"}
    env.pop("IRIS_PASSWORD", None)
    result = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True)
    assert result.returncode != 0 and "Set IRIS_PASSWORD" in result.stderr
