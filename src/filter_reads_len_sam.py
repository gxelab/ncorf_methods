# -*- coding: utf-8 -*-
# Author: Lei
import pysam
from collections import Counter
import click


@click.command(context_settings=dict(help_option_names=['-h', '--help'], show_default=True))
@click.argument('sam_path', type=click.STRING)
@click.option('-l', '--length', default='28', type=click.STRING,
              help='correct reads length, separated by commas')
@click.option('-p', '--prefix', default='fm60', type=click.STRING,
              help='output prefix')

def sam_select(sam_path, length, prefix = 'fm60'):
    """
    Filter the line in the sam file that specifies the reads length
    """
    
    sam_file = pysam.AlignmentFile(sam_path, 'r')

    out = f'{prefix}.sam'

    outfile = pysam.AlignmentFile(out, 'w', template = sam_file)
    
    len_list = [int(len) for len in length.split(',')]
    
    for align in sam_file:
        if align.query_alignment_length in len_list :
            outfile.write(align)

    sam_file.close()       
    outfile.close()
        
    return
    
    
if __name__ == '__main__':
    sam_select()
    
    