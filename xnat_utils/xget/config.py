import args
import Sessions
import sys
import os
import string
import XnatPass
import time 

class Connection():
    def __init__(self,dict):
        self.dict = dict
    def getHost(self):
        return self.dict['host']
    def _available(self):
        return self.getHost() != None

class Auth():
    def __init__(self,dict):
        self.dict = dict
    def getUser(self):
        return self.dict['u']
    def getPass(self):
        return self.dict['p']
    def _available(self):
        return self.getUser() != None and self.getPass() != None

class PassFile(Connection,Auth):
    def __init__(self,dict):
        self.dict = XnatPass.readXnatPass(dict['passfile'])
    def _available(self):
        return self.dict != None

class Constraints():
    def __init__(self,dict):
        self.dict = dict
    # "proj"
    def getProj(self):
        return self.dict['proj']
    # "quality"
    def getQuality(self):
        return self.dict['quality']
    # "r"
    def getFormat(self):
        return self.dict['r']
    # "-acq
    def getScanTypes(): ()
    # "readme"
    def getReadme(self):
        return self.dict('readme')

class Session():
    def __init__(self,dict):
        self.dict = dict
        self.sessions = dict['s']

    def _available(self):
        return self.sessions is not None

    def getSessions(self):
        return Sessions.getSessionIds(self.dict,sys.stdin)
        
class Project():
    def __init__(self,dict):
        self.dict = dict
        self.project = dict['proj']

    def _available(self):
        return self.project is not None
    
    def getSessions(self):
        def get_from_xnat(conn):
            # Assume the project ID is given
            byID = conn.select.project(self.project).experiments().get()
            byLabel = conn.select.project(SessionUtils.label_to_id(conn,self.project).experiments())
            return (byID is not None and byID or byLabel.get())
        return get_from_xnat

class Model(Auth,Connection):
    def __init__(self,dict,stdin):
        self.dict = dict
        self.output = dict['o']
        self.zip = dict['z']
        self.passfile = PassFile(dict)
        self.session = Session(dict)
        self.auth = Auth(dict)
        self.connection = Connection(dict)
        self.constraints = Constraints(dict)
        self.project = Project(dict)
    def getHost(self):
        if self.connection._available():
            return self.connection.getHost()
        elif self.passfile._available():
            return self.passfile.getHost()
        else:
            sys.stderr.write("No host specified on command line or in the XNAT pass file\n")
            sys.exit
    def getUser(self):
        if self.auth._available():
            return self.auth.getUser()
        elif self.passfile._available():
            return self.passfile.getUser()
        else:
            sys.stderr.write("No user specified on command line or in the XNAT pass file\n")
            sys.exit()
            
    def getPass(self):
        if self.auth._available():
            return self.auth.getPass()
        elif self.passfile._available():
            return self.passfile.getPass()
        else:
            sys.stderr.write("No password specified on command line or in the XNAT pass file\n")
            sys.exit()
    def getSessions(self):
        return Sessions.getSessionIds(self.dict,sys.stdin)
    def getProject(self):
        return self.dict['proj']
    def getOutputDir(self):
        return self.dict['o']
    def getScanTypes(self):
        return self.dict['acq'] and self.dict['acq'] or None
    def getAssTypes(self):
        return self.dict['ass'] and self.dict['ass'] or None
    def getReconTypes(self):
        return self.dict['recon'] and self.dict['recon'] or None
    def extractZip(self):
        return self.dict['z']
    def overwrite(self):
        return self.dict['overwrite']
    def getQuality(self):
        return self.dict['quality'] and self.dict['quality'] or None
    def getFormat(self):
        return self.dict['format'] and self.dict['format'] or None
    def getLongName(self):
        return self.dict['longname']
    def getStart(self):
        return self.dict['start']
    def getEnd(self):
        return self.dict['end']
