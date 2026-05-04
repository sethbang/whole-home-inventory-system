#!/bin/sh
# WHIS mDNS sidecar entrypoint. Renders the avahi config + service file from
# their templates using $WHIS_MDNS_PORT and $WHIS_MDNS_HOSTNAME, brings up
# dbus, then runs avahi-daemon in the foreground so tini can supervise it.
set -eu

PORT="${WHIS_MDNS_PORT:-5173}"
HOSTNAME_VAL="${WHIS_MDNS_HOSTNAME:-whis}"

sed "s|__WHIS_MDNS_HOSTNAME__|${HOSTNAME_VAL}|g" \
    /etc/avahi/avahi-daemon.conf.template \
    > /etc/avahi/avahi-daemon.conf

sed "s|__WHIS_MDNS_PORT__|${PORT}|g" \
    /etc/avahi/services/whis.service.template \
    > /etc/avahi/services/whis.service

mkdir -p /run/dbus
dbus-daemon --system --nofork --nopidfile &
DBUS_PID=$!

trap 'kill "${DBUS_PID}" 2>/dev/null || true; exit 0' TERM INT

# Brief wait for the system bus socket to come up before avahi connects.
for _ in 1 2 3 4 5; do
    [ -S /run/dbus/system_bus_socket ] && break
    sleep 1
done

exec avahi-daemon --no-rlimits --no-chroot
