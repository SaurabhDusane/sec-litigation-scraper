#!/bin/bash

#SBATCH --account=grp_hdavulcu
#SBATCH -N 1                # number of nodes
#SBATCH -c 1                # number of cores
#SBATCH -t 0-03:00:00       # time in d-hh:mm:ss
#SBATCH -p public              # partition
#SBATCH -q public           # QOS
#SBATCH -G a100:1                # number of GPUs
#SBATCH --mem=32G           # memory
#SBATCH -o slurm.%j.out     # file to save job's STDOUT (%j = JobId)
#SBATCH -e slurm.%j.err     # file to save job's STDERR (%j = JobId)
#SBATCH --mail-type=ALL     # Send an e-mail when a job starts, stops, or fails
#SBATCH --mail-user="sdusane1@asu.edu"
#SBATCH --export=NONE       # Purge the job-submitting shell environment

#Load required software
module load mamba/latest

source activate legal_ai

pip freeze

echo "Starting at $(date)"
echo "Python: $(python --version)"
echo "curl: $(curl --version | head -1)"

# Scrape with 3 workers, 10 pages
python sec_litigation_scraper_v8.py scrape --pages 10 --workers 3

# Show status
python sec_litigation_scraper_v8.py status

# Export both formats
python sec_litigation_scraper_v8.py export --format both -o sec_litigation_releases

echo "Completed at $(date)"