# Last modified: L. Toffolin, 9/6/2026
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

#finally, we can submit the 1st FCC job containing 2 applications in this case
fcc.submit()

