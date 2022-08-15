import os.path as osp, shutil

import cmssw_interface

def pytest_sessionstart(session):
    if not osp.isdir('CMSSW_12_1_1'):
        cmssw_interface.run([
            'shopt -s expand_aliases',
            'source /cvmfs/cms.cern.ch/cmsset_default.sh',
            'cmsrel CMSSW_12_1_1'
            ])

def pytest_sessionfinish(session, exitstatus):
    if osp.isdir('CMSSW_12_1_1'):
        shutil.rmtree('CMSSW_12_1_1')
