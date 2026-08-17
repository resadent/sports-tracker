// app.js — hash router + nav, and boot.
const routes = {
  "/login": renderLogin,
  "/register": renderRegister,
  "/dashboard": renderDashboard,
  "/workouts": renderWorkouts,
};

const AUTH_ROUTES = ["/dashboard", "/workouts"];

function currentRoute() {
  const hash = location.hash || "#/dashboard";
  return hash.replace(/^#/, "") || "/dashboard";
}

function render() {
  const path = currentRoute();
  const app = document.getElementById("app");
  const nav = document.getElementById("nav");
  const token = getToken();

  if (token) {
    nav.innerHTML = `
      <a href="#/dashboard">Dashboard</a>
      <a href="#/workouts">Workouts</a>
      <button id="logout-btn">Logout</button>`;
    nav.querySelector("#logout-btn").addEventListener("click", logout);
  } else {
    nav.innerHTML = `
      <a href="#/login">Login</a>
      <a href="#/register">Register</a>`;
  }

  const view = routes[path];
  if (!view) {
    location.hash = token ? "#/dashboard" : "#/login";
    return;
  }

  if (AUTH_ROUTES.includes(path) && !token) {
    location.hash = "#/login";
    return;
  }
  if ((path === "/login" || path === "/register") && token) {
    location.hash = "#/dashboard";
    return;
  }

  app.innerHTML = "";
  view(app);
}

window.addEventListener("hashchange", render);
render();
