# https://contributors.home-assistant.io/apps/guides/dockerfile/
#
# A thin layer over the published Print Handy image: nothing is rebuilt.
# The upstream workflow (scripts/upstream.py) rewrites the two lines below
# when Print Handy publishes a release: the version tag and the digest of
# its multi-arch index, so every build of one app version is the same image.
ARG PRINT_HANDY_VERSION=2.3.5
ARG PRINT_HANDY_DIGEST=sha256:904da6919466b2e646e14f4aae8052425522dfbbaafce52ff9be17c123236f3f
FROM ghcr.io/catduckgnaf/print-handy:${PRINT_HANDY_VERSION}@${PRINT_HANDY_DIGEST}

# The Supervisor mounts /data and /config owned by root, and the upstream
# image runs as its unprivileged `handy` user. The entry script starts as
# root only long enough to prepare those folders, then drops to `handy`
# and hands over to Print Handy's own entrypoint and supervisor.
USER root
# The settings file lives in the app's config folder (see print-handy-app).
ENV PRINT_HANDY_CONFIG=/config/print-handy.yaml HOME=/data
COPY rootfs /
RUN chmod 0755 /usr/local/bin/print-handy-app /usr/local/bin/print-handy-app-health

ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/usr/local/bin/print-handy-app"]
CMD []
# Liveness only (see print-handy-app-health): the Supervisor watchdog acts
# on this, and an unconfigured chat bot must not restart a fresh install.
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 CMD ["/usr/local/bin/print-handy-app-health"]

LABEL \
    io.hass.type="app" \
    org.opencontainers.image.title="Home Assistant App: Print Handy" \
    org.opencontainers.image.description="Print Handy packaged as a Home Assistant OS app" \
    org.opencontainers.image.source="https://github.com/catduckgnaf/print-handy-haos-addon" \
    org.opencontainers.image.licenses="AGPL-3.0-only"
