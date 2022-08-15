# -*- coding: utf-8 -*-
import os.path as osp, logging, subprocess, os, time, pprint, sys, glob
from contextlib import contextmanager

PY3 = sys.version_info.major == 3
PY2 = sys.version_info.major == 2


INCLUDE_DIR = osp.join(osp.abspath(osp.dirname(__file__)), "include")
def version():
    with open(osp.join(INCLUDE_DIR, "VERSION"), "r") as f:
        return(f.read().strip())


def setup_logger(name='cmssw_interface'):
    if name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(name)
        logger.info('Logger %s is already defined', name)
    else:
        fmt = logging.Formatter(
            fmt = (
                '\033[33m%(levelname)7s:%(asctime)s:%(module)s:%(lineno)s\033[0m'
                + ' %(message)s'
                ),
            datefmt='%Y-%m-%d %H:%M:%S'
            )
        handler = logging.StreamHandler()
        handler.setFormatter(fmt)
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
    return logger
logger = setup_logger()
subprocess_logger = setup_logger('cmssw_subprocess_logger')
subprocess_logger.handlers[0].formatter._fmt = '\033[35m%(asctime)s\033[0m %(message)s'


def get_clean_env():
    """
    Returns a clean environment in which CMSSW may be set up.
    """
    env = os.environ.copy()
    for var in [
        "ROOTSYS", "PATH", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "SHLIB_PATH",
        "LIBPATH", "PYTHONPATH", "MANPATH", "CMAKE_PREFIX_PATH", "JUPYTER_PATH",
        # Added due to ROOT-env.sh
        "CPLUS_INCLUDE_PATH", "CXX", "ZLIB_HOME", "CURL_HOME", "DAVIX_HOME",
        "GSL_HOME", "SETUPTOOLS_HOME", "FONTCONFIG_HOME", "CAIRO_HOME", "SQLITE_HOME",
        "PIXMAN_HOME", "FREETYPE_HOME", "TBB_HOME", "FC", "PKG_CONFIG_HOME",
        "VC_HOME", "PNG_HOME", "FFTW_HOME", "BOOST_HOME", "VDT_HOME", "ROOT_HOME",
        "ZEROMQ_HOME", "LIBXML2_HOME", "PKG_CONFIG_PATH", "EXPAT_HOME",
        "COMPILER_PATH", "BLAS_HOME", "R_HOME", "XROOTD_HOME", "MYSQL_HOME",
        "GFAL_HOME", "CC", "C_INCLUDE_PATH", "PYTHON_HOME", "PYTHONHOME",
        "ORACLE_HOME", "GPERF_HOME", "SRM_IFCE_HOME", "NUMPY_HOME", "DCAP_HOME",
    ]:
        if var in env:
            del env[var]
    return env


def run(cmds, env=None):
    """
    Runs a list of commands using subprocess.
    """
    logger.info("Sending cmds:\n{0}".format(pprint.pformat(cmds)))
    if env == 'clean': env = get_clean_env()
    process = subprocess.Popen(
        "bash",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        bufsize=1,
        close_fds=True,
        **(dict(encoding='utf8') if PY3 else dict(universal_newlines=True))
        )
    # Break on first error (stdin will still be written but execution will be stopped)
    process.stdin.write("set -e\n")
    process.stdin.flush()
    # Send commands to stdin of the subprocess
    for cmd in cmds:
        if not (cmd.endswith("\n")): cmd += "\n"
        process.stdin.write(cmd)
        process.stdin.flush()
    process.stdin.close()
    # Collect output
    output = []
    process.stdout.flush()
    for line in iter(process.stdout.readline, ""):
        if len(line) == 0:
            break
        line = line.rstrip("\n")
        subprocess_logger.info(line)
        output.append(line)
    process.stdout.close()
    process.wait()
    returncode = process.returncode
    if returncode == 0:
        logger.info("Command exited with status 0 - all good")
        return output
    else:
        raise subprocess.CalledProcessError(cmd, returncode)


@contextmanager
def chdir(dst):
    cwd = os.getcwd()
    try:
        os.chdir(dst)
        yield dst
    finally:
        os.chdir(cwd)


def is_str(obj):
    if PY3:
        return isinstance(obj, str)
    else:
        return isinstance(obj, basestring) # type:ignore


class CMSSW:
    def __init__(self, path):
        path = osp.abspath(path)
        if not osp.basename(path).startswith('CMSSW_'):
            raise Exception('Initialization should have CMSSW_BASE as the argument')
        self.path = path
        self.is_renamed = False
        self.is_externallylinked = False

    @classmethod
    def from_tarball(cls, path, dst=None):
        """
        Initializes from a remotely stored tarball.
        """
        if dst is None:
            import tempfile
            dst = tempfile.mkdtemp()
        if not osp.isdir(dst):
            os.makedirs(dst)

        if '://' in path:
            try:
                import seutils # type:ignore
                seutils.cp(path, dst)
            except ImportError:
                cmd = 'xrdcp {} {}'.format(path, dst)
                logger.warning('Attempting copy with cmd %s', cmd)
                run([cmd])
            tarball = osp.join(dst, osp.basename(path))
            if not osp.isfile(tarball):
                raise Exception('Failed to download {}'.format(path))
        else:
            tarball = path

        cmssw_basename = get_contained_cmssw(tarball)
        if cmssw_basename is None:
            raise Exception('Tarball does not contain a directory called CMSSW_X_Y_Z')

        logger.warning("Extracting {0} ==> {1}".format(tarball, dst))
        run(['tar -xf {} -C {}'.format(tarball, dst)])

        return cls(osp.join(dst, cmssw_basename))


    @property
    def src(self):
        return osp.join(self.path, 'src')

    @property
    def scram_arch(self):
        if not hasattr(self, '_scram_arch'):
            self._scram_arch = None
            compiled_arches = glob.glob(osp.join(self.path, "bin/slc*"))
            if compiled_arches:
                self._scram_arch = osp.basename(compiled_arches[0])
                logger.info(
                    "Detected CMSSW was compiled with arch %s, using it",
                    self._scram_arch,
                    )
        return self._scram_arch

    def run_nocmsenv(self, cmds):
        """
        Preprends the basic CMSSW environment setup, and executes a set of
        commands in a clean environment
        """
        self.projectrename()
        with chdir(self.src):
            return run(
                [
                    "shopt -s expand_aliases",
                    "source /cvmfs/cms.cern.ch/cmsset_default.sh",
                    "export SCRAM_ARCH={0}".format(self.scram_arch),
                    ]
                + cmds,
                env='clean'
                )

    def projectrename(self):
        if self.is_renamed: return
        self.is_renamed = True
        logger.info("Doing scram b ProjectRename for %s", self.path)
        self.run_nocmsenv(["scram b ProjectRename"])

    def run(self, cmds):
        """
        Main entrypoint for executing commands in the CMSSW environment.
        Prepends basic environment setup (cmsset_default.sh, cmsenv, etc.)
        and runs the passed list of commands.
        Returns the captured stdout.
        Takes a list of strings, but if a single string is passed will format automatically.
        """
        if is_str(cmds): cmds = [cmds]
        return self.run_nocmsenv(['cmsenv'] + cmds)

    def externallinks(self):
        if self.self.is_externallylinked: return
        self.self.is_externallylinked = True
        logger.info("Doing scram b ExternalLinks for %s", self.path)
        self.run_nocmsenv(["scram b ExternalLinks"])


def tarball(cmssw, dst, exclude=None):
    """
    Makes a tarball out of a CMSSW instance.
    """
    if osp.isfile(dst): raise OSError("{0} already exists".format(dst))
    logger.warning("Tarballing {0} ==> {1}".format(cmssw.path, dst))

    if exclude is None:
        exclude = []
    elif is_str(exclude):
        exclude = [exclude]

    cmd = 'tar -zcvf {} --exclude-vcs --exclude-caches-all'.format(dst)
    for item in exclude:
        cmd += ' --exclude=' + item
    cmd += ' ' + osp.basename(cmssw.path)

    with chdir(osp.dirname(cmssw.path)):
        run([cmd])

    return dst


def get_contained_cmssw(tarball):
    """
    Returns the first element in a tarball whose name starts with 'CMSSW'
    """
    import tarfile
    for name in tarfile.open(tarball).getnames():
        if name.startswith("CMSSW"):
            return name
    else:
        logger.error('Could not find an element in %s that starts with CMSSW', tarball)
