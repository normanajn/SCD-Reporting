# Quickstart Guide

Get SCD Effort Reporting running locally in about 10 minutes. Choose your operating system:

- [macOS](#macos)
- [Linux (Ubuntu / Debian)](#linux-ubuntu--debian)
- [Linux (RHEL / Fedora / Rocky)](#linux-rhel--fedora--rocky)
- [Windows](#windows)

All platforms end at the same place: the app running at <http://localhost:8000>.

---

## macOS

### 1. Install prerequisites

Install [Homebrew](https://brew.sh) if you do not already have it, then:

```bash
brew install python@3.12 node git
```

Verify:

```bash
python3.12 --version   # Python 3.12.x
node --version         # v20.x or later
git --version
```

### 2. Clone and set up

```bash
git clone https://github.com/your-org/SCD-Reporting.git
cd SCD-Reporting

python3.12 -m venv venv
source venv/bin/activate

pip install -r requirements-dev.txt

cd theme/static_src && npm install && cd ../..
```

### 3. Initialise the database

```bash
python manage.py migrate
python manage.py seed_taxonomy
SCD_INITIAL_ADMIN_PASSWORD=devpassword python manage.py seed_admin
```

### 4. Start the server

```bash
python manage.py runserver
```

Open <http://localhost:8000> and log in with `scd-admin@fnal.gov` / `devpassword`.

> **Tailwind watcher (optional):** For CSS hot-reload during frontend work, open a second terminal and run `cd theme/static_src && npm start`. It is not required for general use — the development settings load Tailwind from the Play CDN automatically.

> **AI Summary:** Export `ANTHROPIC_API_KEY=sk-ant-...` in your shell before starting `runserver` to enable the AI Summary feature on the Reports page.

---

## Linux (Ubuntu / Debian)

Tested on Ubuntu 22.04 LTS and 24.04 LTS.

### 1. Install prerequisites

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev \
                   nodejs npm git build-essential
```

If `python3.12` is not available in your distro's package manager, use the [deadsnakes PPA](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa):

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev
```

If `node` is older than v18, install a current release via NodeSource:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

Verify:

```bash
python3.12 --version
node --version
git --version
```

### 2. Clone and set up

```bash
git clone https://github.com/your-org/SCD-Reporting.git
cd SCD-Reporting

python3.12 -m venv venv
source venv/bin/activate

pip install -r requirements-dev.txt

cd theme/static_src && npm install && cd ../..
```

### 3. Initialise the database

```bash
python manage.py migrate
python manage.py seed_taxonomy
SCD_INITIAL_ADMIN_PASSWORD=devpassword python manage.py seed_admin
```

### 4. Start the server

```bash
python manage.py runserver
```

Open <http://localhost:8000> and log in with `scd-admin@fnal.gov` / `devpassword`.

---

## Linux (RHEL / Fedora / Rocky)

Tested on Rocky Linux 9 and Fedora 39.

### 1. Install prerequisites

```bash
sudo dnf install -y python3.12 python3.12-devel nodejs npm git gcc
```

On RHEL 8/9 you may need to enable the AppStream module:

```bash
sudo dnf module enable python312
sudo dnf install -y python3.12 python3.12-devel
```

For Node.js 20+:

```bash
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf install -y nodejs
```

Verify:

```bash
python3.12 --version
node --version
git --version
```

### 2. Clone and set up

```bash
git clone https://github.com/your-org/SCD-Reporting.git
cd SCD-Reporting

python3.12 -m venv venv
source venv/bin/activate

pip install -r requirements-dev.txt

cd theme/static_src && npm install && cd ../..
```

### 3. Initialise the database

```bash
python manage.py migrate
python manage.py seed_taxonomy
SCD_INITIAL_ADMIN_PASSWORD=devpassword python manage.py seed_admin
```

### 4. Start the server

```bash
python manage.py runserver
```

Open <http://localhost:8000> and log in with `scd-admin@fnal.gov` / `devpassword`.

---

## Windows

Two paths are available: native Windows (PowerShell) or WSL 2. WSL 2 is recommended for a smoother experience and is identical to the Linux instructions above once the WSL environment is set up.

### Option A — WSL 2 (recommended)

1. Install WSL 2 with Ubuntu (PowerShell as Administrator):

   ```powershell
   wsl --install
   ```

   Restart when prompted, then open the Ubuntu terminal that appears.

2. Follow the [Linux (Ubuntu / Debian)](#linux-ubuntu--debian) instructions above inside the WSL terminal. The app will be available at <http://localhost:8000> from your Windows browser.

### Option B — Native Windows (PowerShell)

#### 1. Install prerequisites

- **Python 3.12** — download from <https://www.python.org/downloads/>. During install, check **"Add python.exe to PATH"**.
- **Node.js 20 LTS** — download from <https://nodejs.org/en/download>.
- **Git** — download from <https://git-scm.com/download/win>.

Open a new PowerShell window after installing so the PATH changes take effect. Verify:

```powershell
python --version    # 3.12.x
node --version      # v20.x or later
git --version
```

#### 2. Clone and set up

```powershell
git clone https://github.com/your-org/SCD-Reporting.git
cd SCD-Reporting

python -m venv venv
venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt

cd theme\static_src
npm install
cd ..\..
```

> If PowerShell blocks script execution, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` first.

#### 3. Initialise the database

```powershell
python manage.py migrate
python manage.py seed_taxonomy
$env:SCD_INITIAL_ADMIN_PASSWORD="devpassword"; python manage.py seed_admin
```

#### 4. Start the server

```powershell
python manage.py runserver
```

Open <http://localhost:8000> and log in with `scd-admin@fnal.gov` / `devpassword`.

> **AI Summary on Windows:** Set the environment variable before starting the server:
> ```powershell
> $env:ANTHROPIC_API_KEY="sk-ant-..."
> python manage.py runserver
> ```

---

## Next steps

| Task | Where |
|---|---|
| Add projects, categories, groups | `/taxonomy/projects/` (Admin) |
| Invite other users | `/admin-users/` → create accounts and assign roles |
| Submit an effort entry | `/entries/new/` |
| Run a report or AI summary | `/reports/` (Admin / Auditor) |
| View the audit log | `/audit/` (Admin / Auditor) |
| Deploy to production | [docs/deploy-docker.md](deploy-docker.md) |

For production deployments using Docker Compose (any OS with Docker installed), see [docs/deploy-docker.md](deploy-docker.md).
