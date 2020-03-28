import multiprocessing 
import uuid


from database import insert_row


def insert_rows_in_parallel(args_list):
    num_procs = len(args_list)

    print(f'Spawning {num_procs} processes...')

    pool = multiprocessing.Pool(num_procs)

    results = pool.map(insert_row, args_list)

    pool.close()
    pool.join()

    print(f'{num_procs} processes complete.')


def generate_example_rows(num_records):
    return [(str(uuid.uuid4()),) for _ in range(0, num_records)]    
