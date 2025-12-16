const boardDiv = document.getElementById("board");
const newBtn = document.getElementById("newGame");

let rows = 2, cols = 2;

// Example values (you can randomize)
const values = ["A","A","B","B"];

newBtn.addEventListener("click", async () => {
  await fetch("/api/new", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({rows, cols, values})
  });
  renderBoard(rows, cols);
});

function renderBoard(r, c) {
  boardDiv.innerHTML = "";
  boardDiv.style.display = "grid";
  boardDiv.style.gridTemplateColumns = `repeat(${c}, 80px)`;
  boardDiv.style.gap = "10px";

  for (let i = 0; i < r; i++) {
    for (let j = 0; j < c; j++) {
      const btn = document.createElement("button");
      btn.textContent = "?";
      btn.style.height = "80px";
      btn.addEventListener("click", () => onPick(i, j, btn));
      boardDiv.appendChild(btn);
    }
  }
}

async function onPick(row, col, btn) {
  const res = await fetch("/api/pick", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({row, col})
  });
  const data = await res.json();

  if (data.status !== "ok") {
    alert(data.message);
    return;
  }

  btn.textContent = data.value;

  // If mismatch, you can call resolve after a short delay
  if (data.match === false) {
    setTimeout(async () => {
      await fetch("/api/resolve", { method: "POST" });
      // simplest UI reset: rerender (later you can keep state client-side)
      renderBoard(rows, cols);
    }, 700);
  }
}