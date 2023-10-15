
import os
import stat
import subprocess
import time
from datetime import datetime


class Packages:
    def __init__(self):
        self.package_times={}
        self.now=datetime.now()

    @staticmethod
    def _run_command(command: [str]) -> [str]:
        result=subprocess.run(command, stdout=subprocess.PIPE)
        return result.stdout.splitlines()

    @staticmethod
    def _fetch_package_last_usage(package: str) -> int:
        versions_and_files=Packages._run_command(["pacman", "-Ql", package])
        files=[entry.decode("utf-8").split(maxsplit=1)[1] for entry in versions_and_files]

        atimes=[]
        for file in files:
            try:
                file_stat=os.stat(file)
            except PermissionError:
                pass
            except FileNotFoundError:
                print(f"Warning: missing file: {file} from {package}")
            else:
                if stat.S_ISREG(file_stat.st_mode):
                    atime=int(file_stat.st_atime)
                    atimes.append(atime)

        if len(atimes) == 0:
            print(f"Warning: could not access files from {package}")
            atimes.append(time.time())

        latest_atime=max(atimes)

        return latest_atime

    @staticmethod
    def _fetch_all_packages() -> [str]:
        packages_and_versions=Packages._run_command(["pacman", "-Q"])
        packages=[entry.decode("utf-8").split(maxsplit=1)[0] for entry in packages_and_versions]
        return packages

    def _calculate_stale_time(self, atime):
        timestamp_datetime=datetime.fromtimestamp(atime)
        time_difference=self.now-timestamp_datetime
        difference_in_days = time_difference.days
        return difference_in_days

    def _get_package_last_usage(self, package: str) -> int:
        atime=self.package_times.get(package)
        if (atime is None):
            atime=Packages._fetch_package_last_usage(package)
            self.package_times[package]=atime
        return atime

    def process(self):
        packages=Packages._fetch_all_packages()

        for package in packages:
            atime=self._get_package_last_usage(package)
            stale=self._calculate_stale_time(atime)

            print(f"Package {package} not used for {stale} days")


p=Packages()
p.process()
