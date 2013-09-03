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
    LOG_LEVEL_NONE = 0
    LOG_LEVEL_ERROR = 1
    LOG_LEVEL_DEBUG = 2
    LOG_LEVEL_VERBOSE = 3

    def __init__(self):
        self.log_level = self.LOG_LEVEL_ERROR
        self.num_weeks = 1
        self.num_teams = 2
        self.num_divisions = 1
        self.min_division_matchups = 1
        self.max_division_matchups = 1
        self.min_non_division_matchups = 0
        self.max_non_division_matchups = 1
        self.min_weeks_between_matchups = 0
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

    def randomize_matchups(self, matchups):
        matchups = copy.copy(matchups)
        random.shuffle(matchups)
        divisionMatchups = []
        nonDivisionMatchups = []
        # Move the division matchups to the front so they are evaluated first.
        # This is an optimization that assumes the requirements for division
        # games are harder to meet than for non-divisional games.
        for matchup in matchups:
            if self.same_division(matchup[0], matchup[1]):
                divisionMatchups.append(matchup)
            else:
                nonDivisionMatchups.append(matchup)
        return divisionMatchups + nonDivisionMatchups

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
            self.cache[team][self.get_num_matchups.__name__] = False
            self.cache[team][self.get_num_division_games.__name__] = False
            self.cache[team][self.get_num_non_division_games.__name__] = False

    @memoize
    def get_other_teams(self, team):
        """Return the teams excluding the given team"""
        return [t for t in self.teams if t != team]

    @memoize
    def get_num_unassigned_weeks(self, team):
        """Get the number of unassigned weeks for the given team"""
        return sum(1 if len(x) > 1 else 0 for x in self.teams[team])

    @memoize
    def get_num_potential_opponents(self, team):
        """Get the number of potential opponents remaining for the given team"""
        numPotential = 0
        opponents = self.get_potential_opponents(team)
        for opponent in opponents:
            numMatchups = self.get_num_matchups(team, opponent)
            maxMatchups = self.get_matchup_max(team, opponent)
            numPotential += (maxMatchups - numMatchups)
        return numPotential

    @memoize
    def get_division(self, team):
        """Return the division for a given team"""
        num_teams_per_division = self.num_teams / self.num_divisions
        return int((team + num_teams_per_division - 1) / num_teams_per_division)

    @memoize
    def same_division(self, team, team2):
        """Check whether 2 teams are in the same division"""
        return self.get_division(team) == self.get_division(team2)

    @memoize
    def get_num_home_games(self, team):
        """Get the number of home games for the given team"""
        return sum(1 if len(matchups) == 1 and matchups[0][0] == team else 0 for matchups in self.teams[team])

    @memoize
    def get_num_away_games(self, team):
        """Get the number of away games for the given team"""
        return self.num_weeks - self.get_num_unassigned_weeks(team) - self.get_num_home_games(team)

    @memoize
    def get_matchup_min(self, team, team2):
        """Get the minimum amount of times 2 teams must matchup"""
        if self.same_division(team, team2):
            return self.min_division_matchups
        else:
            return self.min_non_division_matchups

    @memoize
    def get_matchup_max(self, team, team2):
        """Get the maximum amount of times 2 teams can matchup"""
        if self.same_division(team, team2):
            return self.max_division_matchups
        else:
            return self.max_non_division_matchups

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

    def get_potential_opponents(self, team):
        """Get the list of potential oppoents remaining for the given team"""
        def concat_sets(a, b):
            return set(list(a) + list(b))
        opponents = reduce(concat_sets, [set(matchup)
                           for week in range(self.num_weeks)
                           for matchup in self.teams[team][week] if len(self.teams[team][week]) > 1], set())
        opponents = opponents - set([team])
        return list(opponents)

    def error(self, format, *args):
        if self.log_level >= self.LOG_LEVEL_ERROR:
            self.log("[VERBOSE] " + format, *args)

    def verbose(self, format, *args):
        if self.log_level >= self.LOG_LEVEL_VERBOSE:
            self.log("[VERBOSE] " + format, *args)

    def debug(self, format, *args):
        if self.log_level >= self.LOG_LEVEL_DEBUG:
            self.log("[DEBUG] " + format, *args)

    def log(self, format, *args):
        if args:
            print format % args
        else:
            print format

    def valid(self, team):
        # Check that we can still fill the remaining weeks after this assignment.
        numPotentialOpponents = self.get_num_potential_opponents(team)
        remainingWeeks = self.get_num_unassigned_weeks(team)
        if numPotentialOpponents < remainingWeeks:
            self.debug("Backtracking b/c there are fewer potential opponents (%d) than weeks remaining (%d) for team %d", numPotentialOpponents, remainingWeeks, team)
            self.debug("opponents=%r", self.get_potential_opponents(team))
            return False
        # Check that we don't have too many home or away games.
        if self.get_num_home_games(team) > ((self.num_weeks + 1) & ~0x1) / 2:
            self.debug("Backtracking b/c we have too many home games for team %d", team)
            return False
        # Check that we don't have too many home or away games.
        if self.get_num_away_games(team) > ((self.num_weeks + 1) & ~0x1) / 2:
            self.debug("Backtracking b/c we have too many home games for team %d", team)
            return False
        # For each matchup we are part of ensure the opposing team agrees, and
        # verify we only play the opposing team the correct amount of times.
        teamMatchups = {}
        for week in range(self.num_weeks):
            matchups = self.teams[team][week]
            if len(matchups) == 0:
                self.debug("Backtracking b/c there are no possible matchups for week %d", week)
                return False
            elif len(matchups) == 1:
                team2 = list(set(matchups[0]) - set([team]))[0]
                if len(self.teams[team2][week]) != 1:
                    self.debug("Backtracking b/c of matchup inconsistency in week %d for teams %d and %d", week, team, team2)
                    return False
                if not set(self.teams[team2][week][0]) & set([team]):
                    self.debug("Backtracking b/c of matchup inconsistency in week %d for teams %d and %d", week, team, team2)
                    return False
                if not team2 in teamMatchups:
                    teamMatchups[team2] = []
                teamMatchups[team2].append(week)
                numMatchups = len(teamMatchups[team2])
                maxMatchups = self.get_matchup_max(team, team2);
                if numMatchups > maxMatchups:
                    self.debug("Backtracking b/c team %d plays team %d %d times which is greater than the max of %d", team, team2, numMatchups, maxMatchups)
                    return False
        # If we have filled every week, we must also check matchup minimums.
        if remainingWeeks == 0:
            for team2 in self.teams:
                if team2 == team:
                    continue
                numMatchups = len(teamMatchups[team2]) if team2 in teamMatchups else 0
                minMatchups = self.get_matchup_min(team, team2)
                if numMatchups < minMatchups:
                    self.debug("Backtracking b/c team %d plays team %d %d times which is less than the min of %d", team, team2, numMatchups, minMatchups)
                    return False
        # Ensure we don't play a team twice within the matchup buffer.
        for team2 in teamMatchups:
            for i in range(len(teamMatchups[team2]) - 1):
                numWeeksBetweenMatchups = abs(teamMatchups[team2][i] - teamMatchups[team2][i + 1])
                if numWeeksBetweenMatchups < self.min_weeks_between_matchups:
                    self.debug("Backtracking b/c team %d plays team %d %d weeks apart, which is less than the min of %d", team, team2, numWeeksBetweenMatchups, self.min_weeks_between_matchups)
                    return False
        return True

    def test(self):
        """A set of unit tests"""
        for team in self.teams:
            assert self.valid(team)
            assert self.get_num_home_games(team) + self.get_num_away_games(team) == self.num_weeks
            assert self.get_num_home_games(team) <= ((self.num_weeks + 1) & ~0x1) / 2
            assert self.get_num_away_games(team) <= ((self.num_weeks + 1) & ~0x1) / 2
            assert self.get_num_division_games(team) + self.get_num_non_division_games(team) == self.num_weeks
            # Assert that 2 teams play each other the right amount of times.
            for team2 in self.teams:
                if team != team2:
                    numMatchups = self.get_num_matchups(team, team2)
                    assert numMatchups >= self.get_matchup_min(team, team2)
                    assert numMatchups <= self.get_matchup_max(team, team2)
            # Validate each matchup.
            for week in range(self.num_weeks):
                assert len(self.teams[team][week]) == 1
                matchup = self.teams[team][week][0]
                team2 = list(set(matchup) - set([team]))[0]
                for week2 in range(self.num_weeks):
                    assert len(self.teams[team2][week2]) == 1
                    matchup2 = self.teams[team2][week2][0]
                    if week2 == week: 
                        if not set(matchup2) & set([team]):
                            self.error("Team %d is NOT in team %d's matchup for week %d, but team %d is in team %d's matchup week %d", team, team2, week2+1, team2, team, week+1)
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
