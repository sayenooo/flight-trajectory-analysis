"""Run the documented full-resolution LHR-FRA pipeline.

Prepared with ChatGPT/Codex assistance. Existing raw and prepared inputs remain
unchanged unless --from-raw is explicitly selected. Derived outputs are updated.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def matrix_is_current(root=ROOT):
    import pandas as pd
    prepared = root / 'data/lhr_fra_prepared'
    matrix = root / 'data/lhr_fra_hausdorff'
    required = [matrix/'matrix_report.json', matrix/'hausdorff_distance_matrix_km.npy',
                matrix/'hausdorff_flight_ids.csv', matrix/'matrix.sha256']
    if not all(p.is_file() for p in required):
        return False
    try:
        report = json.loads(required[0].read_text())
        if report['clean_points_sha256'] != digest(prepared/'flight_points_clean.csv.gz'):
            return False
        if required[3].read_text().strip() != digest(required[1]):
            return False
        accepted = pd.read_csv(prepared/'accepted_flights.csv').flight_id.tolist()
        ids = pd.read_csv(required[2])
        return ids.flight_id.tolist() == accepted and ids.matrix_index.tolist() == list(range(len(accepted)))
    except (OSError, ValueError, KeyError, AttributeError):
        return False

def run(script, *args):
    command = [sys.executable, str(ROOT/'src'/script), *args]
    print('\nRunning:', ' '.join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-raw', action='store_true', help='Recreate prepared data from the raw LFS CSV and flight list.')
    parser.add_argument('--rebuild-matrix', action='store_true', help='Recompute all flight-pair distances.')
    args = parser.parse_args()
    if args.from_raw:
        run('prepare_lhr_fra.py')
    for name in ['flight_points_clean.csv.gz', 'accepted_flights.csv', 'flight_qc.csv']:
        if not (ROOT/'data/lhr_fra_prepared'/name).is_file():
            parser.error(f'Missing prepared data: {name}. Clone the complete repository first.')
    if args.from_raw or args.rebuild_matrix or not matrix_is_current():
        run('build_lhr_fra_matrix.py')
        matrix = ROOT/'data/lhr_fra_hausdorff'
        (matrix/'matrix.sha256').write_text(digest(matrix/'hausdorff_distance_matrix_km.npy')+'\n')
    else:
        print('Using the matrix matching the prepared-file hash and accepted flight order.', flush=True)
    run('cluster_lhr_fra.py', '--min-cluster-size', '15', '--min-samples', '5')
    run('cluster_lhr_fra.py', '--min-cluster-size', '10', '--min-samples', '5')
    run('inspect_lhr_fra_candidates.py')
    print('\nComplete. See README.md for output paths.', flush=True)

if __name__ == '__main__':
    main()
