import time
import math
import random
import cv2
import pygame
from pygame_screen_record.ScreenRecorder import ScreenRecorder
from pygame_screen_record.ScreenRecorder import add_codec

add_codec("mp4", "mp4v")

# Initialize pygame
pygame.init()

# Set up display parameters
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Football Match Simulation")

# Define colors
GREEN = (0, 128, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)


def point_on_line(x1, y1, x2, y2, px, py, tolerance=1):
    """
    Check if a point (px, py) lies on the line segment between (x1, y1) and (x2, y2).
    A tolerance is added to account for players being close to, but not exactly on, the line.
    """
    # Calculate line equation: y = mx + c
    if x2 - x1 == 0:  # Vertical line
        return abs(px - x1) < tolerance
    m = (y2 - y1) / (x2 - x1)
    c = y1 - m * x1

    # Check if point is on the line
    return abs(py - (m * px + c)) < tolerance


def check_and_resolve_collisions(players, football):
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            if players[i].collides_with(players[j], football):
                players[i].resolve_collision(players[j])


class Goal:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def draw(self, screen):
        pygame.draw.rect(screen, WHITE, (self.x, self.y, self.width, self.height))


class PlayerStats:
    def __init__(self, kick_range, kick_dispersion):
        self.kick_range = kick_range  # Max distance from which player can attempt a shot
        self.kick_dispersion = kick_dispersion  # Angle of dispersion when shooting


class Player:
    def __init__(self, name, x, y, color, goal_home, goal_away, stats=None, rotation=0):
        self.x = x
        self.y = y
        self.previous_x = x  # Storing initial positions as previous positions initially
        self.previous_y = y
        self.color = color
        self.speed = 5
        self.stats = stats or PlayerStats(kick_range=150, kick_dispersion=15)  # Default stats if none provided
        self.in_possession = False
        self.rotation = rotation
        self.player_surface = pygame.Surface((30, 30), pygame.SRCALPHA)
        self.home_goal = goal_home
        self.away_goal = goal_away
        self._in_collision = False
        self._in_collision_with = None
        self.name = name
        self.sprinting = False
        self.sprint_speed = 7
        self.collision_duration = 0
        self.fatigue = 100

    def __str__(self):
        return self.name

    @property
    def in_collision(self):
        return self._in_collision

    @in_collision.setter
    def in_collision(self, with_whom):
        if with_whom is None:
            self._in_collision_with = None
            self._in_collision = False
        else:
            self._in_collision_with = with_whom
            self._in_collision = True

    @property
    def in_collision_with(self):
        return self._in_collision_with

    def draw_player(self, screen):
        # Create a surface for the player
        pygame.draw.circle(self.player_surface, self.color, (15, 15), 15)

        # Rotate the surface
        rotated_surface = pygame.transform.rotate(self.player_surface, -self.rotation)

        # Calculate the position to draw the rotated surface
        pos_x = self.x - rotated_surface.get_width() // 2
        pos_y = self.y - rotated_surface.get_height() // 2

        # Draw the rotated player
        screen.blit(rotated_surface, (pos_x, pos_y))

    def draw_shooting_range(self, screen):
        pygame.draw.circle(screen, self.color, (self.x, self.y), self.stats.kick_range, 1)

        for angle_offset in [-self.stats.kick_dispersion, self.stats.kick_dispersion]:
            angle = math.radians(self.rotation + angle_offset)

            end_x = self.x + self.stats.kick_range * math.cos(angle)
            end_y = self.y + self.stats.kick_range * math.sin(angle)
            pygame.draw.line(screen, self.color, (self.x, self.y), (end_x, end_y), 1)

    def draw_fatigue_bar(self):
        pygame.draw.rect(screen, (255, 165, 0), (self.x - 20, self.y + 20, 40, 5))  # Background (orange)
        pygame.draw.rect(screen, (255, 255, 0),
                         (self.x - 20, self.y + 20, 0.4 * self.fatigue, 5))  # Foreground (yellow)

    def draw(self, screen, show_shooting_range=False):
        self.draw_player(screen)
        if show_shooting_range:
            self.draw_shooting_range(screen)
        self.draw_fatigue_bar()

    def collides_with(self, other, ball):
        distance = math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
        distance_to_ball = math.sqrt((self.x - ball.x) ** 2 + (self.y - other.y) ** 2)
        self.in_possession = distance_to_ball < 30  # Assuming each player has a radius of 15
        # point_on_line(self.x, self.y, self.away_goal.x + self.away_goal.width // 2,
        #               self.away_goal.y + self.away_goal.height // 2, p.x, p.y)]
        if isinstance(other, Player) and distance < 50 and self.in_possession \
                and not self.is_path_clear(self.away_goal, all_players):
            self.handle_collision()
        self.in_collision = other  # Assuming each player has a radius of 15
        return self.in_collision

    def resolve_collision(self, other):
        # Calculate the vector between the centers
        delta_x = other.x - self.x
        delta_y = other.y - self.y
        distance = math.sqrt(delta_x ** 2 + delta_y ** 2)

        # Calculate the overlap (amount by which they penetrate each other)
        overlap = 30 - distance  # 30 is the sum of the radii

        # Push the players away from each other by half of the overlap amount
        self.x -= (overlap / 2) * (delta_x / distance)
        self.y -= (overlap / 2) * (delta_y / distance)

        other.x += (overlap / 2) * (delta_x / distance)
        other.y += (overlap / 2) * (delta_y / distance)

    def handle_collision(self):
        self.collision_duration += 1

        if self.collision_duration > 5 and self.fatigue > 20 and self.in_possession:
            self.sprinting = True

    def move_towards(self, target_x, target_y):
        # Store current position as previous position
        self.previous_x = self.x
        self.previous_y = self.y
        self.rotation = math.degrees(math.atan2(target_y - self.y, target_x - self.x))

        delta_x = target_x - self.x
        delta_y = target_y - self.y
        distance = max(1, (delta_x ** 2 + delta_y ** 2) ** 0.5)
        delta_x /= distance
        delta_y /= distance

        if self.sprinting:
            # Use sprint speed when sprinting
            self.x += self.sprint_speed * delta_x
            self.y += self.sprint_speed * delta_y

            # Decrease fatigue when sprinting
            self.fatigue = max(0, self.fatigue - 0.5)
            if self.fatigue == 0:
                self.sprinting = False

        else:
            # Update the object's position
            self.x += self.speed * delta_x
            self.y += self.speed * delta_y

    def possess_ball(self, ball):
        if ball.possessed_by != self and ball.possessed_by is not None:
            self.play_around(ball.possessed_by, ball)
        if ball.possessed_by is None:
            ball.change_possession(to_player=self)
        else:
            ball.change_possession(to_player=self)

    def ball_in_reach(self, ball):
        distance = ((self.x - ball.x) ** 2 + (self.y - ball.y) ** 2) ** 0.5
        return distance < 25  # Assuming 15 (player radius) + 10 (ball radius) = 25

    def push_ball(self, ball):
        # Check for collision with ball
        if self.ball_in_reach(ball):
            # Calculate direction based on movement
            dx = self.x - self.previous_x
            dy = self.y - self.previous_y
            ball.set_velocity(dx, dy)

    def can_shoot(self, goal):
        # Calculate distance to the center of the goal
        if self.in_possession:
            distance_to_goal = ((self.x - goal.x) ** 2 + (self.y - (goal.y + goal.height / 2)) ** 2) ** 0.5
            return distance_to_goal <= self.stats.kick_range
        return False

    def shoot(self, goal):
        # Get direction to the goal center
        direction_x = (goal.x + goal.width / 2) - self.x
        direction_y = (goal.y + goal.height / 2) - self.y

        # Introduce dispersion
        dispersion_angle = random.uniform(-self.stats.kick_dispersion, self.stats.kick_dispersion)
        cos_angle = math.cos(math.radians(dispersion_angle))
        sin_angle = math.sin(math.radians(dispersion_angle))

        new_direction_x = direction_x * cos_angle - direction_y * sin_angle
        new_direction_y = direction_x * sin_angle + direction_y * cos_angle

        # Normalize direction for a fixed shooting speed (e.g., 7 units/frame)
        distance = (new_direction_x ** 2 + new_direction_y ** 2) ** 0.5
        new_direction_x /= distance
        new_direction_y /= distance

        # Update ball's position with the shot direction
        # This is a simple implementation; in reality, you might want to add acceleration, deceleration, etc.
        return new_direction_x * 7, new_direction_y * 7

    def direction_to_avoid_obstacle(self, obstruction):
        """
        Determine whether the player should move above or below the obstructing player to avoid them.
        Return 'above' or 'below' based on the best direction to move.
        """
        if player.y < obstruction.y:
            return "above"
        else:
            return "below"

    def navigate_around_obstacle(self, obstruction):
        """
        Update the player's position to move around the obstructing player.
        """
        direction = self.direction_to_avoid_obstacle(obstruction)
        if direction == "above":
            target_y = obstruction.y - 30  # Move 30 units above the obstruction
        else:
            target_y = obstruction.y + 30  # Move 30 units below the obstruction

        self.move_towards(self.x, target_y)  # Move vertically to avoid the obstruction

    def is_path_clear(self, target, all_players):
        """
        Check if the path between player and goal is clear of other players.
        """
        for other_player in all_players:
            if other_player == self:
                continue
            if point_on_line(self.x, self.y, target.x, target.y, other_player.x, other_player.y):
                return False  # Path is obstructed
        return True  # Path is clear

    def should_shoot_at_goal(self):
        # Use conditions to decide if a shot should be taken
        return self.is_path_clear(self.away_goal, all_players) and self.can_shoot(self.away_goal)

    def should_pass_ball(self, other_players):
        # Use conditions to decide if a pass should be made
        teammate = self.find_teammate_in_direction(self.goal_direction(), other_players)
        return teammate is not None

    def should_dribble_around(self):
        # Use conditions to decide if dribbling around is a good idea
        # This is just a placeholder, you'd want more sophisticated logic here
        return self.in_collision

    def pass_ball(self, ball, all_player):
        # Logic to pass the ball to a teammate
        teammate = self.find_teammate_in_direction(self.goal_direction(), all_players)

    def dribble_around(self, ball):
        # Logic to dribble around an obstacle or opponent
        # This will involve moving the player and the ball
        return

    def goal_direction(self):
        # Return a normalized vector pointing towards the goal
        goal_dir = (self.away_goal.x - self.x, self.away_goal.y - self.y)
        magnitude = math.sqrt(goal_dir[0] ** 2 + goal_dir[1] ** 2)
        return (goal_dir[0] / magnitude, goal_dir[1] / magnitude)

    def find_teammate_in_direction(self, direction, players, max_distance=200):
        # Find nearest teammate in the given direction
        nearest_teammate = None
        min_distance = max_distance

        for player in players:
            if player == self or player.color == self.color:  # Check if it's a different teammate
                continue

            dx = player.x - self.x
            dy = player.y - self.y
            distance = math.sqrt(dx ** 2 + dy ** 2)

            # Check if player is in the desired direction
            dot_product = dx * direction[0] + dy * direction[1]

            if dot_product > 0 and distance < min_distance:
                nearest_teammate = player
                min_distance = distance

        return nearest_teammate

    def play_around(self, other, ball):
        # Determine the attacking direction (based on the previous position)
        attack_dir = (self.previous_x - self.x, self.previous_y - self.y)

        # Normalize this direction for unit length
        magnitude = math.sqrt(attack_dir[0] ** 2 + attack_dir[1] ** 2)
        if magnitude == 0:
            magnitude = 1  # To avoid division by zero
        attack_dir = (attack_dir[0] / magnitude, attack_dir[1] / magnitude)

        # Compute a perpendicular direction to the attacking direction
        # This gives two potential directions: clockwise (cw) and counterclockwise (ccw)
        perp_dir_cw = (-attack_dir[1], attack_dir[0])
        perp_dir_ccw = (attack_dir[1], -attack_dir[0])

        # Check which side of the defending player is more open
        # We do this by adding a bit of distance in both directions and seeing which one is further from the defending player
        test_distance = 25  # This can be adjusted based on your requirements
        pos_cw = (self.x + test_distance * perp_dir_cw[0], self.y + test_distance * perp_dir_cw[1])
        pos_ccw = (self.x + test_distance * perp_dir_ccw[0], self.y + test_distance * perp_dir_ccw[1])

        dist_cw = math.sqrt((pos_cw[0] - other.x) ** 2 + (pos_cw[1] - other.y) ** 2)
        dist_ccw = math.sqrt((pos_ccw[0] - other.x) ** 2 + (pos_ccw[1] - other.y) ** 2)

        # Pick the direction that's further from the defending player
        if dist_cw > dist_ccw:
            bypass_dir = perp_dir_cw
        else:
            bypass_dir = perp_dir_ccw

        # Check for a teammate in the direction of the goal
        goal_dir = (self.away_goal.x - self.x, self.away_goal.y - self.y)
        magnitude = math.sqrt(goal_dir[0] ** 2 + goal_dir[1] ** 2)
        goal_dir = (goal_dir[0] / magnitude, goal_dir[1] / magnitude)

        # teammate = self.find_teammate_in_direction(goal_dir, all_players)
        teammate = False

        if teammate:
            # Pass the ball to the teammate
            pass_dir = (teammate.x - self.x, teammate.y - self.y)
            magnitude = math.sqrt(pass_dir[0] ** 2 + pass_dir[1] ** 2)
            pass_dir = (pass_dir[0] / magnitude, pass_dir[1] / magnitude)

            ball_speed = 7  # Adjust as needed
            dx = ball_speed * pass_dir[0]
            dy = ball_speed * pass_dir[1]
        else:
            # Push the ball in the bypass direction and move to retrieve it
            ball_push_distance = 15  # Adjust based on how far you want the ball to be pushed
            dx = ball_push_distance * bypass_dir[0]
            dy = ball_push_distance * bypass_dir[1]
            self.x += self.speed * bypass_dir[0] * 4
            self.y += self.speed * bypass_dir[1] * 4

        ball.set_velocity(dx, dy)

    def decision_making(self, ball, other_players):
        #
        # # Decision-making for the player with the ball
        # obstructions_for_shooting = [p for p in other_players if p != self and
        #                              point_on_line(self.x, self.y, self.away_goal.x + self.away_goal.width // 2,
        #                                            self.away_goal.y + self.away_goal.height // 2, p.x, p.y)]
        #
        # if not self.ball_in_reach(ball):
        #     self.move_towards(ball.x, ball.y)
        # else:
        #     self.push_ball(ball)
        #
        # if obstructions_for_shooting:  # Check if we have any obstructions
        #     # Navigate around the first obstruction in the list
        #     self.navigate_around_obstacle(obstructions_for_shooting[0])
        #
        # else:
        #     if self.is_path_clear(self.away_goal, other_players) and self.can_shoot(self.away_goal):
        #         # If path is clear and player is in shooting range
        #         dx, dy = self.shoot(self.away_goal)
        #         ball.x += dx
        #         ball.y += dy
        #     elif self.in_collision:
        #         dx, dy = self.shoot(self.away_goal)
        #         ball.x += dx
        #         ball.y += dy

        obstructions = [p for p in other_players if p != self and
                        point_on_line(self.x, self.y, self.away_goal.x + self.away_goal.width // 2,
                                      self.away_goal.y + self.away_goal.height // 2, p.x, p.y)]

        if ball.possessed_by is None:
            self.sprinting = True
        else:
            self.sprinting = False

        if not self.ball_in_reach(ball):
            self.move_towards(ball.x, ball.y)
            return
        elif self.ball_in_reach(ball):
            self.possess_ball(ball)
            return
        else:
            if obstructions:
                self.navigate_around_obstacle(obstructions[0])
                self.push_ball(ball)
            elif self.should_shoot_at_goal():
                self.push_ball(ball)
                dx, dy = self.shoot(self.away_goal)
                ball.set_velocity(dx, dy)
                ball.change_possession(from_player=self, to_player=None)
            elif self.should_pass_ball(other_players) and self.in_possession:
                self.push_ball(ball)
                self.pass_ball(ball, all_players)
            elif self.is_path_clear(self.away_goal, other_players):
                self.move_towards(self.away_goal.x, self.away_goal.y)
                self.push_ball(ball)
            elif not self.is_path_clear(self.away_goal, other_players) and self.in_collision:
                self.play_around(self.in_collision_with, ball)

            elif self.should_dribble_around():
                self.dribble_around(ball)


class Ball:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.dx = 0
        self.dy = 0
        self.possessed_by: Player or None = None
        self.friction = 0.92
        self.possession_cooldown = 0

    def draw(self, screen):
        pygame.draw.circle(screen, WHITE, (self.x, self.y), 10)
        spot_offsets = [(-6, -6), (6, -6), (-6, 6), (6, 6), (0, 0), (0, 7), (0, -7), (-7, 0), (7, 0)]
        for offset_x, offset_y in spot_offsets:
            pygame.draw.circle(screen, BLACK, (self.x + offset_x, self.y + offset_y), 2.5)

    def change_possession(self, from_player=None, to_player=None):
        if self.possession_cooldown > 0:
            return 
        if isinstance(from_player, Player):
            from_player.in_possession = False
        if isinstance(to_player, Player):
            to_player.in_possession = True
        self.possessed_by = to_player
        self.possession_cooldown += 3

    def update(self):
        self.possession_cooldown -= 1 if self.possession_cooldown > 0 else 0
        self.update_position()

    def update_position(self):
        self.x += self.dx
        self.y += self.dy

        self.dx *= self.friction
        self.dy *= self.friction

        if abs(self.dx) < 0.1:
            self.dx = 0
        if abs(self.dy) < 0.1:
            self.dy = 0

    def set_velocity(self, dx, dy):
        self.dx = dx
        self.dy = dy


goal_width = 100
goal_height = 150
home_goal = Goal(0, HEIGHT // 2 - goal_height // 2, goal_width, goal_height)
away_goal = Goal(WIDTH - goal_width, HEIGHT // 2 - goal_height // 2, goal_width, goal_height)

player = Player("Alena", WIDTH // 3, HEIGHT // 2, BLUE, goal_home=home_goal, goal_away=away_goal, rotation=0)
player2 = Player("Alek", 2 * WIDTH // 3, HEIGHT // 2, RED, goal_home=away_goal, goal_away=home_goal, rotation=180)
football = Ball(WIDTH // 2, HEIGHT // 2)
all_players = [player, player2]


def game_loop():
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill(GREEN)

        # Check for collisions, sufficient in small scale application
        check_and_resolve_collisions(all_players, football)
        football.update()

        football.draw(screen)
        home_goal.draw(screen)
        away_goal.draw(screen)

        for pl in all_players:
            pl.decision_making(football, all_players)
            pl.draw(screen, show_shooting_range=True)

        pygame.display.flip()
        time.sleep(0.1)


should_record = False

if should_record:
    recorder = ScreenRecorder(60)
    recorder.start_rec()
    try:
        game_loop()
    finally:
        recorder.stop_rec()  # stop recording
        recording = recorder.get_single_recording()  # returns a Recording
        recording.save(("my_recording", "mp4"))
        pygame.quit()
else:
    game_loop()
