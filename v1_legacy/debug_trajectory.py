
import csv

TRAJECTORY_FILE = 'trajectory_replay_v3.csv'

def show_hold_samples():
    with open(TRAJECTORY_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        print(f"Header: {header}")
        
        count = 0
        for row in reader:
            if row[2] == 'HOLD': # State column index 2
                print(row)
                count += 1
                if count >= 10: break

if __name__ == "__main__":
    show_hold_samples()
