async function loadGames() {
    try {
        const response = await fetch("games.json");

        if (!response.ok) {
            throw new Error("Could not load games.json");
        }

        const games = await response.json();

        renderFeatured(games);

    } catch (error) {
        console.error("Game loading error:", error);
    }
}

function renderFeatured(games) {
    const container =
        document.getElementById("featuredGames");

    if (!container) {
        return;
    }

    const featured =
        games.filter(game => game.featured);

    container.innerHTML =
        featured.map(game => {

            return `
                <article class="game-card">

                    <div class="game-card-content">

                        <h3>
                            ${escapeHTML(game.title)}
                        </h3>

                        <p>
                            ${escapeHTML(game.description)}
                        </p>

                        <p>
                            ${escapeHTML(game.category)}
                        </p>

                        <a
                            class="play-button"
                            href="game.html?url=${encodeURIComponent(game.url)}"
                        >
                            Play
                        </a>

                    </div>

                </article>
            `;

        }).join("");
}

function escapeHTML(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

loadGames();
