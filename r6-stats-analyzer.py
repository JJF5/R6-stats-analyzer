import json
from typing import Dict, List, Any

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
        """
        Calculate Kills per Round for each player
        
        :return: Dictionary of username to KPR
        """
        return {
            stat['username']: stat['kills'] / stat['rounds'] 
            for stat in self.overall_stats
        }
    
    def calculate_teamkills(self) -> Dict[str, int]:
        """
        Calculate Teamkills per Round (Note: this example dataset doesn't show teamkills)
        
        :return: Dictionary of username to teamkills
        """
        # In a real implementation, you'd need additional data tracking teamkills
        return {stat['username']: 0 for stat in self.overall_stats}
    
    def calculate_multikills(self) -> Dict[str, int]:
        """
        Calculate number of multikills for each player
        
        :return: Dictionary of username to multikill count
        """
        multikills = {stat['username']: 0 for stat in self.overall_stats}
        
        for round_data in self.rounds:
            # Analyze match feedback to count multikills
            kills_by_player = {}
            for kill in round_data.get('matchFeedback', []):
                if kill['type']['name'] == 'Kill':
                    username = kill['username']
                    kills_by_player[username] = kills_by_player.get(username, 0) + 1
            
            # Count players with multiple kills in a round
            for username, kill_count in kills_by_player.items():
                if kill_count > 1:
                    multikills[username] += 1
        
        return multikills
    
    def calculate_opening_picks(self) -> Dict[str, Dict[str, int]]:
        """
        Calculate opening picks for each player
        
        :return: Dictionary of username to opening pick statistics
        """
        opening_picks = {stat['username']: {
            'opening_picks': 0,
            'opening_deaths': 0
        } for stat in self.overall_stats}
        
        for round_data in self.rounds:
            match_feedback = round_data.get('matchFeedback', [])
            if not match_feedback:
                continue
            
            # First kill of the round
            first_kill = next((kill for kill in match_feedback if kill['type']['name'] == 'Kill'), None)
            if first_kill:
                killer = first_kill['username']
                opening_picks[killer]['opening_picks'] += 1
            
            # Check if the first kill's victim was killed
            if first_kill:
                victim = first_kill['target']
                opening_picks[victim]['opening_deaths'] += 1
        
        return opening_picks
    
    def calculate_clutches(self) -> Dict[str, int]:
        """
        Calculate clutch rounds for each player
        
        :return: Dictionary of username to clutch count
        """
        # This is a simplified implementation
        # A true clutch detection would require more complex round state tracking
        clutches = {stat['username']: 0 for stat in self.overall_stats}
        
        for round_data in self.rounds:
            match_feedback = round_data.get('matchFeedback', [])
            
            # Safely access the 'id' from the teams data
            teams = round_data.get('teams', [])
            
            # Check if there are enough teams and if the 'id' key exists
            if len(teams) > 1 and 'id' in teams[1]:
                team_id = teams[1]['id']
            else:
                # Handle missing 'id' or insufficient teams (e.g., skipping or setting a default value)
                team_id = None  # You can replace 'None' with another default value if needed
            
            # Debug: Print team_id for the current round to ensure it's being handled correctly
            print("Using team_id:", team_id)
            
            # Identify the players that belong to the second team (team 2)
            living_players = {
                player['username'] for player in round_data.get('players', []) 
                if player['teamIndex'] == team_id
            }
            
            # Simple clutch detection: last player alive who gets kills
            kills_by_last_player = {}
            for kill in match_feedback:
                if kill['type']['name'] == 'Kill' and kill['username'] in living_players:
                    kills_by_last_player[kill['username']] = kills_by_last_player.get(kill['username'], 0) + 1
            
            # Mark clutches (simplified)
            for username, kill_count in kills_by_last_player.items():
                if kill_count > 1:
                    clutches[username] += 1
        
        return clutches
    
    def calculate_kost(self) -> Dict[str, float]:
        """
        Calculate KOST (Kill, Objective, Survived, Traded) percentage
        
        :return: Dictionary of username to KOST percentage
        """
        kost = {stat['username']: 0.0 for stat in self.overall_stats}
        total_rounds = len(self.rounds)
        
        for round_data in self.rounds:
            match_feedback = round_data.get('matchFeedback', [])
            round_stats = round_data.get('stats', [])
            
            for player_stat in round_stats:
                username = player_stat['username']
                
                # Check if player got a kill
                player_kills = [kill for kill in match_feedback if kill['username'] == username]
                
                # Check if player survived
                player_survived = not player_stat['died']
                
                # Simplified KOST calculation
                if player_kills or player_survived:
                    kost[username] += 1.0 / total_rounds
        
        return kost
    
    def calculate_survival_rate(self) -> Dict[str, float]:
        """
        Calculate Survival Rate
        
        :return: Dictionary of username to Survival Rate
        """
        return {
            stat['username']: 1 - (stat['deaths'] / stat['rounds']) 
            for stat in self.overall_stats
        }
    
    def calculate_trade_differential(self) -> Dict[str, int]:
        """
        Calculate Trade Differential
        (Simplified due to limited data)
        
        :return: Dictionary of username to Trade Differential
        """
        # This would require more complex tracking of trades
        return {stat['username']: 0 for stat in self.overall_stats}
    
    def calculate_headshot_rate(self) -> Dict[str, float]:
        """
        Calculate Headshot Rate
        
        :return: Dictionary of username to Headshot Rate
        """
        return {
            stat['username']: stat['headshotPercentage'] / 100.0 
            for stat in self.overall_stats
        }
    
    def generate_player_performance_report(self) -> List[Dict[str, Any]]:
        """
        Generate a comprehensive performance report for each player
        
        :return: List of dictionaries with player performance metrics
        """
        kpr = self.calculate_kpr()
        multikills = self.calculate_multikills()
        opening_picks = self.calculate_opening_picks()
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
                'Opening Picks': opening_picks.get(username, {}).get('opening_picks', 0),
                'Opening Deaths': opening_picks.get(username, {}).get('opening_deaths', 0),
                'Clutches': clutches.get(username, 0),
                'KOST %': kost.get(username, 0) * 100,
                'Survival Rate': survival_rate.get(username, 0),
                'Headshot Rate': headshot_rate.get(username, 0) * 100,
                'Total Kills': stat['kills'],
                'Total Deaths': stat['deaths']
            }
            report.append(player_report)
        
        return report

# Example usage
def main():
    # Load the JSON file from the specific path
    json_file_path = r'C:\Users\JJF5\Desktop\siegegg\test.json'
    
    try:
        with open(json_file_path, 'r') as file:
            match_data = json.load(file)
    except FileNotFoundError:
        print(f"Error: File not found at {json_file_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in the file at {json_file_path}")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return
    
    # Create analyzer
    analyzer = R6StatsAnalyzer(match_data)
    
    # Generate and print performance report
    performance_report = analyzer.generate_player_performance_report()
    
    print("Player Performance Report:")
    for player_stats in performance_report:
        print("\n--- {} ---".format(player_stats['Username']))
        for metric, value in player_stats.items():
            if isinstance(value, float):
                print(f"{metric}: {value:.2f}")
            else:
                print(f"{metric}: {value}")

if __name__ == "__main__":
    main()
