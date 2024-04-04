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
elif [ $BRANCH = "testing"]; then
  REPO_ENV="-testing"
else
  REPO_ENV=""
fi

## Need to clean this up to be more elegant
echo "Architectures: $ARCH"
echo "Targets: $TARGETS"
echo "Operating Systems: $OPERATING_SYSTEMS"
echo "PWD: $(pwd)"
echo "BS: ${BASH_SOURCE[0]}"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "DIR: ${DIR}"
PDIR=$(dirname $DIR)
echo "PDIR: ${PDIR}"
ALL_PKG_ROOT=$(dirname ${PDIR})
echo "ALL_PKG_ROOT: ${ALL_PKG_ROOT}"
echo "GH_REL: ${GH_REL}"

D_TAG="ASL3_builder.${OPERATING_SYSTEMS}.${ARCH}${REPO_ENV}"

docker build -f $DIR/Dockerfile -t $D_TAG \
	--build-arg ARCH="$ARCH" \
	--build-arg OS="$OPERATING_SYSTEMS" \
	--build-arg USER_ID=$(id -u) \
	--build-arg GROUP_ID=$(id -g) \
	$DIR
 
docker run -v $ALL_PKG_ROOT:/build $D_TAG

DEBIAN_FRONTEND=noninteractive apt-get -y install gh
gh release upload -R AllStarLink/ASL3 $GH_REL $ALL_PKG_ROOT/_debs/*.deb

docker image rm --force $D_TAG
