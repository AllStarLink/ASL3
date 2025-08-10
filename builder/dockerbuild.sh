#!/bin/bash

set -e
set -x

while [[ $# -gt 0 ]]; do
  case $1 in
    -a|--architecture)
      ARCH_ASK="$2"
      shift
      shift
      ;;
    -o|--operating-systems)
      OPERATING_SYSTEMS="$2"
      shift
      shift
      ;;
    --gh-rel)
      GH_REL="$2"
      shift
      shift
      ;;
	-r)
      REPO_LEVEL="$2"
      shift
      shift	
      ;;
	-*|--*|*)
      echo "Unknown option $1"
	  shift
      shift
      ;;
  esac
done

if [ -z "$ARCH_ASK" ]
then
  ARCH="all"
fi

case $ARCH_ASK in
	arm64)
		ARCH=arm64v8
		;;
	armhf)
		ARCH=arm32v7
		;;
	*)
		ARCH=$ARCH_ASK
		;;
esac

if [ -z "$OPERATING_SYSTEMS" ]
then
  OPERATING_SYSTEMS="bookworm"
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ $BRANCH == "develop" ]; then
  REPO_ENV="-devel"
elif [ $BRANCH == "testing"]; then
  REPO_ENV="-testing"
else
  REPO_ENV=""
fi

APTLY_REPO="asl3-${OPERATING_SYSTEMS}-${REPO_LEVEL}"

## Need to clean this up to be more elegant
echo "Architectures: $ARCH"
echo "Targets: $TARGETS"
echo "Operating Systems: $OPERATING_SYSTEMS"
echo "Aptly Repo: ${APTLY_REPO}"
echo "PWD: $(pwd)"
echo "BS: ${BASH_SOURCE[0]}"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "DIR: ${DIR}"
PDIR=$(dirname $DIR)
echo "PDIR: ${PDIR}"
ALL_PKG_ROOT=$(dirname ${PDIR})
echo "ALL_PKG_ROOT: ${ALL_PKG_ROOT}"
echo "GH_REL: ${GH_REL}"


D_TAG="$(echo "${GH_REPO_NAME}" | cut -d'/' -f2 | tr '[:upper:]' '[:lower:]').${OPERATING_SYSTEMS}.${ARCH}${REPO_ENV}"

docker build -f $DIR/Dockerfile -t $D_TAG \
	--build-arg ARCH="$ARCH" \
	--build-arg OS="$OPERATING_SYSTEMS" \
	--build-arg USER_ID=$(id -u) \
	--build-arg GROUP_ID=$(id -g) \
	$DIR
 
docker run -v $ALL_PKG_ROOT:/build $D_TAG

DEBIAN_FRONTEND=noninteractive apt-get -y install gh
gh release upload -R ${GH_REPO_NAME} $GH_REL $ALL_PKG_ROOT/_debs/*.deb

docker image rm --force $D_TAG

APTLY_USER="${APTLY_API_USER}:${APTLY_API_PASS}"

find $ALL_PKG_ROOT/_debs/*.deb -name "*.deb" | \
	xargs -I {} -d '\n' curl --fail --user ${APTLY_USER} \
	-X POST -F 'file=@"{}"' \
	 https://repo-admin.allstarlink.org/api/files/${APTLY_REPO}-${OPERATING_SYSTEMS}

curl --fail --user ${APTLY_USER} -X POST \
	https://repo-admin.allstarlink.org/api/repos/${APTLY_REPO}/file/${APTLY_REPO}-${OPERATING_SYSTEMS}

curl --fail --user ${APTLY_USER} -X PUT -H "content-Type: application/json" \
	--data "{\"Signing\": {\"Batch\": true, \"Passphrase\": \"${APTLY_GPG_PASSPHRASE}\"}}" \
	"https://repo-admin.allstarlink.org/api/publish/:./${OPERATING_SYSTEMS}"

