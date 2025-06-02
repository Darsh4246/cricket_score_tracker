import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

def init_session_state():
    if 'match_started' not in st.session_state:
        st.session_state.match_started = False
        st.session_state.overs = 20
        st.session_state.team1 = "Team A"
        st.session_state.team2 = "Team B"
        st.session_state.current_batter = ""
        st.session_state.runner = ""
        st.session_state.current_bowler = ""
        st.session_state.batters = {}
        st.session_state.bowlers = {}
        st.session_state.score = 0
        st.session_state.wickets = 0
        st.session_state.balls = 0
        st.session_state.fow = []
        st.session_state.partnership = 0
        st.session_state.innings = 1
        st.session_state.extras = {'wides': 0, 'noballs': 0, 'byes': 0, 'legbyes': 0}
        st.session_state.free_hit = False
        st.session_state.last_event = None
        st.session_state.first_innings_score = 0
        st.session_state.first_innings_wickets = 0
        st.session_state.first_innings_balls = 0
        st.session_state.innings1_batters = {}
        st.session_state.innings1_bowlers = {}
        st.session_state.target = 0
        st.session_state.team_squad = []
        st.session_state.mom = ""

init_session_state()


# Initialize database
def init_db():
    conn = sqlite3.connect('cricket.db')
    c = conn.cursor()

    # Players table
    c.execute('''CREATE TABLE IF NOT EXISTS players
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  matches INTEGER DEFAULT 0,
                  runs INTEGER DEFAULT 0,
                  balls INTEGER DEFAULT 0,
                  fours INTEGER DEFAULT 0,
                  sixes INTEGER DEFAULT 0,
                  wickets INTEGER DEFAULT 0,
                  bowler_runs INTEGER DEFAULT 0,
                  bowler_balls INTEGER DEFAULT 0)''')

    # Matches table
    c.execute('''CREATE TABLE IF NOT EXISTS matches
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT DEFAULT CURRENT_DATE,
                  team1 TEXT,
                  team2 TEXT,
                  overs INTEGER,
                  innings1_score INTEGER,
                  innings1_wickets INTEGER,
                  innings1_overs REAL,
                  innings2_score INTEGER,
                  innings2_wickets INTEGER,
                  innings2_overs REAL,
                  winner TEXT,
                  mom TEXT)''')

    # Match details tables
    c.execute('''CREATE TABLE IF NOT EXISTS batting_scorecards
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  match_id INTEGER,
                  player_id INTEGER,
                  innings INTEGER,
                  runs INTEGER,
                  balls INTEGER,
                  fours INTEGER,
                  sixes INTEGER,
                  out_desc TEXT,
                  FOREIGN KEY(match_id) REFERENCES matches(id),
                  FOREIGN KEY(player_id) REFERENCES players(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS bowling_scorecards
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  match_id INTEGER,
                  player_id INTEGER,
                  innings INTEGER,
                  overs REAL,
                  maidens INTEGER,
                  runs INTEGER,
                  wickets INTEGER,
                  wides INTEGER,
                  noballs INTEGER,
                  FOREIGN KEY(match_id) REFERENCES matches(id),
                  FOREIGN KEY(player_id) REFERENCES players(id))''')

    conn.commit()
    conn.close()


# Initialize the database
init_db()


# Helper functions
def get_player_id(name):
    conn = sqlite3.connect('cricket.db')
    c = conn.cursor()
    c.execute("SELECT id FROM players WHERE name = ?", (name,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


def format_overs(balls):
    return f"{balls // 6}.{balls % 6}"


def switch_strike():
    st.session_state.current_batter, st.session_state.runner = st.session_state.runner, st.session_state.current_batter


def determine_winner():
    if st.session_state.innings == 1:
        return None
    if st.session_state.score > st.session_state.first_innings_score:
        return st.session_state.team2
    elif st.session_state.score < st.session_state.first_innings_score:
        return st.session_state.team1
    else:
        return "Match Tied"


# Initialize session state variables
def init_session_state():
    if 'match_started' not in st.session_state:
        st.session_state.match_started = False
        st.session_state.overs = 20
        st.session_state.team1 = "Team A"
        st.session_state.team2 = "Team B"
        st.session_state.current_batter = ""
        st.session_state.runner = ""
        st.session_state.current_bowler = ""
        st.session_state.batters = {}
        st.session_state.bowlers = {}
        st.session_state.score = 0
        st.session_state.wickets = 0
        st.session_state.balls = 0
        st.session_state.fow = []
        st.session_state.partnership = 0
        st.session_state.innings = 1
        st.session_state.extras = {'wides': 0, 'noballs': 0, 'byes': 0, 'legbyes': 0}
        st.session_state.free_hit = False
        st.session_state.last_event = None
        st.session_state.first_innings_score = 0
        st.session_state.first_innings_wickets = 0
        st.session_state.first_innings_balls = 0
        st.session_state.innings1_batters = {}
        st.session_state.innings1_bowlers = {}
        st.session_state.target = 0
        st.session_state.team_squad = []
        st.session_state.mom = ""


# Scoring functions
def add_runs(runs):
    if st.session_state.free_hit:
        st.info("FREE HIT!")

    # Update batter stats
    batter = st.session_state.current_batter
    st.session_state.batters[batter]['runs'] += runs
    st.session_state.batters[batter]['balls'] += 1
    if runs == 4:
        st.session_state.batters[batter]['4s'] += 1
    if runs == 6:
        st.session_state.batters[batter]['6s'] += 1

    # Update bowler stats
    bowler = st.session_state.current_bowler
    st.session_state.bowlers[bowler]['runs'] += runs
    if not st.session_state.free_hit:
        st.session_state.bowlers[bowler]['balls'] += 1

    # Update match stats
    st.session_state.score += runs
    st.session_state.partnership += runs
    if not st.session_state.free_hit:
        st.session_state.balls += 1

    # Reset free hit after a legal delivery
    if st.session_state.free_hit and not st.session_state.last_event == "noball":
        st.session_state.free_hit = False

    check_milestones()
    st.session_state.last_event = str(runs)


def add_extra(extra_type):
    if extra_type == 'wide':
        st.session_state.score += 1
        st.session_state.extras['wides'] += 1
        st.session_state.last_event = "Wide"
    elif extra_type == 'noball':
        st.session_state.score += 1
        st.session_state.extras['noballs'] += 1
        st.session_state.free_hit = True
        st.session_state.last_event = "No Ball + Free Hit"
    elif extra_type == 'byes':
        st.session_state.score += 1
        st.session_state.extras['byes'] += 1
        st.session_state.last_event = "Byes"
    elif extra_type == 'legbyes':
        st.session_state.score += 1
        st.session_state.extras['legbyes'] += 1
        st.session_state.last_event = "Leg Byes"


def add_wicket(method):
    batter = st.session_state.current_batter
    bowler = st.session_state.current_bowler

    # Update batter stats
    st.session_state.batters[batter]['out'] = method
    if method != 'run_out':
        st.session_state.bowlers[bowler]['wickets'] += 1

    # Update match stats
    st.session_state.wickets += 1
    st.session_state.fow.append({
        'score': st.session_state.score,
        'wicket': st.session_state.wickets,
        'batter': batter,
        'overs': format_overs(st.session_state.balls)
    })

    if not st.session_state.free_hit:
        st.session_state.balls += 1
        st.session_state.bowlers[bowler]['balls'] += 1

    # Reset partnership
    st.session_state.partnership = 0

    # Get new batter
    available_batters = [p for p in st.session_state.team_squad
                         if p not in st.session_state.batters or
                         'out' not in st.session_state.batters[p]]

    if available_batters and st.session_state.wickets < 10:
        st.session_state.current_batter = available_batters[0]
        st.session_state.batters[st.session_state.current_batter] = {
            'runs': 0, 'balls': 0, '4s': 0, '6s': 0
        }
    else:
        end_innings()


# Match management
def check_milestones():
    # Team milestones
    if st.session_state.score == 50:
        st.balloons()
        st.success("🏆 Team 50 up!")
    elif st.session_state.score == 100:
        st.balloons()
        st.success("🏆 Team Century!")

    # Batter milestones
    batter_runs = st.session_state.batters[st.session_state.current_batter]['runs']
    if batter_runs == 50:
        st.balloons()
        st.success(f"🎯 {st.session_state.current_batter} scores 50!")
    elif batter_runs == 100:
        st.balloons()
        st.success(f"🎯 {st.session_state.current_batter} CENTURY!")


def end_innings():
    if st.session_state.innings == 1:
        # Save first innings data
        st.session_state.first_innings_score = st.session_state.score
        st.session_state.first_innings_wickets = st.session_state.wickets
        st.session_state.first_innings_balls = st.session_state.balls
        st.session_state.innings1_batters = st.session_state.batters
        st.session_state.innings1_bowlers = st.session_state.bowlers

        st.session_state.target = st.session_state.first_innings_score + 1
        st.success(f"🏁 Innings Over! Target is {st.session_state.target}")

        if st.button("Start 2nd Innings"):
            reset_for_new_innings()
    else:
        # Match complete
        save_match_to_db()
        update_player_stats()
        st.balloons()
        st.success("🏁 Match Over!")
        show_match_summary()


def reset_for_new_innings():
    st.session_state.innings = 2
    st.session_state.score = 0
    st.session_state.wickets = 0
    st.session_state.balls = 0
    st.session_state.fow = []
    st.session_state.partnership = 0
    st.session_state.batters = {}
    st.session_state.bowlers = {}

    # Swap teams
    st.session_state.team1, st.session_state.team2 = st.session_state.team2, st.session_state.team1

    # Get new squad
    df = load_players()
    player_names = df["name"].tolist()

    # Setup new innings
    st.session_state.current_batter = st.selectbox("Striker", player_names, key="striker_select_2")
    st.session_state.runner = st.selectbox("Non-Striker",
                                           [p for p in player_names if p != st.session_state.current_batter],
                                           key="runner_select_2")
    st.session_state.current_bowler = st.selectbox("Opening Bowler",
                                                   [p for p in player_names if
                                                    p not in [st.session_state.current_batter,
                                                              st.session_state.runner]],
                                                   key="bowler_select_2")

    # Initialize batters and bowlers
    for p in [st.session_state.current_batter, st.session_state.runner]:
        st.session_state.batters[p] = {"runs": 0, "balls": 0, "4s": 0, "6s": 0}
    st.session_state.bowlers[st.session_state.current_bowler] = {"balls": 0, "runs": 0, "wickets": 0}

    st.session_state.match_started = True
    st.experimental_rerun()


# Database functions
def save_match_to_db():
    conn = sqlite3.connect('cricket.db')
    c = conn.cursor()

    # Save match header
    c.execute('''INSERT INTO matches 
                 (team1, team2, overs, innings1_score, innings1_wickets, innings1_overs,
                  innings2_score, innings2_wickets, innings2_overs, winner)
                 VALUES (?,?,?,?,?,?,?,?,?,?)''',
              (st.session_state.team1, st.session_state.team2, st.session_state.overs,
               st.session_state.first_innings_score,
               st.session_state.first_innings_wickets,
               format_overs(st.session_state.first_innings_balls),
               st.session_state.score,
               st.session_state.wickets,
               format_overs(st.session_state.balls),
               determine_winner()))

    match_id = c.lastrowid

    # Save batting scorecards
    for innings in [1, 2]:
        batters = st.session_state[f'innings{innings}_batters'] if innings == 1 else st.session_state.batters
        for player_name, stats in batters.items():
            player_id = get_player_id(player_name)
            c.execute('''INSERT INTO batting_scorecards
                         (match_id, player_id, innings, runs, balls, fours, sixes, out_desc)
                         VALUES (?,?,?,?,?,?,?,?)''',
                      (match_id, player_id, innings,
                       stats['runs'], stats['balls'],
                       stats['4s'], stats['6s'],
                       stats.get('out', 'not out')))

    # Save bowling scorecards
    for innings in [1, 2]:
        bowlers = st.session_state[f'innings{innings}_bowlers'] if innings == 1 else st.session_state.bowlers
        for player_name, stats in bowlers.items():
            player_id = get_player_id(player_name)
            c.execute('''INSERT INTO bowling_scorecards
                         (match_id, player_id, innings, overs, maidens, runs, wickets, wides, noballs)
                         VALUES (?,?,?,?,?,?,?,?,?)''',
                      (match_id, player_id, innings,
                       round(stats['balls'] / 6, 1),
                       stats.get('maidens', 0),
                       stats['runs'], stats['wickets'],
                       stats.get('wides', 0), stats.get('noballs', 0)))

    # Save Man of the Match
    if 'mom' in st.session_state:
        c.execute("UPDATE matches SET mom = ? WHERE id = ?",
                  (st.session_state.mom, match_id))

    conn.commit()
    conn.close()


def update_player_stats():
    conn = sqlite3.connect('cricket.db')
    c = conn.cursor()

    # Update all players who participated
    all_players = set()
    for innings in [1, 2]:
        batters = st.session_state[f'innings{innings}_batters'] if innings == 1 else st.session_state.batters
        bowlers = st.session_state[f'innings{innings}_bowlers'] if innings == 1 else st.session_state.bowlers
        all_players.update(batters.keys())
        all_players.update(bowlers.keys())

    for player in all_players:
        # Get stats across both innings
        batting_stats = {
            'runs': 0,
            'balls': 0,
            '4s': 0,
            '6s': 0
        }
        bowling_stats = {
            'wickets': 0,
            'runs': 0,
            'balls': 0
        }

        for innings in [1, 2]:
            batters = st.session_state[f'innings{innings}_batters'] if innings == 1 else st.session_state.batters
            bowlers = st.session_state[f'innings{innings}_bowlers'] if innings == 1 else st.session_state.bowlers

            if player in batters:
                batting_stats['runs'] += batters[player].get('runs', 0)
                batting_stats['balls'] += batters[player].get('balls', 0)
                batting_stats['4s'] += batters[player].get('4s', 0)
                batting_stats['6s'] += batters[player].get('6s', 0)

            if player in bowlers:
                bowling_stats['wickets'] += bowlers[player].get('wickets', 0)
                bowling_stats['runs'] += bowlers[player].get('runs', 0)
                bowling_stats['balls'] += bowlers[player].get('balls', 0)

        # Update database
        c.execute('''UPDATE players SET
                     matches = matches + 1,
                     runs = runs + ?,
                     balls = balls + ?,
                     fours = fours + ?,
                     sixes = sixes + ?,
                     wickets = wickets + ?,
                     bowler_runs = bowler_runs + ?,
                     bowler_balls = bowler_balls + ?
                     WHERE name = ?''',
                  (batting_stats['runs'],
                   batting_stats['balls'],
                   batting_stats['4s'],
                   batting_stats['6s'],
                   bowling_stats['wickets'],
                   bowling_stats['runs'],
                   bowling_stats['balls'],
                   player))

    conn.commit()
    conn.close()


# UI Components
def scoring_controls():
    st.subheader("🏏 Scoring Controls")

    # Mobile-friendly CSS
    st.markdown("""
    <style>
        .stButton>button {
            min-height: 3em;
            min-width: 5em;
            font-size: 1.2em;
            margin: 0.2em;
        }
        @media (max-width: 600px) {
            .stButton>button {
                min-height: 2.5em;
                min-width: 4em;
                font-size: 1em;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    cols = st.columns(4)

    with cols[0]:
        st.markdown("**Runs**")
        if st.button("1"): add_runs(1)
        if st.button("2"): add_runs(2)
        if st.button("3"): add_runs(3)
        if st.button("4"): add_runs(4)
        if st.button("6"): add_runs(6)

    with cols[1]:
        st.markdown("**Extras**")
        if st.button("Wide"): add_extra('wide')
        if st.button("No Ball"): add_extra('noball')
        if st.button("Byes"): add_extra('byes')
        if st.button("Leg Byes"): add_extra('legbyes')

    with cols[2]:
        st.markdown("**Wickets**")
        if st.button("Bowled"): add_wicket('bowled')
        if st.button("Caught"): add_wicket('caught')
        if st.button("LBW"): add_wicket('lbw')
        if st.button("Run Out"): add_wicket('run_out')

    with cols[3]:
        st.markdown("**Match**")
        if st.button("Switch Strike"): switch_strike()
        if st.button("New Bowler"): change_bowler_ui()
        if st.button("End Innings"): end_innings()


def change_bowler_ui():
    df = load_players()
    player_names = df["name"].tolist()
    available_bowlers = [p for p in player_names
                         if p not in [st.session_state.current_batter, st.session_state.runner]]

    new_bowler = st.selectbox("Select new bowler", available_bowlers)
    if st.button("Confirm Bowler Change"):
        st.session_state.current_bowler = new_bowler
        if new_bowler not in st.session_state.bowlers:
            st.session_state.bowlers[new_bowler] = {"balls": 0, "runs": 0, "wickets": 0}
        st.experimental_rerun()


def show_match_summary():
    st.subheader("📊 Match Summary")

    # Result
    winner = determine_winner()
    if winner == "Match Tied":
        st.success("**Result**: Match Tied")
    else:
        margin = abs(st.session_state.first_innings_score - st.session_state.score)
        st.success(f"**Result**: {winner} won by {margin} runs")

    # Scorecards
    show_detailed_scorecard()

    # Man of the Match selection
    players = list(st.session_state.innings1_batters.keys()) + list(st.session_state.innings1_bowlers.keys())
    players += list(st.session_state.batters.keys()) + list(st.session_state.bowlers.keys())

    st.session_state.mom = st.selectbox("Man of the Match", sorted(set(players)))
    if st.button("Save Match Data"):
        save_match_to_db()  # Save MOM
        st.session_state.match_started = False
        st.experimental_rerun()


def show_detailed_scorecard():
    st.subheader("📝 Detailed Scorecard")

    tab1, tab2 = st.tabs(["1st Innings", "2nd Innings"])

    with tab1:
        show_innings_scorecard(1)
    with tab2:
        show_innings_scorecard(2)


def show_innings_scorecard(innings):
    if innings == 1 or (innings == 2 and st.session_state.innings == 2):
        batters = st.session_state.innings1_batters if innings == 1 else st.session_state.batters
        bowlers = st.session_state.innings1_bowlers if innings == 1 else st.session_state.bowlers

        st.write(f"### {'Team 1' if innings == 1 else 'Team 2'} Batting")
        batting_data = []
        for player, stats in batters.items():
            batting_data.append({
                "Batter": player,
                "Runs": stats['runs'],
                "Balls": stats['balls'],
                "4s": stats['4s'],
                "6s": stats['6s'],
                "SR": round(stats['runs'] / stats['balls'] * 100, 2) if stats['balls'] > 0 else 0,
                "Out": stats.get('out', 'not out')
            })
        st.dataframe(pd.DataFrame(batting_data))

        st.write(f"### {'Team 2' if innings == 1 else 'Team 1'} Bowling")
        bowling_data = []
        for player, stats in bowlers.items():
            bowling_data.append({
                "Bowler": player,
                "Overs": round(stats['balls'] / 6, 1),
                "Maidens": stats.get('maidens', 0),
                "Runs": stats['runs'],
                "Wickets": stats['wickets'],
                "Economy": round(stats['runs'] / (stats['balls'] / 6), 2) if stats['balls'] > 0 else 0,
                "Extras": stats.get('wides', 0) + stats.get('noballs', 0)
            })
        st.dataframe(pd.DataFrame(bowling_data))

        total = st.session_state.first_innings_score if innings == 1 else st.session_state.score
        wickets = st.session_state.first_innings_wickets if innings == 1 else st.session_state.wickets
        balls = st.session_state.first_innings_balls if innings == 1 else st.session_state.balls

        st.write(f"**Total**: {total}/{wickets} in {format_overs(balls)} overs")

        # Fall of wickets
        if innings == 1 or (innings == 2 and st.session_state.innings == 2):
            fow = st.session_state.fow
            if fow:
                st.write("**Fall of Wickets**:")
                for w in fow:
                    st.write(f"{w['wicket']}-{w['score']} ({w['batter']}, {w['overs']})")


# Player management
def load_players():
    conn = sqlite3.connect('cricket.db')
    df = pd.read_sql("SELECT * FROM players", conn)
    conn.close()
    return df


def player_profile():
    st.title("📋 Player Profile Creation")

    name = st.text_input("Enter player name:")
    if st.button("Add Player"):
        conn = sqlite3.connect('cricket.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO players (name) VALUES (?)", (name,))
            conn.commit()
            st.success("Player added successfully!")
        except sqlite3.IntegrityError:
            st.warning("Player already exists!")
        finally:
            conn.close()


def player_stats():
    st.title("📊 Player Statistics")
    df = load_players()

    selected_player = st.selectbox("Select player:", sorted(df["name"].values))
    if selected_player:
        player = df[df["name"] == selected_player].iloc[0]

        # Basic stats
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Matches", int(player.matches))
            st.metric("Runs", int(player.runs))
            if player.balls > 0:
                st.metric("Batting Average", round(player.runs / player.matches, 2))
                st.metric("Strike Rate", round(player.runs / player.balls * 100, 2))

        with col2:
            st.metric("Wickets", int(player.wickets))
            if player.bowler_balls > 0:
                st.metric("Bowling Average",
                          round(player.bowler_runs / player.wickets, 2) if player.wickets > 0 else "-")
                st.metric("Economy Rate", round(player.bowler_runs / (player.bowler_balls / 6), 2))

        # Charts
        st.subheader("Batting Performance")
        fig, ax = plt.subplots()
        stats = ['Runs', 'Fours', 'Sixes']
        values = [int(player.runs), int(player.fours), int(player.sixes)]
        ax.bar(stats, values)
        ax.set_title('Batting Stats')
        ax.set_ylabel('Count')
        st.pyplot(fig)
        plt.close(fig)

        st.subheader("Bowling Performance")
        fig, ax = plt.subplots()
        stats = ['Wickets', 'Runs Conceded']
        values = [int(player.wickets), int(player.bowler_runs)]
        ax.bar(stats, values)
        ax.set_title('Bowling Stats')
        ax.set_ylabel('Count')
        st.pyplot(fig)
        plt.close(fig)


# Match setup
def match_setup():
    st.title("🏏 Match Setup")

    st.session_state.overs = st.number_input("Number of overs", min_value=1, max_value=50, value=20)

    df = load_players()
    player_names = df["name"].tolist()

    st.session_state.team1 = st.text_input("Team 1 Name", "Team A")
    st.session_state.team2 = st.text_input("Team 2 Name", "Team B")

    st.subheader("Select Opening Players")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.session_state.current_batter = st.selectbox("Striker", sorted(player_names), key="striker_select")
    with col2:
        st.session_state.runner = st.selectbox("Non-Striker",
                                               [p for p in sorted(player_names) if p != st.session_state.current_batter],
                                               key="runner_select")
    with col3:
        st.session_state.current_bowler = st.selectbox("Opening Bowler",
                                                       [p for p in sorted(player_names) if
                                                        p not in [st.session_state.current_batter,
                                                                  st.session_state.runner]],
                                                       key="bowler_select")

    if st.button("Start Match"):
        st.session_state.match_started = True
        st.session_state.team_squad = player_names

        # Initialize batters and bowlers
        for p in [st.session_state.current_batter, st.session_state.runner]:
            st.session_state.batters[p] = {"runs": 0, "balls": 0, "4s": 0, "6s": 0}
        st.session_state.bowlers[st.session_state.current_bowler] = {"balls": 0, "runs": 0, "wickets": 0}

        # Initialize match stats
        st.session_state.score = 0
        st.session_state.wickets = 0
        st.session_state.balls = 0
        st.session_state.fow = []
        st.session_state.partnership = 0
        st.session_state.innings = 1
        st.session_state.extras = {'wides': 0, 'noballs': 0, 'byes': 0, 'legbyes': 0}
        st.session_state.free_hit = False
        st.session_state.last_event = None

        st.success("Match Started!")
        st.experimental_rerun()


# Main app
def main():
    # Mobile optimization
    st.set_page_config(layout="wide")

    # Initialize session state
    init_session_state()

    # Navigation
    pages = {
        "Match Setup": "setup",
        "Live Scoring": "scoring",
        "Player Profile": "profile",
        "Player Stats": "stats"
    }

    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Go to", list(pages.keys()))

    # Page routing
    if pages[selection] == "setup":
        match_setup()
    elif pages[selection] == "scoring" and st.session_state.match_started:
        show_scoring()
    elif pages[selection] == "profile":
        player_profile()
    elif pages[selection] == "stats":
        player_stats()
    else:
        st.warning("Please start a match first")


def show_scoring():
    st.title("🏏 Live Scoring")

    # Match info header
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader(f"{st.session_state.team1 if st.session_state.innings == 1 else st.session_state.team2} Batting")
    with col2:
        target_text = f"Target: {st.session_state.target}" if st.session_state.innings == 2 else "1st Innings"
        st.subheader(target_text)
    with col3:
        st.subheader(f"Overs: {format_overs(st.session_state.balls)}/{st.session_state.overs}")

    # Score display
    st.metric("Score",
              f"{st.session_state.score}/{st.session_state.wickets}",
              f"RR: {round(st.session_state.score / (st.session_state.balls / 6), 2) if st.session_state.balls > 0 else 0}")

    # Current players
    col1, col2 = st.columns(2)
    with col1:
        batter_stats = st.session_state.batters[st.session_state.current_batter]
        st.metric("Striker",
                  f"{st.session_state.current_batter} {batter_stats['runs']}({batter_stats['balls']})",
                  f"SR: {round(batter_stats['runs'] / batter_stats['balls'] * 100, 2) if batter_stats['balls'] > 0 else 0}")
    with col2:
        runner_stats = st.session_state.batters[st.session_state.runner]
        st.metric("Non-Striker",
                  f"{st.session_state.runner} {runner_stats['runs']}({runner_stats['balls']})",
                  f"SR: {round(runner_stats['runs'] / runner_stats['balls'] * 100, 2) if runner_stats['balls'] > 0 else 0}")

    # Bowler info
    bowler_stats = st.session_state.bowlers[st.session_state.current_bowler]
    st.metric("Bowler",
              f"{st.session_state.current_bowler} {bowler_stats['wickets']}/{bowler_stats['runs']}",
              f"ER: {round(bowler_stats['runs'] / (bowler_stats['balls'] / 6), 2) if bowler_stats['balls'] > 0 else 0}")

    # Partnership
    st.write(f"Partnership: {st.session_state.partnership} runs")

    # Last event
    if st.session_state.last_event:
        st.info(f"Last event: {st.session_state.last_event}")

    # Scoring controls
    scoring_controls()

    # Over progression
    st.write("Current over:")
    cols = st.columns(6)
    for i in range(6):
        with cols[i]:
            if i < (st.session_state.balls % 6):
                event = "•"  # Replace with actual ball events if tracking
                st.markdown(f"<div style='text-align: center; font-size: 1.5em;'>{event}</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    init_session_state()
    main()
