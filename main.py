import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import glob
from pathlib import Path
import kaleido
# https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
pd.options.mode.chained_assignment = None



# Load each season data
data = []
seasons = []
for f in sorted(glob.glob("season*.csv")):
    seasons.append(Path(f).stem.split('season-')[-1])
    print(f"Loading {f}...")
    #data.append(pd.read_csv(f, header=0, skiprows=1, index_col=0, usecols=lambda x: x not in ['Rk']))
    data.append(pd.read_csv(f, header=0, skiprows=1, usecols=lambda x: x not in ['Rk']))
    #print(data[-1]["GWG"])
stacked_df = pd.concat(df.assign(Season = season) for df, season in zip(data, seasons)).reset_index(drop=True)

# Build list of unique players
list_players = stacked_df.Player.unique().tolist()
# For each player, add an entry for their career total
for p in list_players:
#for p in ["Jared McCann"]:
    # if the player has played only 1 season, we can't use sum
    if stacked_df.loc[stacked_df.Player == p].shape[0] == 1:
        total_row = stacked_df.loc[stacked_df["Player"] == p]
        total_row["Season"] = "Total"
        total_row["Age"] = 1
        stacked_df = pd.concat([stacked_df, total_row]).reset_index(drop=True)
    else:
        total_row = stacked_df.loc[stacked_df["Player"] == p].sum()
        total_row.loc["Player"] = p
        total_row.loc["Season"] = "Total"
        total_row.loc["Age"] = stacked_df.loc[stacked_df.Player == p].shape[0]
        total_row.loc["Flag"] = stacked_df.loc[stacked_df.Player == p].iloc[0]["Flag"]
        total_row.loc["url"] = stacked_df.loc[stacked_df.Player == p].iloc[0]["url"]
        total_row.loc["Pos"] = stacked_df.loc[stacked_df.Player == p].iloc[0]["Pos"]
        if total_row.loc["G"] == 0:
            total_row.loc["S%"] = 0.
        else:
            total_row.loc["S%"] = total_row.loc["G"] / total_row.loc["S"] * 100
        total_row.loc["ATOI"] = total_row.loc["TOI"] / total_row.loc["GP"]
        if total_row.loc["FOW"] == 0:
            total_row.loc["FO%"] = 0.
        else:
            total_row.loc["FO%"] = total_row.loc["FOW"] / (total_row.loc["FOW"] + total_row.loc["FOL"]) * 100
        stacked_df = pd.concat([stacked_df, total_row.to_frame().T]).reset_index(drop=True)

# TOP 10 goal scorers
top_goalscorers = stacked_df.loc[stacked_df.Season == "Total"].sort_values("G", ascending=False).iloc[:15][['Player', 'Flag', 'G']]
fig = go.Figure()
fig = px.bar(top_goalscorers, y='G', x='Player')
fig.show()
fig.write_image("top_goalscorers.png")

#for p in top_goalscorers.Player:
#    print(p, [s for s in stacked_df.loc[stacked_df.Player == p].Season])
def get_goals(df,p,s):
    try:
        return df[(df.Player == p) & (df.Season == s)].G.values[0]
    except IndexError:
        return 0
# Maybe I should think about setting a different index for the subset dfs
fig = go.Figure()
names = [p.split()[-1] for p in top_goalscorers.Player]
for s in seasons:
    goals = [get_goals(stacked_df,p,s) for p in top_goalscorers.Player]
    # goals = []
    # for p in top_goalscorers.Player:
    #     print(p)
    #     goals.append(stacked_df[(stacked_df.Player == p) & (stacked_df.Season == s)].G.values[0] )
    if s != 'Total':
        fig.add_trace(go.Bar(name=s, x=names, y=goals))

fig.update_layout(barmode='stack')
fig.show()
fig.write_image("top_goalscorers_stacked.png")
# TODO
## Use better flags like https://github.com/hampusborgos/country-flags
## or https://github.com/google/region-flags