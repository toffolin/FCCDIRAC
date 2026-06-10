# Last modified: L. Toffolin, 9/6/2026
#************************** libraries importation **************************#

#DIRAC libraries
__RCSID__ = "$Id$"
from DIRAC.Core.Utilities.Subprocess import shellCall
from ILCDIRAC.Workflow.Modules.ModuleBase import ModuleBase, generateRandomString
from ILCDIRAC.Core.Utilities.CombinedSoftwareInstallation import getSoftwareFolder
from ILCDIRAC.Core.Utilities.PrepareOptionFiles import getNewLDLibs
from ILCDIRAC.Core.Utilities.ResolveDependencies import resolveDeps
from ILCDIRAC.Core.Utilities.resolvePathsAndNames import getProdFilename
from DIRAC import gLogger, S_OK, S_ERROR

#standard libraries
import os
import stat
from os import listdir
import subprocess
import tarfile
import shutil
    

#************************************* Classes - Definition ******************************#

#*****************************************#
# Class : ExecutionModule()               #
# role : Uncompress compressed folders    #
# needed by  the application, generate    #
# a script that will run the job          #
#*****************************************#
    
class ExecutionModule(ModuleBase):
  
    """ Run FCC softs  """
  
    def __init__(self):

        super(ExecutionModule, self).__init__()

        self.enable = True
        self.STEP_NUMBER = ''

        self.script_to_source = ''
        self.fcc_executable = ''
        self.fcc_conf_file = ''
        self.fcc_input_files = ''        
        self.fcc_output_file = ''
        self.fccsw = ''
        self.number_of_events = ''

        self.debug = True
        self.log = gLogger.getSubLogger("ExecutionModule")
        self.sourcingFCCStack = ''    
        self.script_name = os.path.join(os.getcwd(), 'user_temp_job.sh')
  

    def uncompress(self, compressed_folder):

        tar = tarfile.open(compressed_folder)

        output_dir, file_extension = os.path.splitext(compressed_folder)

        for item in tar:
            tar.extract(item, output_dir)


    def execute(self):
        """ Run the module
        """

        print('EXECUTABLE')
        print(self.fcc_executable)

        print('\n'.join(os.listdir(os.getcwd())))

        if '' != self.fccsw:

            for file in os.listdir(os.getcwd()):
                if file.endswith('.tgz'):
                    self.uncompress(file)

        if not self.fcc_conf_file.startswith('/cvmfs/'):
            self.fcc_conf_file = os.path.abspath(os.path.basename(self.fcc_conf_file))

        bash_commands = [self.fcc_executable + " " + self.fcc_output_file + " " + self.fcc_conf_file + " " + self.number_of_events]
        self.generate_bash_script(bash_commands, self.script_name)    

        #set environnement + execute job
        p = subprocess.call(self.script_name)

        status = 0

        return self.finalStatusReport(status)
  
  
    def chmod(self, file, permission):

        USER_PERMISSION = eval('stat.S_I' + permission + 'USR')
        GROUP_PERMISSION = eval('stat.S_I' + permission + 'GRP')
        OTHER_PERMISSION = eval('stat.S_I' + permission + 'OTH')

        PERMISSION = USER_PERMISSION | GROUP_PERMISSION | OTHER_PERMISSION

        mode = os.stat(file).st_mode

        os.chmod(file, mode | PERMISSION)


    def generate_bash_script(self, commands, script_name):

        shebang = "#!/bin/bash"
        test1 = "echo $LD_LIBRARY_PATH"
        test3 = "unset LD_LIBRARY_PATH"

        if not self.script_to_source.startswith('/cvmfs/'):
            self.script_to_source = os.path.abspath(os.path.basename(self.script_to_source))

        self.sourcingFCCStack = 'source ' + self.script_to_source
             
        bash_script_text = [shebang, test1, test3, self.sourcingFCCStack, test1] + commands    

        print('\n'.join(bash_script_text))

        self.write2file('w', script_name, '\n'.join(bash_script_text) + '\n')    

        self.chmod(script_name, 'R')    
        self.chmod(script_name, 'X')


    def write2file(self, operation, file_name, filetext):
    
        try:
            with open(file_name, operation) as text_file:
                text_file.write(filetext)
        except:
            print('Error in writting file')
            quit()