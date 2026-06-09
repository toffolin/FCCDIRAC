# Last modified: L. Toffolin, 9/6/2026
#************************** libraries importation **************************#

#standard libraries
import os
import sys
import tarfile
import re
from shutil import copyfile

#Xrootd python API used for EOS
from XRootD import client
from XRootD.client.flags import DirListFlags, OpenFlags, MkDirFlags, QueryCode

#DIRAC libraries
from DIRAC.Core.Base import Script
Script.parseCommandLine()

from ILCDIRAC.Interfaces.API.DiracILC import DiracILC
from ILCDIRAC.Interfaces.API.NewInterface.UserJob import UserJob
from ILCDIRAC.Interfaces.API.NewInterface.Applications import GenericApplication


#************************************* Classes - Definition ******************************#

#********************************************************#
# Class : Submit()                                       #
# role : This class contains methods :                   #
# - to set the sandbox (prepare files for the DIRAC job) #
# - to look for files needed by FCC Applications         #
# and then submit the job to DIRAC                       #
#********************************************************#

class Submit:


    #*****************************************#
    # Function name : __init__                #
    # role : create a DIRAC job, an instance  #
    # of DiracILC, and filter the output      #
    #*****************************************#

    def __init__(self):
    
        self.dIlc = DiracILC(False)

        self.job = UserJob()
        self.job.setJobGroup("FCC")
        self.job.setName("FCC APP")  
        self.job.setOutputSandbox(["*.log", '*.root'])
        
        #EOS public location
        self.EOS_MGM_URL = 'root://eospublic.cern.ch'
        #EOS environment
        self.setEOS = 'export EOS_MGM_URL=' + self.EOS_MGM_URL
        self.myclient = client.FileSystem(self.EOS_MGM_URL + ':1094')

        #sandbox
        self.InputSandbox = []
        self.folders_to_upload = []
        self.filtered_extensions = [] 
        self.excludes_or_includes = []
        self.temp_cwd = os.path.join(os.getcwd(), 'fcc_temp_dirac')
        
    def read_from_file(self, file_name):
        try:
            with open(file_name, 'r') as f:
                content = f.read()
            return content
        except:
            return False
    
    def create_temp_tree_from_files(self, files, fccsw_path):
        if files:
            for file in files:
                tree = os.path.dirname(file)
                tree_full_path = os.path.join(self.temp_cwd, tree)
                if not os.path.exists(tree_full_path):    
                    os.makedirs(tree_full_path)
                root_folder = tree.split(os.path.sep)[0] 
                root_folder_full_path = os.path.join(self.temp_cwd, root_folder)

                if root_folder_full_path not in self.folders_to_upload:
                    self.folders_to_upload += [root_folder_full_path]
                
                source = os.path.join(fccsw_path, file)
                destination = os.path.join(self.temp_cwd, file)
                
                if not os.path.exists(source):
                    print('\nThe file : ' + source + ' does not exist\n')
                    quit()
                else:     
                    copyfile(source, destination)

    def compress(self, temp_folder, actual_folder, tar_extension, filtered_extension, exclude_or_include):

        exclude_func = None
        
        if filtered_extension is not False:
            if exclude_or_include:    
                exclude_func = lambda filename: filename.find(filtered_extension) >= 0
            else:
                exclude_func = lambda filename: os.path.isfile(filename) and filename.find(filtered_extension) < 0
        
        tar = tarfile.open(temp_folder + tar_extension, "w:gz")

        for name in os.listdir(actual_folder):
            renamed = os.path.join(actual_folder, name)
            tar.add(renamed, arcname=os.path.basename(renamed), exclude=exclude_func)
    
        tar.close()

    def find_eos_file(self, file_name):

        eos_file_full_path = self.EOS_MGM_URL + '/' + file_name

        with client.File() as eosFile:
            file_status = eosFile.open(eos_file_full_path, OpenFlags.UPDATE)

        status = self.XRootDStatus2Dictionnary(file_status)

        if status is False or status.get(' ok') == 'False':
            return file_name, False
        else:
            return eos_file_full_path, True

    def find_eos_folder(self, folder_name):

        eos_folder_full_path = self.EOS_MGM_URL + '/' + folder_name

        status, listing = self.myclient.dirlist(folder_name, DirListFlags.STAT)
   
        if listing is None:
            return folder_name, False 
        else:
            return eos_folder_full_path, True       

    def find_path(self, path, file_or_dir='file'):

        if not path.startswith('/eos/'):
            if path.startswith('/afs/') and os.path.exists(path):
                return os.path.abspath(path), True
            elif os.path.exists(os.path.abspath(path)):            
                return os.path.abspath(path), True
            else:
                return path, False

        elif path.startswith('/eos/'):
            
            file_path, is_file_exist = self.find_eos_file(path)
            folder_path, is_folder_exist = self.find_eos_folder(path) 
            
            if is_file_exist:
                return file_path, is_file_exist
            elif is_folder_exist:    
                return folder_path, is_folder_exist
            else:
                return path, False 
        else:
            return path, False
    
    def upload_sandbox_with_application_files(self, paths):
    
        upload_path_message = " does not exist\nPlease ensure that your path exist in an accessible file system (EOS or AFS)\n"
            
        for path in paths:
        
            if not path.startswith('/cvmfs/'):

                path, is_exist = self.find_path(path)
                if is_exist is False:
                    message = "\nThe path '" + path + "'" + upload_path_message
                else:
                    if path.startswith('/afs/'):
                        print('\nWARNING : STORING FILES ON AFS IS DEPRECATED\n')
                        print('\nYou plan to upload :' + path + ' which is stored on AFS\n')
                    
                    if os.path.isfile(path):    
                        self.InputSandbox += [path]
                    else:
                        self.folders_to_upload += [path]

    def upload_sandbox_with_fccsw_files(self, fccsw_path, fcc_conf_file):
  
        InstallArea_folder = os.path.join(fccsw_path, 'InstallArea')
        Detector_folder = os.path.join(fccsw_path, 'Detector')
    
        fccsw_folders = [InstallArea_folder, Detector_folder]            

        self.filtered_extensions += ['.dbg', '.xml']
        self.excludes_or_includes += [True, False]
        
        content = self.read_from_file(fcc_conf_file)

        if content is False:
            print("\nError in reading configuration file :\n" + fcc_conf_file)
            quit()
            
        txt_files = re.findall(r'="(.*.txt)', content)
        cmd_files = re.findall(r'filename="(.*.cmd)', content)

        folders = self.create_temp_tree_from_files(txt_files, fccsw_path)
        if folders is not None:
            fccsw_folders += folders
            
        folders = self.create_temp_tree_from_files(cmd_files, fccsw_path)
        if folders is not None:
            fccsw_folders += folders
            
        self.folders_to_upload = fccsw_folders + self.folders_to_upload

    def update_sandbox(self, fccsw_path, paths, fcc_conf_file):

        if not os.path.exists(self.temp_cwd):
            os.makedirs(self.temp_cwd)

        if paths != '':                        
            self.upload_sandbox_with_application_files(paths) 

        if fccsw_path != '':
            self.upload_sandbox_with_fccsw_files(fccsw_path, fcc_conf_file)
    
    def compress_sandbox_subfolders(self):
    
        compressed_folders = []
            
        for idx, actual_folder in enumerate(self.folders_to_upload):    
            
            tar_extension = '.tgz'

            if idx < len(self.filtered_extensions):
                filtered_extension = self.filtered_extensions[idx]
                exclude_or_include = self.excludes_or_includes[idx]
            else:
                filtered_extension = False
                exclude_or_include = False
                
            temp_folder = os.path.join(self.temp_cwd, os.path.basename(actual_folder)) 

            self.compress(temp_folder, actual_folder, tar_extension, filtered_extension, exclude_or_include)

            compressed_folders += [temp_folder + tar_extension]
        
        self.InputSandbox += compressed_folders                
            
    def submit(self, applications, script_to_source):
    
        fcc_execution_module = os.path.join(os.getcwd(), "fcc_execution_module.py")
        fcc_installation_module = os.path.join(os.getcwd(), 'fcc_installation_module.py')
        
        fcc_environment = script_to_source
        
        paths = [fcc_execution_module, fcc_environment]      
        self.upload_sandbox_with_application_files(paths)
                       
        for application in applications:
        
            job_specification = application.job_specification
        
            fcc_executable = job_specification['fcc_executable'] 
            fccsw_path = job_specification['fccsw_path'] 
            paths = job_specification['paths']
            fcc_conf_file = job_specification['fcc_conf_file']            
            fcc_input_files = '' if job_specification['fcc_input_files'] == '' else ' --ifiles ' + ' '.join(job_specification['fcc_input_files'])
            fcc_output_file = '' if job_specification['fcc_output_file'] == '' else ' --ofile ' + job_specification['fcc_output_file']
            fccsw = '' if job_specification['fccsw_path'] == '' else ' --fccsw ' + job_specification['fccsw_path']
            number_of_events = '' if job_specification['number_of_events'] == '' else ' -N ' + job_specification['number_of_events']

            if fcc_executable == '' or fcc_conf_file == '' or fcc_environment == '':
                print("\nError in parsing applications :\n" + fcc_executable)
                print("\nYou have to provide at least an executable, a configuration file and a script to source for each application\n")
                quit()
                
            self.update_sandbox(fccsw_path, paths, fcc_conf_file)

            generic_dirac_application = GenericApplication()
            generic_dirac_application.setScript(fcc_installation_module)

            arguments = '--source ' + fcc_environment + ' --exec ' + fcc_executable + ' --conf ' + fcc_conf_file + fcc_input_files + fcc_output_file + fccsw + number_of_events
            generic_dirac_application.setExtraCLIArguments(arguments)

            try:
                res = self.job.append(generic_dirac_application)
                if not res['OK']:
                    print(res['Message'])
                    quit()
            except:
                print("\nPlease, configure your proxy before submitting a job from DIRAC")
                print("If you do not set up a proxy, refer to the manual or maybe you have to refresh it")
                print("by typing :")
                print("dirac-proxy-init\n") 
                quit()

        self.compress_sandbox_subfolders()        
                
        print('\n**********************************HERE THE CONTENT OF YOUR SANDBOX*********************************\n')
        print(self.InputSandbox)
        print('\n**********************************HERE THE CONTENT OF YOUR SANDBOX*********************************\n')
                
        self.job.setInputSandbox(self.InputSandbox)
        
        res = self.job.submit(self.dIlc)
        if not res['OK']:
            print('Please check your application requirements')
            print(res['Message'])
            quit()
        else:
            print("The Job you submited has the following ID : " + str(res['JobID']))