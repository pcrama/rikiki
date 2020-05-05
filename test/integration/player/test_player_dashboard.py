from collections import OrderedDict
import time

import pytest  # type: ignore
from flask import url_for
from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.common.exceptions import NoSuchElementException  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
from selenium.webdriver.support import expected_conditions as EC  # type: ignore

from ..helper import ff_driver as driver
from ..helper import (
    element_has_css_class,
    organizer_secret,
    create_a_game,
    start_a_game,
    submit_form,
    temporary_new_tab,
)


def get_player_dashboard_elements(driver):
    return (
        driver.find_element_by_id('game_status'),
        driver.find_element_by_id('players'),
        driver.find_element_by_id('stats'),
        driver.find_element_by_id('cards'),
    )


def test_player_dashboard_while_bidding(driver, organizer_secret):
    players = start_a_game(driver, organizer_secret)
    first_player_id, (first_confirmed_name, first_player_url) = next(
        iter(players.items()))
    for dashboard_id, (dashboard_confirmed_name, dashboard_url) in players.items():
        driver.get(dashboard_url)
        # wait for player's dashboard to load game state
        WebDriverWait(driver, 2).until(EC.presence_of_element_located(
            (By.ID, first_player_id)))
        # Check all players are listed:
        for p_id, (p_confirmed_name, _) in players.items():
            p_li = driver.find_element_by_id(p_id)
            assert p_confirmed_name in p_li.text
            class_list = p_li.get_attribute('class').split()
            assert ('self_player' if p_id == dashboard_id else 'other_player'
                    ) in class_list
            assert ('other_player' if p_id == dashboard_id else 'self_player'
                    ) not in class_list
            if p_id == first_player_id:
                # first_player_id is current player: game/bidding has just begun
                assert 'current_player' in class_list
            else:
                assert 'current_player' not in class_list
        if dashboard_id == first_player_id:
            pass  # check that bidding UI is there
        else:
            pass  # check that bidding UI is not there


def test_player_dashboard_while_others_confirm(driver, organizer_secret):
    player_dict = create_a_game(driver, organizer_secret)
    player_unconfirmed_names = list(player_dict.keys())
    (player_unconfirmed_name, (player_id, player_confirmation_url)) = next(
        iter(player_dict.items()))
    driver.get(player_confirmation_url)
    submit_form(driver)
    (game_status, players_list, stats, cards) = get_player_dashboard_elements(driver)
    # confirmed player sees himself on page (loaded by AJAX) ...
    p_li = WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.ID, player_id)))
    # ... already correctly styled
    assert 'self_player' in p_li.get_attribute('class').split()
    assert player_unconfirmed_name in p_li.text
    # no other players are there yet
    assert len(players_list.find_elements_by_tag_name('li')) == 1
    assert stats.get_property('innerHTML').strip() == ''
    assert cards.get_property('innerHTML').strip() == ''
    # confirm another player
    some_other_player = player_unconfirmed_names[2]
    with temporary_new_tab(driver, player_dict[some_other_player][1]):
        submit_form(driver)
    # wait for first player's dashboard to show someone else joined
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.ID, player_dict[some_other_player][0])))
    # This assertion should be True earlier, but depends on an Ajax
    # call.  Rather that using time.sleep, I just check it a bit
    # later:
    assert 'wait' in game_status.text.lower()
    # ... but other players are not there yet
    for (p_name, (p_id, _)) in player_dict.items():
        if p_name in [player_unconfirmed_name, some_other_player]:
            p_li = driver.find_element_by_id(p_id)
            p_li_classes = p_li.get_attribute('class').split()
            assert p_li.text == p_name
            assert ('self_player'
                    if p_name == player_unconfirmed_name
                    else 'other_player') in p_li_classes
            assert ('other_player'
                    if p_name == player_unconfirmed_name
                    else 'self_player') not in p_li_classes
        else:
            with pytest.raises(NoSuchElementException):
                driver.find_element_by_id(p_id)
    # confirm yet another player
    yet_another_player = player_unconfirmed_names[1]
    with temporary_new_tab(driver, player_dict[yet_another_player][1]):
        submit_form(driver)
    # wait for first player's dashboard to show someone else joined
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.ID, player_dict[yet_another_player][0])))
    # ... but other players are not there yet
    for (p_name, (p_id, _)) in player_dict.items():
        if p_name in [player_unconfirmed_name, some_other_player, yet_another_player]:
            p_li = driver.find_element_by_id(p_id)
            p_li_classes = p_li.get_attribute('class').split()
            assert p_li.text == p_name
            assert ('self_player'
                    if p_name == player_unconfirmed_name
                    else 'other_player') in p_li_classes
            assert ('other_player'
                    if p_name == player_unconfirmed_name
                    else 'self_player') not in p_li_classes
        else:
            with pytest.raises(NoSuchElementException):
                driver.find_element_by_id(p_id)
