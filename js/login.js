const API_URL = "http://127.0.0.1:8000";
const form = document.querySelector("#login-form");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const alertLogin = document.getElementById("alertlogin");

async function login(event) {
  event?.preventDefault();
  alertLogin.classList.remove("d-none");
  alertLogin.textContent = "Signing in...";
  try {
    const response = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: emailInput.value.trim(), password: passwordInput.value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Invalid email or password.");
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("username", data.user.name);
    localStorage.setItem("useremail", data.user.email);
    window.location.href = "chat.html";
  } catch (error) {
    alertLogin.textContent = error.message;
  }
}

form?.addEventListener("submit", login);
window.login = login;
