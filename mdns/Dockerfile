FROM alpine:3.20

RUN apk add --no-cache avahi avahi-tools dbus tini \
    && mkdir -p /run/dbus /etc/avahi/services

COPY avahi-daemon.conf.template /etc/avahi/avahi-daemon.conf.template
COPY whis.service.template /etc/avahi/services/whis.service.template
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV WHIS_MDNS_PORT=5173
ENV WHIS_MDNS_HOSTNAME=whis

ENTRYPOINT ["/sbin/tini", "--", "/entrypoint.sh"]
