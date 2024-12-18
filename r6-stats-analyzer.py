import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import subprocess
import json
from typing import Dict, Any, List

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
        return {
            stat['username']: stat['kills'] / stat['rounds'] 
            for stat in self.overall_stats
        }

    def calculate_multikills(self) -> Dict[str, int]:
        """Calculate number of multikills for each player"""
        multikills = {stat['username']: 0 for stat in self.overall_stats}
        
        for round_data in self.rounds:
            kills_by_player = {}
            for kill in round_data.get('matchFeedback', []):
                if kill['type']['name'] == 'Kill':
                    username = kill['username']
                    kills_by_player[username] = kills_by_player.get(username, 0) + 1
            
            for username, kill_count in kills_by_player.items():
                if kill_count > 1:
                    multikills[username] += 1
        
        return multikills

    def calculate_clutches(self) -> Dict[str, int]:
        """Calculate clutch rounds for each player"""
        clutches = {stat['username']: 0 for stat in self.overall_stats}
        
        for round_data in self.rounds:
            match_feedback = round_data.get('matchFeedback', [])
            teams = round_data.get('teams', [])
            
            if len(teams) > 1 and 'id' in teams[1]:
                team_id = teams[1]['id']
            else:
                team_id = None
            
            living_players = {
                player['username'] for player in round_data.get('players', []) 
                if player['teamIndex'] == team_id
            }
            
            kills_by_last_player = {}
            for kill in match_feedback:
                if kill['type']['name'] == 'Kill' and kill['username'] in living_players:
                    kills_by_last_player[kill['username']] = kills_by_last_player.get(kill['username'], 0) + 1
            
            for username, kill_count in kills_by_last_player.items():
                if kill_count > 1:
                    clutches[username] += 1
        
        return clutches

    def calculate_opening_picks(self) -> Dict[str, Dict[str, int]]:
        """
        Calculate opening kills and deaths for each player.
        
        :return: Dictionary of username to opening kills and deaths.
        """
        opening_stats = {stat['username']: {"opening_kills": 0, "opening_deaths": 0} for stat in self.overall_stats}
        
        for round_data in self.rounds:
            match_feedback = round_data.get('matchFeedback', [])
            if not match_feedback:
                continue
            
            # Find the first kill of the round (opening kill)
            first_kill = next((kill for kill in match_feedback if kill['type']['name'] == 'Kill'), None)
            if first_kill:
                killer = first_kill['username']
                victim = first_kill['target']
                opening_stats[killer]["opening_kills"] += 1
                opening_stats[victim]["opening_deaths"] += 1
        
        return opening_stats

    def calculate_kost(self) -> Dict[str, float]:
        """Calculate KOST (Kill, Objective, Survived, Traded) percentage"""
        kost = {stat['username']: 0.0 for stat in self.overall_stats}
        total_rounds = len(self.rounds)
        
        for round_data in self.rounds:
            match_feedback = round_data.get('matchFeedback', [])
            round_stats = round_data.get('stats', [])
            
            for player_stat in round_stats:
                username = player_stat['username']
                player_kills = [kill for kill in match_feedback if kill['username'] == username]
                player_survived = not player_stat['died']
                
                if player_kills or player_survived:
                    kost[username] += 1.0 / total_rounds
        
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
            username = stat['username']
            player_report = {
                'Username': username,
                'Kills per Round': kpr.get(username, 0),
                'Multikills': multikills.get(username, 0),
                'Clutches': clutches.get(username, 0),
                'Opening Kills': opening_picks[username]["opening_kills"],
                'Opening Deaths': opening_picks[username]["opening_deaths"],
                'KOST %': kost.get(username, 0) * 100,
                'Total Kills': stat['kills'],
                'Total Deaths': stat['deaths']
            }
            report.append(player_report)
        
        return report

class R6DissectGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("R6 Stats Analyzer")
        self.root.geometry("1920x600")
        
        self.label = tk.Label(self.root, text="Select Match Folder and Output JSON File")
        self.label.pack(pady=10)
        
        self.select_folder_button = tk.Button(self.root, text="Select Match Folder", command=self.select_folder)
        self.select_folder_button.pack(pady=5)
        
        self.folder_label = tk.Label(self.root, text="No folder selected")
        self.folder_label.pack(pady=5)
        
        self.select_output_button = tk.Button(self.root, text="Select Output JSON File", command=self.select_output_file)
        self.select_output_button.pack(pady=5)
        
        self.output_label = tk.Label(self.root, text="No output file selected")
        self.output_label.pack(pady=5)
        
        self.process_button = tk.Button(self.root, text="Process and Export", command=self.process)
        self.process_button.pack(pady=15)
        
        self.treeview = ttk.Treeview(self.root, columns=("Username", "Kills per Round", "Multikills", "Clutches", "Opening Kills", "Opening Deaths", "KOST %", "Total Kills", "Total Deaths"), show="headings")
        self.treeview.pack(fill=tk.BOTH, expand=True)
        
        for col in self.treeview["columns"]:
            self.treeview.heading(col, text=col)
            self.treeview.column(col, anchor="center")
        
        self.match_folder = None
        self.output_file = None

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
            
            with open(self.output_file, 'r') as file:
                match_data = json.load(file)
            
            analyzer = R6StatsAnalyzer(match_data)
            performance_report = analyzer.generate_player_performance_report()

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
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"An error occurred while processing the data: {e}")
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Failed to decode JSON from the r6-dissect output.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

def main():
    root = tk.Tk()
    app = R6DissectGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
