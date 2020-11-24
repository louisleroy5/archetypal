import shutil
import subprocess
import time
from threading import Thread

from eppy.runner.run_functions import paths_from_version
from path import Path
from tqdm import tqdm

from archetypal import log
from archetypal.eplus_interface.energy_plus import EnergyPlusProgram
from archetypal.eplus_interface.exceptions import EnergyPlusVersionError
from archetypal.eplus_interface.version import EnergyPlusVersion


class ExpandObjectsExe(EnergyPlusProgram):
    def __init__(self, idf):
        super().__init__(idf)

    @property
    def expandobjs_dir(self):
        return self.eplus_home

    @property
    def cmd(self):
        return ["ExpandObjects"]


class ExpandObjectsThread(Thread):
    def __init__(self, idf, tmp):
        """

        Args:
            idf (IDF):
        """
        super(ExpandObjectsThread, self).__init__()
        self.p = None
        self.std_out = None
        self.std_err = None
        self.idf = idf
        self.cancelled = False
        self.run_dir = Path("")
        self.exception = None
        self.name = "ExpandObjects_" + self.idf.name
        self.tmp = tmp

    def run(self):
        """Wrapper around the EnergyPlus command line interface.

        Adapted from :func:`eppy.runner.runfunctions.run`.
        """
        try:
            self.cancelled = False
            # get version from IDF object or by parsing the IDF file for it

            tmp = self.tmp
            self.epw = self.idf.epw.copy(tmp / "in.epw").expand()
            self.idfname = Path(self.idf.savecopy(tmp / "in.idf")).expand()
            self.idd = self.idf.iddname.copy(tmp / "Energy+.idd").expand()
            self.expandobjectsexe = Path(
                shutil.which("ExpandObjects", path=self.eplus_home.expand())
            ).copy2(tmp)
            self.run_dir = Path(tmp).expand()

            # Run ExpandObjects Program
            self.cmd = str(self.expandobjectsexe.basename())
            with tqdm(
                unit_scale=True,
                miniters=1,
                desc=f"ExpandObjects #{self.idf.position}-{self.idf.name}",
                position=self.idf.position,
            ) as progress:

                self.p = subprocess.Popen(
                    ["./ExpandObjects"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    cwd=self.run_dir.abspath(),
                )
                start_time = time.time()
                # self.msg_callback("ExpandObjects started")
                for line in self.p.stdout:
                    self.msg_callback(line.decode("utf-8"))
                    progress.update()

                # We explicitly close stdout
                self.p.stdout.close()

                # Wait for process to complete
                self.p.wait()

                # Communicate callbacks
                if self.cancelled:
                    self.msg_callback("ExpandObjects cancelled")
                    # self.cancelled_callback(self.std_out, self.std_err)
                else:
                    if self.p.returncode == 0:
                        self.msg_callback(
                            "ExpandObjects completed in {:,.2f} seconds".format(
                                time.time() - start_time
                            )
                        )
                        self.success_callback()
                    else:
                        self.msg_callback("ExpandObjects failed")
        except Exception as e:
            self.exception = e

    def msg_callback(self, *args, **kwargs):
        log(*args, name=self.idf.name, **kwargs)

    def success_callback(self):
        if (self.run_dir / "expanded.idf").exists():
            self.idf.idfname = (self.run_dir / "expanded.idf").copy(
                self.idf.output_directory / self.idf.name
            )
        if (Path(self.run_dir) / "GHTIn.idf").exists():
            self.idf.include.append(
                (Path(self.run_dir) / "GHTIn.idf").copy(
                    self.idf.output_directory / "GHTIn.idf"
                )
            )

    def failure_callback(self):
        pass

    def cancelled_callback(self, stdin, stdout):
        pass

    @property
    def eplus_home(self):
        eplus_exe, eplus_home = paths_from_version(self.idf.as_version.dash)
        if not Path(eplus_home).exists():
            raise EnergyPlusVersionError(
                msg=f"No EnergyPlus Executable found for version "
                f"{EnergyPlusVersion(self.idf.as_version)}"
            )
        else:
            return Path(eplus_home)
