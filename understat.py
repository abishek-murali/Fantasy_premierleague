#!/usr/bin/python
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import pandas as pd
import re
import json
import datetime
from pandas.io.json import json_normalize
import os
import sys
import argparse


class ScrapeFootball:
    def __init__(self, league='La_liga', year='2018', team_xg=True, player_xg=True):
        self.base_url = 'https://understat.com/league/'
        self.league = league  # EPL, Bundeliga, Seria_A
        self.year = year
        # Flags to switch on and off extraction
        self.team_xg_inc = team_xg
        self.player_xg_inc = player_xg
        self.now = datetime.datetime.now()
        self.teams_xG_df = None
        self.players_xG_df = None
        self.matches_xG_df = None
        self.df_list = None

    def check_action(self):
        if not (self.team_xg_inc or self.player_xg_inc):
            return True
        else:
            return False

    def scrape_team_player_xg(self):
        scraping_url = self.base_url + self.league + '/' + self.year
        req = Request(scraping_url, headers={'User-Agent': 'Mozilla/5.0'})
        web_page = urlopen(req).read()
        soup = BeautifulSoup(web_page, 'html.parser')
        league_data = soup.find_all('script')  # retrieves list; contents of list: results, team table and player data

        # retrieves string between \\x5B and \\x5D which in ascii is open and close bracket
        pattern_bw_brackets = re.compile("(?<=\('\\\\x5B)(.*?)(?=\\\\x5D)") 
        # retrieves string between open and close braces (including braces)
        pattern_inc_braces = re.compile("(?<=')(\\\\x7B)(.*?)(\\\\x7D)(?=')")  

        if self.team_xg_inc:
            # scrape data for results
            data_results = pattern_bw_brackets.search(league_data[0].get_text().strip())
            ns = {}  # create new environment to execute script from string
            exec("import json;dummy=json.loads(json.dumps('[" + data_results.group() + "]'))", ns)
            teams_xG = json_normalize(json.loads(ns['dummy']))
            # scrape detailed analysis for team per game
            data_matches = pattern_inc_braces.search(league_data[1].get_text().strip())
            ns = {}
            exec("import json;dummy=json.loads(json.dumps('[" + data_matches.group() + "]'))", ns)
            dat = (json.loads(ns['dummy']))
            game_res = []
            for key, value in dat[0].items():
                game_res.append(value)
            df = json_normalize(game_res, ['history'], ['id', 'title'])
            matches_xG = json_normalize(df.to_dict('records')).copy()
            # define column order
            col_order_teams = ['h.title',
                               'a.title',
                               'datetime',
                               'goals.h',
                               'goals.a',
                               'xG.h',
                               'xG.a',
                               'forecast.w',
                               'forecast.l',
                               'forecast.d',
                               'h.id',
                               'a.id']
            col_order_matches = ['title',
                                 'date',
                                 'h_a',
                                 'xGA',
                                 'xpts',
                                 'npxG',
                                 'npxGA',
                                 'npxGD',
                                 'deep',
                                 'deep_allowed',
                                 'ppda.att',
                                 'ppda.def',
                                 'ppda_allowed.att',
                                 'ppda_allowed.def',
                                 'id']
            self.teams_xG_df = (teams_xG.loc[teams_xG['isResult'] == True, col_order_teams]
                                        .sort_values(['datetime'])).copy()
            self.matches_xG_df = (matches_xG.loc[:, col_order_matches]
                                            .sort_values('date')).copy()

        if self.player_xg_inc:
            data_players = pattern_bw_brackets.search(league_data[2].get_text().strip())
            ns = {}
            exec("import json;dummy=json.loads(json.dumps('[" + data_players.group() + "]'))", ns)
            self.players_xG_df = pd.DataFrame(json.loads(ns['dummy']))

        self.df_list = {'teams_xG_filtered': self.teams_xG_df,
                        'matches_xG_filtered': self.matches_xG_df,
                        'players_xG': self.players_xG_df}

    def write_to_excel(self):
        file_name = str(self.now.day) + '_' + str(self.now.month) + '_' + self.league.split('/')[0] + '_' + self.year
        writer = pd.ExcelWriter('{}_understat.xlsx'.format(file_name))
        for i, df in self.df_list.items():
            df.to_excel(writer, sheet_name='sheet{}'.format(i), index=False)
        writer.save()


def main(league, season, team, player):
    try:
        scraper = ScrapeFootball(league=league, year=season, team_xg=team, player_xg=player)  # initialize
        if scraper.check_action():  # check if at least one action is True
            raise IOError
        scraper.scrape_team_player_xg()  # scrape data
        scraper.write_to_excel()  # write to file
        print('Program complete. File written to {}'.format(os.getcwd()))
    except IOError:
        print('Both team and player xG flags were set to False. No action taken. Program complete.')
        return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scraping football data from understat.com")
    parser.add_argument("-l", "--league", help="Options:La_liga, Bundesliga, EPL, Seria_A, Ligue_1 and RFPL",
                        required=False, default="La_liga")
    parser.add_argument("-s", "--season", help="Range:2014 to 2018", required=False, default="2018")
    parser.add_argument("-t", "--team_xg", help="Option:True or False. Choose to retrieve team XG", required=False,
                        default=True)
    parser.add_argument("-p", "--player_xg", help="Option:True or False. Choose to retrieve player XG", required=False,
                        default=True)
    argument = parser.parse_args()
    status = False
    main(argument.league, argument.season, argument.team_xg, argument.player_xg)
