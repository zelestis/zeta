import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

# -------------------------------
# 1. Load the Data
# -------------------------------
# Game-level log: each row represents a game, with start time and duration.
game_file = "~/.zeta/zeta_log.csv"
df_games = pd.read_csv(game_file, parse_dates=["Timestamp"])
df_games["Duration (s)"] = pd.to_numeric(df_games["Duration (s)"], errors="coerce")
# Calculate game end time based on start time and duration.
df_games["game_end"] = df_games["Timestamp"] + pd.to_timedelta(
    df_games["Duration (s)"], unit="s"
)
df_games = df_games.sort_values("Timestamp")

# Question-level summary log.
summary_file = "~/.zeta/zeta_log_summary.csv"
df_summary = pd.read_csv(summary_file, parse_dates=["datetime"])
df_summary["time_taken"] = pd.to_numeric(df_summary["time_taken"], errors="coerce")

# Extract the operator from the question (e.g., +, -, *, /).
def extract_operator(question):
    import re
    match = re.search(r'([\+\-\*/])', str(question))
    return match.group(1) if match else None

df_summary["operator"] = df_summary["question"].apply(extract_operator)

# Debug print to check extraction
print("\nSample of questions and extracted operators:")
print(df_summary[["question", "operator"]].head(10))

# Remove questions with time_taken > 80 seconds.
df_summary = df_summary[df_summary["time_taken"] <= 80]

df_summary = df_summary.sort_values("datetime")

# After loading summary data
print("\nInitial data counts by operator and date:")
print(df_summary.groupby([df_summary['datetime'].dt.date, 'operator']).size().unstack(fill_value=0))

# -------------------------------
# 3. Skip the Game Assignment for Daily Averages
# -------------------------------
# For the first graph, we'll work directly with df_summary
# since we only need daily averages, not game-specific data
df_daily = df_summary.copy()
df_daily["date"] = df_daily["datetime"].dt.date

# Debug print
print("\nData counts by date and operator before any filtering:")
print(df_daily.groupby(["date", "operator"])["time_taken"].count().unstack(fill_value=0))

# Calculate daily averages
grouped = df_daily.groupby(["date", "operator"])["time_taken"].mean().unstack()
overall_daily = df_daily.groupby("date")["time_taken"].mean()

# Graph 1: Daily Average Times Overall & by Operation
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(overall_daily.index, overall_daily.values, marker="o", label="Overall", color="black", linewidth=2)
for op in ["+", "-", "*", "/"]:
    if op in grouped.columns:
        ax.plot(grouped.index, grouped[op], marker="o", label=op)
        # Add debug print for each operator's data
        print(f"\nData points for operator {op}:")
        print(grouped[op].dropna())

ax.set_xlabel("Date")
ax.set_ylabel("Average Time per Question (s)")
ax.set_title("Daily Average Time per Question (Overall & by Operation)")
ax.legend()
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
ax.xaxis.set_major_locator(mdates.DayLocator())
plt.xticks(rotation=45)
plt.tight_layout()

# -------------------------------
# 5. Set Up PDF for Multiple Plots
# -------------------------------
pdf_filename = "zeta_analysis.pdf"
with PdfPages(pdf_filename) as pdf:
    # Graph 1: Daily Average Times Overall & by Operation
    df_daily = df_summary.copy()
    df_daily["date"] = df_daily["datetime"].dt.date

    # Debug print
    print("\nData counts by date and operator before any filtering:")
    print(df_daily.groupby(["date", "operator"])["time_taken"].count().unstack(fill_value=0))

    # Calculate daily averages
    grouped = df_daily.groupby(["date", "operator"])["time_taken"].mean().unstack()
    overall_daily = df_daily.groupby("date")["time_taken"].mean()

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(overall_daily.index, overall_daily.values, marker="o", label="Overall", color="black", linewidth=2)
    for op in ["+", "-", "*", "/"]:
        if op in grouped.columns:
            ax.plot(grouped.index, grouped[op], marker="o", label=op)
            # Add debug print for each operator's data
            print(f"\nData points for operator {op}:")
            print(grouped[op].dropna())

    ax.set_xlabel("Date")
    ax.set_ylabel("Average Time per Question (s)")
    ax.set_title("Daily Average Time per Question (Overall & by Operation)")
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    plt.xticks(rotation=45)
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

    # Graph 2: Last 24 Hours – Average Time per Question by Game with Smoothed Mean by Operator
    # First, get games from last 24 hours
    last_24h_games = df_games[
        df_games["Timestamp"] >= df_games["Timestamp"].max() - pd.Timedelta(hours=24)
    ]
    
    # Merge questions with games using merge_asof
    last_24h_merged = pd.merge_asof(
        df_summary[df_summary["datetime"] >= df_summary["datetime"].max() - pd.Timedelta(hours=24)],
        last_24h_games[["Timestamp", "game_end"]],
        left_on="datetime",
        right_on="Timestamp",
        direction="backward"
    )
    
    # Keep only questions that fall within game sessions
    last_24h_merged = last_24h_merged[
        (last_24h_merged["datetime"] >= last_24h_merged["Timestamp"]) &
        (last_24h_merged["datetime"] <= last_24h_merged["game_end"])
    ]
    
    operators = ["+", "-", "*", "/"]
    colors = {'+':"blue", '-':"green", '*':"red", '/':"purple"}
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Calculate game-level averages
    game_overall = last_24h_merged.groupby("Timestamp")["time_taken"].mean().reset_index()
    
    # Plot overall scatter points
    ax.scatter(
        game_overall["Timestamp"],
        game_overall["time_taken"],
        color="black",
        label="Overall Average",
        alpha=0.6
    )
    
    # Add overall smoothed mean line
    if len(game_overall) > 1:
        game_overall["smoothed"] = game_overall["time_taken"].rolling(
            window=3, min_periods=1
        ).mean()
        ax.plot(
            game_overall["Timestamp"],
            game_overall["smoothed"],
            color="black",
            linestyle="-",
            label="Overall Smoothed Mean"
        )
    
    # Then plot operator-specific data
    for op in operators:
        op_data = last_24h_merged[last_24h_merged["operator"] == op]
        if not op_data.empty:
            # Calculate averages per game for this operator
            game_avg_op = op_data.groupby("Timestamp")["time_taken"].mean().reset_index()
            
            # Plot scatter points for this operator
            ax.scatter(
                game_avg_op["Timestamp"],
                game_avg_op["time_taken"],
                color=colors[op],
                label=f"{op} Average",
                alpha=0.6
            )
            
            # Add smoothed mean line for this operator
            if len(game_avg_op) > 1:
                game_avg_op["smoothed"] = game_avg_op["time_taken"].rolling(
                    window=3, min_periods=1
                ).mean()
                ax.plot(
                    game_avg_op["Timestamp"],
                    game_avg_op["smoothed"],
                    color=colors[op],
                    linestyle="--",
                    label=f"{op} Smoothed Mean"
                )
    
    ax.set_xlabel("Game Start Time")
    ax.set_ylabel("Average Time per Question (s)")
    ax.set_title("Average Time per Question by Game and Operator (Last 24 Hours)")
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45)
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

    # Graph 3: 30 Worst Question Times in the Last 24 Hours
    worst_30 = last_24h_merged.nlargest(30, "time_taken").sort_values(
        "time_taken", ascending=True
    )
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.barh(worst_30["question"], worst_30["time_taken"], color="salmon")
    ax.set_xlabel("Time Taken (s)")
    ax.set_title("30 Worst Question Times in the Last 24 Hours")
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

    # Graph 4: Distribution of Time Taken for All Questions (Filtered, X-axis 0–80s)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(df_summary["time_taken"], bins=30, color="skyblue", edgecolor="black")
    ax.set_xlabel("Time Taken (s)")
    ax.set_ylabel("Frequency")
    ax.set_title("Distribution of Time Taken for All Questions (<=80s)")
    ax.set_xlim(0, 80)
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

    # Graph 5: Boxplot of Time Taken by Operator (Filtered, omit >80s)
    fig, ax = plt.subplots(figsize=(10, 6))
    operators = ["+", "-", "*", "/"]
    data = [
        df_summary[df_summary["operator"] == op]["time_taken"]
        for op in operators
        if not df_summary[df_summary["operator"] == op].empty
    ]
    present_ops = [op for op in operators if not df_summary[df_summary["operator"] == op].empty]
    ax.boxplot(data, tick_labels=present_ops)
    ax.set_xlabel("Operator")
    ax.set_ylabel("Time Taken (s)")
    ax.set_title("Boxplot of Time Taken by Operator (<=80s)")
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

    # Graph 6: Time Improvement Trend
    # Calculate average time per day and plot trend
    daily_avg = df_summary.groupby(df_summary['datetime'].dt.date).agg({
        'time_taken': 'mean'
    }).reset_index()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot actual averages
    ax.scatter(daily_avg['datetime'], daily_avg['time_taken'], 
              alpha=0.4, color='gray', label='Daily Averages')
    
    # Add trend line
    z = np.polyfit(range(len(daily_avg)), daily_avg['time_taken'], 1)
    p = np.poly1d(z)
    ax.plot(daily_avg['datetime'], p(range(len(daily_avg))), 
            'r--', label='Trend Line')
    
    ax.set_xlabel('Date')
    ax.set_ylabel('Average Time per Question (s)')
    ax.set_title('Time Improvement Trend (All Days)')
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45)
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

print(f"All plots have been saved to {pdf_filename}")
