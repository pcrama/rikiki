from collections import OrderedDict
from contextlib import contextmanager

import pytest  # type: ignore
from flask import url_for
from selenium import webdriver  # type: ignore
from selenium.common.exceptions import NoSuchElementException  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.support import expected_conditions as EC  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore

INITIAL_PLAYER_NAMES = ['Attila', 'Hannibal', 'Chaos', 'Joker',
                        'Neil', 'Douglas', 'Terry']

# Fixture for Firefox
@pytest.fixture(scope='module')
def ff_driver():
    """Create a webdriver using Firefox."""
    from selenium.webdriver.firefox.options import Options  # type: ignore
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    yield driver
    driver.close()


@pytest.fixture
def organizer_secret(live_server):
    return live_server.app.organizer_secret


def extract_player_dict(driver):
    """Build OrderedDict mapping player names to their (id, url) tuples.

    The ordering is important as it represents the order in which the
    players will place their bids and play their cards.

    Assumes the page contains this structure:
      <ul id="player_list">
        {% for player in players %}
        <li id="{{ player.id }}"><span class="player_name">{{ player.name }}</span>: <span class="hostify">{{
            url_for('player.XXX', secret_id=player.secret_id, _method='GET')
            }}</span></li>
        {% endfor %}
      </ul>

    Returns OrderedDict mapping unconfirmed name to
    (player.id, player url) tuple.
    """
    player_list = driver.find_element_by_id('player_list')
    result = OrderedDict()
    for player_li in player_list.find_elements_by_tag_name('li'):
        player_name = player_li.find_element_by_class_name('player_name')
        secret_player_url = player_li.find_element_by_class_name('hostify')
        result[player_name.text] = (
            player_li.get_attribute('id'), secret_player_url.text)
    return result


def submit_form(driver):
    """Find and click the submit button."""
    submit = driver.find_element_by_xpath("//input[@type='submit']")
    submit.click()


@contextmanager
def temporary_new_tab(driver, url=None):
    """Execute in the context of a new tab.

    If url is not None, load it in the tab.

    See https://gist.github.com/lrhache/7686903#gistcomment-3081649
    """
    main_window = driver.current_window_handle
    driver.execute_script("window.open(''),'_blank'")
    tab_window = driver.window_handles[-1]
    driver.switch_to.window(tab_window)
    if url is not None:
        driver.get(url)
    yield (main_window, tab_window)
    driver.switch_to.window(tab_window)
    driver.close()
    driver.switch_to.window(main_window)


class element_has_css_class:
    """An expectation for checking that an element has a particular css class.

    locator - used to find the element
    returns the WebElement once it has the particular css class

    From https://selenium-python.readthedocs.io/waits.html
    """

    def __init__(self, locator, css_class):
        self.locator = locator
        self.css_class = css_class

    def __call__(self, driver):
        # Finding the referenced element
        element = driver.find_element(*self.locator)
        if self.css_class in element.get_attribute("class").split(' '):
            return element
        else:
            return False


def create_a_game(driver, organizer_secret):
    """Create players and a game.

    Returns extract_player_dict's output.
    """
    driver.get(url_for('organizer.setup_game',
                       organizer_secret=organizer_secret,
                       _external=True))
    playerlist = driver.find_element_by_id('playerlist')
    # fill in player list
    playerlist.send_keys('\n'.join(INITIAL_PLAYER_NAMES))
    submit_form(driver)
    return extract_player_dict(driver)


def start_a_game(driver, organizer_secret):
    """Create players, confirm them and start a game.

    Returns an OrderedDict (to keep player order) mapping Player.id to
    confirmed name & URL:
    {'1_aabbccdd': ['confirmed_name',
                    'https://example.com/player/player/<secret_id>'],
     '4_00112233': ['confirmed_name',
                    'https://example.com/player/player/<secret_id>']}
    """
    player_dict = create_a_game(driver, organizer_secret)
    # submission takes us to waiting page with players and their secret links
    players_in_memory = OrderedDict()
    for (unconfirmed_name, suffix) in [(INITIAL_PLAYER_NAMES[0],
                                        ' the Nun" onload="alert("test")'),
                                       (INITIAL_PLAYER_NAMES[2], '</html>'),
                                       (INITIAL_PLAYER_NAMES[1],
                                        ' the <Cannibal>'),
                                       (INITIAL_PLAYER_NAMES[3], ' I & I')]:
        player_link = player_dict[unconfirmed_name][1]
        with temporary_new_tab(driver, player_link):
            name_input = driver.find_element_by_id('player_name')
            name_input.send_keys(suffix)
            submit_form(driver)
        players_in_memory[unconfirmed_name] = unconfirmed_name + suffix
    submit_form(driver)
    result = {}
    # Check that we are in the right state:
    # 1. On the right page
    assert driver.current_url.endswith(
        url_for('organizer.dashboard', organizer_secret=organizer_secret))
    for player, player_info in player_dict.items():
        # player = unconfirmed name
        # player_info = (player.id, player url)
        # players_in_memory = { unconfirmed_name: confirmed_name }
        if player in players_in_memory:
            # 2. All players that confirmed are there, extract their confirmed name and url
            result[player_info[0]] = (
                driver.find_element_by_id(
                    f'{player_info[0]}-name').text,
                driver.find_element_by_id(player_info[0]).find_element_by_class_name('hostify').text)
        else:
            # 3. All players that did not confirm are absent
            with pytest.raises(NoSuchElementException):
                driver.find_element_by_id(player_info[0])
    # Wait for current player to be marked
    WebDriverWait(driver, 2).until(
        EC.presence_of_element_located((By.CLASS_NAME, "current_player")))
    return result


def start_a_game_and_bid(driver, organizer_secret):
    players = start_a_game(driver, organizer_secret)
    for idx, (dashboard_id, (dashboard_confirmed_name, dashboard_url)) \
            in enumerate(players.items()):
        driver.get(dashboard_url)
        # wait for player's dashboard to load game state
        WebDriverWait(driver, 2).until(EC.presence_of_element_located(
            (By.ID, dashboard_id)))
        # place bid for player
        bid_input = driver.find_element_by_id('bidInput')
        bid_submit = driver.find_element_by_id('bidSubmit')
        bid_input.click()
        bid_input.clear()
        bid_input.send_keys(str(idx % 4))
        bid_submit.click()
    return players
