import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import glob
from pathlib import Path
import kaleido


from io import StringIO
import requests
from bs4 import BeautifulSoup, Comment
import pandas as pd
import os
import re

def find_and_parse_tables(soup, url, output_dir, target_table_id):
    """
    Finds tables in the parsed HTML, prioritizing pre-formatted CSV data in hidden divs,
    and falls back to parsing HTML tables.
    """
    all_tables = []
    # Find all table elements to identify their IDs
    for table in soup.find_all('table'):
        table_id = table.get('id')
        if table_id:
            all_tables.append({'id': table_id, 'html': str(table)})
    
    # Also look for tables in comments
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment_soup = BeautifulSoup(comment, 'html.parser')
        for table in comment_soup.find_all('table'):
            table_id = table.get('id')
            if table_id and not any(t['id'] == table_id for t in all_tables):
                 all_tables.append({'id': table_id, 'html': str(table)})

    if not all_tables:
        print("❌ No tables were found on the page to download.")
        return None, 0

    target_df = None
    files_saved = 0

    for table_info in all_tables:
        table_id = table_info['id']
        if table_id not in ['player_stats', 'goalie_stats']:
            continue  # Skip tables we're not interested in
        df = None
        
        try:
            # --- NEW: Prioritize finding the pre-formatted CSV data ---
            csv_div_id = f"csv_{table_id}"
            csv_element = soup.find('div', id=csv_div_id)
            
            if csv_element and csv_element.string:
                print(f"✅ Found pre-formatted CSV for table '{table_id}'. Parsing directly.")
                # The actual CSV data is inside a comment within the div
                csv_comment = csv_element.find(string=lambda text: isinstance(text, Comment))
                if csv_comment:
                    df = pd.read_csv(StringIO(csv_comment))

            # --- Fallback to original HTML table parsing if CSV not found ---
            if df is None:
                print(f"⚠️ No pre-formatted CSV found for '{table_id}'. Parsing HTML table as fallback.")
                table_html = table_info['html']
                data_frames = pd.read_html(StringIO(table_html))
                if data_frames:
                    df = data_frames[0]

            if df is not None:
                # Clean up multi-index column headers
                if isinstance(df.columns, pd.MultiIndex):
                    new_columns = []
                    for col in df.columns:
                        # If the top level is 'Unnamed', just use the bottom level.
                        if 'Unnamed' in col[0]:
                            new_columns.append(col[1])
                        else:
                            # Otherwise, combine them.
                            new_columns.append(f"{col[0]}_{col[1]}".strip())
                    df.columns = new_columns

                # Remove header rows that get included in the data
                if 'Rk' in df.columns:
                    df = df[df['Rk'] != 'Rk'].reset_index(drop=True)

                # Remove "Team Totals" rows before saving
                if 'Player' in df.columns:
                    df = df[~df['Player'].str.startswith('Team Totals')].reset_index(drop=True)
                
                if '+/-' in df.columns:
                    df = df.rename(columns={'+/-': 'PM'})

                # Save to file
                match = re.search(r'/(teams/\w+/\d{4})\.html', url)
                if match:
                    # Create a path like 'teams/SEA/2025_skaters.csv'
                    filename = os.path.join(output_dir, f"{match.group(1)}_{table_id}.csv")
                    os.makedirs(os.path.dirname(filename), exist_ok=True)
                else:
                    filename = os.path.join(output_dir, f"data_{table_id}.csv")
                
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    f.write(f"# Data downloaded from: {url}\n")
                    df.to_csv(f, index=False)
                print(f"✅ Successfully saved table '{table_id}' to ./{filename}")
                files_saved += 1

                if table_id == target_table_id:
                    target_df = df
        
        except Exception as e:
            print(f"⚠️ Could not parse or save table '{table_id}': {e}")
            continue
            
    return target_df, files_saved

def download_hockey_reference_tables(url, target_table_id='skaters'):
    """
    Downloads all statistical tables from a Hockey-Reference page by extracting them
    from HTML comments and saving them as individual CSV files.

    :param url: The URL of the Hockey-Reference page to scrape.
    :param target_table_id: The HTML id of the specific table to find and return.
    :return: A pandas DataFrame of the target table if found, otherwise None.
    """
    print(f"🚀 Starting download process for: {url}")
    # 1. Fetch content
    try:
        response = requests.get(url, timeout=15)
        # Raise an HTTPError for bad responses (4xx or 5xx)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching URL: {e}")
        return None

    # Use 'lxml' or 'html.parser'. 'html.parser' is generally sufficient.
    soup = BeautifulSoup(response.content, 'html.parser')
    
    output_dir = "hockey_reference_csvs"
    os.makedirs(output_dir, exist_ok=True)

    target_df, files_saved = find_and_parse_tables(soup, url, output_dir, target_table_id)

    print("-" * 50)
    if files_saved > 0:
        print(f"✨ Download complete. Found and saved {files_saved} CSV file(s) in the '{output_dir}/' directory.")
    else:
        print("No files were saved.")

    return target_df


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

update_source_data = False
team_short = "SEA"
os.makedirs(f"output/{team_short}/png", exist_ok=True)
os.makedirs(f"output/{team_short}/html", exist_ok=True)
if update_source_data:
    # --- Specify the team and season you want to download ---
    starting_season = 2022
    ending_season = 2026
    for season in range(starting_season, ending_season + 1):
        URL = f"https://www.hockey-reference.com/teams/{team_short}/{season}.html"
        print(f"Downloading data for season {season}...")
        download_hockey_reference_tables(URL, target_table_id='skaters')
        #download_hockey_reference_tables(URL, target_table_id='goalies')

# https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
pd.options.mode.chained_assignment = None
light_blue = [144,211,211]
red = [228,24,46]
red_rgb = "rgb(228,24,46)"
dark_blue = [3,22,35]

# Load citizenship data
input_fd = open("flags.csv", encoding="utf-8")
#flags = pd.read_csv(input_fd, header=0, encoding="latin1", engine="python")
flags = pd.read_csv(input_fd, header=0, encoding="utf-8-sig", engine="python")


# Load each season data for skaters
data = []
seasons = []
for f in sorted(glob.glob(f"hockey_reference_csvs/teams/{team_short}/*_player_stats.csv")):
    seasons.append(Path(f).stem.split('_')[0])
    print(f"Loading {f}...")
    data.append(pd.read_csv(f, header=0, skiprows=1, usecols=lambda x: x not in ['Rk','ATOI']))
stacked_df = pd.concat(df.assign(Season = season) for df, season in zip(data, seasons)).reset_index(drop=True)

stacked_df['Ice Time_TOI'] = stacked_df["Ice Time_TOI"].apply(convert_to_minutes)
# Adding additional stats
stacked_df["PPP"] = stacked_df["Goals_PPG"] + stacked_df["Assists_PP"]


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
        #total_row["url"] = stacked_df.loc[stacked_df.Player == p].iloc[0]["url"]
        total_row["Pos"] = stacked_df.loc[stacked_df.Player == p].iloc[0]["Pos"]
        #if total_row.loc[0, "Scoring_G"] == 0:
        #    total_row["S%"] = 0.
        #else:
        #    total_row["S%"] = total_row["Scoring_G"] / total_row["Shots_SOG"] * 100
        total_row["ATOI"] = total_row["Ice Time_TOI"] / total_row["GP"]
        #if total_row.loc[0, "Faceoffs_FOW"] == 0:
        #    total_row["FO%"] = 0.
        #else:
        #    total_row["FO%"] = total_row["Faceoffs_FOW"] / (total_row["FOW"] + total_row["FOL"]) * 100
        stacked_df = pd.concat([stacked_df, total_row], sort=True).reset_index(drop=True)

stacked_df["PlayerAndFlag"] = stacked_df["Player"] + stacked_df["Flag"]

# Load each season data for goalies
data = []
seasons = []
for f in sorted(glob.glob(f"hockey_reference_csvs/teams/{team_short}/*_goalie_stats.csv")):
    seasons.append(Path(f).stem.split('_')[0])
    print(f"Loading {f} for goalies...")
    data.append(pd.read_csv(f, header=0, skiprows=1, usecols=lambda x: x not in ['Rk','ATOI']))
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
        #total_row["url"] = stacked_dfg.loc[stacked_dfg.Player == p].iloc[0]["url"]
        if total_row.loc[0, "Goalie Stats_GA"] == 0:
            total_row["SV%"] = 100.
        else:
            total_row["SV%"] = total_row["Goalie Stats_SV"] / total_row["Goalie Stats_Shots"] * 100
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
def plotAlltimeLeaders(df, stat, statName, num, singleSeasonRecord, team, team_short, goalies=False):
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
        fig.write_image(f"output/{team_short}/png/top_goalies_leaders_{stat}_stacked.png",scale=2)
        fig.write_html(f"output/{team_short}/html/top_goalies_leaders_{stat}_stacked.html")
    else:
        fig.write_image(f"output/{team_short}/png/top_leaders_{stat}_stacked.png",scale=2)
        fig.write_html(f"output/{team_short}/html/top_leaders_{stat}_stacked.html")



team = "Seattle Kraken"
statNames = {"GP": "Games Played",
            "Scoring_G": "Goals Scored",
            "Scoring_A": "Assists",
            "Scoring_PTS": "Points Scored",
            "PIM": "Penalty Minutes",
            "Goals_EVG": "Even-Strength Goals",
            "Goals_PPG": "Powerplay Goals",
            "Goals_SHG": "Short-handed Goals",
            "Goals_GWG": "Game-Winnning Goals",
            "Assists_EV": "Even-Strength Assists",
            "Assists_PP": "Powerplay Assists",
            "PPP": "Powerplay Points",
            "Assists_SH": "Short-handed Assists",
            "Shots_SOG": "Shots On Goal",
            #"Shots_PCT": "Shot Percentage",
            "BLK": "Blocked Shots",
            "HIT": "Hits",
            "PM": "Plus/Minus",
            }
single_season_records = {}
for stat in statNames:
    single_season_records[stat] = stacked_df[stacked_df.Season != 'Total'][stat].max()
    plotAlltimeLeaders(stacked_df, stat, statNames[stat], 15, single_season_records[stat], team, team_short, seasons)

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
    plotAlltimeLeaders(stacked_dfg, stat, statName[stat], 15, single_season_records[stat], team, team_short, seasons, goalies=True)

# TODO
## Use better flags like https://github.com/hampusborgos/country-flags
## or https://github.com/google/region-flags
## Add plus/minus with a staggered stack chart
