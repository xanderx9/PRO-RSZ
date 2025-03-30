import json
import requests
import time
import os

PROGRESS_FILE = "progress.json"

def save_progress(address, num_transactions, checked_count, found_count):
    with open(PROGRESS_FILE, "w") as file:
        json.dump({
            "address": address,
            "num_transactions": num_transactions,
            "checked_count": checked_count,
            "found_count": found_count
        }, file)

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as file:
            return json.load(file)
    return {"checked_count": 0, "found_count": 0}

def fetch_transactions(addr, num_transactions):
    url = f'https://blockchain.info/address/{addr}?format=json&offset=0'
    all_txs = []
    
    try:
        response = requests.get(url, headers={"Accept-Encoding": "gzip"})
        response.raise_for_status()
        data = response.json()
        
        ntx = data['n_tx']
        print(f"Address: {addr} has {ntx} transactions.")
        
        if num_transactions > ntx:
            num_transactions = ntx
        
        for offset in range(0, num_transactions, 100):
            while True:
                try:
                    print(f"Fetching transactions from offset {offset}...")
                    response = requests.get(f'https://blockchain.info/address/{addr}?format=json&offset={offset}', headers={"Accept-Encoding": "gzip"})
                    response.raise_for_status()
                    batch_data = response.json()
                    all_txs.extend(batch_data['txs'])
                    break
                except requests.exceptions.RequestException as e:
                    print(f"Error fetching transactions: {e}")
                    print("Retrying in 5 seconds...")
                    time.sleep(5)
    
    except requests.exceptions.RequestException as e:
        print(f"Critical error fetching initial transaction data: {e}")
        return None
    
    return all_txs

def check_r_reuse_in_tx(tx):
    inputs = [inp['script'] for inp in tx.get('inputs', []) if 'script' in inp]
    outputs = [out['script'] for out in tx.get('out', []) if 'script' in out]
    all_scripts = inputs + outputs
    
    try:
        r_values = [script[10:74] for script in all_scripts if len(script) > 74]
        
        duplicates = {}
        for idx, r in enumerate(r_values):
            if r in duplicates:
                duplicates[r].append(idx)
            else:
                duplicates[r] = [idx]
        
        reused_r = {r: idx_list for r, idx_list in duplicates.items() if len(idx_list) > 1}
        return reused_r
    except Exception as e:
        print(f"Error processing transaction {tx['hash']}: {e}. Skipping this transaction.")
        return None

def analyze_address(addr, num_transactions, checked_count, found_count):
    transactions = fetch_transactions(addr, num_transactions)
    if not transactions:
        print("No transactions fetched for address. Skipping.")
        return checked_count, found_count
    
    print(f"Analyzing {len(transactions)} transactions for address {addr}...\n")
    
    reused_found = False
    results = []
    
    for tx in transactions:
        reused_r = check_r_reuse_in_tx(tx)
        if reused_r:
            reused_found = True
            results.append(f"Transaction {tx['hash']} has reused R-values:")
            for r, locations in reused_r.items():
                results.append(f"  R-value: {r} reused at positions: {locations}")
    
    checked_count += 1
    if reused_found:
        found_count += 1
        filename = f"{addr}.txt"
        with open(filename, "w") as file:
            file.write("\n".join(results))
        print(f"🔴 R-value reuse found. Results saved in '{filename}'.")
    else:
        print(f"No R-value reuse detected for address: {addr}.")
    
    print(f"Total Addresses Checked So Far: {checked_count}")
    print(f"Total Vulnerabilities Found So Far: {found_count}")
    
    return checked_count, found_count

def main():
    print("Welcome to the CRYPTOGRAPHYTUBE!")
    
    progress = load_progress()
    
    if progress.get("address"):
        print(f"Resuming from address: {progress['address']} with {progress['num_transactions']} transactions.")
        address_file = input("Enter the path to the Bitcoin address file (same file as before): ")
    else:
        address_file = input("Enter the path to the Bitcoin address file: ")
    
    with open(address_file, 'r') as file:
        addresses = file.readlines()

    if progress.get("address"):
        start_index = addresses.index(progress["address"] + "\n")
    else:
        start_index = 0

    while True:
        try:
            num_transactions = int(input("Enter the number of transactions to fetch (1-infinite): "))
            if num_transactions >= 1:
                break
            else:
                print("Please enter a number greater than or equal to 1.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")
    
    checked_count = progress["checked_count"]
    found_count = progress["found_count"]

    for addr in addresses[start_index:]:
        addr = addr.strip()
        print(f"Processing address: {addr}")
        checked_count, found_count = analyze_address(addr, num_transactions, checked_count, found_count)
        save_progress(addr, num_transactions, checked_count, found_count)
        print("Waiting for 5 seconds before processing next address...")
        time.sleep(5)

if __name__ == "__main__":
    main()







