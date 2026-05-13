import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import io

def plot_log(log_path, output_path, title):
    print(f"Processing {log_path}...")
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Official log format vs backtester log format
        if content.startswith('{'):
            # It's a JSON file
            data = json.loads(content)
            csv_content = data.get('activitiesLog', '')
        else:
            # Maybe it has a Sandbox logs section, look for Activities log
            if 'Activities log:' in content:
                csv_content = content.split('Activities log:\n')[1].split('\n\n')[0]
            else:
                print("Could not find activities log in", log_path)
                return

        if not csv_content:
            print("No CSV content found.")
            return

        df = pd.read_csv(io.StringIO(csv_content), sep=';')
        
        # Calculate total PnL per timestamp
        if 'profit_and_loss' not in df.columns:
            print(f"No profit_and_loss column in {log_path}")
            return
            
        # Group by timestamp and sum PnL for overall, or plot per product
        timestamps = df['timestamp'].unique()
        timestamps.sort()
        
        plt.style.use('dark_background')
        plt.figure(figsize=(12, 6))
        
        products = df['product'].unique()
        
        total_pnl = {t: 0 for t in timestamps}
        
        for p in products:
            p_df = df[df['product'] == p].sort_values('timestamp')
            plt.plot(p_df['timestamp'], p_df['profit_and_loss'], label=p, alpha=0.6)
            
            for _, row in p_df.iterrows():
                total_pnl[row['timestamp']] += row['profit_and_loss']
                
        # Plot total PnL
        sorted_ts = sorted(list(total_pnl.keys()))
        overall_pnl = [total_pnl[t] for t in sorted_ts]
        plt.plot(sorted_ts, overall_pnl, label='Total PnL', color='white', linewidth=2, linestyle='--')
        
        plt.title(title, fontsize=16)
        plt.xlabel("Timestamp", fontsize=12)
        plt.ylabel("PnL", fontsize=12)
        plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
        plt.grid(True, alpha=0.2)
        plt.tight_layout()
        
        plt.savefig(output_path, dpi=300)
        plt.close()
        print(f"Saved plot to {output_path}")
        
    except Exception as e:
        print(f"Error processing {log_path}: {e}")

if __name__ == "__main__":
    os.makedirs(r"d:\PROSPERITY\visualizations", exist_ok=True)
    
    # Plot Round 3
    plot_log(
        r"d:\PROSPERITY\round3\logs\432769\432769.log", 
        r"d:\PROSPERITY\visualizations\Round3_PnL.png", 
        "Round 3 Bot PnL"
    )
    
    # Plot Round 4
    plot_log(
        r"d:\PROSPERITY\round4\Logs\544851\544851.log", 
        r"d:\PROSPERITY\visualizations\Round4_PnL.png", 
        "Round 4 Bot PnL (Total PnL ~57k)"
    )
    
    # Plot Round 5
    plot_log(
        r"d:\PROSPERITY\round5\Logs\576896\576896.log", 
        r"d:\PROSPERITY\visualizations\Round5_PnL.png", 
        "Round 5 Bot PnL"
    )
