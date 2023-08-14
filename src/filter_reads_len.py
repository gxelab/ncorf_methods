# -*- coding: utf-8 -*-
# Author: Lei
import pysam
from collections import Counter
import click


@click.command(context_settings=dict(help_option_names=['-h', '--help'], show_default=True))
@click.argument('bam_path', type=click.STRING)
@click.option('-l', '--length', default='28', type=click.STRING,
              help='correct reads length, separated by commas')
@click.option('-p', '--prefix', default='fm60', type=click.STRING,
              help='output prefix')

def bam_select(bam_path, length, prefix = 'fm60'):
    """
    Filter the line in the bam file that specifies the reads length
    """
    
    bam_file = pysam.AlignmentFile(bam_path, 'rb')

    out = f'{prefix}.bam'

    outfile = pysam.AlignmentFile(out, 'wb', template = bam_file)
    
    len_list = [int(len) for len in length.split(',')]
    
    for align in bam_file:
        if align.query_alignment_length in len_list :
            outfile.write(align)

    bam_file.close()       
    outfile.close()
        
    return
    
    
if __name__ == '__main__':
    bam_select()
    
    