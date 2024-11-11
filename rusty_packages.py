
import argparse
import logging
import os
import stat
import subprocess
import sys
import time
import tqdm
from datetime import datetime
from tqdm.contrib.logging import logging_redirect_tqdm


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
            logging.warning(f"Warning: missing file: {file} from {package}")
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
            logging.warning(f"Warning: could not access files from {package}")
            atimes.append(self.now_ts)

        latest_atime=max(atimes)

        return latest_atime

    def _fetch_package_last_update(self, package: str) -> int:
        files=RustyPackages._fetch_package_files(package)

        ctimes=[]
        for file in files:
            file_stat=RustyPackages._fetch_file_properties(file, package)

            if file_stat and stat.S_ISREG(file_stat.st_mode):
                ctime=int(file_stat.st_ctime)
                ctimes.append(ctime)

        if len(ctimes) == 0:
            logging.warning(f"Warning: could not access files from {package}")
            ctimes.append(self.now_ts)

        latest_ctime=max(ctimes)

        return latest_ctime

    def _calculate_days_time(self, atime):
        timestamp_datetime=datetime.fromtimestamp(atime)
        time_difference=self.now-timestamp_datetime
        difference_in_days = time_difference.days
        return difference_in_days

    def process(self, check_depending_packages=False, since_upgrade=False, use_ctime=False, rusty_time=30):
        packages=RustyPackages._fetch_all_packages()

        required_by={}
        package_time={}

        # calcualate atime/ctime for each package
        with logging_redirect_tqdm():
            for package in tqdm.tqdm(packages, leave=False, unit="package"):
                if use_ctime:
                    time=self._fetch_package_last_update(package)
                elif since_upgrade and RustyPackages._was_package_used_after_upgrade(package):
                    time=self.now_ts
                else:
                    time=self._fetch_package_last_usage(package)

                package_time[package]=time
                if check_depending_packages:
                    dependent_packages=RustyPackages._fetch_required_by(package)
                    required_by[package]=dependent_packages

        # include dependencies in atime
        if check_depending_packages:
            package_and_deps_time={}
            for package in packages:
                time=package_time[package]
                package_required_by=required_by[package]
                for dependent in package_required_by:
                    ratime=package_time[dependent]
                    time=max(time, ratime)
                package_and_deps_time[package]=time
            package_time=package_and_deps_time

        # find rusty ones
        rusty_packages=[]
        for package in packages:
            time=package_time[package]
            days=self._calculate_days_time(time)

            if days > rusty_time:
                rusty_packages.append((days, package))

        # print them out
        sorted_packages=sorted(rusty_packages)
        logging.info(f"Found {len(sorted_packages)} rusty packages")

        for package in sorted_packages:
            if use_ctime:
                logging.info(f"package {package[1]} not upgraded for {package[0]} days.")
            else:
                logging.info(f"package {package[1]} not used for {package[0]} days.")



if __name__ == '__main__':
    logging.basicConfig(format='', level=logging.INFO)
    parser = argparse.ArgumentParser(description='Look for unused packages.')
    parser.add_argument("--follow-deps", "-d",
                        action='store_true',
                        default=False,
                        help="When calculating package's last use time, take into consideration last use of packages depending on it also. Not allowed with --last-upgraded")

    parser.add_argument("--since-upgrade", "-u",
                        action='store_true',
                        default=False,
                        help="Show packages not used since last upgrade only. Not allowed with --last-upgraded")

    parser.add_argument("--last-upgraded", "-l",
                        action='store_true',
                        default=False,
                        help="Instead of last use time, look for last update time. This allows finding packages not updated for a long time. Not allowed with --since-upgrade")

    parser.add_argument("--time", "-t",
                        action='store',
                        default=30,
                        help="Show packages not used for more than specified number of days. Default is 30.")

    args = parser.parse_args(sys.argv[1:])
    rusty_time=int(args.time)

    if rusty_time < 0:
        logging.error("--time needs to be 0 at least")
        exit(1)

    if (args.since_upgrade and args.last_upgraded):
        logging.error("--since-upgrade and --last-upgraded are mutually exclusive")
        exit(1)

    if (args.follow_deps and args.last_upgraded):
        logging.error("--follow-deps and --last-upgraded are mutually exclusive")
        exit(1)

    p=RustyPackages()
    p.process(check_depending_packages=args.follow_deps, since_upgrade=args.since_upgrade, use_ctime=args.last_upgraded, rusty_time=rusty_time)
