import copy
import pdb

NUM_TEAMS = 16
NUM_WEEKS = 15

def generate_matchups(teams):
    return [(a, b) for a in teams for b in teams if a != b]

def test_preconditions():
    """A set of unit tests for validating pre-conditions"""
    # TODO: Check if there is possible solution based on the inputs
    assert len(matchups) == NUM_TEAMS * (NUM_TEAMS - 1)
    assert all(a != b for a, b in matchups)
    assert all(len(team_matchups[i]) == (NUM_TEAMS - 1) * 2
               for i in team_matchups)
    assert all(set(team_matchups[i][j]) & set([i])
               for j in range(len(team_matchups[i]))
               for i in team_matchups)

def test_postconditions(schedule):
    """A set of unit tests for validating post-conditions"""
    for team in schedule:
        for week in range(NUM_WEEKS):
            assert len(schedule[team][week]) > 0
            if len(schedule[team][week]) == 1:
                matchup = schedule[team][week][0]
                other_team = set(matchup) - set([team])
                assert len(other_team) == 1
                # Verify this team doesn't appear in the other team's schedule
                # any other week.
                assert all(not set(matchup2) & set([team])
                           for week2 in range(NUM_WEEKS) if week2 != week
                           for matchup2 in schedule[list(other_team)[0]][week2])
                # Verify the other team doesn't appear in this team's schedule
                # any other week.
                assert all(not set(matchup2) & other_team
                           for week2 in range(NUM_WEEKS) if week2 != week
                           for matchup2 in schedule[team][week2])

def assign(schedule, week, matchup):
    """Eliminate all matchups other than the given one from the provided week,
    and propagate. Return the schedule, except return False if a contradiction
    is detected."""
    for team in matchup:
        if not all(eliminate(schedule, week, matchup2)
                   for matchup2 in copy.copy(schedule[team][week]) if matchup2 != matchup):
            return False
        # Can only play a team once, eliminate from other weeks.
        other_team = set(matchup) - set([team])
        if not all(eliminate(schedule, week2, matchup2)
                   for week2 in range(NUM_WEEKS) if week2 != week
                   for matchup2 in copy.copy(schedule[team][week2]) if set(matchup2) & other_team):
            return False
    return schedule

def eliminate(schedule, week, matchup):
    """Elimniate matchup from the given week. Propagate when possible. Return
    schedule, except return False if a contradiction is detected."""
    #print "Removing %r from week %d" % (matchup, week)
    for team in matchup:
        if matchup in schedule[team][week]:
            schedule[team][week].remove(matchup)
        else:
            continue

        # Contradiction: removed last value.
        if len(schedule[team][week]) == 0:
            return False

        # If a slot is reduced to one value, eliminate the value from its peers.
        if len(schedule[team][week]) == 1:
            matchup2 = schedule[team][week][0]
            #print "%r is the last matchup in week %d for team %d" % (matchup2, week, team)
            #pdb.set_trace()
            if not all(eliminate(schedule, week, matchup3)
                       for team2 in teams if not set([team2]) & set(matchup2)
                       for matchup3 in copy.copy(schedule[team2][week]) if set(matchup2) & set(matchup3)):
                return False
    return schedule

def search(schedule):
    """Using depth first search and propagation, try all possible values."""
    if schedule is False:
        return False # Already failed earlier
    if all(len(schedule[team][week]) == 1
           for team in teams
           for week in range(NUM_WEEKS)):
        return schedule # Solved
    # Choose the team and week with the fewest possibilities
    count, team, week = min((len(schedule[team][week]), team, week)
                            for team in teams
                            for week in range(NUM_WEEKS) if len(schedule[team][week]) > 1)
    return some(search(assign(copy.deepcopy(schedule), week, matchup))
                for matchup in schedule[team][week])

def some(seq):
    """Return some element of seq that is true."""
    for e in seq:
        if e: return e
    return False

def display(schedule):
    """Display the schedule as a 2D grid."""
    print "Team",
    for week in range(NUM_WEEKS):
        print "   %2d" % (week + 1),
        if week == NUM_WEEKS - 1: print ""
    for team in sorted(schedule.keys()):
        print "  %2d" % team,
        for week in range(NUM_WEEKS):
            if len(schedule[team][week]) == 1:
                matchup = schedule[team][week][0]
                if matchup[0] == team:
                    print "   %2d" % matchup[1],
                else:
                    print "  @%2d" % matchup[0],
            else:
                print "  !!!",
            if week == NUM_WEEKS - 1: print ""

# Generate the list of teams from 1-NUM_TEAMS.
teams = [i + 1 for i in range(NUM_TEAMS)]
# Genaerate all the possible matchups between teams.
matchups = generate_matchups(teams)
# Generate a dictionary of team to possible matchups involving the team.
team_matchups = dict((i, [matchups[j] for j in range(len(matchups)) if set([i]) & set(matchups[j])])
                    for i in teams)
# Generate the initial schedule which is a dictionary of team to possible
# matchups for each week.
init_schedule = dict((i, [copy.copy(team_matchups[i]) for _ in range(NUM_WEEKS)])
                    for i in teams)

test_preconditions()

final_schedule = search(init_schedule)
test_postconditions(final_schedule)
display(final_schedule)
