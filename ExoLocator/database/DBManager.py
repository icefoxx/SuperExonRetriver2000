'''
Created on May 8, 2012

@author: marioot
'''
from utilities.ConfigurationReader import Singleton, ConfigurationReader
import MySQLdb
from data_analysis.containers.ExonContainer import ExonContainer
from data_analysis.utilities import generate_structure
from data_analysis.containers.DataMapContainer import DataMapContainer
from utilities import FileUtilities
from utilities.DescriptionParser import DescriptionParser
from data_analysis.containers.ProteinContainer import ProteinContainer
from data_analysis.base.EnsemblExon import EnsemblExon
from data_analysis.base.GenewiseExon import GenewiseExon
from data_analysis.analysis.AlignmentPostprocessing import annotate_spurious_alignments_batch
from data_analysis.base.Exon import Exon
from data_analysis.containers.GeneContainer import GeneContainer
from data_analysis.translation import BestExonAlignment, Runner
from data_analysis.translation.AlignmentExonPiece import AlignmentExonPiece
from data_analysis.translation.BestExonAlignmentContainer import BestExonAlignmentContainer
import data_analysis

@Singleton
class DBManager(object):
    '''
    classdocs
    '''
    def __init__(self):
        '''
        Constructor
        '''
        #use config in the future
        conf_reader = ConfigurationReader.Instance()
        database = conf_reader.get_value('database', 'database')
        hostname = conf_reader.get_value('database', 'hostname')
        username = conf_reader.get_value('database', 'username')
        password = conf_reader.get_value('database', 'password')
        self.db  = MySQLdb.connect(hostname, username, password, database)

    def update_gene_table(self, data_map_list):
        err_f = open('/home/marioot/err_status_monday.txt', 'a')
        '''
        Updates the protein table.
        Data format: (protein_id, sequence, protein_info)
        '''
        #need real data argument
        cursor = self.db.cursor()
        #SQL: Inserts record into database. If the record exists, updates the target_ensembl_id.
        sql = """
                INSERT INTO
                  gene (gene.gene_id, 
                          gene.ref_protein_id, 
                          gene.species, 
                          gene.location_type, 
                          gene.location_id, 
                          gene.strand, 
                          gene.start, 
                          gene.stop, 
                          gene.exp_start, 
                          gene.ab_initio)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  gene.gene_id = VALUES (gene.gene_id), \
                  gene.ref_protein_id = VALUES (gene.ref_protein_id), \
                  gene.species = VALUES (gene.species), \
                  gene.location_type = VALUES (gene.location_type), \
                  gene.location_id = VALUES (gene.location_id), \
                  gene.strand = VALUES (gene.strand), \
                  gene.start = VALUES (gene.start), \
                  gene.stop = VALUES (gene.stop), \
                  gene.exp_start = VALUES (gene.exp_start), \
                  gene.ab_initio = VALUES (gene.ab_initio)
                """
        #from protein list derive data:
        data = []
        for data_map in data_map_list:
            try:
                data.append((data_map.gene_id, 
                             data_map.ref_protein_id, 
                             data_map.species, 
                             data_map.location_type, 
                             data_map.location_id, 
                             data_map.strand, 
                             data_map.start, 
                             data_map.stop, 
                             data_map.get_expanded_start(), 
                             data_map.ab_initio))
            except Exception, e:
                err_f.write('DB: update_gene_table: {0}\n'.format(e))

        try:
            cursor.executemany(sql, data)
            self.db.commit()
            return True
        except:
            self.db.rollback()
            return False

    def update_ortholog_table(self, data_map_list):
        err_f = open('/home/marioot/err_status_monday.txt', 'a')
        '''
        Updates the protein table.
        Data format: (protein_id, sequence, protein_info)
        '''
        #need real data argument
        cursor = self.db.cursor()
        #SQL: Inserts record into database. If the record exists, updates the target_ensembl_id.
        sql = """
                INSERT INTO
                  ortholog (ortholog.ref_protein_id, ortholog.species, ortholog.protein_id, ortholog.transcript_id, ortholog.gene_id, ortholog.location_id, ortholog.start, ortholog.stop)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)                  
                """
        #from protein list derive data:
        data = []
        for data_map in data_map_list:
            try:
                data.append((data_map.ref_protein_id, 
                             data_map.species, 
                             data_map.protein_id, 
                             data_map.transcript_id, 
                             data_map.gene_id, 
                             data_map.location_id, 
                             data_map.start, 
                             data_map.stop))
            except Exception, e:
                err_f.write('DB: ortholog_table: {0} {1} \n'.format(e))

        try:
            cursor.executemany(sql, data)
            self.db.commit()
            return True
        except:
            self.db.rollback()
            return False

    def update_protein_table(self, protein_list):
        err_f = open('/home/marioot/err_status_monday.txt', 'a')
        '''
        Updates the protein table.
        Data format: (protein_id, sequence, protein_info)
        '''
        #need real data argument
        cursor = self.db.cursor()
        #SQL: Inserts record into database. If the record exists, updates the target_ensembl_id.
        sql = """
                INSERT INTO
                  protein (protein.ensembl_id, protein.sequence, protein.assembled_sequence, protein.info)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  protein.sequence = VALUES (protein.sequence), protein.assembled_sequence = VALUES(protein.assembled_sequence), protein.info = VALUES (protein.info)
                """
        #from protein list derive data:
        data = []
        for protein in protein_list:
            try:
                data.append((protein.protein_id, protein.get_sequence_record().seq, "",protein.species))
            except Exception, e:
                err_f.write('DB: protein_table: {0}\n'.format(e))

        try:
            cursor.executemany(sql, data)
            self.db.commit()
            return True
        except:
            self.db.rollback()
            return False
   
    def update_exon_table(self, exon_list):
        err_f = open('/home/marioot/err_status_monday.txt', 'a')
        '''
        Updates the exon table.
        Each row represents a single exon found.
        Data format is: (ref_protein_id, ref_ordinal, alignment_ordinal, species, source, ensembl_id, start, stop, sequence)
        '''
        #need real data argument
        cursor = self.db.cursor()
        #SQL: Inserts record into database. If the record exists, updates the target_ensembl_id.
        sql = """
                INSERT INTO
                  exon (exon.ref_protein_id, exon.ref_ordinal, exon.alignment_ordinal, exon.species, exon.source, exon.ensembl_id, exon.start, exon.stop, exon.sequence)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  exon.ref_protein_id = VALUES (exon.ref_protein_id), \
                  exon.ref_ordinal = VALUES (exon.ref_ordinal), \
                  exon.alignment_ordinal = VALUES (exon.alignment_ordinal), \
                  exon.species = VALUES (exon.species), \
                  exon.source = VALUES (exon.source), \
                  exon.ensembl_id = VALUES (exon.ensembl_id), \
                  exon.start = VALUES (exon.start), \
                  exon.stop = VALUES (exon.stop), \
                  exon.sequence = VALUES (exon.sequence)                  
                """
                
        dmc = DataMapContainer.Instance()
        config_reader = ConfigurationReader.Instance()
        expansion = int(config_reader.get_value("gene_expansion", "expand"))
        
        data = []
        for exon in exon_list:
            try:
                if type(exon) is EnsemblExon:
                    source = "ensembl"
                    ordinal             = exon.ordinal
                    alignment_ordinal   = exon.ordinal
                    exon_id             = exon.exon_id
                    start               = exon.start
                    stop                = exon.stop
                    sequence            = exon.sequence
                elif type(exon) is GenewiseExon:
                    source = "genewise"
                    ordinal             = exon.ordinal
                    alignment_ordinal   = exon.ordinal
                    exon_id             = ""
                    start               = exon.start
                    stop                = exon.stop
                    sequence            = exon.sequence
                else:
                    data_map = dmc.get((exon.ref_protein_id, exon.species))
                    
                    source              = exon.exon_type
                    ordinal             = exon.ordinal
                    alignment_ordinal   = exon.alignment_ordinal
                    exon_id             = exon.ref_exon_id
                    start               = max (1, data_map.start - expansion) + exon.alignment_info["query_start"]
                    stop                = start + len (exon.alignment_info["query_seq"])
                    sequence            = exon.alignment_info["query_seq"]
            
                data.append(( exon.ref_protein_id, 
                              ordinal, 
                              alignment_ordinal, 
                              exon.species, 
                              source, 
                              exon_id,
                              start,
                              stop,
                              sequence))
            except Exception, e:
                err_f.write('DB: exon_table: {0} {1} \n'.format(e))
        
        try:
            cursor.executemany(sql, data)
            self.db.commit()
            return True
        except:
            self.db.rollback()
            return False

    def update_alignment_table(self, exon_list):
        err_f = open('/home/marioot/err_status_monday.txt', 'a')
        '''
        Updates the exon table.
        Each row represents a single exon found.
        Data format is: (ref_protein_id, ref_ordinal, alignment_ordinal, species, source, ensembl_id, start, stop, sequence)
        '''
        #need real data argument
        cursor = self.db.cursor()
        #SQL: Inserts record into database. If the record exists, updates the target_ensembl_id.
        sql = """
                INSERT INTO
                  exolocator_db.alignment (alignment.ref_protein_id, alignment.ref_ordinal, alignment.alignment_ordinal, alignment.species, alignment.source, alignment.identities, alignment.positives, alignment.gaps, alignment.sbjct_start, alignment.sbjct_end, alignment.query_start, alignment.query_end, alignment.length, alignment.sbjct_seq, alignment.query_seq)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  alignment.ref_protein_id = VALUES (alignment.ref_protein_id), \
                  alignment.ref_ordinal = VALUES (alignment.ref_ordinal), \
                  alignment.alignment_ordinal = VALUES (alignment.alignment_ordinal), \
                  alignment.species = VALUES (alignment.species), \
                  alignment.source = VALUES (alignment.source), \
                  alignment.identities = VALUES (alignment.identities), \
                  alignment.positives = VALUES (alignment.positives), \
                  alignment.gaps = VALUES (alignment.gaps), \
                  alignment.sbjct_start = VALUES (alignment.sbjct_start), \
                  alignment.sbjct_end = VALUES (alignment.sbjct_end), \
                  alignment.query_start = VALUES (alignment.query_start), \
                  alignment.query_end = VALUES (alignment.query_end), \
                  alignment.length = VALUES (alignment.length), \
                  alignment.sbjct_seq = VALUES (alignment.sbjct_seq), \
                  alignment.query_seq = VALUES (alignment.query_seq)
                """
        data = []
        for exon in exon_list:
            try:
                if type(exon) is Exon:
                    data.append(( exon.ref_protein_id, 
                                  exon.ordinal, 
                                  exon.alignment_ordinal, 
                                  exon.species, 
                                  exon.exon_type,
                                  exon.alignment_info["identities"],
                                  exon.alignment_info["positives"],
                                  exon.alignment_info["gaps"],
                                  exon.alignment_info["sbjct_start"],
                                  exon.alignment_info["sbjct_end"],
                                  exon.alignment_info["query_start"],
                                  exon.alignment_info["query_end"],
                                  exon.alignment_info["length"],
                                  exon.alignment_info["sbjct_seq"],
                                  exon.alignment_info["query_seq"]
                                  ))
            except Exception, e:
                err_f.write('DB: alignment_table: {0}\n'.format(e))
        try:
            cursor.executemany(sql, data)
            self.db.commit()
            return True
        except:
            self.db.rollback()
            return False
        
    def update_exon_alignment_piece_table(self, exon_aln_piece_list):
        err_f = open('/home/marioot/err_status_monday.txt', 'a')
        '''
        Updates the exon_alignment_piece table.
        Each row represents a single exon alignment piece.
        Data format is: (unknown atm)
        '''
        #need real data argument
        cursor = self.db.cursor()
        #SQL: Inserts record into database. If the record exists, updates the target_ensembl_id.
        sql = """
                INSERT INTO
                  exolocator_db.exon_alignment_piece (exon_alignment_piece.ref_exon_id, exon_alignment_piece.species, exon_alignment_piece.type, exon_alignment_piece.ref_protein_seq, exon_alignment_piece.spec_protein_seq, exon_alignment_piece.ref_dna_seq, exon_alignment_piece.spec_dna_seq, exon_alignment_piece.ref_prot_start, exon_alignment_piece.ref_prot_stop, exon_alignment_piece.genome_start, exon_alignment_piece.genome_stop, exon_alignment_piece.frame, exon_alignment_piece.location_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  exon_alignment_piece.ref_exon_id = VALUES (exon_alignment_piece.ref_exon_id), \
                  exon_alignment_piece.species = VALUES (exon_alignment_piece.species), \
                  exon_alignment_piece.type = VALUES (exon_alignment_piece.type), \
                  exon_alignment_piece.ref_protein_seq = VALUES (exon_alignment_piece.ref_protein_seq), \
                  exon_alignment_piece.spec_protein_seq = VALUES (exon_alignment_piece.spec_protein_seq), \
                  exon_alignment_piece.ref_dna_seq = VALUES (exon_alignment_piece.ref_dna_seq), \
                  exon_alignment_piece.spec_dna_seq = VALUES (exon_alignment_piece.spec_dna_seq), \
                  exon_alignment_piece.ref_prot_start = VALUES (exon_alignment_piece.ref_prot_start), \
                  exon_alignment_piece.ref_prot_stop = VALUES (exon_alignment_piece.ref_prot_stop), \
                  exon_alignment_piece.genome_start = VALUES (exon_alignment_piece.genome_start), \
                  exon_alignment_piece.genome_stop = VALUES (exon_alignment_piece.genome_stop), \
                  exon_alignment_piece.frame = VALUES (exon_alignment_piece.frame), \
                  exon_alignment_piece.location_id = VALUES (exon_alignment_piece.location_id)
                """
                
        data = []
        for (ref_exon_id, species, exon_aln_piece) in exon_aln_piece_list:
            try:
                if type(exon_aln_piece) is AlignmentExonPiece:
                    
                    data.append(( ref_exon_id, 
                                  species, 
                                  exon_aln_piece.type, 
                                  exon_aln_piece.ref_protein_seq, 
                                  exon_aln_piece.spec_protein_seq,
                                  exon_aln_piece.ref_seq,
                                  exon_aln_piece.spec_seq,
                                  exon_aln_piece.ref_protein_start, 
                                  exon_aln_piece.ref_protein_stop, 
                                  exon_aln_piece.genomic_start, 
                                  exon_aln_piece.genomic_stop, 
                                  exon_aln_piece.frame, 
                                  exon_aln_piece.sequence_id
                                  ))
            except Exception, e:
                print '{0} {1} \n'.format(ref_exon_id, species)
                err_f.write('DB: alignment_piece_table: {0} {1}\n'.format(ref_exon_id, species))
        try:
            cursor.executemany(sql, data)
            self.db.commit()
            return True
        except:
            self.db.rollback()
            return False

    def update_dictionary_table(self, data=None):
        pass
    
    def read_exon_table(self, protein_id):
        '''
        Returns a list of rows in exon table, under specified species protein id.
        Each row represents a single exon found.
        Output format is: (protein_id, exon_number, species, location_on_protein, location_on_gene, source)
        '''
        # prepare a cursor object using cursor() method
        cursor = self.db.cursor()
        
        # Prepare SQL query to SELECT a record from the database.
        sql = """
                SELECT * FROM exon \
                WHERE \
                ensembl_id = %s
              """
        data = [
               (protein_id)
               ]
        try:
            cursor.executemany(sql, data)
            return cursor.fetchall()
        except:
            print "Error: unable to fecth data"
            return None
        
    def read_ortholog_table(self, reference_protein_id):
        '''
        Returns a list of rows in ortholog table, under specified reference protein id.
        Each row represents a triplet  discovered by Reciprocal Best Hit method.
        Output format is: (reference_protein_id, species, target_protein_id)
        '''
        # prepare a cursor object using cursor() method
        cursor = self.db.cursor()
        
        # Prepare SQL query to SELECT a record from the database.
        sql = """
                SELECT * FROM ortholog \
                WHERE \
                query_ensembl_id = %s
              """
        data = [
               (reference_protein_id)
               ]
        try:
            cursor.executemany(sql, data)
            return cursor.fetchall()
        except:
            print "Error: unable to fecth data"
            return None
        
    def read_protein_table(self, protein_id):
        '''
        Returns a list representing one row in a protein table for the specified protein id.
        The row represents an information about the specified protein
        Output format is: (protein_id, sequence, protein_info)
        '''
        # prepare a cursor object using cursor() method
        cursor = self.db.cursor()
        
        # Prepare SQL query to SELECT a record from the database.
        sql = """
                SELECT * FROM alignment \
                WHERE \
                ref_protein_id = %s
              """
        data = [
               (protein_id)
               ]
        try:
            cursor.executemany(sql, data)
            return cursor.fetchall()
        except:
            print "Error: unable to fecth data"
            return None
        
    def read_dictionary_table(self):
        pass
