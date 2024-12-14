# R6StatsAnalyzer

The **R6StatsAnalyzer** is a Python class designed to analyze and generate performance metrics for players based on match data from Rainbow Six Siege. The class provides several methods to calculate key player performance statistics, including kills per round (KPR), multikills, opening picks, clutches, KOST (Kill, Objective, Survived, Traded) percentage, survival rate, trade differential, and headshot rate.

## Requirements

- Python 3.6 or higher
- `json` module (standard in Python)
- r6-dissect (https://github.com/redraskal/r6-dissect)

## Overview

The `R6StatsAnalyzer` class processes match data in JSON format and calculates the following statistics:

1. **Kills per Round (KPR):** Average number of kills per round for each player.
2. **Teamkills:** Tracks the number of teamkills (note: not implemented in the provided dataset).
3. **Multikills:** Counts the number of multikills (more than 1 kill in a single round) per player.
4. **Opening Picks:** Tracks the number of times a player gets the first kill in a round and the number of times they are killed first.
5. **Clutches:** Counts the number of clutch rounds where a player performs well under pressure.
6. **KOST:** Kill, Objective, Survived, Traded percentage for each player.
7. **Survival Rate:** The percentage of rounds where a player survived.
8. **Trade Differential:** The difference between the number of trades a player makes and the number of times they are traded (simplified for this dataset).
9. **Headshot Rate:** The percentage of kills a player made with headshots.

## Installation

To use the **R6StatsAnalyzer** class, simply include the code in your Python project. No external libraries are required.

## Usage

To use the **R6StatsAnalyzer**, load match data from a JSON file, create an instance of the class, and then call the `generate_player_performance_report` method to generate a comprehensive performance report.

### Example Usage

```python
import json
from R6StatsAnalyzer import R6StatsAnalyzer

def main():
    # Load the JSON file from the specific path
    json_file_path = r'C:\path\to\your\match_data.json'
    
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
```

###Input Format
The match data should be provided in a JSON format with the following structure:

rounds: A list of rounds played in the match.
matchFeedback: A list of kills, deaths, and other match-related feedback for each round.
stats: A list of player statistics, including kills, deaths, and other performance data.
An example match data file (test.json):
```
{
  "rounds": [
    {
      "matchFeedback": [
        {
          "username": "Player1",
          "type": { "name": "Kill" },
          "target": "Player2"
        }
      ],
      "stats": [
        {
          "username": "Player1",
          "kills": 3,
          "deaths": 1,
          "rounds": 5,
          "headshotPercentage": 25
        },
        {
          "username": "Player2",
          "kills": 2,
          "deaths": 2,
          "rounds": 5,
          "headshotPercentage": 50
        }
      ]
    }
  ],
  "stats": [
    {
      "username": "Player1",
      "kills": 10,
      "deaths": 5,
      "rounds": 10,
      "headshotPercentage": 30
    },
    {
      "username": "Player2",
      "kills": 8,
      "deaths": 6,
      "rounds": 10,
      "headshotPercentage": 40
    }
  ]
}

```
Methods
__init__(self, match_data: Dict[str, Any])
Initializes the analyzer with the provided match data.

Parameters:

match_data (dict): A dictionary containing the match data in JSON format.
calculate_kpr(self) -> Dict[str, float]
Calculates the Kills per Round for each player.

Returns:

A dictionary mapping player usernames to their Kills per Round (KPR).
calculate_teamkills(self) -> Dict[str, int]
Calculates the number of teamkills for each player. This is a placeholder method as the example dataset does not provide data for teamkills.

Returns:

A dictionary mapping player usernames to the number of teamkills.
calculate_multikills(self) -> Dict[str, int]
Calculates the number of multikills (more than 1 kill in a round) for each player.

Returns:

A dictionary mapping player usernames to their multikill count.
calculate_opening_picks(self) -> Dict[str, Dict[str, int]]
Calculates opening picks and opening deaths for each player (first kill and first death of a round).

Returns:

A dictionary mapping player usernames to a dictionary containing their opening picks and opening deaths.
calculate_clutches(self) -> Dict[str, int]
Calculates the number of clutches for each player (last player alive who gets multiple kills).

Returns:

A dictionary mapping player usernames to their clutch count.
calculate_kost(self) -> Dict[str, float]
Calculates the KOST (Kill, Objective, Survived, Traded) percentage for each player.

Returns:

A dictionary mapping player usernames to their KOST percentage.
calculate_survival_rate(self) -> Dict[str, float]
Calculates the Survival Rate for each player (percentage of rounds where the player survived).

Returns:

A dictionary mapping player usernames to their survival rate.
calculate_trade_differential(self) -> Dict[str, int]
Calculates the Trade Differential for each player. This method is a placeholder for more complex tracking.

Returns:

A dictionary mapping player usernames to their trade differential.
calculate_headshot_rate(self) -> Dict[str, float]
Calculates the Headshot Rate for each player.

Returns:

A dictionary mapping player usernames to their headshot rate.
generate_player_performance_report(self) -> List[Dict[str, Any]]
Generates a comprehensive player performance report for each player.

Returns:

A list of dictionaries, each containing the player's performance metrics.
