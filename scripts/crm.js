// scripts/crm.js

const db = firebase.firestore();

const leadForm = document.getElementById("leadForm");
const leadTableBody = document.querySelector("#leadTable tbody");
const searchInput = document.getElementById("searchInput");

const statusChart = new Chart(document.getElementById("statusChart"), {
  type: 'doughnut',
  data: {
    labels: ['Lead', 'Prospect', 'Qualified', 'Closed'],
    datasets: [{
      label: 'Lead Status',
      data: [0, 0, 0, 0],
      backgroundColor: ['#0077cc', '#00bcd4', '#ffc107', '#4caf50'],
    }]
  },
  options: { responsive: true, maintainAspectRatio: false }
});

function updateChart() {
  const counts = { Lead: 0, Prospect: 0, Qualified: 0, Closed: 0 };
  db.collection("leads").get().then(snapshot => {
    snapshot.forEach(doc => {
      const status = doc.data().status;
      if (counts[status] !== undefined) counts[status]++;
    });
    statusChart.data.datasets[0].data = Object.values(counts);
    statusChart.update();
  });
}

function loadLeads() {
  db.collection("leads").onSnapshot(snapshot => {
    leadTableBody.innerHTML = "";
    snapshot.forEach(doc => {
      const data = doc.data();
      const row = `<tr>
        <td>${data.name}</td>
        <td>${data.company}</td>
        <td>${data.email}</td>
        <td>${data.phone}</td>
        <td>${data.status}</td>
        <td>${data.lastContacted || "-"}</td>
      </tr>`;
      leadTableBody.innerHTML += row;
    });
    updateChart();
  });
}

leadForm.addEventListener("submit", e => {
  e.preventDefault();
  const name = document.getElementById("name").value.trim();
  const company = document.getElementById("company").value.trim();
  const email = document.getElementById("email").value.trim().toLowerCase();
  const phone = document.getElementById("phone").value.trim();
  const status = document.getElementById("status").value;

  if (!name || !company || !email || !phone) return alert("All fields required");

  db.collection("leads").where("email", "==", email).get().then(query => {
    if (!query.empty) return alert("Lead already exists");
    db.collection("leads").add({
      name, company, email, phone, status,
      lastContacted: new Date().toISOString().split("T")[0]
    });
    leadForm.reset();
  });
});

function exportToCSV() {
  db.collection("leads").get().then(snapshot => {
    let csv = "Name,Company,Email,Phone,Status,Last Contacted\n";
    snapshot.forEach(doc => {
      const d = doc.data();
      csv += `${d.name},${d.company},${d.email},${d.phone},${d.status},${d.lastContacted || "-"}\n`;
    });
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "corecloud-leads.csv";
    a.click();
  });
}

function handleLinkedInUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    const lines = e.target.result.split("\n");
    lines.slice(1).forEach(line => {
      const [name, email, phone, company] = line.split(",");
      if (!name || !email) return;
      db.collection("leads").where("email", "==", email.toLowerCase()).get().then(query => {
        if (query.empty) {
          db.collection("leads").add({
            name, company, email: email.toLowerCase(), phone, status: "Lead",
            lastContacted: new Date().toISOString().split("T")[0]
          });
        }
      });
    });
  };
  reader.readAsText(file);
}

function filterLeads() {
  const filter = searchInput.value.toLowerCase();
  const rows = leadTableBody.querySelectorAll("tr");
  rows.forEach(row => {
    const text = row.innerText.toLowerCase();
    row.style.display = text.includes(filter) ? "" : "none";
  });
}

loadLeads();
