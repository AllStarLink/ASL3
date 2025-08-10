ARG ARCH
ARG OS

FROM $ARCH/debian:$OS

ARG ARCH
ARG OS
ARG ASL_REPO
ARG USER_ID
ARG GROUP_ID

RUN addgroup --gid $GROUP_ID user; exit 0
RUN adduser --disabled-password --gecos '' --uid $USER_ID --gid $GROUP_ID user; exit 0

# Install build dependencies
RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get -y install \
	apt-utils build-essential devscripts fakeroot debhelper git lsb-release \
	libterm-readline-gnu-perl  libterm-readline-perl-perl libdistro-info-perl \
    gh ca-certificates wget --no-install-recommends

# Install build dependencies
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install \
	pandoc \
	--no-install-recommends

# Import entrypoint script
COPY ./entrypoint.sh /entrypoint.sh

# Make Executable
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
