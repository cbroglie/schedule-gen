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
        self.cache = {}

    def init(self):
        """Setup the initial state based on the number of teams and weeks"""
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
            self.cache[team][self.get_num_unassigned_weeks.__name__] = False
            self.cache[team][self.get_num_potential_opponents.__name__] = False
            self.cache[team][self.get_num_away_games.__name__] = False
            self.cache[team][self.get_num_home_games.__name__] = False

    @memoize
    def get_num_unassigned_weeks(self, team):
        """Get the number of unassigned weeks for the given team"""
        return sum(1 if len(x) > 1 else 0 for x in self.teams[team])

    @memoize
    def get_num_potential_opponents(self, team):
        """Get the number of potential opponents remaining for the given team"""
        return len(self.get_potential_opponents(team))

    @memoize
    def get_num_home_games(self, team):
        """Get the number of home games for the given team"""
        return sum(1 if len(matchups) == 1 and matchups[0][0] == team else 0 for matchups in self.teams[team])

    @memoize
    def get_num_away_games(self, team):
        """Get the number of away games for the given team"""
        return self.num_weeks - self.get_num_unassigned_weeks(team) - self.get_num_home_games(team)

    def get_potential_opponents(self, team):
        """Get the list of potential oppoents remaining for the given team"""
        def concat_sets(a, b):
            return set(list(a) + list(b))
        opponents = reduce(concat_sets, [set(matchup)
                           for week in range(self.num_weeks)
                           for matchup in self.teams[team][week] if len(self.teams[team][week]) > 1], set())
        opponents = opponents - set([team])
        return list(opponents)

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
        # verify we only play opposing teams at most once.
        opponent_counts = {}
        for week in range(self.num_weeks):
            matchups = self.teams[team][week]
            if len(matchups) == 1:
                team2 = list(set(matchups[0]) - set([team]))[0]
                if len(self.teams[team2][week]) != 1:
                    return False
                if not set(self.teams[team2][week][0]) & set([team]):
                    return False
                if not team2 in opponent_counts:
                    opponent_counts[team2] = 0
                opponent_counts[team2] += 1
                if opponent_counts[team2] > 1:
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
                if len(self.teams[team][week]) == 1:
                    matchup = self.teams[team][week][0]
                    team2 = list(set(matchup) - set([team]))[0]
                    for week2 in range(self.num_weeks):
                        assert len(self.teams[team2][week2]) == 1
                        matchup2 = self.teams[team2][week2][0]
                        if week2 == week: 
                            if not set(matchup2) & set([team]):
                                print "Team %d is not in team %d's matchup for week %d, but team %d is in team %d's matchup week %d" % (team, team2, week2+1, team2, team, week+1)
                                assert False
                        else:
                            if set(matchup2) & set([team]):
                                print "Team %d is in team %d's matchup for week %d, but team %d is in team %d's matchup week %d" % (team, team2, week2+1, team2, team, week+1)
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
                        print "   %2d" % matchup[1],
                    else:
                        print "  @%2d" % matchup[0],
                else:
                    print "    !",
                if week == self.num_weeks - 1: print ""
