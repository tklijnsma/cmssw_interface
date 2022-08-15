import os, os.path as osp, shutil
import cmssw_interface

def cleanup(*files):
    if cmssw_interface.is_str(files): files = [files]
    for file in files:
        if osp.isfile(file):
            os.remove(file)
        elif osp.isdir(file):
            shutil.rmtree(file)


def test_run():
    assert cmssw_interface.run(['echo "Hello World!"']) == ["Hello World!"]


def test_testcmssw_exists():
    """
    Only tests if the test setup in conftest.py succeeded
    """
    assert osp.isdir('CMSSW_12_1_1')


def test_cmsrun_help():
    cmssw = cmssw_interface.CMSSW('CMSSW_12_1_1')
    assert cmssw.run(['cmsRun -h'])[0] == 'cmsRun [options] [--parameter-set] config_file '
    assert cmssw.run('cmsRun -h')[0] == 'cmsRun [options] [--parameter-set] config_file '


def test_tarball():
    cleanup('tarball.tar.gz')
    cmssw = cmssw_interface.CMSSW('CMSSW_12_1_1')
    cmssw_interface.tarball(cmssw, 'tarball.tar.gz')
    assert osp.isfile('tarball.tar.gz')
    cleanup('tarball.tar.gz')


def test_local_tarball():
    cleanup('tmpextracted', 'tarball.tar.gz')
    cmssw = cmssw_interface.CMSSW('CMSSW_12_1_1')
    cmssw_interface.tarball(cmssw, 'tarball.tar.gz')
    cmssw_from_tarball = cmssw_interface.CMSSW.from_tarball('tarball.tar.gz', dst='tmpextracted')
    assert cmssw_from_tarball.path == osp.abspath('tmpextracted/CMSSW_12_1_1')
    cleanup('tmpextracted', 'tarball.tar.gz')


def test_remote_tarball():
    # Put a tarball on the storage element, clean it up locally
    cleanup('tarball.tar.gz')
    cmssw = cmssw_interface.CMSSW('CMSSW_12_1_1')
    cmssw_interface.tarball(cmssw, 'tarball.tar.gz')
    cmssw_interface.run(['xrdcp tarball.tar.gz root://cmseos.fnal.gov//store/user/klijnsma/tarball.tar.gz'])
    cleanup('tarball.tar.gz')
    cmssw_from_tarball = cmssw_interface.CMSSW.from_tarball(
        'root://cmseos.fnal.gov//store/user/klijnsma/tarball.tar.gz',
        dst='tmpextracted'
        )
    assert cmssw_from_tarball.path == osp.abspath('tmpextracted/CMSSW_12_1_1')
    cleanup('tmpextracted', 'tarball.tar.gz')
    cmssw_interface.run(['xrdfs root://cmseos.fnal.gov/ rm /store/user/klijnsma/tarball.tar.gz'])
