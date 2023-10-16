
# Rusty Packages
A tool for identifying Arch packages that have not been used for an extended period.

## How It Works
This Python script examines the access time (atime) of the files associated with each installed package.
It then compiles a list of packages whose files have not been accessed for more than 30 days.

## Caveats
* Rusty Packages relies on knowing the atime of files. If the root filesystem is mounted with the "noatime" option, the results may be inaccurate.
* Updating packages can update the atime even if the package's files have not been used otherwise.
