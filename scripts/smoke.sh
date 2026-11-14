#!/bin/bash
# Build the app image for this machine and start it the way the Supervisor
# does: /data and /config bind-mounted, owned by root, with an options.json.
# Passes when the Web UI answers /healthz, the settings file was seeded into
# /config, and Print Handy runs as `handy`, not root.
# shellcheck disable=SC2329  # helpers run through check() and the EXIT trap
set -euo pipefail

APP_DIR="${1:-./print_handy}"
IMAGE=print-handy-app-smoke
NAME=print-handy-app-smoke
WORK="$(mktemp -d)"
TIMEOUT="${SMOKE_TIMEOUT:-300}"


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

# /healthz is the chat bot's health: 503 on a fresh install with no bot
# configured, which is expected. Any HTTP answer means the server is up.
web_status() { curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://127.0.0.1:8088/healthz || true; }
echo "Waiting up to ${TIMEOUT}s for the Web UI"
deadline=$((SECONDS + TIMEOUT))
until [[ "$(web_status)" =~ ^(200|503)$ ]]; do
    if ! docker inspect -f '{{.State.Running}}' "${NAME}" | grep -q true; then
        echo "::error::the container exited"; docker logs "${NAME}" || true; exit 1
    fi
    if (( SECONDS > deadline )); then
        echo "::error::/healthz did not answer within ${TIMEOUT}s"; docker logs "${NAME}" || true; exit 1
    fi
    sleep 5
done
echo "Web UI is up (/healthz answered $(web_status))"

echo "Waiting for Docker to report the app healthy (liveness check)"
until [ "$(docker inspect -f '{{.State.Health.Status}}' "${NAME}")" = healthy ]; do
    status="$(docker inspect -f '{{.State.Health.Status}}' "${NAME}")"
    if [ "${status}" = unhealthy ] || (( SECONDS > deadline + 120 )); then
        echo "::error::health status ${status}"
        docker inspect -f '{{json .State.Health}}' "${NAME}" || true
        exit 1
    fi
    sleep 5
done
echo "Docker health: healthy"

fail=0
check() {
    local label="$1"; shift
    if "$@"; then echo "ok: ${label}"; else echo "::error::${label}"; fail=1; fi
}

handy_uid="$(docker exec "${NAME}" id -u handy)"
owner() { sudo stat -c %u "$1"; }

seeded() { sudo test -s "${WORK}/config/print-handy.yaml"; }
config_owned() { [ "$(owner "${WORK}/config/print-handy.yaml")" = "${handy_uid}" ]; }
state_owned() { [ "$(owner "${WORK}/data/state")" = "${handy_uid}" ]; }
options_root() { [ "$(owner "${WORK}/data/options.json")" = 0 ]; }

# The supervisor and the Web UI run as handy; nothing of Print Handy runs
# as root (only tini and the entry script's exec chain start there).
print_handy_uids() {
    docker top "${NAME}" -eo uid,args | awk '/print-handy-supervise|print_handy\.webui/ {print $1}' | sort -u
}
not_root() {
    local uids
    uids="$(print_handy_uids)"
    [ -n "${uids}" ] && [ "${uids}" = "${handy_uid}" ]
}

# Root in the container cannot read other users' /proc environ without
# ptrace, so read handy's processes as handy.
options_in_env() {
    # shellcheck disable=SC2016  # expanded by the container's shell
    docker exec -u handy "${NAME}" sh -c \
        'for e in /proc/[0-9]*/environ; do tr "\000" "\n" < "$e" 2>/dev/null; done' \
        | grep -qx 'PRINT_HANDY_SMOKE_MARKER=from-options'
}

api_answers() {
    local code
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 60 http://127.0.0.1:8088/api/status || true)"
    [[ "${code}" =~ ^(200|401)$ ]]
}

check "settings file seeded into /config" seeded
check "/config/print-handy.yaml owned by handy" config_owned
check "/data/state owned by handy" state_owned
check "options.json left to root" options_root
check "Print Handy runs as handy, not root" not_root
check "app options reach the environment" options_in_env
check "the API answers" api_answers

docker top "${NAME}" -eo user,uid,pid,args | head -20
exit "${fail}"
