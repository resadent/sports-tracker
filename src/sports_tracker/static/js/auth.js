// auth.js — login (form-encoded, as OAuth2PasswordRequestForm requires),
// registration, logout, and the login/register views.
async function login(email, password, rememberMe = false) {
  const body = new URLSearchParams({
    username: email,
    password,
    remember_me: rememberMe ? "true" : "false",
  });
  const res = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || "Login failed");
  }
  setToken(data.access_token, rememberMe);
}

async function register(email, password) {
  await api("POST", "/api/v1/users", { email, password });
}

function logout() {
  clearToken();
  location.hash = "#/login";
}

function renderLogin(app) {
  app.innerHTML = `
    <form class="auth-form panel" id="login-form">
      <h1>Log in</h1>
      <label>Email<input type="email" id="login-email" required autocomplete="username"></label>
      <label>Password<input type="password" id="login-password" required autocomplete="current-password"></label>
      <label class="checkbox-row"><input type="checkbox" id="login-remember" checked> Remember me</label>
      <button type="submit">Log in</button>
      <p class="msg error" id="login-msg"></p>
      <p style="font-size:0.85rem;color:var(--muted)">No account? <a href="#/register">Register</a></p>
    </form>`;

  app.querySelector("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = app.querySelector("#login-msg");
    msg.textContent = "";
    try {
      await login(
        app.querySelector("#login-email").value,
        app.querySelector("#login-password").value,
        app.querySelector("#login-remember").checked,
      );
      location.hash = "#/dashboard";
    } catch (err) {
      msg.textContent = err.message;
    }
  });
}

function renderRegister(app) {
  app.innerHTML = `
    <form class="auth-form panel" id="register-form">
      <h1>Register</h1>
      <label>Email<input type="email" id="reg-email" required autocomplete="username"></label>
      <label>Password (min 8 chars)<input type="password" id="reg-password" minlength="8" required autocomplete="new-password"></label>
      <button type="submit">Register</button>
      <p class="msg error" id="reg-msg"></p>
      <p style="font-size:0.85rem;color:var(--muted)">Have an account? <a href="#/login">Log in</a></p>
    </form>`;

  app.querySelector("#register-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = app.querySelector("#reg-msg");
    msg.textContent = "";
    try {
      await register(
        app.querySelector("#reg-email").value,
        app.querySelector("#reg-password").value,
      );
      // Auto-login after registering — remember the new account by default.
      await login(
        app.querySelector("#reg-email").value,
        app.querySelector("#reg-password").value,
        true,
      );
      location.hash = "#/dashboard";
    } catch (err) {
      msg.textContent = err.message;
    }
  });
}
