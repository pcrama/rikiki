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
    INITIAL_PLAYER_NAMES,
    extract_player_dict,
    element_has_css_class,
    organizer_secret,
    start_a_game,
    submit_form,
    temporary_new_tab,
)


def define_players(driver, organizer_secret):
    driver.get(url_for('organizer.wait_for_users',
                       organizer_secret=organizer_secret,
                       _external=True))
    # redirected to organizer.setup_game ...
    assert url_for('organizer.setup_game',
                   organizer_secret=organizer_secret,
                   _method='GET'
                   ) in driver.current_url
    # ... and error displayed
    error_msg = driver.find_element_by_class_name('error')
    assert "Game not initialized" in error_msg.text
    # form is loaded immediately as page is loaded, so no WebDriverWait.
    playerlist = driver.find_element_by_id('playerlist')
    assert playerlist.tag_name == 'textarea'
    # fill in player list
    playerlist.send_keys('\n'.join(INITIAL_PLAYER_NAMES))
    submit_form(driver)
    # submission takes us to waiting page ...
    assert driver.current_url.endswith(url_for('organizer.wait_for_users',
                                               organizer_secret=organizer_secret))
    # ... without errors ...
    with pytest.raises(NoSuchElementException):
        driver.find_element_by_class_name("error")
    with pytest.raises(NoSuchElementException):
        driver.find_element_by_class_name("flash")
    # ... game is created ...  For some reason, there seem to be 2 app
    # instances, one in each of 2 processes.  This makes the assertion
    # fail, because the controllers in process 1 start the game, but
    # the game in process 2 is not started.  How I don't get into
    # trouble with organizer_secret mismatches is a mistery to me
    # (maybe because it is serializable and stored in the
    # app.config?).  See also https://stackoverflow.com/a/9476701 and
    # ~use_reloader=False~ for how I could maybe get around this.  For
    # now, I will just test the app by looking only at the end-user
    # observable state.
    #
    # assert live_server.app.game is not None
    #
    # ... and player list is displayed with their links
    player_dict = extract_player_dict(driver)
    assert len(player_dict) == len(INITIAL_PLAYER_NAMES)
    assert all(
        initial_name in player_dict for initial_name in INITIAL_PLAYER_NAMES)
    # Players start out unconfirmed
    for p in player_dict.values():
        p_li = driver.find_element_by_id(p[0])
        classes = p_li.get_attribute('class').split(' ')
        assert 'confirmed_player' not in classes
        assert 'unconfirmed_player' in classes
    # Players (their interface is tested elsewhere) may confirm their
    # participation, altering their names (in any order, not even all
    # of them).  As the participants confirm their presence, the
    # organizer's view is updated.
    players_in_memory = {}
    for (unconfirmed_name, suffix) in [(INITIAL_PLAYER_NAMES[0],
                                        ' the Nun" onload="alert("test");'),
                                       (INITIAL_PLAYER_NAMES[2], '</html>'),
                                       (INITIAL_PLAYER_NAMES[1],
                                        ' the <Cannibal>'),
                                       (INITIAL_PLAYER_NAMES[3], ' I & I')]:
        player_link = player_dict[unconfirmed_name][1]
        with temporary_new_tab(driver, player_link):
            name_input = driver.find_element_by_id('player_name')
            name_input.send_keys(suffix)
            submit_form(driver)
        # allow javascript polling to discover change & update page
        WebDriverWait(driver, 2).until(element_has_css_class(
            (By.ID, player_dict[unconfirmed_name][0]),
            'confirmed_player'))
        # track which players we confirmed so far, so that we can
        # validate that the displayed styles and names are updated:
        players_in_memory[unconfirmed_name] = unconfirmed_name + suffix
        for p in INITIAL_PLAYER_NAMES:
            p_li = driver.find_element_by_id(player_dict[p][0])
            classes = p_li.get_attribute('class').split(' ')
            # CSS class matches status of the player
            assert ('confirmed_player' if p in players_in_memory else 'unconfirmed_player'
                    ) in classes
            assert ('unconfirmed_player' if p in players_in_memory else 'confirmed_player'
                    ) not in classes
            # name matches current state (i.e. updates are seen, but old names remain untouched)
            assert p_li.find_element_by_class_name('player_name').text == \
                players_in_memory.get(p, p)
            # link is updated for confirmed players, the same for unconfirmed players
            player_link = p_li.find_element_by_class_name('hostify').text
            if p in players_in_memory:
                assert player_link != player_dict[p][1]
            else:
                assert player_link == player_dict[p][1]
    submit_form(driver)
    assert driver.current_url.endswith(
        url_for('organizer.dashboard', organizer_secret=organizer_secret))


def dashboard(driver, organizer_secret):
    player_dict = start_a_game(driver, organizer_secret)
    player_ids = list(player_dict.keys())
    # without errors:
    with pytest.raises(NoSuchElementException):
        driver.find_element_by_class_name("error")
    with pytest.raises(NoSuchElementException):
        driver.find_element_by_class_name("flash")
    # It is the first Player's turn, all other players are styled normally
    for (idx, p_id) in enumerate(player_ids):
        p_li = driver.find_element_by_id(p_id)
        p_li_classes = p_li.get_attribute('class').split(' ')
        if idx == 0:
            assert 'current_player' in p_li_classes
        else:
            assert 'current_player' not in p_li_classes
    # TODO: make each player bid in turn and observe the progress of
    # current_player CSS class.
