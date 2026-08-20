///////////////////dark mode/////////////////////////
const applyTheme = (theme) => {
  const isDark = theme === "dark";
  document.body.classList.toggle("dark-mode", isDark);

  const themeButtons = document.querySelectorAll("#theme-btn, .chat-theme-btn");
  themeButtons.forEach((button) => {
    if (!button) return;
    button.textContent = isDark ? "☀️" : "🌙";
    button.setAttribute(
      "aria-label",
      isDark ? "Switch to light mode" : "Switch to dark mode",
    );
  });
};

const savedTheme = localStorage.getItem("theme") || "light";
applyTheme(savedTheme);

const themeButtons = document.querySelectorAll("#theme-btn, .chat-theme-btn");
themeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const nextTheme = document.body.classList.contains("dark-mode") ? "light" : "dark";
    applyTheme(nextTheme);
    localStorage.setItem("theme", nextTheme);
  });
});

const menuToggle = document.querySelector("#navbar-toggler");
const topbar = document.querySelector(".topbar");
const mainNavLinks = document.querySelectorAll(".main-nav a");

if (menuToggle && topbar) {
  menuToggle.addEventListener("click", () => {
    const isOpen = topbar.classList.toggle("nav-open");
    menuToggle.setAttribute("aria-expanded", String(isOpen));
  });

  mainNavLinks.forEach((link) => {
    link.addEventListener("click", () => {
      topbar.classList.remove("nav-open");
      menuToggle.setAttribute("aria-expanded", "false");
    });
  });
}

const authGatedLinks = document.querySelectorAll(".auth-gated-link");

authGatedLinks.forEach((link) => {
  link.addEventListener("click", (event) => {
    const isLoggedIn = Boolean(
      localStorage.getItem("username") && localStorage.getItem("useremail"),
    );

    if (isLoggedIn) {
      event.preventDefault();
      window.location.href = "chat.html";
      return;
    }

    event.preventDefault();

    document.querySelector(".auth-toast")?.remove();

    const message = document.createElement("div");
    message.className = "auth-toast";
    message.textContent = "Please register or login first to start chatting.";
    document.body.appendChild(message);

    setTimeout(() => {
      window.location.assign("./sign-up.html");
    }, 2500);
  });
});

// function to show the pdf of the topic
function openCV() {
  window.open("low-back-pain.pdf", "_blank");
}

////////////////////////////////////////////////

///typing text//
function typingEffect(elementId, text, speed = 120, delay = 1500) {
  const typingElement = document.getElementById(elementId);
  if (!typingElement) return;
  let index = 0;

  function type() {
    if (index < text.length) {
      typingElement.textContent += text.charAt(index);
      index++;
      setTimeout(type, speed);
    } else {
      setTimeout(() => {
        typingElement.textContent = "";
        index = 0;
        type();
      }, delay);
    }
  }

  type();
}

/////////////////////////////////////////////
// top btn//
const topBtn = document.getElementById ("top");

if (topBtn) {
  topBtn.addEventListener("click", function () {
    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
   
  });
}

