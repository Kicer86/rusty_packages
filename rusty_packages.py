
import argparse
import os
import progressbar
import stat
import subprocess
import sys
import time
from datetime import datetime


class RustyPackages:
    def __init__(self):
        self.now_ts=time.time()
        self.now=datetime.now()

    @staticmethod
    def _run_command(command: [str]) -> [str]:
        result=subprocess.run(command, stdout=subprocess.PIPE, env={"LC_ALL": "C"})
        return [line.decode("utf-8") for line in result.stdout.splitlines()]

    @staticmethod
    def _fetch_all_packages() -> [str]:
        packages_and_versions=RustyPackages._run_command(["pacman", "-Q"])
        packages=[entry.split(maxsplit=1)[0] for entry in packages_and_versions]
        return packages

    @staticmethod
    def _fetch_required_by(package: str) -> [str]:
        return RustyPackages._run_command(["pactree", "-rl", package])[1:]

    @staticmethod
    def _fetch_package_files(package: str) -> [str]:
        versions_and_files=RustyPackages._run_command(["pacman", "-Ql", package])
        files=[entry.split(maxsplit=1)[1] for entry in versions_and_files]
        return files

    @staticmethod
    def _fetch_file_properties(file: str, package: str) -> stat:
        file_stat=None
        try:
            file_stat=os.stat(file)
        except PermissionError:
            pass
        except FileNotFoundError:
            print(f"Warning: missing file: {file} from {package}")
        return file_stat

    @staticmethod
    def _was_package_used_after_upgrade(package: str) -> int:
        files=RustyPackages._fetch_package_files(package)

        used=False
        for file in files:
            file_stat=RustyPackages._fetch_file_properties(file, package)

            if file_stat and stat.S_ISREG(file_stat.st_mode):
                atime=int(file_stat.st_atime)
                ctime=int(file_stat.st_ctime)

                if atime > ctime:
                    used = True
                    break

        return used

    def _fetch_package_last_usage(self, package: str) -> int:
        files=RustyPackages._fetch_package_files(package)

        atimes=[]
        for file in files:
            file_stat=RustyPackages._fetch_file_properties(file, package)

            if file_stat and stat.S_ISREG(file_stat.st_mode):
                atime=int(file_stat.st_atime)
                atimes.append(atime)

        if len(atimes) == 0:
            print(f"Warning: could not access files from {package}")
            atimes.append(self.now_ts)

        latest_atime=max(atimes)

        return latest_atime


    def _calculate_days_time(self, atime):
        timestamp_datetime=datetime.fromtimestamp(atime)
        time_difference=self.now-timestamp_datetime
        difference_in_days = time_difference.days
        return difference_in_days

    def process(self, check_depending_packages=False, since_upgrade=False):
        packages=RustyPackages._fetch_all_packages()

        required_by={}
        package_atime={}

        # calcualate atime for each package
        for i in progressbar.progressbar(range(len(packages)), redirect_stdout=True):
            package=packages[i]

            if since_upgrade and RustyPackages._was_package_used_after_upgrade(package):
                atime=self.now_ts
            else:
                atime=self._fetch_package_last_usage(package)

            package_atime[package]=atime
            if check_depending_packages:
                dependent_packages=RustyPackages._fetch_required_by(package)
                required_by[package]=dependent_packages

        # include dependencies in atime
        if check_depending_packages:
            package_and_deps_atime={}
            for package in packages:
                atime=package_atime[package]
                package_required_by=required_by[package]
                for dependent in package_required_by:
                    ratime=package_atime[dependent]
                    atime=max(atime, ratime)
                package_and_deps_atime[package]=atime
            package_atime=package_and_deps_atime

        # find rusty ones
        rusty_packages=[]
        for package in packages:
            atime=package_atime[package]
            days=self._calculate_days_time(atime)

            if days > 30:
                rusty_packages.append((days, package))

        # print them out
        sorted_packages=sorted(rusty_packages)
        for package in sorted_packages:
            print(f"package {package[1]} not used for {package[0]} days.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Look for unused packages')
    parser.add_argument("--follow-deps", "-d",
                        action='store_true',
                        default=False,
                        help="When calculating package's last use time, take into consideration last use of packages depending on it.")

    parser.add_argument("--since-upgrade", "-u",
                        action='store_true',
                        default=False,
                        help="Show packages not used since last upgrade only.")

    args = parser.parse_args(sys.argv[1:])

    p=RustyPackages()
    p.process(check_depending_packages=args.follow_deps, since_upgrade=args.since_upgrade)
