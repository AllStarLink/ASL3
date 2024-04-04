#!/bin/bash
set -e
set -x

if [ -f /etc/os-release ] ; then
  OS_CODENAME=$(cat /etc/os-release | grep "^VERSION_CODENAME=" | sed 's/VERSION_CODENAME=\(.*\)/\1/g')
elif [ command -v lsb_release ] ; then
  OS_CODENAME=$(lsb_release -a 2>/dev/null | grep "^Codename:" | sed 's/^Codename:\s*\(.*\)/\1/g')
elif [ command -v hostnamectl ] ; then
  OS_CODENAME=$(hostnamectl | grep "Operating System: " | sed 's/.*Operating System: [^(]*(\([^)]*\))/\1/g')
else
  OS_CODENAME=unknown
fi

echo "OS_CODENAME: ${OS_CODENAME}"

cd /build

export EMAIL="AllStarLink <autobuild@allstarlink.org>"
pushd ASL3
make deb
popd
mkdir _debs
mv *.deb _debs/
