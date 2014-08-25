import random
import os
import sys

header_str = \
    """new
load /usr/local/google/home/smoitra/denovo_experiments/trio_NA12878.xml
snapshotDirectory /usr/local/google/home/smoitra/denovo_experiments/snapshots/{dirname}"""
if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Generates IGV scripts")
    parser.add_argument("--callsfile", type=str, help="File containing calls")
    parser.add_argument("--numrandom", type=int, default=50,
                        help="Number of calls to pick at random")
    parser.add_argument("--dirname", type=str, help="Directory to store images",
                        default="")
    args = parser.parse_args()

    with open(args.callsfile) as fin:
        calls = [line.strip().split(",")[:2] for line in fin]
        random.shuffle(calls)
        calls = calls[:args.numrandom]

    snapshot_dir = os.path.expanduser("~/denovo_experiments/snapshots/{dirname}".\
                                      format(dirname=args.dirname))
    if not os.path.exists(snapshot_dir):
        os.mkdir(snapshot_dir)

    with open(os.path.expanduser("~/denovo_experiments/igv_commands.txt"), "w") as fout:
        print >>fout, header_str.format(dirname=args.dirname)
        for (chromosome, pos) in calls:
            print >>fout, "goto "+chromosome+":"+pos
            print >>fout, "collapse"
            print >>fout, "snapshot"
