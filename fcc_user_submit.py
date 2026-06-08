#!/bin/env python

#************************** libraries importation **************************#

#user libraries
#importations of fcc core classes
from fcc_core import *

#standard libraries
import os

        
#1st FCC job
fcc = Job()

#we specify the source we script
#for now the same for each job
fcc.set_sourcing_script(os.path.join(os.getcwd(), "init_fcc.sh"))

#1st application of the 1st FCC job

#---------------FCC PHYSICS---------------------------------#
fcc_physics = Application()


fcc_physics.set_executable('fcc-pythia8-generate')
fcc_physics.set_configuration_file('/cvmfs/fcc.cern.ch/sw/0.7/fcc-physics/0.1/x86_64-slc6-gcc49-opt/share/ee_ZH_Zmumu_Hbb.txt')

#we add the application to the job
fcc.append(fcc_physics)




#2nd application of the 1st FCC job

#---------------FCCSW---------------------------------#
fccsw = Application()


fccsw_path = '/build/<YOUR_USERNAME>/FCC/FCCSW'

#we test these 2 configurations succesfully
#conf_file = os.path.join(fccsw_path,'Examples/options/geant_pgun_fullsim.py')
conf_file = os.path.join(fccsw_path,'Examples/options/simple_pythia.py')

#stuff to call gaudirun.py
python = '/cvmfs/lhcb.cern.ch/lib/lcg/releases/LCG_83/Python/2.7.9.p1/x86_64-slc6-gcc49-opt/bin/python2.7'
xenv = '/cvmfs/lhcb.cern.ch/lib/lhcb/LBSCRIPTS/LBSCRIPTS_v8r5p3/LbUtils/cmake/xenv'
arg_xenv  = 'InstallArea/FCCSW.xenv'
exe = 'gaudirun.py'


fccsw.set_executable('exec ' + python + ' ' + xenv + ' ' + arg_xenv + ' ' + exe)
fccsw.set_configuration_file(conf_file)


fccsw.set_fccsw_path(fccsw_path)

#example of how to add 'extra' files or folders
#fccsw.add_paths(['/afs/cern.ch/user/<YOUR_INITIAL>/<YOUR_USERNAME>/foo.bar','/afs/cern.ch/user/<YOUR_INITIAL>/<YOUR_USERNAME>/HelloWorld'])

fcc.append(fccsw)

#finally, we can submit the 1st FCC job containing 2 applications in this case
fcc.submit()
