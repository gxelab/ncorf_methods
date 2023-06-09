import pyBigWig
import numpy as np
import pandas as pd
from scipy.stats import ranksums, wilcoxon
from numpy.lib.stride_tricks import sliding_window_view
import click


def get_txcov(path_fwd, path_rev, givs):
    """
    extract coverage for transcript genomic intervals from bigwig files
    """
    bw_fw = pyBigWig.open(path_fwd)
    bw_rc = pyBigWig.open(path_rev)
    chroms = bw_fw.chroms().keys()
    cov = dict()

    for row in givs.itertuples():
        block_size = np.array([int(i) for i in row.col11.split(',')])
        block_start = np.array([int(i) for i in row.col12.split(',')])
        intv_start = row.col2 + block_start
        intv_end = intv_start + block_size

        bw = bw_fw if row.col6 == '+' else bw_rc
        chrom = str(row.col1)
        if chrom in chroms:
            ntcov = np.empty((0,))
            for i, j in zip(intv_start, intv_end):
                values = np.array(bw.values(chrom, i, j))
                values[np.isnan(values)] = 0
                ntcov = np.concatenate((ntcov, values))
            if row.col6 == '-':
                ntcov = np.flip(ntcov)
        else:
            ntcov = np.zeros(sum(block_size))
        cov[row.col4] = ntcov.astype(int)
    return cov


def orf_stat(row, cov):
    """
    row: items returned by pandas itertuples
    """
    # print(row)
    cov_orf = cov[row.tx_name][(row.tstart - 1):row.tend]
    cov_f5p = cov[row.tx_name][(row.flank5 - 1):(row.tstart - 1)]
    cov_f3p = cov[row.tx_name][row.tend:row.flank3]
    # ignore stop codon when counting reads and codons
    if (cov_orf.size % 3) != 0:
        # some annotated CDSs are incomplete at either 5' or 3' end. Such ORFs
        # are used as candidate ORFs by ribotricer, which will cause errors
        # when running this script. we append 1 or 2 zero values to the end of
        # this array so that the ORF length is a multiple of 3
        cov_orf = np.concatenate((cov_orf, np.zeros(3 - (cov_orf.size % 3))))
    cov_orf_codon = cov_orf.reshape((3, -1))[:,:-1]
    cov_f5p_codon = cov_f5p.reshape((3, -1))
    cov_f3p_codon = cov_f3p.reshape((3, -1))

    # counts
    psite_total = cov_orf_codon.sum()
    psite_f0, psite_f1, psite_f2 = cov_orf_codon.sum(axis = 1)
    n_codon = cov_orf_codon.shape[1]
    n_codon_f5p = cov_f5p_codon.shape[1]
    n_codon_f3p = cov_f3p_codon.shape[1]

    # periodicity test as in RiboCode (Xiao et al., 2018, NAR)
    try:
        wilcoxon1 = wilcoxon(cov_orf_codon[0], cov_orf_codon[1], alternative='greater').pvalue
    except ValueError:
        wilcoxon1 = np.nan
    try:
        wilcoxon2 = wilcoxon(cov_orf_codon[0], cov_orf_codon[2], alternative='greater').pvalue
    except ValueError:
        wilcoxon2 = np.nan

    # RRS (ribosome release score; Guttman et al., 2013, Cell; Chew et al., 2013, Development)
    # RAS (ribosome association score; similar idea as RRS but for start codon)
    # add pseudocount 1 to avoid divid by zero and stabilize results 
    if n_codon_f5p > 0:
        ras = (psite_total + 1) / n_codon / ((cov_f5p.sum() + 1) / n_codon_f5p)
        ras_p = ranksums(cov_orf_codon.sum(axis=0), cov_f5p_codon.sum(axis=0)).pvalue
        ras0 = (cov_orf_codon[0].sum() + 1) / n_codon / ((cov_f5p_codon[0].sum() + 1) / n_codon_f5p)
        ras0_p = ranksums(cov_orf_codon[0], cov_f5p_codon[0], alternative='greater').pvalue
    else:
        ras, ras_p, ras0, ras0_p = np.full(4, np.nan)
    if n_codon_f3p > 0:
        rrs = (psite_total + 1) / n_codon / ((cov_f3p.sum() + 1) / n_codon_f3p)
        rrs_p = ranksums(cov_orf_codon.sum(axis=0), cov_f3p_codon.sum(axis=0)).pvalue
        rrs0 = (cov_orf_codon[0].sum() + 1) / n_codon / ((cov_f3p_codon[0].sum() + 1) / n_codon_f3p)
        rrs0_p = ranksums(cov_orf_codon[0], cov_f3p_codon[0], alternative='greater').pvalue
    else:
        rrs, rrs_p, rrs0, rrs0_p = np.full(4, np.nan)

    # coverage (uniformity; Chothani et al., 2022, Molecular Cell)
    n_codon_cov = np.sum(cov_orf_codon.sum(axis=0) > 0)
    n_codon_cov0 = np.sum(cov_orf_codon[0] > 0)

    # PME as in RibORF (Ji et al., 2015, elife)
    # the 3p portion that is not enough for a window is dicarded
    if psite_total > 1:
        w = int(1 if psite_total > n_codon else np.floor(n_codon / psite_total))
        wcnt = sliding_window_view(cov_orf_codon, window_shape=(3, w))[0][::w].sum(axis=(1, 2))
        max_ent = np.sum(wcnt.size * (1 / wcnt.size) * np.log2(1/wcnt.size))
        wp = (wcnt / wcnt.sum())[wcnt > 0]
        pme = np.sum(wp * np.log2(wp)) / max_ent
    else:
        pme = np.nan
    return [
        psite_total, psite_f0, psite_f1, psite_f2,  # psite counts
        n_codon, n_codon_cov, n_codon_cov0,  # coverage and uniformity
        n_codon_f5p, n_codon_f3p,  # flanking region stat
        wilcoxon1, wilcoxon2,  # periodicity
        ras, ras_p, ras0, ras0_p, rrs, rrs_p, rrs0, rrs0_p, # start/stop coverage shift
        pme # possible RNP comtamination
    ]


@click.command(context_settings=dict(help_option_names=['-h', '--help'], show_default=True))
@click.argument('bw_fwd', type=click.STRING)
@click.argument('bw_rev', type=click.STRING)
@click.argument('tx_bed12', type=click.STRING)
@click.argument('orf_table', type=click.STRING)
@click.option('-o', '--output', type=click.STRING, default=None,
              help='output path. Use the input prefix + "orfquant.tsv" is not set.')
def main(bw_fwd, bw_rev, tx_bed12, orf_table, output=None):
    """
    Compute ribosomal footprint statistics for translated ORFs

    \b
    BW_FWD: genomic p-site coverage on the plus strand (cmd: `psite coverage` with genomic bam)
    BW_REV: genomic p-site coverage on the minus strand (cmd: `psite coverage` with genomic bam)
    TX_BED12: genomic coordinates of transcripts (cmd: `gppy convert2bed`)
    ORF_TABLE: table of translated ORFs (cmd: `orf_type.py`)

    note: It's better to filter too short ORFs (< 5 AA or 18 nt).  
    """
    orfs = pd.read_table(orf_table, dtype={'chrom': 'string'})
    orfs['flank5'] = np.int64(orfs.tstart - 3 * np.minimum(20, np.floor((orfs.tstart - 1)/3)))
    orfs['flank3'] = np.int64(orfs.tend + 3 * np.minimum(20, np.floor((orfs.tx_len - orfs.tend)/3)))

    tx_givs = pd.read_table(tx_bed12, header=None, dtype={0: 'string'})
    tx_givs.columns = [f'col{i + 1}' for i in tx_givs.columns]
    tx_givs = tx_givs[tx_givs.col4.isin(orfs.tx_name)]
    tx_givs['col11'] = tx_givs.col11.str.rstrip(',')
    tx_givs['col12'] = tx_givs.col12.str.rstrip(',')

    txcov = get_txcov(bw_fwd, bw_rev, tx_givs)

    orf_stats = [
        'psite_total', 'psite_f0', 'psite_f1', 'psite_f2', 'n_codon',
        'n_codon_cov', 'n_codon_cov0', 'n_codon_f5p', 'n_codon_f3p',
        'wilcoxon1', 'wilcoxon2', 'ras', 'ras_pval', 'ras0', 'ras0_pval',
        'rrs', 'rrs_pval', 'rrs0', 'rrs0_pval', 'pme']
    orfs[orf_stats] = orfs.apply(orf_stat, axis=1, result_type='expand', cov=txcov)

    if output == None:
        output = f"{orf_table.removesuffix('.tsv')}.orfquant.tsv"
    orfs.to_csv(output, sep='\t', float_format='%g', index=False)
    return


if __name__ == '__main__':
    main()
