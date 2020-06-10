from collections import OrderedDict

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
    KEEP_EXISTING_SESSION,
    element_has_css_class,
    organizer_secret,
    create_a_game,
    start_a_game,
    submit_form,
    temporary_new_tab,
    temporary_session,
)


def restore_player(driver):
    """Navigate to & confirm player's restore link, return new Player URL.

    The Player to operate on is implicit in the cookies set in the
    driver.
    """
    driver.get(url_for('player.restore_link', _external=True))
    # make sure we are not on an error page
    driver.find_element_by_id('submit_restore')
    submit_form(driver)
    return driver.current_url


def while_others_confirm(driver, organizer_secret):
    player_dict = create_a_game(driver, organizer_secret)
    player_unconfirmed_names = list(player_dict.keys())
    (player_unconfirmed_name, (player_id, player_confirmation_url)) = next(
        iter(player_dict.items()))
    driver.get(player_confirmation_url)
    submit_form(driver)
    old_player_url = driver.current_url
    with temporary_session(driver, session=KEEP_EXISTING_SESSION) as \
            first_player_session_info:
        first_player_url = restore_player(driver)
    assert first_player_url != old_player_url
    nav_title = driver.find_element_by_tag_name('nav').text
    assert player_unconfirmed_name in nav_title
    second_player_id, second_player_confirmation_url = player_dict[
        player_unconfirmed_names[1]]
    with temporary_session(driver,
                           session=None,
                           url=second_player_confirmation_url) as second_player_session_info:
        submit_form(driver)
        second_player_url = driver.current_url
    driver.get(url_for('organizer.wait_for_users',
                       _external=True,
                       organizer_secret=organizer_secret))
    # organizer dashboard is updated
    WebDriverWait(driver, 5).until(EC.presence_of_element_located(
        (By.XPATH, f"//span[text()='{first_player_url}']")))
    WebDriverWait(driver, 5).until(EC.presence_of_element_located(
        (By.XPATH, f"//span[text()='{second_player_url}']")))
    # Second player can restore:
    with temporary_session(driver,
                           session=second_player_session_info['after']):
        with temporary_new_tab(driver):
            new_second_player_url = restore_player(driver)
    # organizer dashboard is updated:
    WebDriverWait(driver, 5).until(EC.presence_of_element_located(
        (By.XPATH, f"//span[text()='{new_second_player_url}']")))
    # First player can restore again:
    with temporary_session(driver,
                           session=first_player_session_info['after']):
        with temporary_new_tab(driver):
            new_first_player_url = restore_player(driver)
    # organizer dashboard is updated
    WebDriverWait(driver, 5).until(EC.presence_of_element_located(
        (By.XPATH, f"//span[text()='{new_first_player_url}']")))


def while_bidding(driver, organizer_secret):
    players = start_a_game(driver, organizer_secret)
    organizer_url = driver.current_url
    with temporary_new_tab(driver):
        # new URL for last player to confirm:
        new_player_url = restore_player(driver)
    url_span = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
        (By.XPATH, f"//span[text()='{new_player_url}']")))
    player_id = url_span.get_property('parentNode').get_attribute('id')
    _, old_player_url = players[player_id]
    driver.get(old_player_url)
    assert 'forbidden' in driver.find_element_by_tag_name('nav').text.lower()
    driver.get(new_player_url)
    while True:
        cards = [i.get_attribute('src')
                 for i in driver.find_elements_by_tag_name('img')]
        if (len(cards) + 1) * len(players) >= 52:
            break
    # restoring player's link ...
    with temporary_new_tab(driver):
        newer_player_url = restore_player(driver)
    # ... will invalidate his current dashboard ...
    assert 'forbidden' in WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".error"))
    ).text.lower()
    # ... but the new dashboard will contain the same cards:
    driver.get(newer_player_url)
    while True:
        newer_cards = [i.get_attribute('src')
                       for i in driver.find_elements_by_tag_name('img')]
        if len(newer_cards) >= len(cards):
            break
    assert cards == newer_cards
    # organizer's dashboard sees newest URL for player
    driver.get(organizer_url)
    u = [e.find_elements_by_css_selector('.hostify')
         for e in driver.find_elements_by_id(player_id)]
    assert driver.find_element_by_id(player_id).find_element_by_css_selector(
        '.hostify').text == newer_player_url
