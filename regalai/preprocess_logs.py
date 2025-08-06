### Updated: preprocess_logs.py
# (This file is now optional and mainly used for dumping CSVs manually)
from utils.log_parser import parse_logs
import pandas as pd

def main():
    data = parse_logs("logs.txt")
    df = pd.DataFrame(data)
    df.to_csv("regalai/parsed_dataset.csv", index=False)
    print(f"✅ Exported {len(df)} entries to parsed_dataset.csv")

if __name__ == "__main__":
    main()