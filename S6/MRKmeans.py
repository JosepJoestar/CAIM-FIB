import argparse
import os
import shutil
from functools import reduce
from time import time

from mrjob.util import to_lines

from MRKmeansStep import MRKmeansStep

assignation = {}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prot', default='prototypes.txt',
                        help='Initial prototypes file')
    parser.add_argument('--docs', default='documents.txt',
                        help='Documents data')
    parser.add_argument('--iter', default=5, type=int,
                        help='Number of iterations')
    parser.add_argument('--nmaps', default=2, type=int,
                        help='Number of parallel map processes to use')
    parser.add_argument('--nreduces', default=2, type=int,
                        help='Number of parallel reduce processes to use')
    parser.add_argument('--folder', default='//',
                        help='Experiments folder')
    args = parser.parse_args()
    return args


def copy_prototypes(prototypes_file, folder):
    cwd = os.getcwd()
    previous_folder = folder.split('/')
    previous_folder = f'{previous_folder[0]}/{previous_folder[1]}'
    if not os.path.exists(folder):
        os.mkdir(folder)
    shutil.copy(f'{cwd}/{previous_folder}/{prototypes_file}', f'{cwd}/{folder}/prototypes0.txt')


def write_prototype(prototype, file_name):
    with open(file_name, mode='w') as prototype_file:
        for key, values in prototype.items():
            aux = reduce(
                lambda acc, x: f'{acc} {x[0]}+{x[1]}', values, f'{key}:')
            prototype_file.write(f'{aux}\n')


def run_runner(mr_job, i, folder):
    with mr_job.make_runner() as runner:
        runner.run()
        new_assignation = {}
        new_prototype = {}
        for line in to_lines(runner.cat_output()):
            key, value = mr_job.parse_output_line(line)

            new_assignation[key] = value[0]
            new_prototype[key] = value[1]

        cwd = os.getcwd()
        with open(f'{cwd}/{folder}/assignments{i + 1}.txt', mode='w') as new_assignation_file:
            for key, values in new_assignation.items():
                aux = reduce(lambda acc, x: f'{acc} {x}', values, f'{key}:')
                new_assignation_file.write(f'{aux}\n')

        global assignation
        if assignation == new_assignation:
            return i, new_prototype
        else:
            assignation = new_assignation
            write_prototype(new_prototype, f'{cwd}/{folder}/prototypes{i + 1}.txt')


def perform_iterations(iterations, docs, nmaps, nreduces, folder):
    cwd = os.getcwd()

    i = 0
    for i in range(iterations):
        print(f'Iteration #{i+1}')
        start_time = time()

        # The --file flag tells to MRjob to copy the file to HADOOP
        # The --prot flag tells to MRKmeansStep where to load the prototypes from
        mr_job = MRKmeansStep(args=['-r', 'local', docs,
                                    '--file', f'{cwd}/{folder}/prototypes{i}.txt',
                                    '--prot', f'{cwd}/{folder}/prototypes{i}.txt',
                                    '--jobconf', f'mapreduce.job.maps={nmaps}',
                                    '--jobconf', f'mapreduce.job.reduces={nreduces}',
                                    '--num-cores', str(nmaps)])
        result = run_runner(mr_job, i, folder)
        print(f'Time = {time() - start_time} seconds')

        # If there are no changes in two consecutive iteration we can stop
        if result is not None:
            print('Algorithm converged')
            write_prototype(result[1], f'{cwd}/{folder}/prototypes-final.txt')
            return result[0]

    return i


def main(args):
    copy_prototypes(args.prot, args.folder)
    perform_iterations(args.iter, args.docs, args.nmaps, args.nreduces, args.folder)


if __name__ == '__main__':
    main(parse_args())
