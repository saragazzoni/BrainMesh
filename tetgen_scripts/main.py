from problem import Problem
import time
from datetime import datetime
from mpi4py import MPI
import sys
import argparse

### MAIN ###

if __name__ == "__main__":
    tic=time.time()
    
    if MPI.COMM_WORLD.size > 1:
        serial_or_parallel = "parallel"
    else:
        serial_or_parallel = "serial"
    sys.stdout.write(f"Running in {serial_or_parallel} mode")
    sys.stdout.flush()

    parser = argparse.ArgumentParser(description="Run simulation")
    parser.add_argument("name_file", type=str, help="Path to parameters file")
        
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    problem = Problem(parser)
    tic_fom=time.time()
    problem.refine_mesh()
    toc_fom=time.time()
    if MPI.COMM_WORLD.rank==0:
        print("Elapsed time FOM : ", toc_fom-tic_fom)


