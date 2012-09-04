import copy
from functools import wraps
import pdb
import random

def memoize(f):
    fname = f.__name__
    disable = False

    @wraps(f)
    def memoizedFunction(self, team, *args):
        #print "in memoize %r" % fname,
        #if disable: 
        #    print "...dirty"
        #    return f(self, team, *args)
        #pdb.set_trace()
        if not team in self.cache:
            self.cache[team] = {}
        if not fname in self.cache[team]:
            self.cache[team][fname] = False
        if not self.cache[team][fname]:
            self.cache[team][fname] = {}
        if not args in self.cache[team][fname]:     
            self.cache[team][fname][args] = f(self, team, *args)
        #    print "...dirty"
        #else:
        #    print "...cached"
        return self.cache[team][fname][args]
    return memoizedFunction

class Schedule:
    def __init__(self):
        self.num_weeks = 1
        self.num_teams = 2
        self.num_divisions = 1
        self.min_division_matchups = 1
        self.max_division_matchups = 1
        self.max_non_division_matchups = 1
        self.min_weeks_between_matchups = 1
        self.cache = {}

    def init(self):
        """Setup the initial state based on the number of teams and weeks"""
        assert self.num_teams % self.num_divisions == 0

        # Generate the list of teams from 1-num_teams.
        teams = [i + 1 for i in range(self.num_teams)]

        # Genaerate all the possible matchups between teams.
        matchups = self.generate_matchups(teams)
        assert len(matchups) == self.num_teams * (self.num_teams - 1)
        assert all(a != b for a, b in matchups)

        # Generate a dictionary of team to possible matchups involving the team.
        team_matchups = dict((i, [matchups[j]
                             for j in range(len(matchups)) if set([i]) & set(matchups[j])])
                             for i in teams)
        assert all(len(team_matchups[i]) == (self.num_teams - 1) * 2
                   for i in team_matchups)
        assert all(set(team_matchups[i][j]) & set([i])
                   for j in range(len(team_matchups[i]))
                   for i in team_matchups)

        # Generate the initial schedule which is a dictionary of team to possible
        # matchups for each week.
        self.teams = dict((i, [self.randomize_matchups(team_matchups[i]) for _ in range(self.num_weeks)])
                          for i in teams)

    def initFromFile(self, filename):
        self.teams = {}
        def not_empty(value):
            return value != ""
        inputFile = file(filename)
        tokens = filter(not_empty, inputFile.readline().strip().split(" "))
        num_weeks = int(tokens[len(tokens) - 1])
        assert num_weeks == self.num_weeks

        tokens = filter(not_empty, inputFile.readline().strip().split(" "))
        while len(tokens) > 0:
            assert len(tokens) == num_weeks + 1
            team = int(tokens.pop(0))
            self.teams[team] = []
            for token in tokens:
                home = token[0] != "@"
                if home:
                    self.teams[team].append([(team, int(token))])
                else:
                    self.teams[team].append([(int(token[1:]), team)])
            tokens = filter(not_empty, inputFile.readline().strip().split(" "))

    def randomize_matchups(self, matchups):
        matchups = copy.copy(matchups)
        random.shuffle(matchups)
        return matchups

    def generate_matchups(self, teams):
        return [(a, b) for a in teams for b in teams if a != b]

    def remove_matchup(self, team, week, matchup):
        """Remove a possible matchup for the given team and week"""
        self.teams[team][week].remove(matchup)
        # If the number of matchups for a week becomes 1, it means that matchup
        # has been assigned. Invalidate any cached results for the team.
        if len(self.teams[team][week]) == 1:
            if not team in self.cache:
                self.cache[team] = {}
            # NOTE: it would be safest to clear everything here, but not
            # everything we cache needs to be recalculated. So we only cache
            # bust explicit functions.
            self.cache[team][self.get_num_unassigned_weeks.__name__] = False
            self.cache[team][self.get_num_potential_opponents.__name__] = False
            self.cache[team][self.get_num_away_games.__name__] = False
            self.cache[team][self.get_num_home_games.__name__] = False
            self.cache[team][self.get_num_matchups.__name__] = False
            self.cache[team][self.get_num_division_games.__name__] = False
            self.cache[team][self.get_num_non_division_games.__name__] = False

    @memoize
    def get_num_unassigned_weeks(self, team):
        """Get the number of unassigned weeks for the given team"""
        return sum(1 if len(x) > 1 else 0 for x in self.teams[team])

    @memoize
    def get_num_potential_opponents(self, team):
        """Get the number of potential opponents remaining for the given team"""
        max_remaining = {}
        num_opponents = 0
        for team2 in self.teams:
            if team2 == team:
                continue
            num_matchups = self.get_num_matchups(team, team2)
            max_matchups = self.get_matchup_max(team, team2)
            max_remaining[team2] = (max_matchups - num_matchups)
        for week in range(self.num_weeks):
            if len(self.teams[team][week]) == 1:
                continue
            opponents_for_week = set()
            for matchup in self.teams[team][week]:
                team2 = list(set(matchup) - set([team]))[0]
                if team2 in opponents_for_week:
                    continue # Only count opponent once per week max
                if team2 in max_remaining and max_remaining[team2] > 0:
                    max_remaining[team2] -= 1
                    num_opponents += 1
                    opponents_for_week |= set([team2])
        return num_opponents

    @memoize
    def get_num_home_games(self, team):
        """Get the number of home games for the given team"""
        return sum(1 if len(matchups) == 1 and matchups[0][0] == team else 0 for matchups in self.teams[team])

    @memoize
    def get_num_away_games(self, team):
        """Get the number of away games for the given team"""
        return self.num_weeks - self.get_num_unassigned_weeks(team) - self.get_num_home_games(team)

    @memoize
    def get_division(self, team):
        """Return the division for a given team"""
        return int((team + self.num_divisions - 1) / self.num_divisions) + 1 # Number starting at 1

    @memoize
    def same_division(self, team, team2):
        """Check whether 2 teams are in the same division"""
        return self.get_division(team) == self.get_division(team2)

    @memoize
    def get_matchup_max(self, team, team2):
        """Get the maximum amount of times 2 teams can matchup"""
        if self.same_division(team, team2):
            return self.max_division_matchups
        else:
            return self.max_non_division_matchups

    @memoize
    def get_matchup_min(self, team, team2):
        """Get the minimum amount of times 2 teams must matchup"""
        if self.same_division(team, team2):
            return self.min_division_matchups
        else:
            return 0 # Currently there is no supported min for non-division opponents

    @memoize
    def get_num_matchups(self, team, team2):
        """Get the number of matchups between 2 teams"""
        return sum(1 if len(matchups) == 1 and set(matchups[0]) & set([team2]) else 0 for matchups in self.teams[team])

    @memoize
    def get_num_division_games(self, team):
        """Get the number of divisional games for the given team"""
        return sum(1 if len(matchups) == 1 and self.same_division(matchups[0][0], matchups[0][1]) else 0 for matchups in self.teams[team])

    @memoize
    def get_num_non_division_games(self, team):
        """Get the number of non-divisional games for the given team"""
        return self.num_weeks - self.get_num_unassigned_weeks(team) - self.get_num_division_games(team)

    def valid(self, team):
        # Check that we can still fill the remaining weeks after this assignment.
        remaining_opponent_count = self.get_num_potential_opponents(team)
        remaining_weeks = self.get_num_unassigned_weeks(team)
        if remaining_opponent_count < remaining_weeks:
            return False
        # Check that we don't have too many home or away games.
        if self.get_num_home_games(team) > ((self.num_weeks + 1) & ~0x1) / 2:
            return False
        # Check that we don't have too many home or away games.
        if self.get_num_away_games(team) > ((self.num_weeks + 1) & ~0x1) / 2:
            return False
        # For each matchup we are part of ensure the opposing team agrees, and
        # verify we only play the opposing team the correct amount of times.
        matchup_weeks = {}
        for week in range(self.num_weeks):
            matchups = self.teams[team][week]
            if len(matchups) == 0:
                return False
            elif len(matchups) == 1:
                team2 = list(set(matchups[0]) - set([team]))[0]
                if len(self.teams[team2][week]) != 1:
                    return False
                if not set(self.teams[team2][week][0]) & set([team]):
                    return False
                if not team2 in matchup_weeks:
                    matchup_weeks[team2] = []
                matchup_weeks[team2].append(week)
                if len(matchup_weeks[team2]) > self.get_matchup_max(team, team2):
                    return False
        # If we have filled every week, we must also check matchup minimums.
        if remaining_weeks == 0:
            for team2 in self.teams:
                if team2 == team:
                    continue
                min_matchups = self.get_matchup_min(team, team2)
                if min_matchups > 0 and (team2 not in matchup_weeks or len(matchup_weeks[team2]) < min_matchups):
                    return False
        # Ensure we don't play a team twice within the matchup buffer.
        for team2 in matchup_weeks:
            for i in range(len(matchup_weeks[team2]) - 1):
                if abs(matchup_weeks[team2][i] - matchup_weeks[team2][i + 1]) < self.min_weeks_between_matchups:
                    return False
        return True

    def test(self):
        """A set of unit tests"""
        for team in self.teams:
            assert self.valid(team)
            for week in range(self.num_weeks):
                assert len(self.teams[team][week]) == 1
                assert self.get_num_home_games(team) + self.get_num_away_games(team) == self.num_weeks
                assert self.get_num_home_games(team) <= ((self.num_weeks + 1) & ~0x1) / 2
                assert self.get_num_away_games(team) <= ((self.num_weeks + 1) & ~0x1) / 2
                assert self.get_num_division_games(team) + self.get_num_non_division_games(team) == self.num_weeks
                matchup = self.teams[team][week][0]
                team2 = list(set(matchup) - set([team]))[0]
                num_matchups = self.get_num_matchups(team, team2)
                assert num_matchups >= self.get_matchup_min(team, team2)
                assert num_matchups <= self.get_matchup_max(team, team2)
                for week2 in range(self.num_weeks):
                    assert len(self.teams[team2][week2]) == 1
                    matchup2 = self.teams[team2][week2][0]
                    if week2 == week: 
                        if not set(matchup2) & set([team]):
                            print "Team %d is NOT in team %d's matchup for week %d, but team %d is in team %d's matchup week %d" % (team, team2, week2+1, team2, team, week+1)
                            assert False

    def display(self):
        """Display the schedule as a 2D grid."""
        print "Team",
        for week in range(self.num_weeks):
            print "   %2d" % (week + 1),
            if week == self.num_weeks - 1: print ""
        for team in sorted(self.teams.keys()):
            print "  %2d" % team,
            for week in range(self.num_weeks):
                if len(self.teams[team][week]) == 1:
                    matchup = self.teams[team][week][0]
                    if matchup[0] == team:
                        print "   %02d" % matchup[1],
                    else:
                        print "  @%02d" % matchup[0],
                else:
                    print "    !",
                if week == self.num_weeks - 1: print ""

    def csv(self):
        """Display the schedule in csv format."""
        print "Week,Home,Away"
        for week in range(self.num_weeks):
            for team in self.teams:
                matchup = self.teams[team][week][0]
                if matchup[0] == team:
                    print "%d,Team-%02d,Team-%02d" % (week + 1, matchup[0], matchup[1])