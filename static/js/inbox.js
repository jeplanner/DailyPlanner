async function save() {
  await fetch("/api/inbox", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      user_id: "demo",
      url: document.getElementById("url").value,
      description: document.getElementById("desc").value
    })
  });

  load();
}

async function load() {
  const res = await fetch("/api/inbox?user_id=demo");
  const data = await res.json();

  const list = document.getElementById("list");
  list.innerHTML = "";

  data.forEach(x => {
    list.innerHTML += `
      <div>
        <a href="${x.url}" target="_blank">${x.title || x.url}</a>
        <div>${x.description || ""}</div>
        <button onclick="fav('${x.id}')">⭐</button>
      </div>
    `;
  });
}

async function fav(id) {
  await fetch(`/api/inbox/${id}/favorite`, { method: "POST" });
  load();
}
await fetch("http://localhost:5000/api/inbox", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({
    user_id: "demo",
    url,
    description
  })
});
load();