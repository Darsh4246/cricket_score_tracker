import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import time as t
import os
import shutil
from datetime import datetime
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Helper functions
def get_player_id(name):
    response = supabase.table("players").select("id").eq("name", name).execute()
    if response.data:
        return response.data[0]["id"]
    return None



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

def check_match_completion():
    # Get current team's player count
    current_team_size = st.session_state.team1_size if st.session_state.innings == 1 else st.session_state.team2_size
    
    # Check if innings is complete (all overs bowled or all out)
    innings_complete = (
        (st.session_state.balls >= st.session_state.overs * 6) or 
        (st.session_state.wickets >= current_team_size)  # All players except last one are out
    )
    
    # For 2nd innings, also check if target is reached
    if st.session_state.innings == 2:
        target_reached = st.session_state.score >= st.session_state.target
        if target_reached or innings_complete:
            end_innings()
            st.rerun()  # Force immediate UI update
    elif innings_complete:
        end_innings()
        st.rerun()  # Force immediate UI update

def determine_winner():
    if st.session_state.innings == 1:
        return None
    
    team1_score = st.session_state.first_innings_score
    team2_score = st.session_state.score
    team1_wickets = st.session_state.first_innings_wickets
    team2_wickets = st.session_state.wickets
    
    # Team 1 wins if team2 scored less runs
    if team2_score < team1_score:
        return st.session_state.team1
    # Team 2 wins if they scored more runs
    elif team2_score > team1_score:
        return st.session_state.team2
    # If scores are equal
    else:
        # Team with more wickets wins
        if team1_wickets > team2_wickets:
            return st.session_state.team1
        elif team2_wickets > team1_wickets:
            return st.session_state.team2
        else:
            return "Match Tied"

def show_match_summary():
    st.subheader("📊 Match Summary")
    winner = determine_winner()
    
    if winner == "Match Tied":
        st.success("**Result**: Match Tied")
    else:
        if winner == st.session_state.team1:
            margin = st.session_state.first_innings_score - st.session_state.score
            wickets_left = st.session_state.team1_size - 1 - st.session_state.first_innings_wickets
            st.success(f"**Result**: {winner} won by {wickets_left} wickets and {margin} runs")
        else:
            margin = st.session_state.score - st.session_state.first_innings_score
            wickets_left = st.session_state.team2_size - 1 - st.session_state.wickets
            st.success(f"**Result**: {winner} won by {margin} runs (with {wickets_left} wickets remaining)")
    
    # Show detailed scorecards
    show_detailed_scorecard()
    
    # Man of the Match selection
    players = list(st.session_state.innings1_batters.keys()) + list(st.session_state.innings1_bowlers.keys())
    players += list(st.session_state.batters.keys()) + list(st.session_state.bowlers.keys())
    
    st.session_state.mom = st.selectbox("Man of the Match", sorted(set(players)))
    if st.button("Save Match Data"):
        save_match_to_db()  # Save MOM
        st.session_state.match_started = False
        
# Initialize session state variables
def init_session_state():
    if 'match_started' not in st.session_state:
        st.session_state.match_started = False
        st.session_state.match_active = False
        st.session_state.overs = 20
        st.session_state.team1 = "Team A"
        st.session_state.team2 = "Team B"
        st.session_state.team1_players = []
        st.session_state.team2_players = []
        st.session_state.current_batter = ""
        st.session_state.runner = ""
        st.session_state.current_bowler = ""
        st.session_state.batters = {}
        st.session_state.bowlers = {}
        st.session_state.score = 0
        st.session_state.wickets = 0
        st.session_state.balls = 0
        st.session_state.current_over = []
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
        st.session_state.show_new_batter_modal = False
        st.session_state.show_new_bowler_modal = False
        st.session_state.team1_size = 0
        st.session_state.team2_size = 0
        st.session_state.current_partners = []


# Scoring functions
def add_runs(runs):
    st.toast(f"add_runs({runs}) called")
    if st.session_state.free_hit and runs != 0:
        st.info("FREE HIT!")

    batter = st.session_state.current_batter
    bowler = st.session_state.current_bowler

    # Update batter stats
    st.session_state.batters[batter]['runs'] += runs
    if runs == 0:
        st.session_state.batters[batter]['dots'] = st.session_state.batters[batter].get('dots', 0) + 1
    if runs == 4:
        st.session_state.batters[batter]['4s'] += 1
    if runs == 6:
        st.session_state.batters[batter]['6s'] += 1

    # Update bowler stats
    st.session_state.bowlers[bowler]['runs'] += runs

    # Count balls only on legal deliveries
    if not st.session_state.free_hit:
        st.session_state.batters[batter]['balls'] += 1
        st.session_state.bowlers[bowler]['balls'] += 1  # Fixed typo
        st.session_state.balls += 1
        st.session_state.current_over.append(str(runs))

    # Update match stats
    st.session_state.score += runs
    st.session_state.partnership += runs

    # Reset free hit after a legal delivery
    if st.session_state.free_hit and not st.session_state.last_event == "noball":
        st.session_state.free_hit = False

    check_milestones()
    st.session_state.last_event = "Dot Ball" if runs == 0 else str(runs)

    # Check if over is completed
    if st.session_state.balls % 6 == 0 and st.session_state.balls > 0:
        st.session_state.show_new_bowler_modal = True
        st.session_state.current_over = []

    check_match_completion()
    st.rerun()

def add_extra(extra_type):
    if extra_type == 'wide':
        st.session_state.score += 1
        st.session_state.extras['wides'] += 1
        st.session_state.bowlers[st.session_state.current_bowler]['wides'] = st.session_state.bowlers[st.session_state.current_bowler].get('wides', 0) + 1
        st.session_state.last_event = "Wide"
    elif extra_type == 'noball':
        st.session_state.score += 1
        st.session_state.extras['noballs'] += 1
        st.session_state.bowlers[st.session_state.current_bowler]['noballs'] = st.session_state.bowlers[st.session_state.current_bowler].get('noballs', 0) + 1
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
    check_match_completion() 
    st.rerun()

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

    # Show new batter modal
    st.session_state.show_new_batter_modal = True
    check_match_completion()
    st.rerun()

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

        # Reset for second innings
        reset_for_new_innings()
    else:
        # Match complete
        save_match_to_db()
        update_player_stats()
        st.balloons()
        st.success("🏁 Match Over!")
        show_match_summary()
        st.session_state.match_active = False

def reset_for_new_innings():
    st.session_state.innings = 2
    st.session_state.score = 0
    st.session_state.wickets = 0
    st.session_state.balls = 0
    st.session_state.fow = []
    st.session_state.partnership = 0
    st.session_state.batters = {}
    st.session_state.bowlers = {}
    st.session_state.extras = {'wides': 0, 'noballs': 0, 'byes': 0, 'legbyes': 0}
    st.session_state.free_hit = False
    st.session_state.last_event = None

    # Swap teams
    st.session_state.team1, st.session_state.team2 = st.session_state.team2, st.session_state.team1
    st.session_state.team1_players, st.session_state.team2_players = st.session_state.team2_players, st.session_state.team1_players

    # Setup new innings
    st.session_state.current_batter = st.session_state.team1_players[0]
    st.session_state.runner = st.session_state.team1_players[1]
    st.session_state.current_bowler = st.session_state.team2_players[0]

    # Initialize batters and bowlers
    for p in [st.session_state.current_batter, st.session_state.runner]:
        st.session_state.batters[p] = {"runs": 0, "balls": 0, "4s": 0, "6s": 0}
    st.session_state.bowlers[st.session_state.current_bowler] = {"balls": 0, "runs": 0, "wickets": 0, "wides": 0, "noballs": 0}

    st.session_state.match_started = True
    st.rerun()

# Database functions
def save_match_to_db():
    match = {
        "team1": st.session_state.team1,
        "team2": st.session_state.team2,
        "overs": st.session_state.overs,
        "innings1_score": st.session_state.first_innings_score,
        "innings1_wickets": st.session_state.first_innings_wickets,
        "innings1_overs": format_overs(st.session_state.first_innings_balls),
        "innings2_score": st.session_state.score,
        "innings2_wickets": st.session_state.wickets,
        "innings2_overs": format_overs(st.session_state.balls),
        "winner": determine_winner(),
        "mom": st.session_state.mom
    }
    response = supabase.table("matches").insert(match).execute()
    match_id = response.data[0]["id"]

    # Batting
    for innings in [1, 2]:
        batters = st.session_state[f"innings{innings}_batters"] if innings == 1 else st.session_state.batters
        for name, stats in batters.items():
            player_id = get_player_id(name)
            supabase.table("batting_scorecards").insert({
                "match_id": match_id,
                "player_id": player_id,
                "innings": innings,
                "runs": stats["runs"],
                "balls": stats["balls"],
                "fours": stats["4s"],
                "sixes": stats["6s"],
                "out_desc": stats.get("out", "not out")
            }).execute()

    # Bowling
    for innings in [1, 2]:
        bowlers = st.session_state[f"innings{innings}_bowlers"] if innings == 1 else st.session_state.bowlers
        for name, stats in bowlers.items():
            player_id = get_player_id(name)
            supabase.table("bowling_scorecards").insert({
                "match_id": match_id,
                "player_id": player_id,
                "innings": innings,
                "overs": round(stats["balls"] / 6, 1),
                "maidens": stats.get("maidens", 0),
                "runs": stats["runs"],
                "wickets": stats["wickets"],
                "wides": stats.get("wides", 0),
                "noballs": stats.get("noballs", 0)
            }).execute()


def update_player_stats():
    all_players = set()
    for innings in [1, 2]:
        batters = st.session_state[f"innings{innings}_batters"] if innings == 1 else st.session_state.batters
        bowlers = st.session_state[f"innings{innings}_bowlers"] if innings == 1 else st.session_state.bowlers
        all_players.update(batters.keys())
        all_players.update(bowlers.keys())

    for name in all_players:
        batting = {"runs": 0, "balls": 0, "4s": 0, "6s": 0, "dots": 0}
        bowling = {"wickets": 0, "runs": 0, "balls": 0, "wides": 0, "noballs": 0}
        for innings in [1, 2]:
            batters = st.session_state[f"innings{innings}_batters"] if innings == 1 else st.session_state.batters
            bowlers = st.session_state[f"innings{innings}_bowlers"] if innings == 1 else st.session_state.bowlers
            if name in batters:
                b = batters[name]
                batting["runs"] += b["runs"]
                batting["balls"] += b["balls"]
                batting["4s"] += b["4s"]
                batting["6s"] += b["6s"]
                batting["dots"] += b.get("dots", 0)
            if name in bowlers:
                bl = bowlers[name]
                bowling["wickets"] += bl["wickets"]
                bowling["runs"] += bl["runs"]
                bowling["balls"] += bl["balls"]
                bowling["wides"] += bl.get("wides", 0)
                bowling["noballs"] += bl.get("noballs", 0)

        supabase.table("players").update({
            "matches": supabase.table("players").select("matches").eq("name", name).execute().data[0]["matches"] + 1,
            "runs": batting["runs"],
            "balls": batting["balls"],
            "dots": batting["dots"],
            "fours": batting["4s"],
            "sixes": batting["6s"],
            "wickets": bowling["wickets"],
            "bowler_runs": bowling["runs"],
            "bowler_balls": bowling["balls"]
        }).eq("name", name).execute()

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
        row1 = st.columns(2)
        with row1[0]:
            if st.button("0 (Dot)"): add_runs(0)
            if st.button("1"): add_runs(1)
        with row1[1]:
            if st.button("2"): add_runs(2)
            if st.button("3"): add_runs(3)
        row2 = st.columns(2)
        with row2[0]:
            if st.button("4"): add_runs(4)
        with row2[1]:
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
        if st.button("New Bowler"): 
            st.session_state.show_new_bowler_modal = True
        if st.button("End Innings"): end_innings()
        if st.button("Cancel Match", type="secondary"): 
            st.session_state.match_started = False
            st.session_state.match_active = False

def show_new_batter_modal():
    if st.session_state.show_new_batter_modal:
        with st.container():
            st.write("### Select New Batter")
            
            # Get available players from the CURRENT batting team
            current_batting_team = st.session_state.team1_players if st.session_state.innings == 1 else st.session_state.team2_players
            
            available_players = [p for p in current_batting_team
                             if p not in st.session_state.batters or 'out' not in st.session_state.batters[p]]
            
            max_wickets = len(current_batting_team) - 1  # Team size - 1
            
            if available_players and st.session_state.wickets < max_wickets:
                new_batter = st.selectbox("New Batter", available_players)

                if st.button("Confirm"):
                    st.session_state.current_batter = new_batter
                    st.session_state.batters[new_batter] = {'runs': 0, 'balls': 0, '4s': 0, '6s': 0}
                    st.session_state.current_partners = [st.session_state.current_batter, st.session_state.runner]
                    st.session_state.partnership = 0
                    st.session_state.show_new_batter_modal = False
                    st.rerun()
            else:
                end_innings()

def show_new_bowler_modal():
    if st.session_state.show_new_bowler_modal:
        with st.container():
            st.write("### Select New Bowler")

            # Get available players from the **current bowling team**
            if st.session_state.innings == 1:
                bowling_team = st.session_state.team2_players
            else:
                bowling_team = st.session_state.team2_players  # <- STILL team2, because of team swap earlier

            available_players = [p for p in bowling_team
                                 if p not in [st.session_state.current_batter, st.session_state.runner]]

            if available_players:
                new_bowler = st.selectbox("New Bowler", available_players)

                if st.button("Confirm"):
                    st.session_state.current_bowler = new_bowler
                    if new_bowler not in st.session_state.bowlers:
                        st.session_state.bowlers[new_bowler] = {
                            "balls": 0, "runs": 0, "wickets": 0, "wides": 0, "noballs": 0
                        }
                    st.session_state.show_new_bowler_modal = False
                    st.rerun()

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
        st.rerun()

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
    response = supabase.table("players").select("*").execute()
    return pd.DataFrame(response.data)

def player_profile():
    st.title("📋 Player Profile Creation")
    name = st.text_input("Enter player name:")
    if st.button("Add Player"):
        try:
            supabase.table("players").insert({"name": name}).execute()
            st.success("Player added successfully!")
        except Exception:
            st.warning("Player already exists or error occurred!")


def player_stats():
    st.title("📊 Player Statistics")
    df = load_players()

    if df.empty:
        st.warning("No players found. Please add players first.")
        return

    selected_player = st.selectbox("Select player:", sorted(df["name"].values))
    if selected_player:
        player = df[df["name"] == selected_player].iloc[0]

        # Basic stats
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Matches", int(player.matches))
            st.metric("Runs", int(player.runs))
            st.metric("Dot Balls", int(player.dots))
            if player.balls > 0:
                st.metric("Batting Average", round(player.runs / player.matches, 2) if player.matches > 0 else 0)
                st.metric("Strike Rate", round(player.runs / player.balls * 100, 2))
            else:
                st.metric("Batting Average", "-")
                st.metric("Strike Rate", "-")

        with col2:
            st.metric("Wickets", int(player.wickets))
            if player.bowler_balls > 0:
                st.metric("Bowling Average",
                          round(player.bowler_runs / player.wickets, 2) if player.wickets > 0 else "-")
                st.metric("Economy Rate", round(player.bowler_runs / (player.bowler_balls / 6), 2))
            else:
                st.metric("Bowling Average", "-")
                st.metric("Economy Rate", "-")

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
    if df.empty:
        st.warning("No players found. Please add players first.")
        return

    player_names = df["name"].tolist()

    st.session_state.team1 = st.text_input("Team 1 Name", "Team A")
    st.session_state.team2 = st.text_input("Team 2 Name", "Team B")

    st.subheader("Select Team Squads")
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.team1_players = st.multiselect(f"Select {st.session_state.team1} squad", 
                                                      sorted(player_names),
                                                      key="team1_select")
    
    with col2:
        st.session_state.team2_players = st.multiselect(f"Select {st.session_state.team2} squad", 
                                                      sorted(player_names),
                                                      key="team2_select")

    if len(st.session_state.team1_players) < 2 or len(st.session_state.team2_players) < 2:
        st.warning("Each team must have at least 2 players")
        return

    st.subheader("Select Opening Players")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.session_state.current_batter = st.selectbox("Striker", 
                                                     st.session_state.team1_players,
                                                     key="striker_select")
    with col2:
        st.session_state.runner = st.selectbox("Non-Striker",
                                             [p for p in st.session_state.team1_players 
                                              if p != st.session_state.current_batter],
                                             key="runner_select")
    with col3:
        st.session_state.current_bowler = st.selectbox("Opening Bowler",
                                                     st.session_state.team2_players,
                                                     key="bowler_select")

    if st.button("Start Match"):
        st.session_state.match_started = True
        st.session_state.match_active = True
        st.session_state.team_squad = st.session_state.team1_players + st.session_state.team2_players
        st.session_state.team1_size = len(st.session_state.team1_players)
        st.session_state.team2_size = len(st.session_state.team2_players)

        # Initialize batters and bowlers
        for p in [st.session_state.current_batter, st.session_state.runner]:
            st.session_state.batters[p] = {"runs": 0, "balls": 0, "4s": 0, "6s": 0}
        st.session_state.bowlers[st.session_state.current_bowler] = {"balls": 0, "runs": 0, "wickets": 0, "wides": 0, "noballs": 0}

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
        st.rerun()


# Main app
def main():
    st.set_page_config(layout="wide")
    init_session_state()

    pages = {
        "Match Setup": "setup",
        "Live Scoring": "scoring",
        "Player Profile": "profile",
        "Player Stats": "stats"
    }

    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Go to", list(pages.keys()))

    if pages[selection] == "setup":
        match_setup()

    elif pages[selection] == "scoring":
        if st.session_state.match_started:
            show_scoring()
        else:
            st.warning("\u26a0\ufe0f Please start the match first from ‘Match Setup’.")

    elif pages[selection] == "profile":
        player_profile()

    elif pages[selection] == "stats":
        player_stats()

    else:
        st.warning("Unknown page selected. Please check the navigation options.")

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

    # Over progression
    st.write("Current over:")
    cols = st.columns(6)
    for i in range(6):
        with cols[i]:
            if i < (st.session_state.balls % 6):
                event = "•"  # Replace with actual ball events if tracking
                st.markdown(f"<div style='text-align: center; font-size: 1.5em;'>{event}</div>", unsafe_allow_html=True)

    # Scoring controls
    scoring_controls()
    
    # Show modals if needed
    show_new_batter_modal()
    show_new_bowler_modal()


if __name__ == "__main__":
    main()
