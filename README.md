
# Rusty Packages
A tool for identifying Arch packages that have not been used for an extended period.

## How It Works
This Python script examines the access time (atime) of the files associated with each installed package.
It then compiles a list of packages whose files have not been accessed for more than 30 days.

## Caveats
* Rusty Packages relies on knowing the atime of files. If the root filesystem is mounted with the "noatime" option, the results may be inaccurate.
* Updating packages can update the atime even if the package's files have not been used otherwise.

## Run options
You can change the default number of 30 days after which package is considered rusty with --time parameter.

By default, Rusty Packages calculates the atime of the package itself and provides results based on this atime.
You can use the --follow-deps option to take into account the atime of packages that depend on the currently analyzed one.
For instance, if package X has not been used for 60 days, but there is a package Y that depends on it and has only been unused for 5 days, package X will not be marked as "rusty."

If you want to limit results to packages which were not used since they were upgraded, use --since-upgrade.

For systems with root partition mounted with "noatime" option one may use --last-upgraded parameter. It will cause Rusty Packages to list packages not updated for a given time.
