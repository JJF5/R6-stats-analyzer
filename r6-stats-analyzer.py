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
    
    def calculate_survival_rate(self) -> Dict[str, float]:
        """Calculate Survival Rate"""
        return {
            stat['username']: 1 - (stat['deaths'] / stat['rounds']) 
            for stat in self.overall_stats
        }
    
    def calculate_headshot_rate(self) -> Dict[str, float]:
        """Calculate Headshot Rate"""
        return {
            stat['username']: stat['headshotPercentage'] / 100.0 
            for stat in self.overall_stats
        }
    
    def generate_player_performance_report(self) -> List[Dict[str, Any]]:
        """Generate a comprehensive performance report for each player"""
        kpr = self.calculate_kpr()
        multikills = self.calculate_multikills()
        clutches = self.calculate_clutches()
        kost = self.calculate_kost()
        survival_rate = self.calculate_survival_rate()
        headshot_rate = self.calculate_headshot_rate()
        
        report = []
        for stat in self.overall_stats:
            username = stat['username']
            player_report = {
                'Username': username,
                'Kills per Round': kpr.get(username, 0),
                'Multikills': multikills.get(username, 0),
                'Clutches': clutches.get(username, 0),
                'KOST %': kost.get(username, 0) * 100,
                'Survival Rate': survival_rate.get(username, 0),
                'Headshot Rate': headshot_rate.get(username, 0) * 100,
                'Total Kills': stat['kills'],
                'Total Deaths': stat['deaths']
            }
            report.append(player_report)
        
        return report

class R6DissectGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("R6 Dissect GUI")
        self.root.geometry("1920x600")
        
        # Label for instructions
        self.label = tk.Label(self.root, text="Select Match Folder and Output JSON File")
        self.label.pack(pady=10)
        
        # Folder selection button
        self.select_folder_button = tk.Button(self.root, text="Select Match Folder", command=self.select_folder)
        self.select_folder_button.pack(pady=5)
        
        # Label to show selected folder
        self.folder_label = tk.Label(self.root, text="No folder selected")
        self.folder_label.pack(pady=5)
        
        # Output file selection button
        self.select_output_button = tk.Button(self.root, text="Select Output JSON File", command=self.select_output_file)
        self.select_output_button.pack(pady=5)
        
        # Label to show selected output file
        self.output_label = tk.Label(self.root, text="No output file selected")
        self.output_label.pack(pady=5)
        
        # Process button
        self.process_button = tk.Button(self.root, text="Process and Export", command=self.process)
        self.process_button.pack(pady=15)
        
        # Table to display the stats
        self.treeview = ttk.Treeview(self.root, columns=("Username", "Kills per Round", "Multikills", "Clutches", "KOST %", "Survival Rate", "Headshot Rate", "Total Kills", "Total Deaths"), show="headings")
        self.treeview.pack(fill=tk.BOTH, expand=True)
        
        for col in self.treeview["columns"]:
            self.treeview.heading(col, text=col)
            self.treeview.column(col, anchor="center")
        
        # Variables to store selected folder and output file paths
        self.match_folder = None
        self.output_file = None

    def select_folder(self):
        """Open a folder dialog to select the match folder."""
        folder_path = filedialog.askdirectory(title="Select Match Folder")
        if folder_path:
            self.match_folder = folder_path
            self.folder_label.config(text=f"Selected Folder: {self.match_folder}")
    
    def select_output_file(self):
        """Open a file save dialog to select the output JSON file."""
        output_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], title="Save Output as JSON")
        if output_path:
            self.output_file = output_path
            self.output_label.config(text=f"Selected File: {self.output_file}")

    def process(self):
        """Execute the r6-dissect command with selected folder and output file."""
        if not self.match_folder or not self.output_file:
            messagebox.showerror("Error", "Please select both the match folder and output file.")
            return
        
        try:
            # Construct the command to run r6-dissect
            command = ["r6-dissect", self.match_folder, "-o", self.output_file]
            
            # Run the command
            subprocess.run(command, check=True)
            
            # Load the match data from the generated JSON
            with open(self.output_file, 'r') as file:
                match_data = json.load(file)
            
            # Create analyzer and generate the performance report
            analyzer = R6StatsAnalyzer(match_data)
            performance_report = analyzer.generate_player_performance_report()

            # Clear previous table rows
            for row in self.treeview.get_children():
                self.treeview.delete(row)
            
            # Add the new data into the table
            for player_stats in performance_report:
                self.treeview.insert("", "end", values=(
                    player_stats['Username'],
                    f"{player_stats['Kills per Round']:.2f}",
                    player_stats['Multikills'],
                    player_stats['Clutches'],
                    f"{player_stats['KOST %']:.2f}",
                    f"{player_stats['Survival Rate']:.2f}",
                    f"{player_stats['Headshot Rate']:.2f}",
                    player_stats['Total Kills'],
                    player_stats['Total Deaths']
                ))
                
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"An error occurred while processing the data: {e}")
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Failed to decode JSON from the r6-dissect output.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

# Create the GUI window and start the application
def main():
    root = tk.Tk()
    app = R6DissectGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
