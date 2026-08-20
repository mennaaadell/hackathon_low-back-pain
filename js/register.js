const API_URL = "http://127.0.0.1:8000";
const form = document.querySelector("#register-form");
const nameInput = document.getElementById("name");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const confirmInput = document.getElementById("confirmpassword");
const phoneInput = document.getElementById("number");
const ageInput = document.getElementById("age");
const genderInput = document.getElementById("gender");
const message = document.getElementById("alertregister");

function showValidation(id, valid) {
  const element = document.getElementById(id);
  if (element) element.classList.toggle("d-none", valid);
  return valid;
}

async function register(event) {
  event?.preventDefault();
  const valid = nameInput.value.trim().length >= 2 &&
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailInput.value) &&
    passwordInput.value.length >= 8 && passwordInput.value === confirmInput.value;
  if (!valid) {
    message.textContent = "Please enter a valid name, email, and matching password (8+ characters).";
    message.classList.remove("d-none");
    return;
  }
  message.textContent = "Creating your account...";
  message.classList.remove("d-none");
  try {
    const response = await fetch(`${API_URL}/api/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: nameInput.value.trim(), email: emailInput.value.trim(), password: passwordInput.value,
        phone: phoneInput.value.trim() || null, age: ageInput.value ? Number(ageInput.value) : null,
        gender: genderInput.value || null,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not create account.");
    if (data.access_token) {
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("username", data.user.name);
      localStorage.setItem("useremail", data.user.email);
      window.location.href = "chat.html";
    } else {
      message.textContent = "Account created. Check your email, then log in.";
      setTimeout(() => { window.location.href = "login.html"; }, 1800);
    }
  } catch (error) {
    message.textContent = error.message;
  }
}

form?.addEventListener("submit", register);
window.register = register;
