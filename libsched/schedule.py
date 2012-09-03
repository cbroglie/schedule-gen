import copy

class Schedule:
    def __init__(self):
        self.num_weeks = 1
        self.num_teams = 2

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
        self.teams = dict((i, [copy.copy(team_matchups[i]) for _ in range(self.num_weeks)])
                          for i in teams)

    def generate_matchups(self, teams):
        return [(a, b) for a in teams for b in teams if a != b]

    def remove_matchup(self, team, week, matchup):
        """Remove a possible matchup for the given team and week"""
        self.teams[team][week].remove(matchup)

    def get_num_unassigned_weeks(self, team):
        """Get the number of unassigned weeks for the given team"""
        return sum(1 if len(x) > 1 else 0 for x in self.teams[team])

    def get_num_potential_opponents(self, team):
        """Get the number of potential opponents remaining for the given team"""
        return len(self.get_potential_opponents(team))

    def get_potential_opponents(self, team):
        """Get the list of potential oppoents remaining for the given team"""
        def concat_sets(a, b):
            return set(list(a) + list(b))
        opponents = reduce(concat_sets, [set(matchup)
                           for week in range(self.num_weeks)
                           for matchup in self.teams[team][week] if len(self.teams[team][week]) > 1], set())
        opponents = opponents - set([team])
        return list(opponents)

    def test(self):
        """A set of unit tests"""
        # TODO: Ensure that if team a plays team b for week x in team a's
        # schedule, team b also thinks it is playing team a in week x.
        for team in self.teams:
            for week in range(self.num_weeks):
                assert len(self.teams[team][week]) > 0
                if len(self.teams[team][week]) == 1:
                    matchup = self.teams[team][week][0]
                    other_team = set(matchup) - set([team])
                    assert len(other_team) == 1
                    # Verify this team doesn't appear in the other team's schedule
                    # any other week.
                    assert all(not set(matchup2) & set([team])
                               for week2 in range(self.num_weeks) if week2 != week
                               for matchup2 in self.teams[list(other_team)[0]][week2])
                    # Verify the other team doesn't appear in this team's schedule
                    # any other week.
                    assert all(not set(matchup2) & other_team
                               for week2 in range(self.num_weeks) if week2 != week
                               for matchup2 in self.teams[team][week2])

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
