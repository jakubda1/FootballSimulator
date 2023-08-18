import random
from mocks import MockDataSource


class Tactics:
    TACTIC_EFFECTS = {
        "normal": {},
        "defensive": {"powerInDefense": 1.1, "powerInOffense": 0.9},
        "offensive": {"powerInOffense": 1.1, "powerInDefense": 0.9},
        "counter_attacks": {"speed": 1.1, "powerInMidfield": 1.05, "powerInDefense": 0.9},
        "kicked_balls": {"powerInAccuracy": 1.1},
        "short_pass": {"powerInMidfield": 1.1}
    }

    @staticmethod
    def apply_tactic(player, tactic_name):
        """
        Modifies player attributes based on the given tactic.
        """
        effects = Tactics.TACTIC_EFFECTS.get(tactic_name, {})
        for attr, multiplier in effects.items():
            setattr(player, attr, getattr(player, attr) * multiplier)

    @staticmethod
    def get_tactic_behaviors(tactic_name):
        """
        Returns behaviors or actions associated with a tactic.
        For now, this is a placeholder and can be expanded with more behaviors.
        """
        if tactic_name == "short_pass":
            return ["short_pass"]
        else:
            return ["standard_play"]


class StatsPlayer:
    def __init__(self):
        self.yellow_card = 0
        self.red_card = 0
        self.goals = 0
        self.assists = 0
        self.shots_on = 0
        self.shots_off = 0
        self.fouls = 0
        self.plus = 0

    def __str__(self):
        return str(self.__dict__)


class Player:
    def __init__(self, player):
        self.name = player.name
        self.experience = player.experience
        self.powerInGoal = player.powerInGoal
        self.powerInDefense = player.powerInDefense
        self.powerInMidfield = player.powerInMidfield
        self.powerInOffense = player.powerInAttack
        self.powerInAccuracy = player.powerInAccuracy
        self.energy = player.actualEnergy
        self.positionId = player.positionId
        self.id = player.id
        self.injured = False
        if not player.banned:
            self.banned = 0
        else:
            self.banned = player.banned
        self.stats = StatsPlayer()
        self.injury_chance = 0.01  # Chance of getting injured during a play


    def get_injured(self):
        """Method to potentially injure a player based on their injury chance."""
        if random.random() < self.injury_chance:
            self.injured = True

    def __str__(self):
        return self.name


class Team:
    def __init__(self, players, tactics=None):
        """
        Initialize a team with a list of players and optional tactics.
        """
        self.players = players  # List of Player objects
        self.tactics = tactics or {}  # Placeholder for tactics/strategy data (e.g., formation, style of play)

    def get_active_players(self):
        """
        Returns a list of players who are not injured and not banned.
        """
        return [player for player in self.players if not player.injured and not player.banned]

    def __str__(self):
        return ", ".join([player.name for player in self.players])


class Match:
    HOME_ADVANTAGE = 1.05
    MATCH_TIME = 90

    def __init__(self, home_team, away_team, home_tactic="normal", away_tactic="normal"):
        self.home_team = home_team
        self.away_team = away_team
        self.home_tactic = home_tactic
        self.away_tactic = away_tactic
        self.home_goals = 0
        self.away_goals = 0
        self.ball_possession = random.choice([self.home_team, self.away_team])
        self.commentary = []

    def apply_home_advantage(self):
        for player in self.home_team.players:
            player.powerInGoal *= Match.HOME_ADVANTAGE
            player.powerInDefense *= Match.HOME_ADVANTAGE
            player.powerInMidfield *= Match.HOME_ADVANTAGE
            player.powerInOffense *= Match.HOME_ADVANTAGE
            player.powerInAccuracy *= Match.HOME_ADVANTAGE

    def apply_tactics(self):
        for player in self.home_team.players:
            Tactics.apply_tactic(player, self.home_tactic)
        for player in self.away_team.players:
            Tactics.apply_tactic(player, self.away_tactic)

    def setup_phase(self):
        self.apply_home_advantage()
        self.apply_tactics()

    def pass_ball(self, player):
        success_chance = random.random() + 0.2
        return success_chance > 0.5

    def shoot(self, player):
        success_chance = random.random() + 0.1
        return success_chance > 0.8

    def simulation_phase(self):
        for minute in range(Match.MATCH_TIME):
            # Selecting a random player from the team in possession for the action
            active_player = random.choice(self.ball_possession.get_active_players())

            if self.ball_possession == self.home_team:
                if self.pass_ball(active_player):
                    self.commentary.append(
                        f"Minute {minute}: {active_player.name} from the Home team successfully passes the ball.")
                else:
                    self.commentary.append(
                        f"Minute {minute}: {active_player.name}'s pass is intercepted by the Away team!")
                    self.ball_possession = self.away_team

                if self.shoot(active_player):
                    self.home_goals += 1
                    self.commentary.append(
                        f"Minute {minute}: GOAL! {active_player.name} from the Home team scores! Current score: {self.home_goals}-{self.away_goals}")
            else:
                if self.pass_ball(active_player):
                    self.commentary.append(
                        f"Minute {minute}: {active_player.name} from the Away team successfully passes the ball.")
                else:
                    self.commentary.append(
                        f"Minute {minute}: {active_player.name}'s pass is intercepted by the Home team!")
                    self.ball_possession = self.home_team

                if self.shoot(active_player):
                    self.away_goals += 1
                    self.commentary.append(
                        f"Minute {minute}: GOAL! {active_player.name} from the Away team scores! Current score: {self.home_goals}-{self.away_goals}")

    def outcome_phase(self):
        if self.home_goals > self.away_goals:
            return "Home Team Wins!"
        elif self.home_goals < self.away_goals:
            return "Away Team Wins!"
        else:
            return "It's a Draw!"

    def simulate_match(self):
        self.setup_phase()
        self.simulation_phase()
        outcome = self.outcome_phase()
        self.commentary.append(outcome)
        return self.commentary
#
#
# mock_data_1 = MockDataSource("Jane Doe")
# mock_data_2 = MockDataSource("Al Bundy")
# player_instance_1 = Player(mock_data_1)
# player_instance_2 = Player(mock_data_2)
# team_instance = Team([player_instance_1, player_instance_2])
# match_instance = Match(home_team=team_instance, away_team=team_instance, home_tactic="defensive",
#                        away_tactic="offensive")
# match_result = match_instance.simulate_match()
# match_goals = (match_instance.home_goals, match_instance.away_goals)
#
# [print(comm) for comm in match_instance.commentary]
# print(match_result, match_goals)
