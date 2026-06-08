# Last modified: 8/6/2026
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

class Submit():


    #*****************************************#
    # Function name : __init__                #
    # role : create a DIRAC job, an instance  #
    # of DiracILC, and filter the output      #
    #*****************************************#

    def __init__(self):
    
        self.dIlc = DiracILC(False)


        self.job = UserJob()
        self.job.setJobGroup( "FCC" )
        self.job.setName( "FCC APP" )  
        self.job.setOutputSandbox(["*.log",'*.root'])
        #self.job.setDestination('LCG.DESY-HH.de')
        
        #EOS public location
        self.EOS_MGM_URL= 'root://eospublic.cern.ch'
        #EOS environment
        self.setEOS = 'export EOS_MGM_URL=' + self.EOS_MGM_URL
        self.myclient = client.FileSystem(self.EOS_MGM_URL + ':1094')


        #sandbox
        self.InputSandbox = []
        self.folders_to_upload = []
        self.filtered_extensions = [] 
        self.excludes_or_includes = []
        self.temp_cwd = os.path.join(os.getcwd(),'fcc_temp_dirac')
        
    #********************************************#
    # Function name : read_from_file             #
    # input : file_name                          #
    # role : read a file and return its content  #
    #********************************************#

    def read_from_file(self,file_name):

        try:
            
            with open(file_name, 'r') as f:
                content = f.read()
            return content
        except:
            return False
    
    #*********************************************************************************#
    # Function name : create_temp_tree_from_files                                     #
    # role : given a relative tree path of file to the local FCCSW folder of the user #
    # it looks for this file, recreates the relative tree in a temporary folder       # 
    # containing only this file and not all files of the source folder                #
    # Finally, the folder will be added to the DIRAC sandbox                          #
    #*********************************************************************************#
    
    def create_temp_tree_from_files(self,files,fccsw_path):
        
                    
        if files:
            for file in files:
                tree = os.path.dirname(file)
                tree_full_path = os.path.join(self.temp_cwd,tree)
                if not os.path.exists(tree_full_path):    
                    os.makedirs(tree_full_path)
                root_folder = tree.split(os.path.sep)[0] 
                root_folder_full_path = os.path.join(self.temp_cwd,root_folder)

                if root_folder_full_path not in self.folders_to_upload:
                    self.folders_to_upload += [root_folder_full_path]
                
                source = os.path.join(fccsw_path,file)
                destination = os.path.join(self.temp_cwd,file)
                
                if not os.path.exists(source):
                    print '\nThe file : ' +  source + ' does not exist\n'
                    quit()
                else:     
                    copyfile(source,destination)




    #***************************************************#
    # Function name : compress                          #
    # role : it compress all folders, the job           #  
    # will need once in the grid                        #
    #***************************************************#
        
    def compress(self,temp_folder,actual_folder,tar_extension,filtered_extension,exclude_or_include):

        #print filtered_extension,exclude_or_include
        
        exclude_func = None
        
        if False is not filtered_extension:
        
            if exclude_or_include:    
                exclude_func = lambda filename: filename.find(filtered_extension)>=0 
            else:
                exclude_func = lambda filename: os.path.isfile(filename) and filename.find(filtered_extension)<0
        
        
        tar = tarfile.open(temp_folder + tar_extension, "w:gz")

        for name in os.listdir(actual_folder):
            #print name
            renamed = os.path.join(actual_folder,name)
            #print renamed
            #print os.path.basename(renamed)
            
            tar.add(renamed,arcname=os.path.basename(renamed),exclude=exclude_func)
    

        tar.close()

    #*************************************************#
    # Function name : find_eos_file                   #
    # input : file_name                               #
    # role : check if file exists on EOS              #
    # before sending the job to DIRAC                 #
    #*************************************************#


    def find_eos_file(self,file_name):
        #then the file is in EOS


        eos_file_full_path = self.EOS_MGM_URL + '/' + file_name

        with client.File() as eosFile:
            file_status = eosFile.open(eos_file_full_path,OpenFlags.UPDATE)


        #problem with file created directly on eos
        #no problem with uploded files with xrdcp cmd

        #print eos_file_full_path
        #print file_status
        status = self.XRootDStatus2Dictionnary(file_status)

        if 'False' == status[' ok'] or False == status:
            return file_name,False
        else:
            return eos_file_full_path,True

    #*************************************************#
    # Function name : find_eos_folder                 #
    # input : folder_name                             #
    # role : check if folder exists on eos            #
    # before sending the job to the worker            #
    #*************************************************#


    def find_eos_folder(self,folder_name):
        #then the file is in eos
        
        eos_folder_full_path = self.EOS_MGM_URL + '/' + folder_name

        status, listing = self.myclient.dirlist(folder_name, DirListFlags.STAT)
   
        if None == listing:
            return folder_name,False 
        else:
            return  eos_folder_full_path,True       
   
    


    #*************************************************#
    # Function name : find_path                       #
    # input : file_name                               #
    # role : check if file/folder exists on afs       #
    # before checking on eos                          #
    #*************************************************#

    def find_path(self,path,file_or_dir='file'):
        
        

        #we suppose that the user enter absolute or relative afs path
        #or only absolute eos path

        if not path.startswith('/eos/'):
        #afs path are absolute or relative
        #because software are stored in this filesystem
        #and users generally submit their job from lxplus

            
            #absolute path provided
            #os.isabs not cross platform
            #i used startwith...
            if path.startswith('/afs/') and os.path.exists(path):
                return os.path.abspath(path), True
            #if relative (does not start with /afs/)
            #add cwd    
            elif os.path.exists(os.path.abspath(path)):            
                return os.path.abspath(path), True
            #maybe local user machine, print upload error message    
            else:
                return path,False

        #absolute path
        elif path.startswith('/eos/'):
            #print "the file is in eos"        
            
            #eos path are absolute
            
            file_path , is_file_exist = self.find_eos_file(path)
        
            folder_path , is_folder_exist = self.find_eos_folder(path) 
            
            if is_file_exist:
                return file_path , is_file_exist
            elif is_folder_exist:    
                return folder_path , is_folder_exist
            else:
                return path,False 
        else:#other file system
            return path,False
    
    #********************************************************#
    # Function name : upload_sandbox_with_application_files  #
    # role : upload all extra folders or files               #
    # specified by the user for an application               #
    # For now, we do not check if file exists on cvmfs       #
    #********************************************************# 
    
    def upload_sandbox_with_application_files(self,paths):
    
        upload_path_message = " does not exist\nPlease ensure that your path exist in an accessible file system (EOS or AFS)\n"
            
       
        for path in paths:
        
            if not path.startswith('/cvmfs/'):

                path , is_exist = self.find_path(path)
                if False == is_exist:
                    message = "\nThe path '" + path + "'" + upload_path_message
                else:
                    if path.startswith('/afs/'):
                        print '\nWARNING : STORING FILES ON AFS IS DEPRECATED\n'
                        print '\nYou plan to upload :' + path + ' which is stored on AFS\n'
                    
                    #files are directly added to the sandbox                        
                    if os.path.isfile(path):    
                        self.InputSandbox += [path]
                    else :#folders are compressed before
                        self.folders_to_upload += [path]

    #********************************************************#
    # Function name : upload_sandbox_with_fccsw_files        #
    # role : upload files called in FCCSW configuration file #
    # and needed folders relative to FCCSW                   #
    #********************************************************#      
  
    def upload_sandbox_with_fccsw_files(self,fccsw_path,fcc_conf_file):
  
 
        InstallArea_folder = os.path.join(fccsw_path,'InstallArea')
        
        Detector_folder = os.path.join(fccsw_path,'Detector')
    
        fccsw_folders = [InstallArea_folder,Detector_folder]            

        #explanation
        #InstallArea_folder : dbg files are excluded
        #Detector_folder : only xml files are included
        self.filtered_extensions += ['.dbg','.xml']
        
        self.excludes_or_includes += [True,False]
        
        content = self.read_from_file(fcc_conf_file)

        if False is content :
            print "\nError in reading configuration file :\n" + fcc_conf_file
            quit()
            
        #xml_files = re.findall(r'file:(.*.xml)',content)

        txt_files = re.findall(r'="(.*.txt)',content)

        cmd_files = re.findall(r'filename="(.*.cmd)',content)

        #print txt_files
        #print cmd_files
        

       
        folders = self.create_temp_tree_from_files(txt_files,fccsw_path)
        if None != folders:
            fccsw_folders += folders
            
        
        folders = self.create_temp_tree_from_files(cmd_files,fccsw_path)
        if None != folders:
            fccsw_folders += folders
            
        self.folders_to_upload = fccsw_folders + self.folders_to_upload
                

    #********************************************************#
    # Function name : update_sandbox                         #
    # role : check the files and folders required by the job #
    # and add them to the sandbox                            #
    # Indeed, it calls upload_sandbox_with_* functions       #
    #********************************************************#    
    
    def update_sandbox(self,fccsw_path,paths,fcc_conf_file):

        #first, it creates a specific local working directory for the sandbox        
        if not os.path.exists(self.temp_cwd):
            os.makedirs(self.temp_cwd)

        #update sandbox with application files
        if '' != paths:                        
            self.upload_sandbox_with_application_files(paths) 

        
        #update sandbox with FCCSW application files
        if '' != fccsw_path:
            self.upload_sandbox_with_fccsw_files(fccsw_path,fcc_conf_file)
    
        
    #********************************************************#
    # Function name : compress_sandbox_subfolders            #
    # role : compress all local folders required by the job  #
    #********************************************************#
            
    def compress_sandbox_subfolders(self):
    
        compressed_folders = []
            
        for idx,actual_folder in enumerate(self.folders_to_upload):    
            

            tar_extension = '.tgz'

            if idx < len(self.filtered_extensions):
                filtered_extension = self.filtered_extensions[idx]
                exclude_or_include = self.excludes_or_includes[idx]
            else:
                filtered_extension = False
                exclude_or_include = False
                
            temp_folder = os.path.join(self.temp_cwd,os.path.basename(actual_folder)) 

            #DIRAC already compressed the sandbox before submitting the job
            self.compress(temp_folder,actual_folder,tar_extension,filtered_extension,exclude_or_include)

            compressed_folders += [temp_folder + tar_extension]
        
        self.InputSandbox += compressed_folders                
            
    #**************************************************#
    # Function name : submit                           #
    # role : create DIRAC generic application for each #
    # FCC application and submit the DIRAC job         #
    # containing these generic DIRAC applications      #
    #**************************************************#
       
    def submit(self,applications,script_to_source):
    

        fcc_execution_module = os.path.join(os.getcwd(),"fcc_execution_module.py")
        fcc_installation_module = os.path.join(os.getcwd(),'fcc_installation_module.py')
        
        fcc_environment = script_to_source
        
        #Initialization of the sandbox
        paths = [fcc_execution_module,fcc_environment]      
        self.upload_sandbox_with_application_files(paths)
                       
        for application in applications :
        
            #application specification
            job_specification = application.job_specification
        
            #application specification details       
            fcc_executable = job_specification['fcc_executable'] 
            fccsw_path = job_specification['fccsw_path'] 
            paths =  job_specification['paths']
            fcc_conf_file = job_specification['fcc_conf_file']            
            fcc_input_files = '' if '' == job_specification['fcc_input_files'] else ' --ifiles ' + ' '.join(job_specification['fcc_input_files'])
            fcc_output_file = '' if '' == job_specification['fcc_output_file'] else ' --ofile ' + job_specification['fcc_output_file']
            fccsw = '' if '' == job_specification['fccsw_path'] else ' --fccsw ' + job_specification['fccsw_path']
            number_of_events = '' if '' == job_specification['number_of_events'] else ' -N ' + job_specification['number_of_events']
            

            #**************************************************MINIMUM REQUIREMENTS CHECKING*******************************************************#
            if '' == fcc_executable or '' == fcc_conf_file or '' == fcc_environment :
                print "\nError in parsing applications :\n" + fcc_executable
                print "\nYou have to provide at least an executable, a configuration file and a script to source for each application\n"
                quit()
            #**************************************************MINIMUM REQUIREMENTS CHECKING*******************************************************#
                
                
            #we update the sandbox according to the specification of the application
            self.update_sandbox(fccsw_path,paths,fcc_conf_file)

            #we instanciate a generic DIRAC application
            generic_dirac_application = GenericApplication()
            
            #we set the the installation module as the main script 
            generic_dirac_application.setScript(fcc_installation_module)            

            #we set the arguments of the script
            arguments = '--source ' + fcc_environment + ' --exec ' + fcc_executable + ' --conf ' + fcc_conf_file + fcc_input_files + fcc_output_file + fccsw +  number_of_events
                  
            generic_dirac_application.setExtraCLIArguments(arguments)

            
            #we add the generic DIRAC application to the DIRAC job              
            try:
                res = self.job.append(generic_dirac_application)
                if not res['OK']:
                    print res['Message']
                    quit()
            except :
                print "\nPlease, configure your proxy before submitting a job from DIRAC"
                print "If you do not set up a proxy, refer to the manual or maybe you have to refresh it"
                print "by typing :"
                print "dirac-proxy-init\n" 
                quit()

        
        #before submitting the DIRAC job, we compress all folders of the sandbox
        self.compress_sandbox_subfolders()        
                
        print '\n**********************************HERE THE CONTENT OF YOUR SANDBOX*********************************\n'
        print self.InputSandbox
        print '\n**********************************HERE THE CONTENT OF YOUR SANDBOX*********************************\n'
                
        #we set the sandbox    
        self.job.setInputSandbox(self.InputSandbox)
        
        #-------------------------------now we submit the job containing all applications-------------------------------------------#
        
        res = self.job.submit( self.dIlc )
        if not res['OK']:
            print 'Please check your application requirements'
            print res['Message']
            quit()
        else:
            print "The Job you submited has the following ID : " + str(res['JobID'])
      
   
