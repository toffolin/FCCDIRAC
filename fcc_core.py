#******************************* libraries importation ***********************************#

#standard libraries
import os

#************************************* Classes - Definition ******************************#


#**********************************************#
# Classes : The core is composed of 2 classes  #
# - Job()                                      #
# - Application()                              #
#**********************************************#


#*********************************************#
# Class : Job()                               #
# role : A FCC Job is the final entity        #
# It may contain one or more FCC applications #
#*********************************************#

class Job():


    def __init__(self):

        self.sourcingDIRAC = 'source /afs/cern.ch/eng/clic/software/DIRAC/bashrc'
        self.dirac_sourcing_message = "\nPlease ensure that you set up correctly your environnement in order to use DIRAC ie.: \n" + self.sourcingDIRAC + '\n'

        self._init_dirac()
        self._fcc_applications = [] 
        self.script_to_source = '' 

    #*********************************************#
    # Function name : _init_dirac                 #
    # role : it checks DIRAC environment          #
    #*********************************************#

    def _init_dirac(self):

        #DIRAC environment
        try:
            DIRAC_PATH_AFS=os.environ["DIRAC"]
        except:
            #print default CLIC path of source script as 'help'
            print  self.dirac_sourcing_message
            quit()  

    def set_sourcing_script(self,script_to_source):
        self.script_to_source = script_to_source

    def append(self,application):
        self._fcc_applications.append(application)

    def submit(self): 

        from fcc_dirac_submit import Submit 

        Submit().submit(self._fcc_applications,self.script_to_source)



#*********************************************************#
# Class : Application()                                   #
# role : A FCC application is the smallest building block #
# In general, it represents a 'command'                   #
#*********************************************************#

        
class Application(): 


    def __init__(self):

        self.job_specification = {}

        #required
        self.job_specification['fcc_executable'] = ''   
        self.job_specification['fcc_conf_file'] = ''
           
        #not mandatory 
        self.job_specification['fcc_output_file'] = ''
        self.job_specification['fcc_input_files']  = ''
        self.job_specification['number_of_events']  = ''
        self.job_specification['fccsw_path']  = ''
        self.job_specification['paths']  = []
           
    #specification of the application  
    def set_executable(self,executable):
        self.job_specification['fcc_executable'] = executable

    def set_configuration_file(self,conf_file):
        self.job_specification['fcc_conf_file'] = conf_file
        self.add_paths([conf_file])

    def set_output_file(self,output_file):
        self.job_specification['fcc_output_file'] = output_file

    def set_input_files(self,input_files):
        self.job_specification['fcc_input_files']  = input_files

    def set_number_of_events(self,number_of_events):
        self.job_specification['number_of_events']  = number_of_events

    def set_fccsw_path(self,fccsw_path):
        self.job_specification['fccsw_path']  = fccsw_path   

    def add_paths(self,paths):
        self.job_specification['paths']  += paths     
