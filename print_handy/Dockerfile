# https://contributors.home-assistant.io/apps/guides/dockerfile/
#
# A thin layer over the published Print Handy image: nothing is rebuilt.
# The upstream workflow (scripts/upstream.py) rewrites the two lines below
# when Print Handy publishes a release: the version tag and the digest of
# its multi-arch index, so every build of one app version is the same image.
ARG PRINT_HANDY_VERSION=2.3.2
ARG PRINT_HANDY_DIGEST=sha256:2e34364549370cb502af3327f67a7ccbb388acd8126e02b4b14c8100b573387b
FROM ghcr.io/catduckgnaf/print-handy:${PRINT_HANDY_VERSION}@${PRINT_HANDY_DIGEST}

# The Supervisor mounts /data and /config owned by root, and the upstream
# image runs as its unprivileged `handy` user. The entry script starts as
# root only long enough to prepare those folders, then drops to `handy`
# and hands over to Print Handy's own entrypoint and supervisor.
USER root
COPY rootfs /
RUN chmod 0755 /usr/local/bin/print-handy-app

ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/usr/local/bin/print-handy-app"]
CMD []

LABEL \
    io.hass.type="app" \
    org.opencontainers.image.title="Home Assistant App: Print Handy" \
    org.opencontainers.image.description="Print Handy packaged as a Home Assistant OS app" \
    org.opencontainers.image.source="https://github.com/catduckgnaf/print-handy-haos-addon" \
    org.opencontainers.image.licenses="AGPL-3.0-only"
