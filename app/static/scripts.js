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

let updateTimer = null;

async function updatePlayerStatus(statusUrl) {
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
    console.log(data)
    for (p in data.players) {
        const li = document.getElementById(p);
        console.log(`${p}: ${li}: ${data.players[p]}`);
        if (li) {
            li.style = "color: #00aa00;";
            li.children[0].textContent = "✔ " + data.players[p];
        }
    }
    updateTimer = setTimeout(updatePlayerStatus, 1000 /* milliseconds */, statusUrl);
    return updateTimer;
}

async function updateGameStatusOrganizeDashboard(statusUrl) {
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
    const normalPlayerStyle = "";
    const currentPlayerStyle = "color: #00aa00;"
    let totalBids = 0;
    for (pid in data.players) {
        const li = document.getElementById(pid);
        if (li) {
            li.style = (pid == currentPlayer) ? currentPlayerStyle : normalPlayerStyle;
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
    updateTimer = setTimeout(updateGameStatusOrganizeDashboard, 1000 /* milliseconds */, statusUrl);
    return updateTimer;
}

function gameStateName(x) {
    switch (x) {
    case 0: return "Confirming";
    case 1: return "Playing";
    case 2: return "Paused between rounds";
    case 3: return "Done";
    default: return "Error!  script.js and Game.State are out of sync."
    }
}
