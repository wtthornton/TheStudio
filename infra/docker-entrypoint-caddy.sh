#!/bin/sh
# Select Caddy config based on THESTUDIO_HTTPS_ENABLED.
# HTTPS=true -> Caddyfile (TLS). HTTPS=false or unset -> Caddyfile.http (plain HTTP).
if [ "${THESTUDIO_HTTPS_ENABLED}" = "true" ]; then
	cp /mnt/caddy/Caddyfile /tmp/Caddyfile
else
	cp /mnt/caddy/Caddyfile.http /tmp/Caddyfile
fi
exec caddy run --config /tmp/Caddyfile --adapter caddyfile
