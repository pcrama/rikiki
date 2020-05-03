// my deployment choice (repl.it for playing in family circle) means
// I am not too sure about what host my server will run on.  So I
// prepend it dynamically to the URL:
function hostifyUrls(_) {
    const urlPrefix = document.location.origin;
    Array.from(document.getElementsByClassName("hostify")).forEach((item, index, array) => {
        if (!item.innerHTML.startsWith(urlPrefix)) {
            item.innerHTML = urlPrefix + item.innerHTML;
        }
    });
}

const GAME_STATE_CONFIRMING = 0;

function gameStateName(x) {
    switch (x) {
    case GAME_STATE_CONFIRMING: return "Confirming";
    case 1: return "Playing";
    case 2: return "Paused between rounds";
    case 3: return "Done";
    default: return "Error!  script.js and Game.State are out of sync."
    }
}

function roundStateName(x) {
    switch (x) {
    case 100: return "Bidding";
    case 101: return "Playing";
    case 102: return "Done";
    default: return "Error!  script.js and Round.State are out of sync."
    }
}

function clearElement(elt) {
    while (elt.firstChild) {
        elt.removeChild(elt.firstChild);
    }
    return elt;
}

let updateTimer = null;

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
            li.children[0].textContent = data.players[p];
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
    const currentPlayerClass = 'current_player'; // css class defined in style.css
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
        gameStateSpan.textContent = gameStateName(data.state) + (cardCount ? ` with ${cardCount} cards, ${totalBids} tricks bid so far`:'');
    }
    updateTimer = setTimeout(updateGameStatusOrganizerDashboard, 1000 /* milliseconds */, statusUrl);
    return updateTimer;
}

async function updatePlayerDashboard(statusUrl) {
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
    const gameState = data.game.state;
    const selfId = data.id;
    const otherPlayers = data.players;
    const gameStatusElt = document.getElementById('game_status');
    const otherPlayersElt = document.getElementById('other_players');
    const cardsElt = document.getElementById('cards');
    const statsElt = document.getElementById('stats');
    console.log(`${data}\ngameState=${gameState} GAME_STATE_CONFIRMING=${GAME_STATE_CONFIRMING}`);
    if (gameState == GAME_STATE_CONFIRMING) {
        console.log(gameStatusElt);
        gameStatusElt.textContent = 'Waiting for other players to join and organizer to start the game';
        clearElement(statsElt);
        clearElement(cardsElt);
        clearElement(otherPlayersElt);
        otherPlayers.forEach(({id: p_id, name: p_name}) => {
            let newLi = document.createElement('li');
            newLi.textContent = p_name;
            newLi.classList.add('player_name');
            newLi.classList.add(p_id == selfId ? 'self_player' : 'other_player');
            newLi.id = p_id;
            otherPlayersElt.append(newLi);
        });
    } else {
        const round = data.round;
        const currentPlayer = round && round.currentPlayer;
        const roundState = round && round.state;
        const currentPlayerClass = 'current_player'; // css class defined in style.css
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
        if (gameStatusSpan) {
            const cardCount = data.currentCardCount;
            gameStatusSpan.textContent = gameStateName(data.state) + (cardCount ? ` with ${cardCount} cards, ${totalBids} tricks bid so far`:'');
        }
    }
    updateTimer = setTimeout(updatePlayerDashboard, 1000 /* milliseconds */, statusUrl);
    return updateTimer;
}
