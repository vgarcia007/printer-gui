FROM olbat/cupsd:stable

ARG TARGETARCH
ARG HP_DRIVER_URL=https://ftp.hp.com/pub/softlib/software13/printers/MFP170/uld-hp_V1.00.39.12_00.15.tar.gz
ARG HP_DRIVER_SHA256=cebb9b7b6125e7406634bb9c2a98b01477d1e11d66c7c90474669de9927bc91d

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates curl jq printer-driver-dymo usbutils \
    && case "$TARGETARCH" in \
         amd64) hp_arch=x86_64 ;; \
         arm64) hp_arch=aarch64 ;; \
         *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
       esac \
    && curl --fail --location --retry 3 --output /tmp/hp-uld.tar.gz "$HP_DRIVER_URL" \
    && echo "$HP_DRIVER_SHA256  /tmp/hp-uld.tar.gz" | sha256sum --check --strict - \
    && mkdir -p /tmp/hp-uld /opt/smfp-common/printer/lib /usr/share/cups/model/uld-hp/cms \
    && tar --extract --gzip --file /tmp/hp-uld.tar.gz --directory /tmp/hp-uld \
         "uld/$hp_arch/rastertospl" \
         "uld/$hp_arch/libscmssc.so" \
         uld/noarch/share/ppd/HP_Color_Laser_MFP_17x_Series.ppd \
         uld/noarch/share/ppd/cms/17xsc.cts \
    && install -m 0755 "/tmp/hp-uld/uld/$hp_arch/rastertospl" /usr/lib/cups/filter/rastertospl \
    && install -m 0755 "/tmp/hp-uld/uld/$hp_arch/libscmssc.so" /opt/smfp-common/printer/lib/libscmssc.so \
    && install -m 0644 /tmp/hp-uld/uld/noarch/share/ppd/HP_Color_Laser_MFP_17x_Series.ppd /usr/share/cups/model/uld-hp/HP_Color_Laser_MFP_17x_Series.ppd \
    && install -m 0644 /tmp/hp-uld/uld/noarch/share/ppd/cms/17xsc.cts /usr/share/cups/model/uld-hp/cms/17xsc.cts \
    && cupstestppd /usr/share/cups/model/uld-hp/HP_Color_Laser_MFP_17x_Series.ppd \
    && ldd /usr/lib/cups/filter/rastertospl \
    && cp -a /etc/cups /opt/cups-defaults \
    && rm -rf /tmp/hp-uld /tmp/hp-uld.tar.gz /var/lib/apt/lists/*

COPY cups/entrypoint.sh /usr/local/bin/printer-cups-entrypoint
RUN chmod 0755 /usr/local/bin/printer-cups-entrypoint

ENTRYPOINT ["/usr/local/bin/printer-cups-entrypoint"]
