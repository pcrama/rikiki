import pytest  # type: ignore

import app  # type: ignore


@pytest.fixture(scope='module')
def client():
    # Heavily simplified from
    # https://flask.palletsprojects.com/en/1.1.x/testing/
    #
    # db_fd, flaskr.app.config['DATABASE'] = tempfile.mkstemp()
    # flaskr.app.config['TESTING'] = True

    with app.create_app('testing').test_client() as client:
        # with flaskr.app.app_context():
        #     flaskr.init_db()
        yield client

    # os.close(db_fd)
    # os.unlink(flaskr.app.config['DATABASE'])


def rendered_template(response, t):
    marker = {
        'organizer': b'!!organizer!-810856715183258229!!'
    }[t]
    return marker in response.data


def test_organizer_get_with_wrong_secret(client):
    response = client.get('/organizer/wrong_secret', follow_redirects=True)
    assert response.status_code == 403


def test_organizer_get_without_secret(client):
    response = client.get('/organizer/')
    assert response.status_code == 403
    response = client.get('/organizer', follow_redirects=True)
    assert response.status_code == 403


def test_organizer_get_with_secret(client):
    response = client.get(
        f'/organizer/{app.ORGANIZER_SECRET}', follow_redirects=True)
    assert response.status_code == 200
    assert rendered_template(response, 'organizer')
    response = client.get(f'/organizer/{app.ORGANIZER_SECRET}/')
    assert response.status_code == 200


def test_organizer_post_with_secret_without_data(client):
    response = client.post(
        f'/organizer/', data={'organizer_secret': app.ORGANIZER_SECRET})
    assert response.status_code == 200
    assert rendered_template(response, 'organizer')
    assert b"No player list provided" in response.data
