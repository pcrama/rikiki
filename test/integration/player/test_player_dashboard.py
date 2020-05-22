import pytest  # type: ignore
from flask import url_for
from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.common.exceptions import NoSuchElementException  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
from selenium.webdriver.support import expected_conditions as EC  # type: ignore

import app.models as models

from ..helper import ff_driver as driver
from ..helper import (
    element_has_css_class,
    organizer_secret,
    create_a_game,
    start_a_game,
    start_a_game_and_bid,
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


def while_playing(driver, organizer_secret):
    players = start_a_game_and_bid(driver, organizer_secret)
    expected_table = []
    total_card_count = 0  # count how many cards have been dealt
    for dashboard_id, (dashboard_confirmed_name, dashboard_url) in players.items():
        driver.get(dashboard_url)
        # wait for player's dashboard to load game state
        WebDriverWait(driver, 2).until(EC.presence_of_element_located(
            (By.ID, dashboard_id)))
        playable_card = WebDriverWait(driver, 2).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, '.playable_card')))
        total_card_count += len(driver.find_element_by_id(
            'cards').find_elements_by_tag_name('img'))
        played_card_id = playable_card.get_attribute('id')
        playable_card.click()
        total_card_count -= 1
        # make sure the played cards appear in the 'table' display
        table_elt = driver.find_element_by_id('table')
        expected_table.append(played_card_id)
        for c in expected_table:
            WebDriverWait(driver, 2).until(EC.presence_of_element_located(
                (By.XPATH, f'//div[@id="table"]/span[@id="{c}"]')))
        # but table only contains those cards
        assert len(table_elt.find_elements_by_tag_name('img')
                   ) == len(expected_table)
        # no errors
        assert driver.find_elements_by_css_selector('.error') == []
    trick_winner_id = WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, '.current_player'))).get_attribute('id')
    trick_winner_name, trick_winner_url = players[trick_winner_id]
    assert trick_winner_name in driver.find_element_by_id('game_status').text
    driver.get(trick_winner_url)
    playable_card = WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, '.playable_card')))
    played_card_id = playable_card.get_attribute('id')
    playable_card.click()
    total_card_count -= 1
    # make sure the played cards appear in the 'table' display
    table_elt = driver.find_element_by_id('table')
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.XPATH, f'//div[@id="table"]/span[@id="{played_card_id}"]')))
    # but table only contains those cards
    assert len(table_elt.find_elements_by_tag_name('img')) == 1
    # no errors
    assert driver.find_elements_by_css_selector('.error') == []
    # finish the round
    while total_card_count > 0:
        next_player_id = WebDriverWait(driver, 2).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, '.current_player'))).get_attribute('id')
        next_player_name, next_player_url = players[next_player_id]
        driver.get(next_player_url)
        playable_card = WebDriverWait(driver, 2).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, '.playable_card')))
        played_card_id = playable_card.get_attribute('id')
        playable_card.click()
        total_card_count -= 1
        # make sure the played card appears in the 'table' display
        WebDriverWait(driver, 2).until(EC.presence_of_element_located(
            (By.XPATH, f'//div[@id="table"]/span[@id="{played_card_id}"]')))
        # and no errors are displayed
        assert driver.find_elements_by_css_selector('.error') == []
    finish_round_elt = WebDriverWait(driver, 2).until(
        EC.presence_of_element_located((By.ID, 'finishRound')))
    finish_round_button = finish_round_elt.find_element_by_id(
        'finishRoundSubmit')
    finish_round_button.click()
    # Wait for player to get new cards for next round
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.XPATH, f'//div[@id="cards"]//img')))
    # in second round, there must always be a trump card
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.XPATH, f'//div[@id="trump"]//img')))


def while_bidding(driver, organizer_secret):
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
        for id_ in ('bidInput', 'bidSubmit'):
            bid_elt = driver.find_element_by_id(id_)
            if dashboard_id == first_player_id:
                assert bid_elt.is_displayed()
            else:
                assert not bid_elt.is_displayed()
    # Return to first player to actually place a bid
    driver.get(first_player_url)
    # wait for player's dashboard to load game state
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.ID, first_player_id)))
    # place bid for first player
    bid_input = driver.find_element_by_id('bidInput')
    assert bid_input.get_attribute('min') == '0'
    assert bid_input.get_attribute('max') == str(
        models.MAX_CARDS // len(players))
    assert bid_input.get_attribute('required')
    bid_input.click()
    bid_input.clear()
    bid_input.send_keys('4')
    bid_submit = driver.find_element_by_id('bidSubmit')
    bid_submit.click()
    second_player_id, (_name, second_player_url) = list(players.items())[1]
    # player dashboard must update with next current_player, ...
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.XPATH,
         f'//li[@id="{second_player_id}" and ' +
         'contains(concat(" ",normalize-space(@class)," ")," current_player ")]')))
    # ... bidding UI must disappear, ...
    for id_ in ('bidInput', 'bidSubmit'):
        bid_elt = driver.find_element_by_id(id_)
    # ... bid must be visible
    assert 'bid for 4 tricks' in driver.find_element_by_id(
        first_player_id).text.lower()
    # check second player is allowed to bid:
    driver.get(second_player_url)
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.ID, second_player_id)))
    # second player sees first player's bid
    p_li = driver.find_element_by_id(first_player_id)
    assert 'current_player' not in p_li.get_attribute('class').split()
    assert 'bid for 4 tricks' in p_li.text.lower()
    for id_ in ('bidInput', 'bidSubmit'):
        bid_elt = driver.find_element_by_id(id_)
        assert bid_elt.is_displayed()
    # ... and can place a valid bid
    bid_input = driver.find_element_by_id('bidInput')
    assert bid_input.get_attribute('min') == '0'
    assert bid_input.get_attribute('max') == str(
        models.MAX_CARDS // len(players))
    assert bid_input.get_attribute('required')
    bid_input.click()
    bid_input.clear()
    bid_input.send_keys('5')
    bid_submit = driver.find_element_by_id('bidSubmit')
    bid_submit.click()
    third_player_id, (_name, third_player_url) = list(players.items())[1]
    # player dashboard must update with next current_player:
    p_li = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
        (By.XPATH,
         f'//li[@id="{third_player_id}" and ' +
         'contains(concat(" ",normalize-space(@class)," ")," current_player ")]')))
    assert 'not bid' in p_li.text
    p_li = WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.XPATH,
         f'//li[@id="{second_player_id}" and ' +
         'not(contains(concat(" ",normalize-space(@class)," ")," current_player "))]')))
    assert ' 5 ' in p_li.text
    # bid numbers are updated/correct
    # this is a race between JS in browser to copy information from
    # server into page and selenium:
    # assert ' 4 ' in driver.find_element_by_id(first_player_id).text
    # assert ' 5 ' in driver.find_element_by_id(second_player_id).text
    # assert ' 9 ' in driver.find_element_by_id('game_status').text


def while_others_confirm(driver, organizer_secret):
    player_dict = create_a_game(driver, organizer_secret)
    player_unconfirmed_names = list(player_dict.keys())
    # confirm last player in the list first, to check that player list
    # remains in order of player_dict even if players do not confirm
    # in that order.
    player_unconfirmed_name = player_unconfirmed_names[-1]
    player_id, player_confirmation_url = player_dict[player_unconfirmed_name]
    confirmed_ids = []  # is sorted by order of confirmation
    driver.get(player_confirmation_url)
    submit_form(driver)
    confirmed_ids.append(player_id)
    (game_status, players_list, stats, cards) = get_player_dashboard_elements(driver)
    # confirmed player sees himself on page (loaded by AJAX) ...
    p_li = WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.ID, player_id)))
    assert 'wait' in game_status.text.lower()
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
    confirmed_ids.append(player_dict[some_other_player][0])
    # wait for first player's dashboard to show someone else joined
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.ID, player_dict[some_other_player][0])))
    # player's list order should match organizer's order, not
    # chronological confirmation order:
    confirmed_ids_sorted_by_player_dict = [
        p_id for p_id, _ in player_dict.values() if p_id in confirmed_ids]
    confirmed_ids_sorted_by_appearance_on_page = [
        p_li.get_attribute('id') for p_li in players_list.find_elements_by_tag_name('li')]
    assert confirmed_ids_sorted_by_appearance_on_page == confirmed_ids_sorted_by_player_dict
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
    for id_ in ('bidInput', 'bidSubmit'):
        bid_elt = driver.find_element_by_id(id_)
        assert not bid_elt.is_displayed()
    # confirm yet another player
    yet_another_player = player_unconfirmed_names[1]
    with temporary_new_tab(driver, player_dict[yet_another_player][1]):
        submit_form(driver)
    confirmed_ids.append(player_dict[yet_another_player][0])
    # wait for first player's dashboard to show someone else joined
    WebDriverWait(driver, 2).until(EC.presence_of_element_located(
        (By.ID, player_dict[yet_another_player][0])))
    # player's list order should match organizer's order, not
    # chronological confirmation order:
    confirmed_ids_sorted_by_player_dict = [
        p_id for p_id, _ in player_dict.values() if p_id in confirmed_ids]
    confirmed_ids_sorted_by_appearance_on_page = [
        p_li.get_attribute('id') for p_li in players_list.find_elements_by_tag_name('li')]
    assert confirmed_ids_sorted_by_appearance_on_page == confirmed_ids_sorted_by_player_dict
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
