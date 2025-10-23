ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8

# Install base system
RUN apk update && \
    apk upgrade && \
    apk add --no-cache --virtual build-deps alpine-sdk cmake git libusb-dev qt5-qtbase-dev pulseaudio-dev

# Install rtl-sdr software
RUN cd /tmp && \
    git clone https://gitea.osmocom.org/sdr/rtl-sdr.git && \
    cd rtl-sdr && \
    mkdir build && \
    cd build && \
    cmake ../ -DINSTALL_UDEV_RULES=ON -DDETACH_KERNEL_DRIVER=ON && \
    make && \
    make install && \
    cd / && \
    rm -r /tmp/rtl-sdr

# Install multimon-ng software
RUN cd /tmp && \
    git clone https://github.com/EliasOenal/multimon-ng.git && \
    cd multimon-ng && \
    mkdir build && \
    cd build && \
    /usr/lib/qt5/bin/qmake ../multimon-ng.pro && \
    make && \
    make install && \
    cd / && \
    rm -r /tmp/multimon-ng

# Cleanup build environment and install runtimes instead
RUN apk del build-deps alpine-sdk cmake git libusb-dev qt5-qtbase-dev pulseaudio-dev && \
    apk add --no-cache libusb gcc pulseaudio qt5-qtbase py3-yaml py3-geopy py3-usb py3-paho-mqtt py3-requests sqlite

# Install the add-on code and data
COPY sdl_ids.txt /var/lib/
COPY p2000.py /
COPY p2000.sqlite3 /
COPY p2000.py /
COPY entrypoint.sh /entrypoint.sh
COPY watchdog.sh /watchdog.sh

RUN chmod a+x /entrypoint.sh /watchdog.sh /p2000.py

ENTRYPOINT ["/entrypoint.sh"]

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG BUILD_ARCH
ARG BUILD_DATE
ARG BUILD_DESCRIPTION
ARG BUILD_NAME
ARG BUILD_REF
ARG BUILD_REPOSITORY
ARG BUILD_VERSION
LABEL \
    io.hass.name="${BUILD_NAME}" \
    io.hass.description="${BUILD_DESCRIPTION}" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version=${BUILD_VERSION} \
    maintainer="cyberjunky (https://github.com/cyberjunky)" \
    org.opencontainers.image.title="${BUILD_NAME}" \
    org.opencontainers.image.description="${BUILD_DESCRIPTION}" \
    org.opencontainers.image.vendor="Home Assistant Add-ons" \
    org.opencontainers.image.authors="cyberjunky (https://github.com/cyberjunky)" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.url="https://github.com/cyberjunky" \
    org.opencontainers.image.source="https://github.com/${BUILD_REPOSITORY}" \
    org.opencontainers.image.documentation="https://github.com/${BUILD_REPOSITORY}/blob/main/README.md" \
    org.opencontainers.image.created=${BUILD_DATE} \
    org.opencontainers.image.revision=${BUILD_REF} \
    org.opencontainers.image.version=${BUILD_VERSION}

