function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function save() {
  const url = document.getElementById("url").value.trim();
  const desc = document.getElementById("desc").value.trim();

  if (!url) return;

  await fetch("/api/inbox", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, description: desc }),
  });

  document.getElementById("url").value = "";
  document.getElementById("desc").value = "";
  load();
}

async function load() {
  const res = await fetch("/api/inbox");
  const data = await res.json();

  const list = document.getElementById("list");
  list.innerHTML = "";

  data.forEach((x) => {
    const div = document.createElement("div");
    div.className = "inbox-item";

    const a = document.createElement("a");
    a.href = x.url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = x.title || x.url;

    const desc = document.createElement("div");
    desc.textContent = x.description || "";

    const favBtn = document.createElement("button");
    favBtn.textContent = x.favorite ? "★" : "☆";
    favBtn.onclick = () => fav(x.id);

    div.appendChild(a);
    div.appendChild(desc);
    div.appendChild(favBtn);
    list.appendChild(div);
  });
}

async function fav(id) {
  await fetch(`/api/inbox/${id}/favorite`, { method: "POST" });
  load();
}

async function deleteItem(id) {
  await fetch(`/api/inbox/${id}`, { method: "DELETE" });
  load();
}

load();
