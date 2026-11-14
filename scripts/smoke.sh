#!/bin/bash
# Build the app image for this machine and start it the way the Supervisor
# does: /data and /config bind-mounted, owned by root, with an options.json.
# Passes when the Web UI answers /healthz, the settings file was seeded into
# /config, and Print Handy runs as `handy`, not root.
set -euo pipefail

APP_DIR="${1:-./print_handy}"
IMAGE=print-handy-app-smoke
NAME=print-handy-app-smoke
WORK="$(mktemp -d)"
TIMEOUT="${SMOKE_TIMEOUT:-300}"

# shellcheck disable=SC2329  # invoked by the EXIT trap
cleanup() {
    docker logs "${NAME}" > "${WORK}/container.log" 2>&1 || true
    docker rm -f "${NAME}" > /dev/null 2>&1 || true
}
trap cleanup EXIT

docker build --pull -t "${IMAGE}" "${APP_DIR}"

mkdir -p "${WORK}/data" "${WORK}/config"
cat > "${WORK}/data/options.json" <<'JSON'
{
  "webui_access_token": "",
  "spoolman_on_lan": false,
  "env_vars": [{"name": "PRINT_HANDY_SMOKE_MARKER", "value": "from-options"}]
}
JSON
sudo chown -R root:root "${WORK}/data" "${WORK}/config"

docker run -d --name "${NAME}" \
    -v "${WORK}/data:/data" -v "${WORK}/config:/config" \
    -e TZ=Etc/UTC -p 8088:8088 "${IMAGE}"

echo "Waiting up to ${TIMEOUT}s for /healthz"
deadline=$((SECONDS + TIMEOUT))
until curl -fsS http://127.0.0.1:8088/healthz > /dev/null 2>&1; do
    if ! docker inspect -f '{{.State.Running}}' "${NAME}" | grep -q true; then
        echo "::error::the container exited"; docker logs "${NAME}" || true; exit 1
    fi
    if (( SECONDS > deadline )); then
        echo "::error::/healthz did not answer within ${TIMEOUT}s"; docker logs "${NAME}" || true; exit 1
    fi
    sleep 5
done
echo "Web UI is up"

fail=0
check() { if eval "$2"; then echo "ok: $1"; else echo "::error::$1"; fail=1; fi; }

handy_uid="$(docker exec "${NAME}" id -u handy)"
check "settings file seeded into /config" "sudo test -s '${WORK}/config/print-handy.yaml'"
check "/config/print-handy.yaml owned by handy" \
    "[ \"\$(sudo stat -c %u '${WORK}/config/print-handy.yaml')\" = '${handy_uid}' ]"
check "/data/state owned by handy" "[ \"\$(sudo stat -c %u '${WORK}/data/state')\" = '${handy_uid}' ]"
check "options.json left to root" "[ \"\$(sudo stat -c %u '${WORK}/data/options.json')\" = 0 ]"
check "Print Handy does not run as root" \
    "! docker top '${NAME}' -eo user,args | grep -E 'print-handy-supervise|print_handy' | grep -q '^root'"
check "app options reach the environment" \
    "docker exec '${NAME}' sh -c 'tr \"\\0\" \"\\n\" < /proc/1/environ; for p in /proc/[0-9]*; do tr \"\\0\" \"\\n\" < \$p/environ 2>/dev/null; done' | grep -q '^PRINT_HANDY_SMOKE_MARKER=from-options$'"
check "the API answers" "curl -fsS http://127.0.0.1:8088/api/printers > /dev/null || curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:8088/api/status | grep -qE '^(200|401)$'"

docker top "${NAME}" -eo user,pid,args | head -20
exit "${fail}"
