'''
Created on Jun 24, 2012

@author: intern
'''
from data_analysis.translation.BestExonAlignment import BestExonAlignment
from utilities.Singleton import Singleton


@Singleton
class BestExonAlignmentContainer (object):
    
    def __init__ (self):
        self._container = {}
        
    def add (self, ref_exon_id, species, best_exon_alignment):
        
        key = (ref_exon_id, species)
        
        if type(best_exon_alignment) is not BestExonAlignment:
            raise TypeError('Transcript, TypeError, {0}'.format(ref_exon_id))
        
        if self._container.has_key(key):
            raise KeyError('Transcript, KeyError, {0}, {1}'.format(ref_exon_id, species))
        
        self._container[key] = best_exon_alignment
        
    def get (self, ref_exon_id, species):
        
        return self._container[(ref_exon_id, species)]
