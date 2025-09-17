import csv

input_file = "/home/quakinh943/IPLOCALTION/data/ip_locations.csv"
output_file = "ip_locations_clean.csv"

with open(input_file, "r", encoding="utf-8", errors="ignore") as infile, \
     open(output_file, "w", encoding="utf-8", newline="") as outfile:
    
    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    for row in reader:
        if len(row) < 4:  # thiếu cột
            continue
        writer.writerow(row)
