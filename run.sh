#!/bin/bash
#BSUB -P fus131
#BSUB -J test_disrupt
#BSUB -W 00:30 #30 minutes
#BSUB -q debug
#BSUB -nnodes 1
#BSUB -alloc_flags maximizegpfs

#echo this run.sh file contents in the log file, to capture inputs
echo "$0"
printf "%s" "$(<$0)"
echo ""

#Not sure how to get this with LSF yet
#echo $SLURM_JOB_NODELIST
#nodes="$(scontrol show hostname $SLURM_JOB_NODELIST | paste -d, -s)"
#echo ${nodes}

#For now, leave off nvidia-smi 
#Run nvidia-smi on each node
#TODO: Can we send signal to kill? Instead of timeout?
#for node in ${nodes//,/ } 
#do
#    ssh ${node} 'timeout 2400 nvidia-smi -l 1 -f '${PWD}'/nvidia.'${SLURM_JOB_ID}'.${HOSTNAME}.txt' &
#done

#print out git commit
echo "git commit"
git --git-dir=$PWD/disruptcnn/.git  show --oneline -s

#for cProfile, to force sync CUDA ops
#export CUDA_LAUNCH_BLOCKING=0

file="file:///gpfs/alpine/scratch/rchurchi/fus131/main_${LSB_JOBID}.txt"
export OMP_NUM_THREADS=8
#fileprof="profile_${LSB_JOBID}_rank_${LS_JOBPID}.prof"
module load ibm-wml-ce
source activate torch-env
module load nsight-systems
#may have to specify full path to python here (on Ascent had to with nsys)
jsrun --nrs 6 --rs_per_host 6 --tasks_per_rs 1 --cpu_per_rs 6 --gpu_per_rs 1 \
                   nsys profile -t cuda,nvtx -s cpu -o profile_%q{OMPI_COMM_WORLD_RANK} \
		   python -u disruptcnn/main.py --dist-url $file --backend 'nccl' \
                    --batch-size=12 --dropout=0.1 --clip=0.3 \
                    --lr=0.5 \
                    --workers=6 \
                    --nsub 78125 \
                    --epochs=4 \
                    --label-balance='const' \
                    --data-step=10 --levels=4 --nrecept=30000 --nhid=80 \
                    --undersample \
                    --iterations-valid 600
#try to ensure the profiler and file movement finishes with everything
sleep 60
