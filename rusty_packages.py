
import os
import progressbar
import stat
import subprocess
import time
from datetime import datetime


class RustyPackages:
    def __init__(self):
        self.package_times={}
        self.now_ts=time.time()
        self.now=datetime.now()

    @staticmethod
    def _run_command(command: [str]) -> [str]:
        result=subprocess.run(command, stdout=subprocess.PIPE, env={"LC_ALL": "C"})
        return result.stdout.splitlines()

    def _fetch_package_last_usage(self, package: str) -> int:
        versions_and_files=RustyPackages._run_command(["pacman", "-Ql", package])
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
            atimes.append(self.now_ts)

        latest_atime=max(atimes)

        return latest_atime

    @staticmethod
    def _fetch_all_packages() -> [str]:
        packages_and_versions=RustyPackages._run_command(["pacman", "-Q"])
        packages=[entry.decode("utf-8").split(maxsplit=1)[0] for entry in packages_and_versions]
        return packages

    @staticmethod
    def _fetch_required_by(package: str) -> [str]:
        required_by=[]
        package_info=RustyPackages()._run_command(["pacman", "-Qii", package])
        for info in package_info:
            info=info.decode("utf-8")
            if info.startswith("Required By"):
                packages=info.split(":")[1]
                packages=packages.strip()

                if packages != "None":
                    required_by=packages.split()
                break

        return required_by

    def _calculate_days_time(self, atime):
        timestamp_datetime=datetime.fromtimestamp(atime)
        time_difference=self.now-timestamp_datetime
        difference_in_days = time_difference.days
        return difference_in_days

    def _get_package_last_usage(self, package: str) -> int:
        atime=self.package_times.get(package)
        if (atime is None):
            atime=self._fetch_package_last_usage(package)
            self.package_times[package]=atime
        return atime

    def process(self):
        packages=RustyPackages._fetch_all_packages()

        rusty_packages=[]
        for i in progressbar.progressbar(range(len(packages)), redirect_stdout=True):
            package=packages[i]
            atime=self._get_package_last_usage(package)
            required_by=RustyPackages._fetch_required_by(package)

            for required in required_by:
                ratime=self._get_package_last_usage(required)
                atime=max(atime, ratime)

            days=self._calculate_days_time(atime)

            if days > 30:
                rusty_packages.append((days, package))

        sorted_packages=sorted(rusty_packages)
        for package in sorted_packages:
            print(f"package {package[1]} not used for {package[0]} days.")


p=RustyPackages()
p.process()
