import os
import Utils
from functools import partial
from pyxnat import Interface
from lxml import etree
from datetime import datetime
import time

class AmbiguousLabelError(Exception):
     def __init__(self, value):
         self.value = value
     def __str__(self):
         return repr(self.value)

def non_unique_error(res_type, label, resources):
    """
    Make an exception that indicates that the given label of the
    given res_type('experiment'/'project') is ambigous.
    
    """
    return AmbiguousLabelError("More than one " + res_type +
                                     " associated with name " +
                                     label +
                                     ": " + ",".join(resources))

label_filter = lambda l: {'label':l}

def in_project(e,p):
     proj_xpath = e.xpath("@project", namespaces=e.nsmap)
     shared_xpath = e.xpath("/*/xnat:sharing/xnat:share/@project", namespaces=e.nsmap)
     proj = proj_xpath and proj_xpath[0]
     share = shared_xpath and shared_xpath[0]
     return proj == p or share == p
has_id = lambda r, i: r.xpath("@ID", namespaces=e.nsmap)[0] == i

class Resource():
    """
    Prototype for a class containing common actions on a resource(project,experiment...)
    """
    def __init__(self,res_type, conn):
        """
        Parameters:
        ----------
        res_type: A string that describes this resource, used for printing
                  good error messages
        conn:     An Interface object described in
                  pyxnat/pyxnat/core/Interface.py. Used for querying XNAT.         
        """
        pass
    def get_all(self):
        """
        Get all the resources of this type
        """
        pass
    def get(self, res_id):
        """
        Get only the resource with the given res_id
        """
        pass
    def label(self,res):
        """
        Get the label of this resource. Expects a pyxnat object,
        eg. if the resource is a project, the argument should be
        a pyxnat/pyxnat/core/resources.Project
        """
        pass
    def get_res_id(self,res):
        """
        Get the ID of this resource. Expects a pyxnat object,
        eg. if the resource is a project, the argument should be
        a pyxnat/pyxnat/core/resources.Project
        """
        pass
    
class Project():
    def __init__(self,res_type, conn):
        self.res_type = res_type
        self.conn = conn
        self.xml = {}
    def get_all(self):
        return self.conn.select.projects()
    def get(self, proj_id):
         if proj_id not in self.xml:
              try:
                   self.xml[proj_id] = etree.fromstring(self.conn.select.project(proj_id).get())
              except Exception,e:
                   self.xml[proj_id] = None
         return self.xml[proj_id]
    def xpath(self,xml,xp):
         if xml is not None:
              res = xml.xpath(xp, namespaces=xml.nsmap)
              return res and res or []
         else:
              return None
    def search_label(self,label):
        constraints =  [("xnat:projectData/NAME", "=", label)]
        res = self.conn.select('xnat:projectData',['xnat:projectData/ID']).where(constraints).get("id")
        if res and type(res) == list:
             return res
        else:
             return [res]
    def exists(self,proj_id):
        try :
            if self.xpath(self.get(proj_id),"@ID"): return True
        except Exception, e:
            return False
    def label(self,proj_id):
        return self.xpath(self.get(proj_id),"/xnat:Project/xnat:name")[0].text
    def get_res_id(self,proj_id):
        res_ids = self.xpath(self.get(proj_id),"@ID")
        if res_ids:
             return res_ids[0]
        else:
             return []

class Experiment():
    def __init__(self,res_type, conn):
        self.res_type = res_type
        self.conn = conn
        self.xml = {}
    def get_all(self):
        return self.conn.select.experiments()
    def get(self, exp_id):
         if exp_id not in self.xml:
              try:
                   _xml = self.conn.select.experiment(exp_id).get()
                   self.xml[exp_id] = etree.fromstring(_xml)
              except Exception, e:
                   self.xml[exp_id] = None
         return self.xml[exp_id]
    def xpath(self,xml,xp):
         if xml is not None:
              res = xml.xpath(xp, namespaces=xml.nsmap)
              return res and res or []
         else:
              return None
    def date(self,exp_id):
         date = self.xpath(self.get(exp_id),"xnat:date")
         if date:
              return time.strptime(date[0].text,"%Y-%m-%d")
         else:
              return None
    def exists(self,exp_id):
        try :
            if self.xpath(self.get(exp_id),"@ID"):
                 return True
        except Exception, e:
            return False
    def label(self,exp):
        return self.xpath(self.get(exp),"@label")[0]
    def get_res_id(self,exp):
        res_ids = self.xpath(self.get(exp),"@ID")
        if res_ids:
             return res_ids[0]
        else:
             return []
    def get_subject_id(self,exp):
         return self.xpath(self.get(exp),"///xnat:subject_ID")[0].text
    def get_project_id(self,exp):
         return self.xpath(self.get(exp),"@project")[0]
    
class Scan():
     def __init__(self,exp_xml):
          self.res_type = 'scan'
          self.exp_xml = exp_xml
     def xpath(self,xml,xp):
          if xml is not None:
               res = xml.xpath(xp, namespaces=xml.nsmap)
               return res and res or []
          else:
               return None
     def get_quality(self,quality):
          ret = []
          if quality != "ALL":
               for e in self.xpath(self.exp_xml,"/*/xnat:scans/xnat:scan"):
                    for _e in list(e):
                         if _e.tag == "{http://nrg.wustl.edu/xnat}quality":
                              if _e.text == quality:
                                   ret.append(e.attrib['ID'])
          elif quality == "ALL":
               return self.get_ids()
          return ret
     def is_id(self,scan_id):
          return scan_id in self.get_ids()
     def is_type(self,scan_type):
          return self.get_type(scan_type) is not None
     def is_id_and_type(self,scan_id_or_type):
          return self.is_id(scan_id_or_type) and self.is_type(scan_id_or_type)
     def get_ids(self):
          ret = []
          for e in self.xpath(self.exp_xml,"/*/xnat:scans/xnat:scan"):
               ret.append(e.attrib['ID'])
          return ret
     def with_format(self,format):
         ret = []
         if format != "ALL":
              for e in self.xpath(self.exp_xml,"/*/xnat:scans/xnat:scan"):
                   for _e in list(e):
                        if _e.tag == "{http://nrg.wustl.edu/xnat}file":
                             if _e.attrib['format'] == format:
                                  ret.append(e.attrib['ID'])
         elif format == "ALL":
              return self.get_ids()
         return ret
     def has_format(self,format):
          return format == "ALL" and True or self.with_format(format) != []
     def has_type(self,res_id,res_type):
          return res_id in self.get_type(res_type)
     def get_type(self,type):
         ret = []
         if type != "ALL":
              for e in self.xpath(self.exp_xml,"/*/xnat:scans/xnat:scan"):
                   if e.attrib['type'] == type:
                        ret.append(e.attrib['ID'])
         elif type == "ALL":
              for e in self.xpath(self.exp_xml,"/*/xnat:scans/xnat:scan"):
                   ret.append(e.attrib['ID'])
         return ret
     def has_quality(self,quality):
          qs = [x.text for x in self.xpath(self.exp_xml,"/*/xnat:scans/xnat:scan/xnat:quality")]
          return quality != 'ALL' and quality in qs or True

class Assessor():
     def __init__(self,exp_xml):
          self.res_type = 'assessor'
          self.exp_xml = exp_xml
     def xpath(self,xml,xp):
          if xml is not None:
               res = xml.xpath(xp, namespaces=xml.nsmap)
               return res and res or []
          else:
               return None
     def get_ids(self):
          ret = []
          for e in self.xpath(self.exp_xml,"/*/xnat:assessors/xnat:assessor"):
               ret.append(e.attrib['ID'])
          return ret
     def is_id(self,ass_id):
          return ass_id in self.get_ids()
     def is_type(self,ass_type):
          return self.get_type(ass_type) is not None
     def is_id_and_type(self,id_or_type):
          return self.is_id(id_or_type) and self.is_type(id_or_type)
     def has_files(self,ass_id):
          for e in self.xpath(self.exp_xml,"/*/xnat:assessors/xnat:assessor"):
               if e.attrib['ID'] == ass_id:
                    for _e in list(e):
                         if _e.tag == "{http://nrg.wustl.edu/xnat}out":
                              return True
          return False
     def get_type(self,ass_type):
          ret = []
          if ass_type != "ALL":
               for e in self.xpath(self.exp_xml,"/*/xnat:assessors/xnat:assessor"):
                    if e.attrib['{http://www.w3.org/2001/XMLSchema-instance}type'] == ass_type:
                         ret.append(e.attrib['ID'])
          elif ass_type == "ALL":
               return self.get_ids()
          return ret
     def has_type(self,ass_type):
          return ass_type != 'ALL' and ass_type in self.get_type(ass_type) \
              or True
     
class Reconstruction():
     def __init__(self,exp_xml):
          self.res_type = 'reconstruction'
          self.exp_xml = exp_xml
     def xpath(self,xml,xp):
          if xml is not None:
               res = xml.xpath(xp, namespaces=xml.nsmap)
               return res and res or []
          else:
               return None
     def get_ids(self):
          ret = []
          for e in self.xpath(self.exp_xml,"/*/xnat:reconstructions/xnat:reconstructedImage"):
               ret.append(e.attrib['ID'])
          return ret
     def is_id(self,recon_id):
          return recon_id in self.get_ids()
     def is_type(self,recon_type):
          return self.get_type(recon_type) is not None
     def is_id_and_type(self,id_or_type):
          return self.is_id(id_or_type) and self.is_type(id_or_type)
     def has_files(self,recon_id):
          for e in self.xpath(self.exp_xml,"/*/xnat:reconstructions/xnat:reconstructedImage"):
               if e.attrib['ID'] == recon_id:
                    for _e in list(e):
                         if _e.tag == "{http://nrg.wustl.edu/xnat}out":
                              return True
          return False
     def get_type(self,recon_type):
          ret = []
          if recon_type != "ALL":
               for e in self.xpath(self.exp_xml,"/*/xnat:reconstructions/xnat:reconstructedImage"):
                    if e.attrib['{http://www.w3.org/2001/XMLSchema-instance}type'] == recon_type:
                         ret.append(e.attrib['ID'])
          elif recon_type == "ALL":
               return self.get_ids()
          return ret
     def has_type(self,recon_type):
          return recon_type != 'ALL' and recon_type in self.get_type(recon_type) \
              or True
    
def id_to_label(resource, res_id):
    """
    Convert the given ID into a label.
    Parameters
    ----------
    resource : A Resource object containing functions that can retrieve
               various attributes about this resource from XNAT
    res_id : The project ID

    Returns:
    -------
    String or None if the id does not exist
    """    
    if not res_id:
        return None
    else:
        try:
            res = resource.get(res_id)
            return resource.label(res_id)
        except Exception as e:
            return None

def choose_by_project(proj_id):
     def _choose_by_project(resource,resources):
          exp = None
          for e in resources:
               if in_project(resource.get(e), proj_id):
                    exp = e
                    break
          return exp
     return _choose_by_project

def choose_by_id(res_id):
    def _choose_by_id(resource,resources):
        if len(resources) > 1:
            raise non_unique_error(resource.res_type,
                                   res_id,
                                   resources)
        elif not resources:
            return None
        else:
            exp = None
            for r in resources:
                if has_id(resource.get(r),res_id):
                    exp = r
                    break
            return exp
    return _choose_by_id

def choose_single(name):
    def _choose_single(resource,resources):
        if len(resources) > 1:
            raise non_unique_error(resource.res_type,
                                   name,
                                   resources)
        elif not resources:
            return None
        else:
            return resources[0]
    return _choose_single

def choose_first():
    return lambda resource, resources: resources and \
        resources[0] or None

def resources_matching_label(resource, label):
    if not label:
        return None
    else:
         def exact_match(p):
              return p == label
         resources = resource.get_all()
         resources._filters = label_filter(label)
         # There's bug in the XNAT 1.4 where querying by
         # project with a constraint that doesn't exist
         # returns the complete list of projects.
         if (resource.res_type == 'project'):
              return resource.search_label(label)
         else:
              return resources.get()

def label_to_id(resource,label,choose=None):
    if not choose:
        choose = choose_single(label)
    if not label:
        return None
    else:
        resources = resources_matching_label(resource,label)
        if resources:
            resource_id = choose(resource,resources)
            if resource_id:
                return resource.get_res_id(resource_id)
            else:
                return None
        else:
            return None

def exists(resource,label_or_id,choose=None):
    if resource.exists(label_or_id):
        if choose:
            return choose(resource,[label_or_id]) is not None
        else:
            return True
    else:
        if not choose:
            return label_to_id(resource,label_or_id,choose_single(label_or_id)) is not None
        else:
            return label_to_id(resource,label_or_id,choose) is not None

def label_id_flip(resource,label_or_id):
    label = choose_single(label_or_id)(resource,
                                       resources_matching_label(resource,
                                                                label_or_id))
    is_id = resource.get(label_or_id) is not None
    label_of_id = id_to_label(resource,label_or_id)
    if label:
        if is_id and label_of_id != label_or_id:
            raise AmbiguousLabelError("The given " + resource.res_type \
                                          + " " + label_or_id \
                                          + " is both a name and an ID.")
        else:
            return label
    else:
        if is_id:
            return label_of_id
        else:
            return None

def to_id(resource,label_or_id,choose=None):
    if choose:
         label = choose(resource,resources_matching_label(resource,label_or_id))
    else:
         label = choose_single(label_or_id)(resource,
                                            resources_matching_label(resource,label_or_id))
    is_id = resource.get(label_or_id) is not None
    label_of_id = id_to_label(resource,label_or_id)
    if label:
        if is_id and label_of_id != label_or_id:
            raise AmbiguousLabelError("The given " + resource.res_type \
                                          + " " + label_or_id \
                                          + " is both a name and an ID.")
        else:
            if choose: 
                 return label_to_id(resource,label_or_id,choose)
            else:
                 return label_to_id(resource,label_or_id)
    else:
        if is_id:
            return label_or_id
        else:
            return None
