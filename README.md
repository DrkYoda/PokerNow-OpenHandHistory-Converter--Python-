# PokerNow-OpenHandHistory-Converter--Python-
WHAT THIS DOES

goal of this program is to process Poker Now (https://www.pokernow.club/) hand history csv files and
convert to JSON format that matches the standardized open hand History format specified by 
PokerTracker and documented here: https://hh-specs.handhistory.org/

To do this we will take the logs and break it up hand by hand

Then we can loop through each hand, and convert to the JSON format specified.
Finally, we output the new JSON.
