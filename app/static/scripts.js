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


function roundStateName(x) {
    switch (x) {
    case 100: return "Bidding";
    case 101: return "Playing";
    case 102: return "Done";
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
    const response = await fetch(statusUrl, {
            method: 'GET',
            mode: 'cors',
            cache: 'no-cache',
            credentials: 'same-origin',
            redirect: 'follow'});
    if (!response.ok) {
        const nav = document.getElementsByTagName('nav');
        if (nav) {
            nav[0].innerHTML = `<h1 class="error">Server error</h1>`;
            nav[0].children[0].textContent += `: ${response.status}, ${response.statusText}`;
        }
        Array.from(document.getElementsByTagName('input')).forEach((item, _index, _array) => {
            item.disabled = true;
        });
        return -1;
    }
    const data = await response.json();
    const classToRemove = 'unconfirmed_player';
    for (p in data.players) {
        const li = document.getElementById(p);
        if (li && li.classList.contains(classToRemove)) {
            li.classList.remove(classToRemove);
            li.classList.add('confirmed_player');
            li.children[0].textContent = data.players[p].name;
            li.children[1].textContent = prependHostName(data.players[p].url);
        }
    }
    updateTimer = setTimeout(updatePlayerStatusForOrganizer, 1000 /* milliseconds */, statusUrl);
    return updateTimer;
}


async function updateGameStatusOrganizerDashboard(statusUrl) {
    const response = await fetch(statusUrl, {
            method: 'GET',
            mode: 'cors',
            cache: 'no-cache',
            credentials: 'same-origin',
            redirect: 'follow'});
    if (!response.ok) {
        const nav = document.getElementsByTagName('nav');
        if (nav) {
            nav[0].innerHTML = `<h1 class="error">Server error</h1>`;
            nav[0].children[0].textContent += `: ${response.status}, ${response.statusText}`;
        }
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
    updateTimer = setTimeout(updateGameStatusOrganizerDashboard, 1000 /* milliseconds */, statusUrl);
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
    return leftPart + '/' + rightPart;
}

async function updatePlayerDashboard(statusUrl) {
    const response = await fetch(maybeJoin(statusUrl, lastGameStatusSummary + '/'), {
        method: 'GET',
        mode: 'cors',
        cache: 'no-cache',
        credentials: 'same-origin',
        redirect: 'follow'});
    if (!response.ok) {
        const nav = document.getElementsByTagName('nav');
        if (nav) {
            nav[0].innerHTML = `<h1 class="error">Server error</h1>`;
            nav[0].children[0].textContent += `: ${response.status}, ${response.statusText}`;
        }
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
        clearElement(gameStatusElt);
        if (gameState) {
            gameStatusElt.insertAdjacentHTML('beforeend', gameState);
        }
        clearElement(cardsElt);
        if (cards) {
            cardsElt.insertAdjacentHTML('beforeend', cards);
        }
        fillPlayerDashboardPlayerList(players, selfId, playersElt);
        if (trump) {
            trumpElt.innerHTML = trump;
        } else {
            clearElement(trumpElt);
        }
    }
    lastGameStatusSummary = newStatusSummary;
    updateTimer = setTimeout(updatePlayerDashboard, 1000 /* milliseconds */, statusUrl);
    return updateTimer;
}
