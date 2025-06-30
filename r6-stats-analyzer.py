import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
import subprocess
import json
from typing import Dict, Any, List
import datetime

class R6StatsAnalyzer:
    def __init__(self, match_data: Dict[str, Any]):
        """
        Initialize the analyzer with match data
        
        :param match_data: JSON data containing match information
        """
        self.match_data = match_data
        self.rounds = match_data.get('rounds', [])
        self.overall_stats = match_data.get('stats', [])
        
    def calculate_kpr(self) -> Dict[str, float]:
        """Calculate Kills per Round for each player"""
        result = {}
        for stat in self.overall_stats:
            if 'username' in stat and 'kills' in stat and 'rounds' in stat and stat['rounds'] > 0:
                result[stat['username']] = stat['kills'] / stat['rounds']
            else:
                result[stat.get('username', 'Unknown')] = 0.0
        return result

    def calculate_multikills(self) -> Dict[str, int]:
        """Calculate number of multikills for each player"""
        multikills = {stat.get('username', 'Unknown'): 0 for stat in self.overall_stats}
        
        for round_data in self.rounds:
            kills_by_player = {}
            for kill in round_data.get('matchFeedback', []) or []:
                if isinstance(kill, dict) and kill.get('type', {}).get('name') == 'Kill':
                    username = kill.get('username', 'Unknown')
                    kills_by_player[username] = kills_by_player.get(username, 0) + 1
            
            for username, kill_count in kills_by_player.items():
                if kill_count > 1:
                    multikills[username] = multikills.get(username, 0) + 1
        
        return multikills

    def calculate_clutches(self) -> Dict[str, int]:
        """
        Calculate 1vX clutch rounds for each player
        
        A clutch is defined as a situation where a player is the last alive on their team
        and successfully wins the round against multiple opponents.
        """
        clutches = {stat.get('username', 'Unknown'): 0 for stat in self.overall_stats}
        
        for round_data in self.rounds:
            match_feedback = round_data.get('matchFeedback', []) or []
            teams = round_data.get('teams', []) or []
            
            if len(teams) < 2:
                continue
                
            # Track players on each team
            team_players = {}
            for player in round_data.get('players', []) or []:
                if not isinstance(player, dict) or 'teamIndex' not in player or 'username' not in player:
                    continue
                    
                team_id = player.get('teamIndex')
                if team_id not in team_players:
                    team_players[team_id] = []
                team_players[team_id].append(player.get('username'))
            
            # Track which team won this round
            winning_team = None
            for event in match_feedback:
                if isinstance(event, dict) and event.get('type', {}).get('name') == 'RoundEnd':
                    winning_team = event.get('winner')
                    break
            
            if winning_team is None:
                continue  # Can't determine winning team
                
            # Initialize alive players for each team
            alive_players = {}
            for team_id, players in team_players.items():
                alive_players[team_id] = set(players)
            
            # Find which team_id corresponds to the winning team name
            winning_team_id = None
            for team_id, team_obj in enumerate(teams):
                if isinstance(team_obj, dict) and team_obj.get('name') == winning_team:
                    winning_team_id = team_id
                    break
            
            if winning_team_id is None:
                continue  # Can't determine winning team ID
            
            # Process kills chronologically to track who's alive
            clutch_candidate = None
            enemy_count_at_clutch_start = 0
            clutch_started = False
            
            for event in match_feedback:
                if not isinstance(event, dict):
                    continue
                    
                event_type = event.get('type', {}).get('name')
                
                if event_type in ('Kill', 'TeamKill'):
                    # Update alive players based on who died
                    target = event.get('target')
                    if not target:
                        continue
                        
                    # Find which team the target was on
                    target_team = None
                    for team_id, players in team_players.items():
                        if target in players:
                            target_team = team_id
                            break
                    
                    if target_team is not None:
                        # Remove player from alive players
                        if target in alive_players.get(target_team, set()):
                            alive_players[target_team].remove(target)
                        
                        # Check if this creates a clutch situation
                        if target_team == winning_team_id and len(alive_players[winning_team_id]) == 1 and not clutch_started:
                            clutch_candidate = next(iter(alive_players[winning_team_id]))
                            # Count alive enemies at clutch start
                            enemy_count_at_clutch_start = sum(len(alive_players[t]) for t in alive_players if t != winning_team_id)
                            
                            # Only consider it a potential clutch if there are multiple enemies
                            if enemy_count_at_clutch_start >= 2:
                                clutch_started = True
            
            # If clutch situation was identified and the winning team had a single player at the end
            if clutch_started and clutch_candidate and len(alive_players[winning_team_id]) == 1:
                # Find how many kills the clutch candidate got after clutch situation started
                kills_after_clutch = 0
                clutch_event_index = 0
                
                # Find index where clutch started
                for i, event in enumerate(match_feedback):
                    if isinstance(event, dict) and event.get('type', {}).get('name') in ('Kill', 'TeamKill'):
                        target = event.get('target')
                        for team_id, players in team_players.items():
                            if target in players and team_id == winning_team_id:
                                alive_count = sum(1 for p in players if p not in [e.get('target') for e in match_feedback[:i+1] 
                                                 if isinstance(e, dict) and e.get('type', {}).get('name') in ('Kill', 'TeamKill')])
                                if alive_count == 1:
                                    clutch_event_index = i
                                    break
                
                # Count the clutch player's kills after clutch start
                for event in match_feedback[clutch_event_index+1:]:
                    if isinstance(event, dict) and event.get('type', {}).get('name') == 'Kill':
                        if event.get('username') == clutch_candidate:
                            kills_after_clutch += 1
                
                # If the player got at least one kill or faced 3+ enemies, count it as a clutch
                if kills_after_clutch > 0 or enemy_count_at_clutch_start >= 3:
                    clutches[clutch_candidate] = clutches.get(clutch_candidate, 0) + 1
        
        return clutches

    def calculate_opening_picks(self) -> Dict[str, Dict[str, int]]:
        """
        Calculate opening kills and deaths for each player.
        
        :return: Dictionary of username to opening kills and deaths.
        """
        opening_stats = {stat.get('username', 'Unknown'): {"opening_kills": 0, "opening_deaths": 0} for stat in self.overall_stats}
        
        for round_data in self.rounds:
            match_feedback = round_data.get('matchFeedback', []) or []
            if not match_feedback:
                continue
            
            # Find the first kill of the round (opening kill)
            first_kill = next((kill for kill in match_feedback if isinstance(kill, dict) and kill.get('type', {}).get('name') == 'Kill'), None)
            if first_kill and 'username' in first_kill and 'target' in first_kill:
                killer = first_kill['username']
                victim = first_kill['target']
                
                # Make sure the players exist in our stats dictionary
                if killer not in opening_stats:
                    opening_stats[killer] = {"opening_kills": 0, "opening_deaths": 0}
                if victim not in opening_stats:
                    opening_stats[victim] = {"opening_kills": 0, "opening_deaths": 0}
                    
                opening_stats[killer]["opening_kills"] += 1
                opening_stats[victim]["opening_deaths"] += 1
        
        return opening_stats

    def calculate_kost(self) -> Dict[str, float]:
        """Calculate KOST (Kill, Objective, Survived, Traded) percentage"""
        kost = {stat.get('username', 'Unknown'): 0.0 for stat in self.overall_stats}
        total_rounds = max(len(self.rounds), 1)  # Avoid division by zero
        
        for round_data in self.rounds:
            match_feedback = round_data.get('matchFeedback', []) or []
            round_stats = round_data.get('stats', []) or []
            
            for player_stat in round_stats:
                if not isinstance(player_stat, dict):
                    continue
                
                username = player_stat.get('username', 'Unknown')
                player_kills = [kill for kill in match_feedback 
                               if isinstance(kill, dict) and kill.get('username') == username]
                player_survived = not player_stat.get('died', True)
                
                if player_kills or player_survived:
                    kost[username] = kost.get(username, 0.0) + (1.0 / total_rounds)
        
        return kost

    def generate_player_performance_report(self) -> List[Dict[str, Any]]:
        """Generate a comprehensive performance report for each player"""
        kpr = self.calculate_kpr()
        multikills = self.calculate_multikills()
        clutches = self.calculate_clutches()
        opening_picks = self.calculate_opening_picks()
        kost = self.calculate_kost()
        
        report = []
        for stat in self.overall_stats:
            if not isinstance(stat, dict):
                continue
                
            username = stat.get('username', 'Unknown')
            player_report = {
                'Username': username,
                'Kills per Round': kpr.get(username, 0),
                'Multikills': multikills.get(username, 0),
                'Clutches': clutches.get(username, 0),
                'Opening Kills': opening_picks.get(username, {"opening_kills": 0, "opening_deaths": 0})["opening_kills"],
                'Opening Deaths': opening_picks.get(username, {"opening_kills": 0, "opening_deaths": 0})["opening_deaths"],
                'KOST %': kost.get(username, 0) * 100,
                'Total Kills': stat.get('kills', 0),
                'Total Deaths': stat.get('deaths', 0)
            }
            report.append(player_report)
        
        return report
        
    def get_round_events(self, round_index: int) -> List[Dict[str, Any]]:
        """
        Get a chronological list of events that occurred in a specific round
        
        :param round_index: Index of the round to analyze
        :return: List of event dictionaries with timestamp, type, and description
        """
        if round_index < 0 or round_index >= len(self.rounds):
            return []
            
        round_data = self.rounds[round_index]
        events = []
        
        # Get match feedback events (kills, deaths, etc.)
        match_feedback = round_data.get('matchFeedback', []) or []
        
        # Parse timestamps to seconds for consistent handling
        def parse_time_to_seconds(time_str):
            if isinstance(time_str, (int, float)):
                return float(time_str)
            elif isinstance(time_str, str):
                # Handle MM:SS format
                if ':' in time_str:
                    parts = time_str.split(':')
                    if len(parts) == 2:
                        try:
                            minutes = int(parts[0])
                            seconds = int(parts[1])
                            return minutes * 60 + seconds
                        except ValueError:
                            print(f"Warning: Could not parse time string: {time_str}")
                            return 0
                # Try parsing as a straight number
                try:
                    return float(time_str)
                except ValueError:
                    print(f"Warning: Could not parse time: {time_str}")
                    return 0
            return 0
        
        # Find the start timestamp for relative timing
        start_time = 0
        for event in match_feedback:
            if isinstance(event, dict) and event.get('type', {}).get('name') == 'RoundStart':
                raw_timestamp = event.get('timestamp') or event.get('time', 0)
                start_time = parse_time_to_seconds(raw_timestamp)
                break
        
        for event in match_feedback:
            if not isinstance(event, dict):
                continue
                
            event_type = event.get('type', {}).get('name')
            # Look for timestamp in both 'timestamp' and 'time' fields
            raw_timestamp = event.get('timestamp') or event.get('time', 0)
            timestamp = parse_time_to_seconds(raw_timestamp)
            
            # Calculate relative time from round start
            relative_time = max(0, timestamp - start_time)
            
            # Format timestamp as MM:SS
            minutes = int(relative_time // 60)
            seconds = int(relative_time % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            # Debug print to see actual timestamp values
            print(f"Event: {event_type}, Raw timestamp: {raw_timestamp}, Relative time: {relative_time}, Formatted: {time_str}")
            
            description = "Unknown event"
            
            if event_type == 'Kill':
                weapon = event.get('weapon', {}).get('name', 'Unknown weapon')
                headshot = "HEADSHOT" if event.get('headshot') else ""
                description = f"{event.get('username', 'Unknown')} killed {event.get('target', 'Unknown')} with {weapon} {headshot}"
            elif event_type == 'TeamKill':
                weapon = event.get('weapon', {}).get('name', 'Unknown weapon')
                description = f"TEAMKILL: {event.get('username', 'Unknown')} killed {event.get('target', 'Unknown')} with {weapon}"
            elif event_type == 'Death':
                description = f"{event.get('username', 'Unknown')} died"
            elif event_type == 'RoundStart':
                description = "Round Started"
            elif event_type == 'RoundEnd':
                description = f"Round Ended - Winner: {event.get('winner', 'Unknown')}"
            elif event_type == 'OperatorSwap':
                # Handle operator swap events
                username = event.get('username', 'Unknown')
                # Get the 'from' operator
                from_operator = event.get('fromOperator', {}).get('name', 'Unknown')
                # Get the 'to' operator
                to_operator = event.get('toOperator', {}).get('name', 'Unknown')
                description = f"{username} swapped from {from_operator} to {to_operator}"
            
            events.append({
                'timestamp': timestamp,
                'time_str': time_str,
                'type': event_type,
                'description': description
            })
        
        # Sort events by timestamp
        events.sort(key=lambda x: x['timestamp'])
        
        return events
    
    def get_round_summary(self, round_index: int) -> Dict[str, Any]:
        """
        Get a summary of a specific round
        
        :param round_index: Index of the round to analyze
        :return: Dictionary with round summary information
        """
        if round_index < 0 or round_index >= len(self.rounds):
            return {}
            
        round_data = self.rounds[round_index]
        
        # Get basic round info
        round_number = round_index + 1
        map_name = round_data.get('map', {}).get('name', 'Unknown Map')
        
        # Get teams
        teams = round_data.get('teams', []) or []
        team_names = []
        for team in teams:
            if isinstance(team, dict):
                team_names.append(team.get('name', 'Unknown Team'))
        
        # Determine winner
        match_feedback = round_data.get('matchFeedback', []) or []
        winner = "Unknown"
        for event in match_feedback:
            if isinstance(event, dict) and event.get('type', {}).get('name') == 'RoundEnd':
                winner = event.get('winner', 'Unknown')
                break
        
        # Count kills per team
        team_kills = {}
        for event in match_feedback:
            if isinstance(event, dict) and event.get('type', {}).get('name') == 'Kill':
                killer_team = "Unknown"
                for player in round_data.get('players', []) or []:
                    if isinstance(player, dict) and player.get('username') == event.get('username'):
                        team_index = player.get('teamIndex')
                        if team_index is not None and team_index < len(teams):
                            team_obj = teams[team_index]
                            killer_team = team_obj.get('name', 'Unknown Team')
                        break
                
                team_kills[killer_team] = team_kills.get(killer_team, 0) + 1
        
        return {
            'round_number': round_number,
            'map': map_name,
            'teams': team_names,
            'winner': winner,
            'team_kills': team_kills
        }
        
class R6DissectGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("R6 Stats Analyzer")
        self.root.geometry("1920x900")
        
        # Create a notebook with tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create frames for each tab
        self.main_tab = ttk.Frame(self.notebook)
        self.rounds_tab = ttk.Frame(self.notebook)
        
        # Add tabs to notebook
        self.notebook.add(self.main_tab, text="Overall Stats")
        self.notebook.add(self.rounds_tab, text="Round Timeline")
        
        # Setup main tab
        self.setup_main_tab()
        
        # Setup rounds tab
        self.setup_rounds_tab()
        
        self.match_folder = None
        self.output_file = None
        self.match_data = None
        self.analyzer = None
        self.current_round = 0

    def setup_main_tab(self):
        self.label = tk.Label(self.main_tab, text="Select Match Folder and Output JSON File")
        self.label.pack(pady=10)
        
        self.select_folder_button = tk.Button(self.main_tab, text="Select Match Folder", command=self.select_folder)
        self.select_folder_button.pack(pady=5)
        
        self.folder_label = tk.Label(self.main_tab, text="No folder selected")
        self.folder_label.pack(pady=5)
        
        self.select_output_button = tk.Button(self.main_tab, text="Select Output JSON File", command=self.select_output_file)
        self.select_output_button.pack(pady=5)
        
        self.output_label = tk.Label(self.main_tab, text="No output file selected")
        self.output_label.pack(pady=5)
        
        self.process_button = tk.Button(self.main_tab, text="Process and Export", command=self.process)
        self.process_button.pack(pady=15)
        
        self.treeview = ttk.Treeview(self.main_tab, columns=("Username", "Kills per Round", "Multikills", "Clutches", "Opening Kills", "Opening Deaths", "KOST %", "Total Kills", "Total Deaths"), show="headings")
        self.treeview.pack(fill=tk.BOTH, expand=True)
        
        for col in self.treeview["columns"]:
            self.treeview.heading(col, text=col)
            self.treeview.column(col, anchor="center")

    def setup_rounds_tab(self):
        # Round navigation frame
        self.round_nav_frame = ttk.Frame(self.rounds_tab)
        self.round_nav_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.prev_round_button = ttk.Button(self.round_nav_frame, text="Previous Round", command=self.prev_round)
        self.prev_round_button.pack(side=tk.LEFT, padx=5)
        
        self.round_label = ttk.Label(self.round_nav_frame, text="Round: 0")
        self.round_label.pack(side=tk.LEFT, padx=20)
        
        self.next_round_button = ttk.Button(self.round_nav_frame, text="Next Round", command=self.next_round)
        self.next_round_button.pack(side=tk.LEFT, padx=5)
        
        self.go_to_round_button = ttk.Button(self.round_nav_frame, text="Go to Round...", command=self.go_to_round)
        self.go_to_round_button.pack(side=tk.LEFT, padx=20)
        
        # Round summary frame
        self.round_summary_frame = ttk.LabelFrame(self.rounds_tab, text="Round Summary")
        self.round_summary_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.round_info_text = tk.Text(self.round_summary_frame, height=5, wrap=tk.WORD)
        self.round_info_text.pack(fill=tk.X, padx=5, pady=5)
        self.round_info_text.config(state=tk.DISABLED)
        
        # Round events frame
        self.round_events_frame = ttk.LabelFrame(self.rounds_tab, text="Round Timeline")
        self.round_events_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.events_treeview = ttk.Treeview(self.round_events_frame, columns=("Time", "Event Type", "Description"), show="headings")
        self.events_treeview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.events_treeview.heading("Time", text="Time")
        self.events_treeview.heading("Event Type", text="Event Type")
        self.events_treeview.heading("Description", text="Description")
        
        self.events_treeview.column("Time", width=100, anchor="center")
        self.events_treeview.column("Event Type", width=150, anchor="center")
        self.events_treeview.column("Description", width=600)

    def select_folder(self):
        folder_path = filedialog.askdirectory(title="Select Match Folder")
        if folder_path:
            self.match_folder = folder_path
            self.folder_label.config(text=f"Selected Folder: {self.match_folder}")
    
    def select_output_file(self):
        output_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], title="Save Output as JSON")
        if output_path:
            self.output_file = output_path
            self.output_label.config(text=f"Selected File: {self.output_file}")

    def process(self):
        if not self.match_folder or not self.output_file:
            messagebox.showerror("Error", "Please select both the match folder and output file.")
            return
        
        try:
            command = ["r6-dissect", self.match_folder, "-o", self.output_file]
            subprocess.run(command, check=True)
            
            try:
                with open(self.output_file, 'r') as file:
                    self.match_data = json.load(file)
                
                if not self.match_data:
                    messagebox.showerror("Error", "The output file contains empty data.")
                    return
                    
                self.analyzer = R6StatsAnalyzer(self.match_data)
                performance_report = self.analyzer.generate_player_performance_report()
    
                for row in self.treeview.get_children():
                    self.treeview.delete(row)
                
                for player_stats in performance_report:
                    self.treeview.insert("", "end", values=(
                        player_stats['Username'],
                        f"{player_stats['Kills per Round']:.2f}",
                        player_stats['Multikills'],
                        player_stats['Clutches'],
                        player_stats['Opening Kills'],
                        player_stats['Opening Deaths'],
                        f"{player_stats['KOST %']:.2f}",
                        player_stats['Total Kills'],
                        player_stats['Total Deaths']
                    ))
                
                # Reset round view
                self.current_round = 0
                self.update_round_view()
                
                # Switch to the rounds tab
                self.notebook.select(1)
                messagebox.showinfo("Success", "Data processed successfully! Showing round timeline.")
                
            except FileNotFoundError:
                messagebox.showerror("Error", f"The output file was not created: {self.output_file}")
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Failed to decode JSON from the r6-dissect output.")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"An error occurred while processing the data: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
    
    def update_round_view(self):
        if not self.analyzer:
            return
            
        # Update round label
        self.round_label.config(text=f"Round: {self.current_round + 1}")
        
        # Update round summary
        round_summary = self.analyzer.get_round_summary(self.current_round)
        
        summary_text = f"Round {round_summary.get('round_number', 0)} on {round_summary.get('map', 'Unknown')}\n"
        summary_text += f"Teams: {', '.join(round_summary.get('teams', ['Unknown']))}\n"
        summary_text += f"Winner: {round_summary.get('winner', 'Unknown')}\n"
        
        team_kills = round_summary.get('team_kills', {})
        summary_text += "Team Kills: " + ", ".join(f"{team}: {kills}" for team, kills in team_kills.items())
        
        self.round_info_text.config(state=tk.NORMAL)
        self.round_info_text.delete(1.0, tk.END)
        self.round_info_text.insert(tk.END, summary_text)
        self.round_info_text.config(state=tk.DISABLED)
        
        # Update events treeview
        for row in self.events_treeview.get_children():
            self.events_treeview.delete(row)
        
        events = self.analyzer.get_round_events(self.current_round)
        
        for event in events:
            self.events_treeview.insert("", "end", values=(
                event.get('time_str', '00:00'),
                event.get('type', 'Unknown'),
                event.get('description', 'Unknown event')
            ))
    
    def next_round(self):
        if not self.analyzer:
            return
            
        max_rounds = len(self.analyzer.rounds)
        if self.current_round < max_rounds - 1:
            self.current_round += 1
            self.update_round_view()
    
    def prev_round(self):
        if not self.analyzer:
            return
            
        if self.current_round > 0:
            self.current_round -= 1
            self.update_round_view()
    
    def go_to_round(self):
        if not self.analyzer:
            return
            
        max_rounds = len(self.analyzer.rounds)
        if max_rounds == 0:
            return
            
        round_num = simpledialog.askinteger("Go to Round", f"Enter round number (1-{max_rounds}):", 
                                          minvalue=1, maxvalue=max_rounds)
        if round_num:
            self.current_round = round_num - 1
            self.update_round_view()

def main():
    root = tk.Tk()
    app = R6DissectGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
