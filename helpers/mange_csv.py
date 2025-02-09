import pandas as pd
import os
import argparse
import zipfile

#
# # split large csv into smaller bite size consumables
#
def split_csv(output_method, input_csv, output_dir, rows_per_file=1000):
    """
    Reads a CSV file in chunks and saves each chunk as a separate CSV.

    Args:
        input_csv (str): Path to the input CSV file.
        output_dir (str): Directory to save the output files. 
        rows_per_file (int,defaults 1000): Number of rows per output file.
    """
    print('filename .........:', input_csv)
    print('output ...........:', output_dir)
    print('rows per file ....:', rows_per_file)
    
    os.makedirs(output_dir, exist_ok=True)
    # get the input file basename from the provided path, remove ext
    base_name, _ = os.path.splitext(os.path.basename(input_csv))
    try:
        for chunk_number, chunk in enumerate(pd.read_csv(input_csv, chunksize=rows_per_file)):
            mt_idx = str(chunk_number+1).zfill(4) # pad with zeros, sortable
            output_file = os.path.join(
                output_dir,
                f"{base_name}_{mt_idx}.{output_method}")
            if output_method=='zip':
                with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    csv_data = chunk.to_csv(index=False)
                    zf.writestr(f"{base_name}_{mt_idx}.csv", csv_data)
            else:
                chunk.to_csv(output_file, index=False)
            print(f"Saved: {output_file}")

    except FileNotFoundError:
      print(f"Error: CSV file not found at {input_csv}")
    except Exception as e:
      print(f"An error occurred: {e}")


if __name__ == "__main__":
    # setup, params
    parser = argparse.ArgumentParser(prog='github-scrape')
    # namespace / repo, maybe split these amd make repo delimited list??
    parser.add_argument('--method', 
                        choices=["zip", "csv"],
                        help='output method - one of csv or zip', default='csv')
    parser.add_argument('--file', help='csv file to split and zip', default='../data/pytorch_pytorch/pytorch_issues.csv')
    parser.add_argument('--rows', type=int, help='number of rows per file', default=2000)
    parser.add_argument('--output', help='folder where files are output', default=None)
    args = parser.parse_args()

    if not args.output:
        args.output = os.path.join(os.path.dirname(args.file),'mange')
    split_csv(args.method.lower(), args.file, args.output, args.rows)
    print("Splitting complete, mange tout!")
