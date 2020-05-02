from contextlib import contextmanager

import pytest  # type: ignore
from selenium import webdriver  # type: ignore

# Fixture for Firefox
@pytest.fixture(scope="module")
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
    """Build dictionary mapping player names to their (id, url) tuples.

    Assumes the page contains this structure:
      <ul id="player_list">
        {% for player in players %}
        <li id="{{ player.id }}"><span class="player_name">{{ player.name }}</span>: <span class="hostify">{{
            url_for('player.XXX', secret_id=player.secret_id, _method='GET')
            }}</span></li>
        {% endfor %}
      </ul>
    """
    player_list = driver.find_element_by_id('player_list')
    result = {}
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
