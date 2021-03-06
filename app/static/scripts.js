// my deployment choice (repl.it for playing in family circle) means
// I am not too sure about what host my server will run on.  So I
// prepend it dynamically to the URL:
function prependHostName(relativeOrAbsoluteUrl) {
    const urlPrefix = document.location.origin;
    return relativeOrAbsoluteUrl.startsWith(urlPrefix)
        ? relativeOrAbsoluteUrl
        : urlPrefix + relativeOrAbsoluteUrl;
}

function hostifyUrls(_) {
    Array.from(document.getElementsByClassName("hostify")).forEach((item, index, array) => {
        let newUrl = prependHostName(item.textContent);
        if (newUrl != item.textContent) {
            item.textContent = newUrl;
            item.onclick = function() { copyEventTargetText(this) };
        }
    });
}


function copyEventTargetText(target) {
    navigator.clipboard.writeText(
        (target.classList.contains('hostify')
         ? target.textContent
         : target.parentNode.textContent)
            .trim().replace(/\n/g, ' '));
}

const GAME_STATE_CONFIRMING = 0;


function gameStateName(x) {
    switch (x) {
    case GAME_STATE_CONFIRMING: return "Confirming";
    case 1: return "Playing";
    case 2: return "Paused between rounds";
    case 3: return "Done";
    default: return `Error!  scripts.js and Game.State are out of sync: ${x} is unknown.`;
    }
}


const ROUND_STATE_BIDDING = 100;
const ROUND_STATE_PLAYING = 101;
const ROUND_STATE_BETWEEN_TRICKS = 102;
const ROUND_STATE_DONE = 103;

function roundStateName(x) {
    switch (x) {
    case ROUND_STATE_BIDDING: return "Bidding";
    case ROUND_STATE_PLAYING: return "Playing";
    case ROUND_STATE_BETWEEN_TRICKS: return "Playing"; // a little white lie
    case ROUND_STATE_DONE: return "Done";
    default: return `Error!  scripts.js and Round.State are out of sync: ${x} is unknown.`;
    }
}


function clearElement(elt) {
    if (elt == null) {
        return elt; // silently ignore null or undefined
    }
    while (elt.firstChild) {
        elt.removeChild(elt.firstChild);
    }
    return elt;
}

let updateTimer = null;

const currentPlayerClass = 'current_player'; // css class defined in style.css


async function updatePlayerStatusForOrganizer(statusUrl) {
    let delay = 1000 /* milliseconds */;
    let response = null;
    try {
        response = await fetch(statusUrl, {
            method: 'GET',
            mode: 'cors',
            cache: 'no-cache',
            credentials: 'same-origin',
            redirect: 'follow'});
    } catch {
        delay *= 3;
    }
    updateTimer = setTimeout(updatePlayerStatusForOrganizer, delay, statusUrl);
    if (null == response) {
        return updateTimer;
    }
    if (!response.ok) {
        const nav = document.getElementsByTagName('nav');
        if (nav) {
            nav[0].innerHTML = `<h1 class="error">Server error</h1>`;
            nav[0].children[0].textContent += `: ${response.status}, ${response.statusText}`;
        }
        Array.from(document.getElementsByTagName('input')).forEach((item, _index, _array) => {
            item.disabled = true;
        });
        clearTimeout(updateTimer);
        return -1;
    }
    const data = await response.json();
    const classToRemove = 'unconfirmed_player';
    for (p in data.players) {
        const li = document.getElementById(p);
        if (li) {
            li.classList.remove(classToRemove);
            li.classList.add('confirmed_player');
            li.children[0].textContent = data.players[p].name;
            li.children[1].textContent = prependHostName(data.players[p].url);
        }
    }
    return updateTimer;
}


async function updateGameStatusOrganizerDashboard(statusUrl) {
    let delay = 1000 /* milliseconds */;
    let response = null;
    try {
        response = await fetch(statusUrl, {
            method: 'GET',
            mode: 'cors',
            cache: 'no-cache',
            credentials: 'same-origin',
            redirect: 'follow'});
    } catch {
        delay *= 3;
    }
    updateTimer = setTimeout(updateGameStatusOrganizerDashboard, delay, statusUrl);
    if (null == response) {
        return updateTimer;
    }
    if (!response.ok) {
        const nav = document.getElementsByTagName('nav');
        if (nav) {
            nav[0].innerHTML = `<h1 class="error">Server error</h1>`;
            nav[0].children[0].textContent += `: ${response.status}, ${response.statusText}`;
        }
        clearTimeout(updateTimer);
        return -1;
    }
    const data = await response.json();
    const round = data.round;
    const currentPlayer = round && round.currentPlayer;
    const roundState = round && round.state;
    let totalBids = 0;
    for (pid in data.players) {
        const li = document.getElementById(pid);
        if (li) {
            if (pid == currentPlayer && !li.classList.contains(currentPlayerClass)) {
                li.classList.add(currentPlayerClass);
            } else if (pid != currentPlayer && li.classList.contains(currentPlayerClass)) {
                li.classList.remove('current_player');
            }
            const playerLink = li.getElementsByClassName('hostify');
            console.log(playerLink);
            if (playerLink) {
                playerLink[0].textContent = prependHostName(data.players[pid].url);
            }
        }
        const cardsSpan = document.getElementById(`${pid}-cards`);
        const bidSpan = document.getElementById(`${pid}-bid`);
        const player = data.players[pid];
        totalBids += player.bid || 0;
        if (cardsSpan) {
            cardsSpan.textContent = player.cards;
        }
        if (bidSpan) {
            bidSpan.textContent = player.bid || 0;
        }
    }
    const gameStateSpan = document.getElementById('game-state');
    if (gameStateSpan) {
        const cardCount = data.currentCardCount;
        gameStateSpan.textContent = gameStateName(data.game_state)
            + (cardCount ? ` with ${cardCount} cards, ${totalBids} tricks bid so far`:'')
            + (roundState ? `.  Players are ${roundStateName(roundState)}`:'')
            + '.';
    }
    return updateTimer;
}


function fillPlayerDashboardPlayerList(players, selfId, playersElt, callback) {
    clearElement(playersElt);
    if (!players) {
        return;
    }

    players.forEach(player => {
        let {h: htmlToInsert} = player;
        playersElt.insertAdjacentHTML('beforeend', htmlToInsert);
    });
}

let lastGameStatusSummary = null;

function maybeJoin(url, trail) {
    if (!trail) {
        return url;
    }

    const leftPart = url.endsWith('/') ? url.slice(0, -1): url;
    const rightPart = trail.startsWith('/') ? trail.substring(1): trail;
    return leftPart + '/' + rightPart + (trail.endsWith('/') ? '' : '/');
}

function extractPlayerSecret(url) {
    const startMarker = '/player/';
    const secretLength = 32;
    const startIdx = url.indexOf(startMarker);
    if (startIdx < 0) {
        return '';
    }

    return url.substr(startIdx + startMarker.length, 32);
}

async function updatePlayerDashboard(statusUrl) {
    let delay = 1000 /* milliseconds */;
    let response = null;
    try {
        response = await fetch(maybeJoin(statusUrl, lastGameStatusSummary), {
            method: 'GET',
            mode: 'cors',
            cache: 'no-cache',
            credentials: 'same-origin',
            redirect: 'follow'});
    } catch {
        delay *= 3;
    }
    updateTimer = setTimeout(updatePlayerDashboard, delay, statusUrl);
    if (null == response) {
        return updateTimer;
    }
    if (!response.ok) {
        const nav = document.getElementsByTagName('nav');
        if (nav) {
            nav[0].innerHTML = `<h1 class="error">Server error</h1>`;
            nav[0].children[0].textContent += `: ${response.status}, ${response.statusText}`;
        }
        clearTimeout(updateTimer);
        return -1;
    }
    const data = await response.json();
    const newStatusSummary = data.summary;
    if (newStatusSummary && newStatusSummary != lastGameStatusSummary) {
        // change in status -> display update
        const gameState = data.game_state;
        const selfId = data.id;
        const players = data.players;
        const cards = data.cards;
        const trump = data.trump;
        const gameStatusElt = document.getElementById('game_status');
        const playersElt = document.getElementById('players');
        const cardsElt = document.getElementById('cards');
        const statsElt = document.getElementById('stats');
        const trumpElt = document.getElementById('trump');
        const round = data.round;
        const roundState = data.round && data.round.state;
        const currentPlayerId = data.round && data.round.current_player;
        clearElement(gameStatusElt);
        if (gameState) {
            gameStatusElt.insertAdjacentHTML('beforeend', gameState);
        }
        clearElement(cardsElt);
        if (cards) {
            cardsElt.insertAdjacentHTML('beforeend', cards);
            if (roundState == ROUND_STATE_PLAYING || roundState == ROUND_STATE_BETWEEN_TRICKS) {
                const secretId = extractPlayerSecret(statusUrl);
                const playableCards = data.playable_cards || [];
                for (let spanElt of cardsElt.getElementsByTagName('SPAN')) {
                    spanElt.className = 'playing_card';
                    if (playableCards.indexOf(spanElt.id) < 0) {
                        spanElt.classList.add('unplayable_card');
                        continue;
                    }
                    spanElt.classList.add('playable_card');
                    spanElt.onclick = async function playCard(e) {
                        e.preventDefault()
                        const playError = document.getElementById('playError');
                        clearElement(playError);
                        playError.classList.remove('error');
                        const playUrl = '/player/play/card/';
                        let formData = new FormData();
                        formData.append('secret_id', secretId);
                        formData.append('card', spanElt.id.substr(1));
                        let response;
                        try {
                            response = await fetch(playUrl, {
                                method: 'POST',
                                body: formData,
                                mode: 'cors',
                                cache: 'no-cache',
                                credentials: 'same-origin',
                                redirect: 'follow'});
                        } catch (e) {
                            playError.classList.add('error');
                            playError.textContent = `${e} Please retry/veuillez réessayer`;
                            return;
                        }
                        if (!response.ok) {
                            playError.classList.add('error');
                            playError.textContent = `${response.status}, ${response.statusText}`;
                            return;
                        }
                        const data = await response.json();
                        if (!data.ok) {
                            playError.classList.add('error');
                            playError.textContent = data.error;
                        }
                    };
                };
            }
        }
        fillPlayerDashboardPlayerList(players, selfId, playersElt);
        if (trump) {
            trumpElt.innerHTML = trump;
        } else {
            clearElement(trumpElt);
        }
        const tableElt = document.getElementById('table');
        clearElement(tableElt);
        if (roundState == ROUND_STATE_PLAYING
            || roundState == ROUND_STATE_BETWEEN_TRICKS
            || roundState == ROUND_STATE_DONE) {
            tableElt.insertAdjacentHTML('beforeend', data.table);
        }
        const bidElt = document.getElementById('bid');
        if (roundState == ROUND_STATE_BIDDING && currentPlayerId == selfId) {
            bidElt.onsubmit = submitBid;
            bidElt.style.display = "inline";
            const bidInput = document.getElementById('bidInput');
            bidInput.value = undefined;
            bidInput.max = document.getElementById('cards').childNodes.length;
        } else {
            bidElt.style.display = "none";
        }
    }
    lastGameStatusSummary = newStatusSummary;
    return updateTimer;
}

async function submitFinishRound(secretId) {
    const finishRoundError = document.getElementById('finishRoundError');
    clearElement(finishRoundError);
    finishRoundError.classList.remove('error');
    const finishRoundUrl = '/player/finish/round/';
    const formData = new FormData();
    formData.append('secret_id', secretId);
    let response;
    try {
        response = await fetch(finishRoundUrl, {
            method: 'POST',
            body: formData,
            mode: 'cors',
            cache: 'no-cache',
            credentials: 'same-origin',
            redirect: 'follow'});
    } catch (e) {
        finishRoundError.classList.add('error');
        finishRoundError.textContent = `${e} Please retry/veuillez réessayer`;
        return false;
    }
    if (!response.ok) {
        finishRoundError.classList.add('error');
        finishRoundError.textContent = `${response.status}, ${response.statusText}`;
        return false;
    }
    const data = await response.json();
    if (data.ok) {
        document.getElementById('finishRound').style.display = 'none';
    } else {
        finishRoundError.classList.add('error');
        finishRoundError.textContent = data.error;
    }
    return false;
}

async function submitBid(e) {
    e.preventDefault()
    const bidElt = e.target;
    const bidError = document.getElementById('bidError');
    clearElement(bidError);
    bidError.classList.remove('error');
    const bidUrl = '/player/place/bid/';
    let response;
    try {
        response = await fetch(bidUrl, {
            method: 'POST',
            body: new FormData(bidElt),
            mode: 'cors',
            cache: 'no-cache',
            credentials: 'same-origin',
            redirect: 'follow'});
    } catch (e) {
        bidError.classList.add('error');
        bidError.textContent = `${e} Please retry/veuillez réessayer`;
        return false;
    }        
    if (!response.ok) {
        bidError.classList.add('error');
        bidError.textContent = `${response.status}, ${response.statusText}`;
        return false;
    }
    const data = await response.json();
    if (data.ok) {
        bidElt.style.display = 'none';
    } else {
        bidError.classList.add('error');
        bidError.textContent = data.error;
    }
    return false;
}
