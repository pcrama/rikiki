// my deployment choice (repl.it for playing in family circle) means
// I am not too sure about what host my server will run on.  So I
// prepend it dynamically to the URL:
function hostify_urls(_) {
    const urlPrefix = document.location.origin;
    Array.from(document.getElementsByClassName("hostify")).forEach((item, index, array) => {
        if (!item.innerHTML.startsWith(urlPrefix)) {
            item.innerHTML = urlPrefix + item.innerHTML;
        }
    });
}

let updateTimer = null;

async function updatePlayerStatus(status_url) {
    const response = await fetch(status_url, {
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
    for (p in data.players) {
        const li = document.getElementById(p);
        if (li) {
            li.style = "color: #00ff00;";
            li.children[0].textContent = data.players[p];
        }
    }
    updateTimer = setTimeout(updatePlayerStatus, 1000 /* milliseconds */, status_url);
    return updateTimer;
}
