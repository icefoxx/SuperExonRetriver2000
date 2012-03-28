'''
Created on Mar 13, 2012

@author: anana
'''

import re
import os, sys, inspect
import ConfigParser;
from BioMartSearchEngine import *
from exon_base_generator import generateExonFastaFromDescription
from AlignmentGenerator import *
from AlignmentParserBlast import *
from StatisticsGenerator import *


def parseDescriptionFile (descrFileName):
    descrFile = open(descrFileName, 'r')
    abinitioSpecies = []
    knownSpecies = []
    i = 0
    for line in descrFile.readlines():
        line = line.strip()
        
        if (len(line) == 0):
            continue
        if (i % 2 == 0):
            species= line
        else :
            data = line.split()
            if (len(data) == 5):
                knownSpecies.append(species)
            else :
                abinitioSpecies.append(species)
        i = i + 1
        
    
    descrFile.close()
    return (knownSpecies,abinitioSpecies)
################################
################################
# generate file name
# prot_type abinitio / all
# species species name in Latin (homo_sapiens)
def generate_file_name (prot_type, species):
    file_name = "%s/%s/pep/" % (fasta_db, species.lower())
    generic_file_name=""
    # extrapolate the generic part of the file name
    # (Species.assembly_id.database_version).pep.prot_type.fa
    for f in os.listdir(file_name):
        if (f != "README"):
            generic_file_name = f
            break
    m = re.findall ('(.*).pep.', generic_file_name)   
    file_name = "%s/%s.pep.%s.fa" % (file_name, m[0], prot_type)
    return file_name

def generate_directories_tree ():
    protein_file = open(protein_list_file, 'r')
    for line in protein_file.readlines():
        line = line.strip()
        if (len(line) == 0):
            continue
        (proteinId, numberOfExons) = line.split()
        numberOfExons = int(numberOfExons)
        protein_sessions_dir = "%s/%s" % (session_folder, proteinId);
        
        if (not os.path.isdir(protein_sessions_dir)):
            os.makedirs(protein_sessions_dir)
        if (not os.path.isdir("%s/%s" % (protein_sessions_dir, gene_regions_folder))):
            os.makedirs("%s/%s" % (protein_sessions_dir, gene_regions_folder))
        if (not os.path.isdir("%s/%s" % (protein_sessions_dir, expanded_regions_folder))):
            os.makedirs("%s/%s" % (protein_sessions_dir, expanded_regions_folder))
            
        if (not os.path.isdir("%s/%s" % (protein_sessions_dir, exons_path))):
            os.mkdir("%s/%s" % (protein_sessions_dir, exons_path))
        if (not os.path.isdir("%s/%s/db" % (protein_sessions_dir, exons_path))):
            os.mkdir("%s/%s/db" % (protein_sessions_dir, exons_path))
        if (not os.path.isdir("%s/%s/wise2" % (protein_sessions_dir, exons_path))):
            os.mkdir("%s/%s/wise2" % (protein_sessions_dir, exons_path))
            
        if (not os.path.isdir("%s/%s" % (protein_sessions_dir, mut_best_proteins))):
            os.makedirs("%s/%s" % (protein_sessions_dir, mut_best_proteins))
            
        if (not os.path.isdir("%s/%s" % (protein_sessions_dir, blastout_folder))):
            os.makedirs("%s/%s" % (protein_sessions_dir, blastout_folder))
        if (not os.path.isdir("%s/%s/dna" % (protein_sessions_dir, blastout_folder))):
            os.makedirs("%s/%s/dna" % (protein_sessions_dir, blastout_folder))
        if (not os.path.isdir("%s/%s/protein" % (protein_sessions_dir, blastout_folder))):
            os.makedirs("%s/%s/protein" % (protein_sessions_dir, blastout_folder))
            
        if (not os.path.isdir("%s/%s/" % (protein_sessions_dir, swout_folder))):
            os.makedirs("%s/%s/" % (protein_sessions_dir, swout_folder))
        if (not os.path.isdir("%s/%s/" % (protein_sessions_dir, swout_folder))):
            os.makedirs("%s/%s/dna" % (protein_sessions_dir, swout_folder))
        if (not os.path.isdir("%s/%s/" % (protein_sessions_dir, swout_folder))):
            os.makedirs("%s/%s/exon" % (protein_sessions_dir, swout_folder))
    protein_file.close()
##################################
## Load necessary configuration ##

config_file     = "../../config.cfg"
config          = ConfigParser.RawConfigParser()
config.read(config_file)

project_root_folder     = config.get('Project root', 'project_root_folder')
session_folder          = config.get('Project root', 'session_folder')
session_folder          = "%s/%s" % (project_root_folder, session_folder)

protein_list_file       = config.get('Test files', 'protein_list')
input_protein_file      = config.get('Session files', 'input_protein_file')
descr_file              = config.get('Session files', 'descr_output')

gene_regions_folder     = config.get('Gene regions path', 'regions')
expanded_regions_folder = config.get('Gene regions path', 'expanded_regions')
exons_path              = config.get('Exon database path', 'exons_path')
mut_best_proteins       = config.get('Found proteins path', 'proteins')
blastout_folder         = config.get('Blastout path', 'blastout')
swout_folder            = config.get('SWout path', 'swout')

fasta_db                = config.get('Ensembl cfg', 'ensembldb')

statistics_path         = config.get('Statistics', 'exon_finder')

###################################

species         = "Homo_sapiens"
protein_type    = "all"

protein_database = generate_file_name(protein_type, species);

generate_directories_tree()

biomart = BioMartSearchEngine()
alignmentGen = AlignmentGenerator()
alParserBlast= AlignmentParserBlast()
statGen =  StatisticsGenerator()

protein_file = open(protein_list_file, 'r')
for line in protein_file.readlines():
    line = line.strip()
    if (len(line) == 0):
            continue
    (protein_id, numberOfExons) = line.split()
    numberOfExons = int(numberOfExons)
    
    protein_session_dir = "%s/%s" % (session_folder, protein_id)
    if (not os.path.isdir(protein_session_dir)):
        os.makedirs(protein_session_dir)
    input_protein = "%s/%s" % (protein_session_dir, input_protein_file)
    print input_protein
    
    cmd_retrieve_protein = "fastacmd -d %s -s %s -p T -o %s"  %  (protein_database,          # database name
                                                                 protein_id,                # id
                                                                 input_protein)
    
    # extract the protein from the database
    os.system(cmd_retrieve_protein)
    
    alignmentGen.setProteinFolder(protein_id)
    alParserBlast.setProteinFolder(protein_id)
    statGen.setProteinFolder(protein_id)
    
    cmd_run_mutual_best = "python ../../protein_mutual_best_search/src/ensembl_mutual_best.py %s %s" % (species, protein_session_dir)
    #run the mutual best protein search
    os.system(cmd_run_mutual_best)
    
    #get the dna data
    cmd_retrieve_dna = "python ../../ensembl_search/src/LocalEnsemblSearchEngine.py %s" % protein_session_dir
    os.system(cmd_retrieve_dna)
    
    #get the exons
    biomart.populateExonDatabase(protein_id)
    
    (known_species, abinitioSpecies) = parseDescriptionFile("%s/%s/%s" % (session_folder, protein_id, descr_file))
    
    alignmentGen.runBatchBlastn(True)
    alignmentGen.runBatchTblastn()
    
    alignmentGen.runBatchGenewise(abinitioSpecies)
    
    (exonsBlastn, exonsFoundBlastn) = alParserBlast.batchParseOutput(numberOfExons, "blastn")
    (exonsTblastn, exonsFoundTblastn) = alParserBlast.batchParseOutput(numberOfExons, "tblastn")
    
    statGen.generate_statistics(exonsTblastn, exonsBlastn, None, known_species+abinitioSpecies, protein_id)
    
    #get the base exons
    '''
    for species in abinitioSpecies:
        cmd_generate_exons = "python ../../exon_finder/src/exon_base_generator.py %s %s %s %s" % ( "%s/%s/%s.fa" % (protein_session_dir, mut_best_proteins, species),
                                                                                                "%s/gene_regions/%s.fa" %  (protein_session_dir, species),
                                                                                                protein_session_dir,
                                                                                                species)
        number_of_exons = os.system(cmd_generate_exons)>>8
        print "Found %d exons for species %s" % (number_of_exons, species)
    generateExonFastaFromDescription(protein_session_dir)
    '''
    
    #print "%s %s %s" % (number_of_exons, protein_session_dir, protein_id)
    #run exon_finder
    #cmd_run_exon_finder = "python ../../exon_finder/src/exon_finder.py %s %s %s" % (number_of_exons, protein_session_dir, protein_id)
    #os.system(cmd_run_exon_finder)