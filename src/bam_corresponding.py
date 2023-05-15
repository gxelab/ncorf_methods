# -*- coding: utf-8 -*-
# Author: Lei
import random
import pysam
from collections import Counter
import click


@click.command(context_settings=dict(help_option_names=['-h', '--help'], show_default=True))
@click.argument('genome_bam_path', type=click.STRING)
@click.argument('trans_bam_1_path', type=click.STRING)
@click.argument('trans_bam_2_path', type=click.STRING)

@click.option('-p', '--prefix', default='split_tmp', type=click.STRING,
              help='output prefix')
def bam_corresponding(genome_bam_path, trans_bam_1_path, trans_bam_2_path, prefix = 'split_tmp'):
    """
    Random split a bam file into two bam files based on read names.
    
    The two output files have the same number of reads.
    All the alignment of a single read will be put into the same file.
    """
    genome_file = pysam.AlignmentFile(genome_bam_path, 'rb')
    bam_1 = pysam.AlignmentFile(trans_bam_1_path, 'rb')
    bam_2 = pysam.AlignmentFile(trans_bam_2_path, 'rb')

    out1 = f'{prefix}.1.bam'
    out2 = f'{prefix}.2.bam'
    out0 = f'{prefix}.0.bam'

    outfile1 = pysam.AlignmentFile(out1, 'wb', template = genome_file)
    outfile2 = pysam.AlignmentFile(out2, 'wb', template = genome_file)
    outfile0 = pysam.AlignmentFile(out0, 'wb', template = genome_file)

    name = Counter()

    for line in genome_file:
        name[line.query_name] = 0
    for line in bam_1:
        name[line.query_name] = 1
    for line in bam_2:
        name[line.query_name] = 2

    genome_file = pysam.AlignmentFile(genome_bam_path, 'rb')
    for line in genome_file:
        if name[line.query_name] == 1:
            outfile1.write(line)
        if name[line.query_name] == 2:
            outfile2.write(line)
        if name[line.query_name] == 0:
            outfile0.write(line)


    genome_file.close()       
    outfile1.close()
    outfile2.close()
    outfile0.close()

    return
    
    
if __name__ == '__main__':
    bam_corresponding()
    
    
