import base64
import requests

class GitHubSync:
    def __init__(self, token: str, repo: str, branch: str = "main"):
        self.token = token
        self.repo = repo
        self.branch = branch
        self.api_base = "https://api.github.com"

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def check_repo(self):
        r = requests.get(f"{self.api_base}/repos/{self.repo}", headers=self.headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            return {"ok": True, "message": "Repositorio accesible", "default_branch": data.get("default_branch")}
        return {"ok": False, "message": f"No pude acceder al repositorio. Status {r.status_code}", "details": r.text[:500]}

    def check_branch(self):
        r = requests.get(f"{self.api_base}/repos/{self.repo}/branches/{self.branch}", headers=self.headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            return {"ok": True, "message": f"Rama {self.branch} encontrada", "commit_sha": data.get("commit", {}).get("sha")}
        return {"ok": False, "message": f"No pude acceder a la rama {self.branch}. Status {r.status_code}", "details": r.text[:500]}

    def verify(self):
        repo_check = self.check_repo()
        if not repo_check["ok"]:
            return {"ok": False, "repo": repo_check, "branch": None}
        branch_check = self.check_branch()
        return {"ok": branch_check["ok"], "repo": repo_check, "branch": branch_check}

    def _get_existing_sha(self, path: str):
        url = f"{self.api_base}/repos/{self.repo}/contents/{path}"
        r = requests.get(url, headers=self.headers, params={"ref": self.branch}, timeout=20)

        if r.status_code == 200:
            return {"ok": True, "sha": r.json().get("sha")}
        if r.status_code == 404:
            return {"ok": True, "sha": None}

        return {
            "ok": False,
            "message": f"No pude consultar archivo existente. Status {r.status_code}",
            "details": r.text[:800],
        }

    def upload_bytes_file(self, path: str, content_bytes: bytes, commit_message: str):
        sha_result = self._get_existing_sha(path)
        if not sha_result["ok"]:
            return sha_result

        url = f"{self.api_base}/repos/{self.repo}/contents/{path}"
        payload = {
            "message": commit_message,
            "content": base64.b64encode(content_bytes).decode("utf-8"),
            "branch": self.branch,
        }

        if sha_result["sha"]:
            payload["sha"] = sha_result["sha"]

        r = requests.put(url, headers=self.headers, json=payload, timeout=30)

        if r.status_code in (200, 201):
            data = r.json()
            commit = data.get("commit", {})
            return {
                "ok": True,
                "message": "Archivo subido correctamente",
                "commit": commit.get("sha"),
                "html_url": commit.get("html_url"),
                "path": path,
            }

        return {
            "ok": False,
            "message": f"No pude subir archivo. Status {r.status_code}",
            "details": r.text[:1000],
        }
