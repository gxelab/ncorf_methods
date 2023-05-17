library(data.table)
path <- commandArgs(trailingOnly = TRUE)

files <- list.files(path, pattern = 'read.dist.sample.\\d{2}.txt', full.names = TRUE)
names(files) <- substr(files, nchar(files) - 5, nchar(files) - 4)

read_dist <- rbindlist(lapply(files, function(x){
    rpf_cov <- strsplit(readLines(x), '\t')
    rpf_cov <- as.numeric(rpf_cov[[1]][-1])
    dtt <- data.table(posn = seq_along(rpf_cov) - 31, cov = rpf_cov)
    dtt <- dtt[posn >= -15]
    dtt[, frame := posn %% 3]
    inframe <- dtt[, sum(cov[frame == 0]) / sum(cov)]
    p1 <- wilcox.test(dtt[frame == 0, cov], dtt[frame == 1, cov], paired = TRUE, alternative = 'greater')
    p2 <- wilcox.test(dtt[frame == 0, cov], dtt[frame == 2, cov], paired = TRUE, alternative = 'greater')
    offset <- dtt[posn >= -15 & posn <= -9, posn[which.max(cov)]]
    list(p1 = p1$p.value, p2 = p2$p.value, offset = -1 * offset, inframe = inframe)
}), idcol = 'len')

read_fine <- read_dist[inframe >0.5 & p1 < 0.01 & p2 < 0.01]

# RibORF requires A-site offset for correction
fwrite(read_fine[, .(len, offset + 3)], col.names = FALSE, sep = '\t',
       file = file.path(path, 'offset.corretion.param'))

