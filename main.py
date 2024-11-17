import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import glob
from pathlib import Path
import kaleido

# Data Source: https://www.hockey-reference.com/teams/SEA
# https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
pd.options.mode.chained_assignment = None
light_blue = [144,211,211]
red = [228,24,46]
red_rgb = "rgb(228,24,46)"
dark_blue = [3,22,35]
def get_color_spectrum(n, color1, color2, number_bands=15):
    colorname = f"rgb({int(color1[0] + n * (color2[0] - color1[0]) / (number_bands - 1))}" \
            + f",{int(color1[1] + n * (color2[1] - color1[1]) / (number_bands - 1))}" \
            + f",{int(color1[2] + n * (color2[2] - color1[2]) / (number_bands - 1))})"
    #print(colorname)
    return colorname

def convert_to_seconds(time_str):
    """Converts a string in the format 'min:sec' to seconds (float)."""
    minutes, seconds = time_str.split(':')
    return int(minutes) * 60 + int(seconds)
def convert_to_minutes(time_value):
    """Converts a string in the format 'min:sec' to seconds (float)."""
    if isinstance(time_value,str):
        if ':' in time_value:
            minutes, seconds = time_value.split(':')
        else:
            minutes = time_value
            seconds = 0
        return float(minutes) + float(seconds) / 60.
    elif isinstance(time_value,int):
        return float(time_value)

def sum_numeric_rows(df):
    # Create a DataFrame with only numeric columns
    numeric_df = df.select_dtypes(include='number')

    # Calculate the sum of each row in the numeric DataFrame
    row_sums = numeric_df.sum(axis=0)

    # Add the row sums to the original DataFrame
    #`df['row_sum'] = row_sums

    #return row_sums.to_frame().T
    return row_sums.to_frame().T

# Load citizenship data
input_fd = open("flags.csv", encoding="utf-8")
#flags = pd.read_csv(input_fd, header=0, encoding="latin1", engine="python")
flags = pd.read_csv(input_fd, header=0, encoding="utf-8-sig", engine="python")


# Load each season data for skaters
data = []
seasons = []
for f in sorted(glob.glob("season*.csv")):
    seasons.append(Path(f).stem.split('season-')[-1])
    print(f"Loading {f}...")
    #data.append(pd.read_csv(f, header=0, skiprows=1, index_col=0, usecols=lambda x: x not in ['Rk']))
    data.append(pd.read_csv(f, header=0, skiprows=1, usecols=lambda x: x not in ['Rk','ATOI']))
    #print(data[-1]["GWG"])
stacked_df = pd.concat(df.assign(Season = season) for df, season in zip(data, seasons)).reset_index(drop=True)

stacked_df['TOI'] = stacked_df["TOI"].apply(convert_to_minutes)
# Adding additional stats
stacked_df["PPP"] = stacked_df["PPG"] + stacked_df["PPA"]


number_seasons = len(seasons)
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
#        total_row = stacked_df.loc[stacked_df["Player"] == p].sum(numeric_only=True)
        total_row = sum_numeric_rows(stacked_df.loc[stacked_df["Player"] == p])
        total_row["Player"] = p
        total_row["Season"] = "Total"
        total_row["Age"] = stacked_df.loc[stacked_df.Player == p].iloc[-1]["Age"]
        try:
            total_row["Flag"] = flags.loc[flags.Player == p].iloc[0]["Flag"]
        except IndexError:
            print("Missing flag",p)
            total_row["Flag"] = None
        total_row["url"] = stacked_df.loc[stacked_df.Player == p].iloc[0]["url"]
        total_row["Pos"] = stacked_df.loc[stacked_df.Player == p].iloc[0]["Pos"]
        if total_row.loc[0, "G"] == 0:
            total_row["S%"] = 0.
        else:
            total_row["S%"] = total_row["G"] / total_row["SOG"] * 100
        total_row["ATOI"] = total_row["TOI"] / total_row["GP"]
        if total_row.loc[0, "FOW"] == 0:
            total_row["FO%"] = 0.
        else:
            total_row["FO%"] = total_row["FOW"] / (total_row["FOW"] + total_row["FOL"]) * 100
        stacked_df = pd.concat([stacked_df, total_row], sort=True).reset_index(drop=True)

stacked_df["PlayerAndFlag"] = stacked_df["Player"] + stacked_df["Flag"]

# Load each season data for goalies
data = []
seasons = []
for f in sorted(glob.glob("goalies*.csv")):
    seasons.append(Path(f).stem.split('goalies-')[-1])
    print(f"Loading {f} for goalies...")
    #data.append(pd.read_csv(f, header=0, skiprows=1, index_col=0, usecols=lambda x: x not in ['Rk']))
    data.append(pd.read_csv(f, header=0, skiprows=1, usecols=lambda x: x not in ['Rk']))
    #print(data[-1]["GWG"])
stacked_dfg = pd.concat(df.assign(Season = season) for df, season in zip(data, seasons)).reset_index(drop=True)

number_seasons = len(seasons)
# Build list of unique goalies
list_goalies = stacked_dfg.Player.unique().tolist()
# For each player, add an entry for their career total
for p in list_goalies:
    # if the player has played only 1 season, we can't use sum
    if stacked_dfg.loc[stacked_df.Player == p].shape[0] == 1:
        total_row = stacked_dfg.loc[stacked_df["Player"] == p]
        total_row["Season"] = "Total"
        total_row["Age"] = 1
        stacked_df = pd.concat([stacked_dfg, total_row]).reset_index(drop=True)
    else:
        total_row = sum_numeric_rows(stacked_dfg.loc[stacked_dfg["Player"] == p])
        total_row["Player"] = p
        total_row["Season"] = "Total"
        total_row["Age"] = stacked_dfg.loc[stacked_dfg.Player == p].shape[0]
        try:
            total_row["Flag"] = flags.loc[flags.Player == p].iloc[0]["Flag"]
        except IndexError:
            print("Missing flag",p)
            total_row["Flag"] = None
        total_row["url"] = stacked_dfg.loc[stacked_dfg.Player == p].iloc[0]["url"]
        if total_row.loc[0, "GA"] == 0:
            total_row["SV%"] = 100.
        else:
            total_row["SV%"] = total_row["SV"] / total_row["Shots"] * 100
        stacked_dfg = pd.concat([stacked_dfg, total_row], sort=True).reset_index(drop=True)

stacked_dfg["PlayerAndFlag"] = stacked_dfg["Player"] + stacked_dfg["Flag"]


def get_stat(df, p, s, stat):
    """

    :param df: database
    :param p: player
    :param s: season
    :param stat: stat
    :return: return the stat value for the player and season specified
    """
    try:
        return df[(df.Player == p) & (df.Season == s)][stat].values[0]
    except IndexError:
        return 0
def plotAlltimeLeaders(df, stat, statName, num, singleSeasonRecord, team, goalies=False):
    """

    :param stat: statistic to chart
    :param num: number of players we want to include
    :param singleSeasonRecord: single season record for the stat of interest
    :return:
    """


    top_leaders = df.loc[df.Season == "Total"].sort_values(stat, ascending=False).iloc[:num][['Player', 'PlayerAndFlag', stat]].reset_index(drop=True)

    # Basic plot
    # fig = go.Figure()
    # fig = px.bar(top_leaders, y=stat, x='Player')
    # fig.write_image("top_goalscorers.png")

    # for p in top_goalscorers.Player:
    #    print(p, [s for s in df.loc[df.Player == p].Season])

    # Maybe I should think about setting a different index for the subset dfs
    fig = go.Figure()
    #names = [f"{p.split()[-1]} {f}" for p,f in zip(top_leaders.Player,top_leaders.Flag)]
    names = [f for f in top_leaders['PlayerAndFlag']]
    #print([n for n in names if "nan" in n])
    for n, s in enumerate(seasons):
        stats = [get_stat(df, p, s, stat) for p in top_leaders.Player]
        #print(stats[5])
        if s != 'Total':
            #colors = [get_color_spectrum(n,light_blue,dark_blue,number_seasons) for st in stats]
            #fig.add_trace(go.Bar(name=s, x=names, y=stats,
            #                     marker_color=colors,
            #                     )
            #              )
            colors = [red_rgb if st == single_season_records[stat] \
                        else get_color_spectrum(n,light_blue,dark_blue,number_seasons) for st in stats]
            if stat == "P_M":
                fig.add_trace(go.Bar(name=s, x=names, y=stats,
                                 marker_color=colors,
                                 showlegend=False,
                                 offsetgroup=0,
                                 width=0.3,
                                 offset=0.3*(n-1),
                               )
                          )
            else:
                fig.add_trace(go.Bar(name=s, x=names, y=stats,
                                     marker_color=colors,
                                     showlegend=False,
                                    )
                             )

        fig.add_trace(go.Bar(x=[None],y=[None],
                                     name=s,
                                     marker_color=get_color_spectrum(n,light_blue,dark_blue,number_seasons), 
                                     showlegend=True))

    if stat == "P_M":
        fig.update_layout(barmode='overlay') #, bargroupgap=0.2)
    else:
        fig.update_layout(barmode='group')
    fig.add_trace(go.Bar(x=[None],y=[None],
                         name='Single Season Record',
                         marker_color=red_rgb,
                         showlegend=True))

    fig.update_layout(barmode='stack')
    fig.update_xaxes(tickangle=45)
    fig.update_layout(title_text=f"{team} All-Time Leaders in {statName}")
    #fig.show()
    if goalies:
        fig.write_image(f"top_goalies_leaders_{stat}_stacked.png",scale=2)
        fig.write_html(f"top_goalies_leaders_{stat}_stacked.html")
    else:
        fig.write_image(f"top_leaders_{stat}_stacked.png",scale=2)
        fig.write_html(f"top_leaders_{stat}_stacked.html")



team = "Seattle Kraken"
statName = {"GP": "Games Played",
            "G": "Goals Scored",
            "A": "Assists",
            "PTS": "Points Scored",
            "PIM": "Penalty Minutes",
            "EVG": "Even-Strength Goals",
            "PPG": "Powerplay Goals",
            "SHG": "Short-handed Goals",
            "GWG": "Game-Winnning Goals",
            "EVA": "Even-Strength Assists",
            "PPA": "Powerplay Assists",
            "PPP": "Powerplay Points",
            "SHA": "Short-handed Assists",
            "SOG": "Shots On Goal",
            "BLK": "Blocked Shots",
            "HIT": "Hits",
            "P_M": "Plus/Minus",
            }
single_season_records = {}
for stat in ["GP", "G", "A", "PTS", "PIM", "EVG", "PPG", "SHG", "GWG", "EVA", "PPA",
             "PPP", "SHA", "SOG", "BLK", "HIT", "P_M"]:
    single_season_records[stat] = stacked_df[stacked_df.Season != 'Total'][stat].max()
    plotAlltimeLeaders(stacked_df, stat, statName[stat], 15, single_season_records[stat], team)

single_season_records = {}
statName = {"GP": "Games Played",
            "GS": "Games Started",
            "W": "Wins",
            "L": "Losses",
            "GA": "Goals Against",
            "Shots": "Shots Against",
            "SV": "Saves",
            "SO": "Shutouts",
            "QS": "Quality Starts",
            "GPS": "Goalie Point Shares",
            }

for stat in statName:
    single_season_records[stat] = stacked_dfg[stacked_dfg.Season != 'Total'][stat].max()
    plotAlltimeLeaders(stacked_dfg, stat, statName[stat], 15, single_season_records[stat], team, goalies=True)

# TODO
## Use better flags like https://github.com/hampusborgos/country-flags
## or https://github.com/google/region-flags
## Add plus/minus with a staggered stack chart

