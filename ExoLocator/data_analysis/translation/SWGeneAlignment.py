'''
Created on Jun 24, 2012

@author: anana
'''
from data_analysis.translation.TranslationUtils import split_exon_seq,\
    set_protein_sequences
import re
from data_analysis.containers.ProteinContainer import ProteinContainer
from data_analysis.containers.DataMapContainer import DataMapContainer
from utilities.ConfigurationReader import ConfigurationReader
from Bio.Seq import Seq
from Bio.Alphabet import IUPAC

class SWGeneAlignment (object):
    
    def __init__ (self, ref_protein_id, species, ref_exon, alignment_exon):   
        
        self.ref_protein_id = ref_protein_id
        self.species        = species
        self.ref_exon       = ref_exon
        self.alignment_exon = alignment_exon
        
        self.load_alignment_pieces()  
        self.determine_absolute_coordinates ()
        
        
    def load_alignment_pieces (self):
        '''
        Loads the alignment pieces and sets their
        translations to protein.
        '''
        
        pc = ProteinContainer.Instance()
        
        ref_protein             = pc.get(self.ref_protein_id)
        ref_protein_seq         = ref_protein.get_sequence_record().seq
        ref_exon_translation    = self.ref_exon.sequence[self.ref_exon.frame:].translate()
        
        # remove the stop codon from the last position
        if str(ref_exon_translation).endswith("*"):
            ref_exon_translation = ref_exon_translation[0:len(ref_exon_translation)-1]
        
        self.alignment_pieces    = split_exon_seq(self.alignment_exon, self.ref_exon)
        
        self.alignment_pieces   = set_protein_sequences (self.alignment_pieces)
        
        # find the locations of the exon translation in the protein
        exon_start = str(ref_protein_seq).find(str(ref_exon_translation))
        exon_stop = exon_start + len(ref_exon_translation)
   
        previous = None
   
        for al_piece in self.alignment_pieces:
            
            if al_piece.type == "coding":

                ref_protein_seq_piece = str(al_piece.ref_protein_seq)
                if ref_protein_seq_piece.endswith("*"):
                    ref_protein_seq_piece = ref_protein_seq_piece[0:len(ref_protein_seq_piece)-1]
                
                # make sure that the piece is location within the bounds of the exon translation    
                for a in list(re.finditer(str(ref_protein_seq_piece), str(ref_protein_seq))): 
                    if a.start() >= exon_start and a.end() <= exon_stop:
                        al_piece.set_protein_locations (a.start(), a.end())
                        break
       
            if al_piece.type == "insertion":
                al_piece.set_protein_locations(previous.ref_protein_stop, previous.ref_protein_stop + 1)
        
            previous = al_piece
            
      
    def determine_absolute_coordinates (self):
        '''
        Sets the absolute genomic locations for alignment pieces
        '''
            
        dmc = DataMapContainer.Instance ()
        conf_reader = ConfigurationReader.Instance ()
        
        expansion = int(conf_reader.get_value("local_ensembl", "expansion"))
        
        data_map = dmc.get((self.ref_protein_id, self.species))
        start, stop = (data_map.start, data_map.stop)
        alignment_start = self.alignment_exon.alignment_info["query_start"]
        
        for al_piece in self.alignment_pieces:
            
            if al_piece.type in ["coding", "insertion"]:
                
                real_start = max (1, start - expansion) + alignment_start + al_piece.alignment_start
                real_stop  = real_start + len(al_piece.ref_seq)
                
                al_piece.set_genomic_locations(real_start, real_stop, data_map.location_id)
                
                
    def create_cDNA (self):
        
        total_exon_len = len(self.ref_exon.sequence)
        
        alignment_start = self.alignment_exon.alignment_info["sbjct_start"]
        padded_cdna = "N"* (alignment_start-1)
        
        len_added = len(padded_cdna)
        
        for al_piece in self.alignment_pieces:
            if al_piece.type == "coding":
                padded_cdna += al_piece.spec_seq
                len_added += len(al_piece.spec_seq)
            elif al_piece.type == "insertion":
                ns_to_add = (3 - (len(al_piece.spec_seq)) % 3) % 3
                padded_cdna += al_piece.spec_seq + "N"*ns_to_add
            elif al_piece.type == "deletion":
                padded_cdna += "N"*len(al_piece.spec_seq)
                len_added += len(al_piece.spec_seq)
                
        padded_cdna += "N" * (total_exon_len-len_added)
        return padded_cdna
                
            
                
        
        
                        
                