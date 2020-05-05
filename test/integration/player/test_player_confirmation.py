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
    element_has_css_class,
    organizer_secret,
    create_a_game,
    submit_form,
    temporary_new_tab,
)


def get_player_dashboard_elements(driver):
    return (
        driver.find_element_by_id('game_status'),
        driver.find_element_by_id('other_players'),
        driver.find_element_by_id('stats'),
        driver.find_element_by_id('cards'),
    )


def happy_path(driver, organizer_secret):
    player_dict = create_a_game(driver, organizer_secret)
    player_unconfirmed_names = list(player_dict.keys())
    (player_unconfirmed_name, (player_id, player_confirmation_url)) = next(
        iter(player_dict.items()))
    driver.get(player_confirmation_url)
    name = driver.find_element_by_id('player_name')
    # validate that name field is focused by sending keys to the
    # top-level <body> element.  If the keys are registered in the
    # confirmed name after the form submission, the text input field
    # had focus.
    extra_input = 'abcDEF'
    driver.find_element_by_tag_name('body').send_keys(extra_input)
    submit_form(driver)
    nav_title = driver.find_element_by_tag_name('nav').text
    assert any(s in nav_title
               # For me, the extra input may go either at the start or
               # the end of the unconfirmed name
               for s in (f'{extra_input}{player_unconfirmed_name}',
                         f'{player_unconfirmed_name}{extra_input}'))
