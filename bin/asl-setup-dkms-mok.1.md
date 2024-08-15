% asl-setup-dkms-mok(1) ASL3 @@HEAD-DEVELOP@@
% Jason McCormick
% August 2024

# NAME
asl-setup-dkms-mok - Configure the Machine Owner Key (MOK)
for signing kernel packages, notably dahdi* for ASL.

# SYNOPSIS
usage: `asl-setup-dkms-mok`

# DESCRIPTION
This script is a walkthrough script for generating a UEFI Machine Owner
Key (MOK). A MOK is needed on systems with UEFI SecureBoot to properly
authenticate the DAHDI-related kernel modules which are rebuilt on kernel
upgrades with DKMS. See the AllStarLink manual for more information or
https://wiki.debian.org/SecureBoot.

# BUGS
Report bugs to https://github.com/AllStarLink/ASL3/issues

# COPYRIGHT
Copyright (C) 2024 Jason McCormick and AllStarLink
under the terms of the AGPL v3.
